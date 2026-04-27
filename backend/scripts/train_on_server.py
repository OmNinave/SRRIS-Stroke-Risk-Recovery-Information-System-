"""
SRRIS — Real Data Training Script
===================================
Run this ON THE SERVER where datasets live.
Outputs: .pkl model files → copy only these back to local PC.

Usage (on server):
    source srris_train_env/bin/activate
    python train_on_server.py
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score
from imblearn.over_sampling import SMOTE
from sksurv.ensemble import RandomSurvivalForest

# ─── Dataset Paths (on server) ────────────────────────────────────────────────
BASE = "/mnt/nextcloud-data/omninave/SRRIS_Dataset"
STROKE_CSV       = f"{BASE}/stroke_prediction/healthcare-dataset-stroke-data.csv"
BRAIN_STROKE_CSV = f"{BASE}/stroke_prediction/brain_stroke.csv"
FRAMINGHAM_CSV   = f"{BASE}/stroke_prediction/framingham.csv"
SURVIVAL_CSV     = f"{BASE}/survival_analysis/dataset.csv"

# Output: where to save .pkl files
OUTPUT_DIR = f"{BASE}/trained_models"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 60)
print("SRRIS Real Data Training Pipeline")
print("=" * 60)

# ─── STEP 1: Load & Merge Stroke Datasets ─────────────────────────────────────
print("\n[1/5] Loading stroke datasets...")

# Primary Fedesoriano dataset
df1 = pd.read_csv(STROKE_CSV)
df1 = df1.dropna(subset=['bmi'])
df1['bmi'] = df1['bmi'].fillna(df1['bmi'].median())
df1['gender_enc'] = LabelEncoder().fit_transform(df1['gender'])
df1['smoking_enc'] = LabelEncoder().fit_transform(df1['smoking_status'].fillna('Unknown'))
df1['work_enc'] = LabelEncoder().fit_transform(df1['work_type'])

df1_clean = df1[['age', 'hypertension', 'heart_disease', 'avg_glucose_level',
                  'bmi', 'gender_enc', 'smoking_enc', 'work_enc', 'stroke']].copy()
print(f"  Fedesoriano: {len(df1_clean)} rows, {df1_clean['stroke'].sum()} stroke cases")

# Secondary Brain Stroke dataset
try:
    df2 = pd.read_csv(BRAIN_STROKE_CSV)
    df2['gender_enc'] = LabelEncoder().fit_transform(df2['gender'])
    df2['smoking_enc'] = LabelEncoder().fit_transform(df2['smoking_status'].fillna('Unknown'))
    df2['work_enc'] = LabelEncoder().fit_transform(df2['work_type'])
    df2 = df2.rename(columns={'stroke': 'stroke'})
    df2_clean = df2[['age', 'hypertension', 'heart_disease', 'avg_glucose_level',
                      'bmi', 'gender_enc', 'smoking_enc', 'work_enc', 'stroke']].copy()
    df2_clean = df2_clean.dropna()
    print(f"  Brain Stroke: {len(df2_clean)} rows, {df2_clean['stroke'].sum()} stroke cases")
    # Merge both datasets for larger training set
    df_main = pd.concat([df1_clean, df2_clean], ignore_index=True)
except Exception as e:
    print(f"  Brain Stroke CSV not found or different format, using only Fedesoriano: {e}")
    df_main = df1_clean

print(f"  Combined Total: {len(df_main)} rows")

# ─── STEP 2: Feature Engineering ──────────────────────────────────────────────
print("\n[2/5] Feature engineering & SMOTE balancing...")

# Add NLP score as a synthetic feature (ClinicalBERT outputs this at runtime)
np.random.seed(42)
df_main['nlp_risk_score'] = np.clip(
    0.3 * (df_main['hypertension']) +
    0.2 * (df_main['heart_disease']) +
    0.1 * (df_main['age'] / 100) +
    np.random.normal(0, 0.05, len(df_main)),
    0, 1
)

FEATURES = ['age', 'hypertension', 'heart_disease', 'avg_glucose_level',
            'bmi', 'gender_enc', 'smoking_enc', 'nlp_risk_score']

X = df_main[FEATURES].fillna(df_main[FEATURES].median())
y = df_main['stroke']

print(f"  Class balance before SMOTE — No Stroke: {(y==0).sum()}, Stroke: {(y==1).sum()}")

smote = SMOTE(random_state=42, k_neighbors=5)
X_balanced, y_balanced = smote.fit_resample(X, y)
print(f"  After SMOTE — Total: {len(X_balanced)}, each class: {y_balanced.sum()}")

# ─── STEP 3: Train XGBoost Model ──────────────────────────────────────────────
print("\n[3/5] Training XGBoost Classifier (real clinical data)...")

X_train, X_test, y_train, y_test = train_test_split(
    X_balanced, y_balanced, test_size=0.2, random_state=42, stratify=y_balanced
)

xgb_model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=1,
    use_label_encoder=False,
    eval_metric="logloss",
    random_state=42
)
xgb_model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)

y_pred = xgb_model.predict(X_test)
y_prob = xgb_model.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_prob)
print(f"  AUC-ROC: {auc:.4f}")
print(classification_report(y_test, y_pred, target_names=['No Stroke', 'Stroke']))

# Save XGBoost
xgb_path = f"{OUTPUT_DIR}/stroke_xgb_model.pkl"
joblib.dump(xgb_model, xgb_path)
print(f"  Saved: {xgb_path}")

# ─── STEP 4: SHAP Explainer ───────────────────────────────────────────────────
print("\n[4/5] Computing SHAP TreeExplainer...")
explainer = shap.TreeExplainer(xgb_model)
shap_path = f"{OUTPUT_DIR}/shap_explainer.pkl"
joblib.dump(explainer, shap_path)
print(f"  Saved: {shap_path}")

# ─── STEP 5: Survival Model (RandomSurvivalForest) ───────────────────────────
print("\n[5/5] Training Random Survival Forest (RSF)...")

try:
    surv_df = pd.read_csv(SURVIVAL_CSV)
    print(f"  Survival dataset columns: {list(surv_df.columns)}")

    # Try to build time-to-event structure from real hospital mortality data
    # Adapt column names based on what's available
    if 'hospital_death' in surv_df.columns:
        event_col = 'hospital_death'
        time_col = 'los' if 'los' in surv_df.columns else surv_df.columns[5]
    else:
        # Fallback: use available numeric columns
        event_col = surv_df.columns[-1]
        time_col = surv_df.columns[-2]

    surv_df = surv_df.dropna(subset=[event_col, time_col])
    surv_df[event_col] = surv_df[event_col].astype(bool)
    surv_df[time_col] = pd.to_numeric(surv_df[time_col], errors='coerce').fillna(30)
    surv_df = surv_df[surv_df[time_col] > 0]

    # Use available numeric features for survival
    numeric_cols = surv_df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in [event_col, time_col]][:8]

    X_surv = surv_df[numeric_cols].fillna(surv_df[numeric_cols].median())
    y_surv = np.array(
        list(zip(surv_df[event_col], surv_df[time_col])),
        dtype=[('Status', '?'), ('Survival_in_days', '<f8')]
    )

    rsf = RandomSurvivalForest(n_estimators=100, max_depth=5, n_jobs=-1, random_state=42)
    rsf.fit(X_surv, y_surv)

    rsf_path = f"{OUTPUT_DIR}/survival_rsf_model.pkl"
    joblib.dump(rsf, rsf_path)
    print(f"  Saved: {rsf_path}")

except Exception as e:
    print(f"  Survival model fallback to synthetic (real data error: {e})")
    # Generate synthetic survival data from the XGBoost training set
    surv_y = np.array(
        list(zip(y_balanced.astype(bool), [90 - np.random.randint(0, 85) if s else 90 for s in y_balanced])),
        dtype=[('Status', '?'), ('Survival_in_days', '<f8')]
    )
    rsf = RandomSurvivalForest(n_estimators=100, max_depth=5, n_jobs=-1, random_state=42)
    rsf.fit(X_balanced, surv_y)
    rsf_path = f"{OUTPUT_DIR}/survival_rsf_model.pkl"
    joblib.dump(rsf, rsf_path)
    print(f"  Saved fallback survival model: {rsf_path}")

print("\n" + "=" * 60)
print("Training Complete!")
print(f"All models saved to: {OUTPUT_DIR}")
print("\nFiles to copy to your local backend/models/ folder:")
for f in os.listdir(OUTPUT_DIR):
    size = os.path.getsize(f"{OUTPUT_DIR}/{f}") / 1024
    print(f"  {f} ({size:.1f} KB)")
print("=" * 60)
print("\nCopy command (run on your local PC):")
print(f"scp apanko@192.168.1.12:{OUTPUT_DIR}/*.pkl 'A:\\Coding Space\\Workspace\\SRRIS\\backend\\models\\'")
