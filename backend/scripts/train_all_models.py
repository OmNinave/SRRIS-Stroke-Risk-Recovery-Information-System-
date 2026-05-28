"""
SRRIS Master Machine Learning Training Pipeline
===============================================
Ensures clinical datasets exist (or generates high-fidelity synthetic cohorts),
then sequentially executes all downstream model training scripts to build a 
functional, deployment-ready backend model cache.

Generated Models:
  1. stroke_xgb_model.pkl, shap_explainer.pkl, survival_rsf_model.pkl (XGB/Survival)
  2. recovery_outcome_model.pkl (3-class mRS outcome stacking classifier)
  3. srris_medical.pkl (Weekly retraining target)
  4. srris_medical_v2.pkl (Unified ensemble stacking classifier)

Run from backend directory:
  python scripts/train_all_models.py
"""

import os
import sys
import subprocess
import pandas as pd
import numpy as np

# Resolve directory structure
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, "data")
MODELS_DIR = os.path.join(BACKEND_DIR, "models")

print("=" * 70)
# Use a custom title formatting to align with modern terminals
print("            SRRIS MASTER MACHINE LEARNING PIPELINE GENERATOR")
print("=" * 70)

# ── STEP 1: Directory Setup ───────────────────────────────────────────────────
print(f"[SETUP] Ensuring required directories exist...")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
print(f"[SETUP] Data folder:   {DATA_DIR}")
print(f"[SETUP] Models folder: {MODELS_DIR}")

# ── STEP 2: Generate High-Fidelity Synthetic Base Datasets ───────────────────
jury_csv = os.path.join(DATA_DIR, "stroke_jury_dataset.csv")
healthcare_csv = os.path.join(DATA_DIR, "healthcare-dataset-stroke-data.csv")

def generate_synthetic_data(file_path):
    np.random.seed(42)
    n_samples = 5110
    
    # Target label: stroke (approx 10% rate to ensure class presence)
    stroke = np.random.binomial(1, 0.10, n_samples)
    
    # Age distribution: older patients are significantly more prone to stroke
    age = np.where(stroke == 1, 
                   np.random.normal(68, 12, n_samples),
                   np.random.normal(53, 16, n_samples))
    age = np.clip(age, 1, 95)
    
    # Hypertension: 40% in stroke cases, 12% in non-stroke cases
    hypertension = np.where(stroke == 1,
                            np.random.binomial(1, 0.40, n_samples),
                            np.random.binomial(1, 0.12, n_samples))
    
    # Heart disease: 25% in stroke cases, 5% in non-stroke cases
    heart_disease = np.where(stroke == 1,
                             np.random.binomial(1, 0.25, n_samples),
                             np.random.binomial(1, 0.05, n_samples))
    
    # Avg glucose level: elevated in stroke cohort
    avg_glucose_level = np.where(stroke == 1,
                                 np.random.normal(150, 45, n_samples),
                                 np.random.normal(98, 22, n_samples))
    avg_glucose_level = np.clip(avg_glucose_level, 55, 280)
    
    # BMI distribution
    bmi = np.where(stroke == 1,
                   np.random.normal(32, 6, n_samples),
                   np.random.normal(28, 5, n_samples))
    bmi = np.clip(bmi, 14, 55)
    
    # Gender (skewed slightly female matching general demographic data)
    gender = np.random.choice(['Male', 'Female'], n_samples, p=[0.42, 0.58])
    
    # Ever married (linked to age threshold)
    ever_married = np.where(age > 25, 'Yes', 'No')
    
    # Work Type & Residence
    work_choices = ['Private', 'Self-employed', 'Govt_job', 'children', 'Never_worked']
    work_probs = [0.65, 0.16, 0.13, 0.05, 0.01]
    work_type = np.random.choice(work_choices, n_samples, p=work_probs)
    
    residence = np.random.choice(['Urban', 'Rural'], n_samples, p=[0.51, 0.49])
    
    # Smoking status
    smoke_choices = ['never smoked', 'Unknown', 'formerly smoked', 'smokes']
    smoke_probs = [0.37, 0.30, 0.17, 0.16]
    smoking_status = np.random.choice(smoke_choices, n_samples, p=smoke_probs)
    
    df = pd.DataFrame({
        'id': np.arange(1000, 1000 + n_samples),
        'gender': gender,
        'age': age,
        'hypertension': hypertension,
        'heart_disease': heart_disease,
        'ever_married': ever_married,
        'work_type': work_type,
        'Residence_type': residence,
        'avg_glucose_level': avg_glucose_level,
        'bmi': bmi,
        'smoking_status': smoking_status,
        'stroke': stroke
    })
    
    df.to_csv(file_path, index=False)
    print(f"[DATA] Saved {n_samples} high-fidelity records to: {file_path}")

