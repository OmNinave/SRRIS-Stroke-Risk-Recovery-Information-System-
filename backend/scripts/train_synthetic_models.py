import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import joblib
import os
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score
from imblearn.over_sampling import SMOTE
from sksurv.ensemble import RandomSurvivalForest

# Ensure models directory exists
os.makedirs("models", exist_ok=True)

print("Synthesizing patient data for High-Fidelity V5 model learning...")

# Generate 2500 synthetic stroke profiles
np.random.seed(42)
n = 2500

# 12 Target Features
age = np.random.uniform(40, 95, n)
hypertension = np.random.binomial(1, 0.5, n)
heart_disease = np.random.binomial(1, 0.3, n)
glucose = np.random.normal(130, 40, n)
bmi = np.random.normal(28, 6, n)
systolic_bp = np.random.normal(140, 25, n)
prior_stroke_count = np.random.poisson(0.3, n)
days_since_last_stroke = np.where(prior_stroke_count > 0, np.random.randint(30, 3650, n), 9999)
medication_adherence_score = np.random.uniform(0.3, 1.0, n)
inr_value = np.random.normal(1.2, 0.4, n)
is_on_anticoagulants = np.random.binomial(1, 0.25, n)
platelet_count = np.random.normal(250000, 50000, n)

# Real risk formula based on physiological weights
risk_logit = (
    (age/100) * 2.5 + 
    (bmi/50) * 1.5 + 
    (glucose/200) * 2.0 + 
    (systolic_bp/200) * 3.0 + 
    hypertension * 2.5 + 
    heart_disease * 2.0 + 
    prior_stroke_count * 3.5 - 
    medication_adherence_score * 2.0 +
    (inr_value > 2.0) * 1.5 - 
    is_on_anticoagulants * 1.0 - 
    11.0 # Bias adjustment
)

probs = 1 / (1 + np.exp(-risk_logit))
stroke = np.random.binomial(1, probs)

df = pd.DataFrame({
    'age': age,
    'hypertension': hypertension,
    'heart_disease': heart_disease,
    'avg_glucose_level': glucose,
    'bmi': bmi,
    'systolic_bp': systolic_bp,
    'prior_stroke_count': prior_stroke_count,
    'days_since_last_stroke': days_since_last_stroke,
    'medication_adherence_score': medication_adherence_score,
    'inr_value': inr_value,
    'is_on_anticoagulants': is_on_anticoagulants,
    'platelet_count': platelet_count,
    'stroke': stroke
})

X = df.drop('stroke', axis=1)
y = df['stroke']

print(f"\nOriginal Dataset Shape: {X.shape}, Stroke Cases: {y.sum()}")

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# SMOTE Balancing on Training Set Only (prevent data leakage)
smote = SMOTE(random_state=42)
X_train_bal, y_train_bal = smote.fit_resample(X_train, y_train)
print(f"Balanced Training Shape: {X_train_bal.shape}, Stroke Cases: {y_train_bal.sum()}")

# ---- 5-Fold Cross Validation for XGBoost ----
print("\n[Executing 5-Fold Cross-Validation Protocol...]")
kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_auc_scores = []

for fold, (train_idx, val_idx) in enumerate(kf.split(X_train_bal, y_train_bal)):
    X_f_train, X_f_val = X_train_bal.iloc[train_idx], X_train_bal.iloc[val_idx]
    y_f_train, y_f_val = y_train_bal.iloc[train_idx], y_train_bal.iloc[val_idx]
    
    model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, eval_metric="logloss", use_label_encoder=False)
    model.fit(X_f_train, y_f_train)
    
    preds = model.predict_proba(X_f_val)[:, 1]
    cv_auc_scores.append(roc_auc_score(y_f_val, preds))

print(f"5-Fold CV AUROC Mean: {np.mean(cv_auc_scores):.4f} (+/- {np.std(cv_auc_scores):.4f})")

# ---- Final Model Training ----
xgb_model = xgb.XGBClassifier(n_estimators=150, max_depth=5, learning_rate=0.05, random_state=42, eval_metric="logloss")
xgb_model.fit(X_train_bal, y_train_bal)

# ---- Evaluation on Test Set ----
y_pred_probs = xgb_model.predict_proba(X_test)[:, 1]
y_pred_class = xgb_model.predict(X_test)

print("\n--- TEST SET EVALUATION METRICS ---")
print(f"Accuracy:  {accuracy_score(y_test, y_pred_class):.4f}")
print(f"Precision: {precision_score(y_test, y_pred_class):.4f}")
print(f"Recall:    {recall_score(y_test, y_pred_class):.4f}")
print(f"F1-Score:  {f1_score(y_test, y_pred_class):.4f}")
print(f"AUROC:     {roc_auc_score(y_test, y_pred_probs):.4f}")
print("-----------------------------------")

# Save XGBoost
xgb_path = "models/stroke_xgb_model.pkl"
joblib.dump(xgb_model, xgb_path)
print(f"✓ Saved Optimized XGBoost Model to {xgb_path}")

# Calculate SHAP Explainer
explainer = shap.TreeExplainer(xgb_model)
joblib.dump(explainer, "models/shap_explainer.pkl")
print("✓ Saved SHAP Interpretability Core")

# ---- Train Random Survival Forest ----
print("\n[Training Random Survival Forest (Recovery Trajectory)...]")
survival_days = []
for i in range(len(X_train_bal)):
    if y_train_bal[i] == 1:
        base_days = 90 - (X_train_bal.iloc[i]['age']/100)*20 - (X_train_bal.iloc[i]['systolic_bp']/200)*15
        survival_days.append(max(5, base_days + np.random.normal(0, 10)))
    else:
        survival_days.append(90)

surv_y = np.array(
    list(zip(y_train_bal.astype(bool), survival_days)), 
    dtype=[('Status', '?'), ('Survival_in_days', '<f8')]
)

rsf = RandomSurvivalForest(n_estimators=100, max_depth=5, min_samples_split=10, min_samples_leaf=5, n_jobs=-1, random_state=42)
rsf.fit(X_train_bal, surv_y)

rsf_path = "models/survival_rsf_model.pkl"
joblib.dump(rsf, rsf_path)
print(f"✓ Saved Advanced RSF Model to {rsf_path} (File size varies by n_estimators)")

print("\n🚀 All Pipeline Models Synced to Production Spec.")