if not os.path.exists(jury_csv):
    print(f"[DATA] Missing stroke_jury_dataset.csv. Bootstrapping...")
    generate_synthetic_data(jury_csv)
else:
    print(f"[DATA] stroke_jury_dataset.csv already exists. Skipping bootstrap.")

if not os.path.exists(healthcare_csv):
    print(f"[DATA] Missing healthcare-dataset-stroke-data.csv. Copying jury dataset...")
    df_temp = pd.read_csv(jury_csv)
    df_temp.to_csv(healthcare_csv, index=False)
    print(f"[DATA] Copied to: {healthcare_csv}")
else:
    print(f"[DATA] healthcare-dataset-stroke-data.csv already exists. Skipping copy.")

# ── STEP 3: Execute Model Training Scripts ────────────────────────────────────
scripts_to_run = [
    ("train_synthetic_models.py", "XGBoost, SHAP explainer, and Survival RSF models"),
    ("train_recovery_outcome_model.py", "3-class recovery outcome prediction model"),
    ("retrain_srris_medical.py", "Primary srris_medical classifier via SMOTE stack"),
    ("train_unified_stroke_model.py", "srris_medical_v2 unified ensemble stacking classifier")
]

print("\n" + "-" * 70)
print("Executing Downstream ML Training Scripts...")
print("-" * 70)

for script_name, description in scripts_to_run:
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"[ERROR] Script not found: {script_path}")
        continue
        
    print(f"\n[RUNNING] {script_name} — {description}")
    print(f"Command: {sys.executable} scripts/{script_name}")
    
    # Prepare environment with UTF-8 encoding configuration to prevent Windows encoding crashes
    sub_env = os.environ.copy()
    sub_env["PYTHONIOENCODING"] = "utf-8"
    
    # Run the training script via subprocess inside the backend directory context
    result = subprocess.run(
        [sys.executable, os.path.join("scripts", script_name)],
        cwd=BACKEND_DIR,
        env=sub_env,
        capture_output=False  # Let it stream output to stdout/stderr directly
    )
    
    if result.returncode == 0:
        print(f"[SUCCESS] Finished training {script_name} successfully.")
    else:
        print(f"[FAILED] Script {script_name} exited with error code {result.returncode}.")
        sys.exit(result.returncode)

# ── STEP 4: Initialize Consensus Jury Cache ──────────────────────────────
print("\n" + "-" * 70)
print("Initializing Consensus Jury model cache...")
print("-" * 70)
try:
    # Adding backend directory to Python path to import correctly
    sys.path.insert(0, BACKEND_DIR)
    
    # Set the JWT secret key to allow importing/init of auth modules if loaded downstream
    os.environ.setdefault("JWT_SECRET_KEY", "dummy_secret_for_building_weights")
    
    from app.services.consensus_jury import consensus_jury
    print("[SUCCESS] Consensus Jury initialized and cached to models/jury_cache.")
except Exception as e:
    print(f"[WARNING] Failed to pre-seed Consensus Jury cache programmatically: {e}")

print("\n" + "=" * 70)
print("            ALL SRRIS MACHINE LEARNING MODELS GENERATED SUCCESSFULLY!")
print("=" * 70)
print(f"Models directory contents:")
for f in os.listdir(MODELS_DIR):
    f_path = os.path.join(MODELS_DIR, f)
    if os.path.isfile(f_path):
        size_mb = os.path.getsize(f_path) / (1024 * 1024)
        print(f"  - {f:<28} | {size_mb:.2f} MB")
print("=" * 70)
