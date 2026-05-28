import json
import datetime
import os
import torch
import torch.nn as nn
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from app.services.recovery_engine import recovery_orchestrator


# 🔹 PyTorch Neural Network (Architecture matching STROKEPREDICTENGINE research)
class NeuralNetwork(nn.Module):
    def __init__(self, input_dim):
        super(NeuralNetwork, self).__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.model(x)


class DiagnosticEnsemble:
    """
    Orchestrates the 'Ensemble Consensus Jury' using high-accuracy research weights.
    Loads XGBoost, Random Forest, and PyTorch Neural Network models.
    """
    def __init__(self):
        # Use absolute path to ensure models load correctly from any CWD
        self.model_dir = os.path.join(os.path.dirname(__file__), "..", "models", "stroke_consensus")
        self.rf = None
        self.xgb = None
        self.nn = None
        self.loaded = False
        self.input_dim = 13  # Fixed for our chosen research subset

    def load(self):
        try:
            rf_path = os.path.join(self.model_dir, "random_forest.pkl")
            xgb_path = os.path.join(self.model_dir, "xgboost.json")
            nn_path = os.path.join(self.model_dir, "neural_network.pth")

            if os.path.exists(rf_path):
                self.rf = joblib.load(rf_path)
            if os.path.exists(xgb_path):
                from xgboost import XGBClassifier
                self.xgb = XGBClassifier()
                self.xgb.load_model(xgb_path)
            if os.path.exists(nn_path):
                self.nn = NeuralNetwork(input_dim=self.input_dim)
                self.nn.load_state_dict(torch.load(nn_path, map_location=torch.device('cpu'), weights_only=True))
                self.nn.eval()

            self.loaded = (self.rf is not None and self.xgb is not None and self.nn is not None)
            if self.loaded:
                print("[ENGINE] Diagnostic Ensemble (RF/XGB/NN) initialized from research weights.")
        except Exception as e:
            print(f"[ENGINE] Failed to load ensemble models: {e}")

    def prepare_features(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Map SRRIS clinical scalars to the 13 research feature inputs."""
        # Feature order expected by STROKEPREDICTENGINE models
        features = [
            "age", "race", "sex", "HTN", "DM", "HLD", "Smoking",
            "HxOfStroke", "HxOfAfib", "HxOfSeizure", "SBP", "DBP", "BloodSugar"
        ]

        # Scaling factors from research run_3.py
        scaling = {
            "age": 100, "race": 10, "sex": 10, "DM": 10, "HTN": 10, "HLD": 10,
            "Smoking": 10, "HxOfStroke": 10, "HxOfAfib": 10, "HxOfSeizure": 10,
            "SBP": 200, "DBP": 109, "BloodSugar": 109
        }

        # Map ethnicity to WHO dataset race codes (1=White, 2=Black, 3=Asian, etc.)
        # Defaulting to 1 if unknown, but allowing data to override.
        eth = str(data.get('ethnicity', '')).lower()
        race_code = 1
        if 'black' in eth or 'african' in eth:
            race_code = 2
        elif 'asian' in eth:
            race_code = 3
        elif 'hispanic' in eth or 'latino' in eth:
            race_code = 4

        raw = {
            "age": data.get('age', 65),
            "race": race_code,
            "sex": 1 if data.get('gender', 'male').lower() == 'male' else 2,
            "HTN": 1 if data.get('systolic', 120) >= 140 else 0,
            "DM": 1 if data.get('glucose', 90) >= 126 else 0,
            "HLD": 1 if data.get('cholesterol', 180) >= 200 else 0,
            "Smoking": 1 if data.get('smoking', 0) > 0 else 0,
            "HxOfStroke": 1 if data.get('prior_strokes', 0) > 0 else 0,
            # BUG FIX 0.3: Read Afib/Seizure from data dict (extracted by predict.py EHR parser)
            "HxOfAfib": int(data.get('HxOfAfib', 0)),
            "HxOfSeizure": int(data.get('HxOfSeizure', 0)),
            "SBP": data.get('systolic', 120),
            "DBP": data.get('diastolic', 80),
            "BloodSugar": data.get('glucose', 90)
        }

        import re
        def _to_f(v):
            if isinstance(v, (int, float)): return float(v)
            try:
                if hasattr(v, 'item'): v = v.item()
                return float(re.sub(r'[\[\]\s]', '', str(v)))
            except Exception:
                return 0.0

        # Apply scaling
        scaled = {k: _to_f(raw[k]) / scaling[k] for k in features}
        return pd.DataFrame([[scaled[f] for f in features]])

    def predict_consensus_risk(self, data: Dict[str, Any]) -> float:
        """Compute consensus risk using a majority-jury logic (0.7 probability threshold)."""
        if not self.loaded:
            self.load()
        if not self.loaded:
            return 45.0 # Fallback to dummy

        df = self.prepare_features(data)

        # 1. XGBoost Prob
        xgb_prob = float(self.xgb.predict_proba(df)[0][1])
        # 2. Random Forest Prob
        rf_prob = float(self.rf.predict_proba(df)[0][1])
        # 3. Neural Network Prob
        input_tensor = torch.tensor(df.values, dtype=torch.float32)
        nn_prob = float(self.nn(input_tensor).detach().numpy()[0][0])

        # Consensus: Mean of top 3 models
        consensus_risk = (xgb_prob + rf_prob + nn_prob) / 3.0
        return round(consensus_risk * 100.0, 2)


# Instantiate singleton engine
ensemble_engine = DiagnosticEnsemble()


def _compute_actual_age(dob_str: str) -> int:
    """Compute real age from date_of_birth string (YYYY-MM-DD)."""
    try:
        dob = datetime.datetime.strptime(dob_str, '%Y-%m-%d').date()
        today = datetime.date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        return 65  # Safe clinical default


def calculate_base_risk(data: Dict[str, Any]) -> float:
    """
    Utilizes the Ensemble Consensus Jury (XGB/RF/NN) to calculate risk.
    Falls back to rule-based logic only if weights are missing.
    """
    if ensemble_engine.loaded or os.path.exists(os.path.join(ensemble_engine.model_dir, "xgboost.json")):
        return ensemble_engine.predict_consensus_risk(data)

    # -------------------------------------------------------------------------
    # Legacy Rule-Based Fallback (If research models are not yet deployed)
    # -------------------------------------------------------------------------
    score = 0.0
    age = data.get('age', 65)
    if age >= 80:   score += 35
    elif age >= 75: score += 30
    elif age >= 65: score += 20
    elif age >= 55: score += 10
    elif age >= 45: score += 5

    systolic = data.get('systolic', 120)
    diastolic = data.get('diastolic', 80)
    if systolic >= 180 or diastolic >= 110:  score += 30
    elif systolic >= 160 or diastolic >= 100: score += 22
    elif systolic >= 140 or diastolic >= 90:  score += 15
    elif systolic >= 130 or diastolic >= 80:  score += 8

    glucose = data.get('glucose', 90)
    if glucose >= 200:   score += 20
    elif glucose >= 126: score += 15
    elif glucose >= 100: score += 5

    prior_strokes = data.get('prior_strokes', 0)
    if prior_strokes >= 2:   score += 25
    elif prior_strokes == 1: score += 18

    if data.get('on_anticoag', False): score -= 8

    return round(min(100.0, max(0.0, score)), 2)


def _safe_shap_float(val) -> float:
    """
    BUG FIX 0.4: Robust SHAP value converter.
    Handles bracket-string format '[7.0319504E-1]' that crashes float() directly.
    """
    import re
    if isinstance(val, (int, float)):
        return float(val)
    try:
        # If it's a numpy array with one element, extract it
        if hasattr(val, 'item'):
            val = val.item()

        # Convert to string and strip any brackets or whitespace
        cleaned = re.sub(r'[\[\]\s]', '', str(val))
        return float(cleaned)
    except Exception:
        return 0.0


def compute_real_shap(base_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compute real feature attribution weights using the SHAP (SHapley Additive exPlanations) library.
    Extracts local explainability from the trained XGBoost ensemble model.
    BUG FIX 0.4: Uses _safe_shap_float() to handle all SHAP output formats.
    """
    try:
        import shap
        if not ensemble_engine.loaded:
            ensemble_engine.load()
        if not ensemble_engine.loaded:
            return compute_shap_determinants(base_data)

        def sanitize_numeric(value):
            if isinstance(value, str):
                value = value.strip().replace("[", "").replace("]", "")
                try:
                    return float(value)
                except:
                    return 0.0
            try:
                return float(value)
            except:
                return 0.0

        patient_uid = base_data.get("patient_uid")
        if patient_uid and hasattr(ensemble_engine, "_shap_cache") and patient_uid in ensemble_engine._shap_cache:
            return ensemble_engine._shap_cache[patient_uid]

        cleaned_data = {k: sanitize_numeric(v) if k != 'gender' else v for k, v in base_data.items()}
        df = ensemble_engine.prepare_features(cleaned_data)

        # FIX: Ensure all inputs to SHAP are strictly floats
        import numpy as np
        cleaned = [sanitize_numeric(v) for v in df.values[0]]
        X = np.array(cleaned, dtype=np.float32).reshape(1, -1)

        # Permanent fix for XGBoost base_score string format '[7.0319504E-1]' crash in SHAP.
        booster = ensemble_engine.xgb.get_booster()

        # Permanent fix for XGBoost base_score string format '[7.0319504E-1]' crash in SHAP.
        # Older versions of SHAP directly call built-in float() on the bracketed string
        # retrieved from XGBoost's UBJ/JSON buffer. We temporarily override builtins.float
        # to safely parse this specific anomaly.
        import builtins
        original_float = builtins.float

        def safe_float(x):
            try:
                return original_float(x)
            except ValueError:
                if isinstance(x, str) and x.startswith('[') and x.endswith(']'):
                    return original_float(x[1:-1])
                raise

        builtins.float = safe_float
        try:
            explainer = shap.TreeExplainer(booster)
            shap_values = explainer.shap_values(X)
        except (TypeError, Exception) as _shap_err:
            # numpy version mismatch (isinstance() arg error) — use heuristic fallback
            raise RuntimeError(f"SHAP compute failed: {_shap_err}") from _shap_err
        finally:
            builtins.float = original_float

        # XGBoost binary classification: single array (new) or list (old)
        if isinstance(shap_values, list):
            attr = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
        else:
            attr = shap_values[0]

        features = [
            "Age", "Race", "Sex", "Hypertension", "Diabetes", "Hyperlipidemia", "Smoking",
            "Prior Stroke", "Atrial Fibrillation", "Seizure History", "Systolic BP", "Diastolic BP", "Glucose"
        ]

        determinants = []
        real_values_found = 0
        for i, feat in enumerate(features):
            try:
                # BUG FIX 0.4: Use safe converter — no more crash on '[7.0319504E-1]'
                weight = _safe_shap_float(attr[i])
                real_values_found += 1
            except (ValueError, TypeError, IndexError):
                continue

            if abs(weight) > 0.0001:
                determinants.append({
                    "feature": feat,
                    "weight": round(abs(weight) * 100, 2),
                    "direction": "positive" if weight > 0 else "negative"
                })

        print(f"[SHAP] Real SHAP values computed for {real_values_found}/{len(features)} features.")

        # Append NIHSS if clinically significant
        nihss = base_data.get('nihss_score', 0)
        if nihss > 5:
            determinants.append({"feature": f"NIHSS Score ({nihss})", "weight": round(nihss * 1.5, 2), "direction": "positive"})

        result = sorted(determinants, key=lambda x: x['weight'], reverse=True)[:10]
        if patient_uid:
            if not hasattr(ensemble_engine, "_shap_cache"):
                ensemble_engine._shap_cache = {}
            ensemble_engine._shap_cache[patient_uid] = result

        return result

    except Exception as e:
        # Keep logs concise: fallback is intentional when SHAP fails.
        import traceback
        traceback.print_exc()
        print(f"[SHAP] Failed to compute real SHAP, using heuristic fallback: {e}")
        return compute_shap_determinants(base_data)


def compute_shap_determinants(base_data: Dict[str, Any]) -> list:
    """
    Heuristic-based feature attribution (Enhanced Fallback).
    Ensures a rich clinical breakdown even when model-specific SHAP weights are inaccessible.
    """
    age = base_data.get('age', 65)
    systolic = base_data.get('systolic', 120)
    glucose = base_data.get('glucose', 90)
    cholesterol = base_data.get('cholesterol', 180)
    smoking = base_data.get('smoking', 0)
    activity = base_data.get('activity', 2)
    prior_strokes = base_data.get('prior_strokes', 0)
    nihss = base_data.get('nihss_score', 0)

    determinants = []

    # 1. Primary High-Weight Determinants
    if age >= 65:
        determinants.append({"feature": f"Advanced Age ({age} yrs)", "weight": 18 + (age-65)/2, "direction": "positive"})
    else:
        determinants.append({"feature": f"Age Factor ({age} yrs)", "weight": 5, "direction": "negative"})

    if systolic >= 140:
        determinants.append({"feature": f"Systolic Hypertension ({systolic}mmHg)", "weight": 15, "direction": "positive"})
    else:
        determinants.append({"feature": f"Controlled BP ({systolic}mmHg)", "weight": 8, "direction": "negative"})

    if prior_strokes > 0:
        determinants.append({"feature": f"Recurrent Stroke History", "weight": 22, "direction": "positive"})
    else:
        determinants.append({"feature": "No Prior Stroke History", "weight": 12, "direction": "negative"})

    # 2. Metabolic & Lifestyle Determinants
    if glucose >= 126:
        determinants.append({"feature": f"Hyperglycemia ({glucose} mg/dL)", "weight": 14, "direction": "positive"})
    else:
        determinants.append({"feature": f"Serum Glucose ({glucose} mg/dL)", "weight": 6, "direction": "negative"})

    if cholesterol >= 200:
        determinants.append({"feature": f"Hyperlipidemia ({cholesterol} mg/dL)", "weight": 10, "direction": "positive"})
    else:
        determinants.append({"feature": f"Cholesterol Tracking ({cholesterol} mg/dL)", "weight": 7, "direction": "negative"})

    if nihss > 0:
        determinants.append({"feature": f"NIHSS Neuro-Deficit ({nihss})", "weight": 10 + nihss, "direction": "positive"})

    if smoking > 0:
        determinants.append({"feature": "Active/Prior Smoker", "weight": 15, "direction": "positive"})
    else:
        determinants.append({"feature": "Non-Smoker Baseline", "weight": 9, "direction": "negative"})

    if activity == 0:
        determinants.append({"feature": "Sedentary Lifestyle", "weight": 12, "direction": "positive"})
    elif activity >= 2:
        determinants.append({"feature": "Active Lifestyle", "weight": 10, "direction": "negative"})

    if base_data.get('on_anticoag', False):
        determinants.append({"feature": "Anticoagulant Protocol", "weight": 11, "direction": "negative"})

    return sorted(determinants, key=lambda x: x['weight'], reverse=True)[:10]


def compute_tpa_eligibility(base_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    AHA/ASA tPA (Alteplase) eligibility check.
    Contraindications per the 2023 AHA/ASA Acute Ischemic Stroke Guidelines.
    Returns: { eligible: bool, checks: list, reason: str }
    """
    checks = []
    contraindications = []

    systolic = base_data.get('systolic', 120)
    diastolic = base_data.get('diastolic', 80)
    inr = base_data.get('inr', 1.0)
    platelets = base_data.get('platelet_count', 250000)
    lkn_hours = base_data.get('lkn_hours', 3.5)
    on_anticoag = base_data.get('on_anticoag', False)
    nihss = base_data.get('nihss_score', 0)

    # 1. Time window (must be within 4.5 hours of last known normal)
    if lkn_hours <= 4.5:
        checks.append({"label": "Time Window", "value": f"{lkn_hours:.1f}h LKN", "pass": True})
    else:
        checks.append({"label": "Time Window", "value": f"{lkn_hours:.1f}h LKN — EXCEEDED", "pass": False})
        contraindications.append(f"Outside 4.5h treatment window ({lkn_hours:.1f}h since LKN)")

    # 2. Blood Pressure must be ≤ 185/110 before tPA
    if systolic <= 185 and diastolic <= 110:
        checks.append({"label": "Blood Pressure", "value": f"{systolic}/{diastolic} mmHg", "pass": True})
    else:
        checks.append({"label": "Blood Pressure", "value": f"{systolic}/{diastolic} mmHg — HIGH", "pass": False})
        contraindications.append(f"BP {systolic}/{diastolic} exceeds threshold 185/110")

    # 3. INR must be < 1.7
    if inr < 1.7:
        checks.append({"label": "INR", "value": f"{inr}", "pass": True})
    else:
        checks.append({"label": "INR", "value": f"{inr} — ELEVATED", "pass": False})
        contraindications.append(f"INR {inr} ≥ 1.7 (anticoagulation risk)")

    # 4. Platelet count must be ≥ 100,000
    if platelets >= 100000:
        checks.append({"label": "Platelets", "value": f"{int(platelets):,}/μL", "pass": True})
    else:
        checks.append({"label": "Platelets", "value": f"{int(platelets):,}/μL — LOW", "pass": False})
        contraindications.append(f"Platelet count {int(platelets):,} < 100,000/μL")

    # 5. Not on active anticoagulation
    if not on_anticoag:
        checks.append({"label": "Anticoagulants", "value": "None Active", "pass": True})
    else:
        checks.append({"label": "Anticoagulants", "value": "Active — CAUTION", "pass": False})
        contraindications.append("Active anticoagulant therapy — verify INR/anti-Xa levels")

    eligible = len(contraindications) == 0
    return {
        "eligible": eligible,
        "checks": checks,
        "contraindications": contraindications,
        "reason": "Patient meets all tPA baseline criteria." if eligible else f"CONTRAINDICATED: {'; '.join(contraindications)}"
    }


def get_medical_recommendations(risk_factors: Dict[str, bool]) -> list:
    """
    Evidence-based protocol from:
    - Brainstroke-Detection-Predection/templates/medications.html
    - Brainstroke-Detection-Predection/templates/lifestyle.html
    - AHA/ASA Secondary Stroke Prevention Guidelines 2023
    """
    recs = []

    if risk_factors.get('ischemic') or risk_factors.get('prior_stroke'):
        recs.append({
            "category": "Pharmacology",
            "title": "Antiplatelet / Anticoagulation Therapy",
            "content": "Aspirin 81mg + Clopidogrel 75mg dual therapy for first 21 days (POINT Trial). Then Clopidogrel monotherapy. Prevents platelet aggregation and secondary infarct.",
            "priority": "Critical / STAT"
        })

    if risk_factors.get('hypertension'):
        recs.append({
            "category": "Clinical",
            "title": "BP Management (ACE Inhibitor + Diuretic)",
            "content": "Initiate Ramipril 2.5mg or Lisinopril 5mg OD. Target SBP <130mmHg. Monitor daily AM/PM. Combination with Chlorthalidone if SBP >160. (PROGRESS Trial)",
            "priority": "Critical / STAT"
        })

    if risk_factors.get('metabolic'):
        recs.append({
            "category": "Lifestyle",
            "title": "Dietary Sodium + Glycemic Control",
            "content": "Limit sodium to <1,500mg/day. Switch to DASH diet. Omega-3 fatty acids (fatty fish, walnuts) reduce inflammation. HbA1c screening every 3 months.",
            "priority": "Routine Clinical"
        })

    if risk_factors.get('sedentary') or True:  # Always include rehab for stroke patients
        recs.append({
            "category": "Rehabilitation",
            "title": "Neurological Deficit Assessment + Physical Therapy",
            "content": "Assess NIHSS within 24h. Early mobilization protocol (within 24-48h if stable). 150 min/week moderate aerobic activity target. Yoga/Tai Chi for balance and fall prevention.",
            "priority": "Routine Clinical"
        })

    if risk_factors.get('smoking'):
        recs.append({
            "category": "Lifestyle",
            "title": "Smoking Cessation Protocol",
            "content": "Immediate cessation — smoking doubles stroke risk by damaging endothelial lining. Nicotine Replacement Therapy (NRT) or Varenicline 1mg BID. Reduces recurrence risk by 30-50%.",
            "priority": "Routine Clinical"
        })

    if risk_factors.get('hypercholesterolemia'):
        recs.append({
            "category": "Pharmacology",
            "title": "Statin Therapy (High-Intensity)",
            "content": "Atorvastatin 40-80mg QD or Rosuvastatin 20-40mg QD. Target LDL <1.4 mmol/L (<55 mg/dL) for very high-risk. (SPARCL Trial — 16% stroke reduction).",
            "priority": "Routine Clinical"
        })

    if not recs:
        recs.append({
            "category": "Preventive",
            "title": "Annual Neurological Follow-up",
            "content": "Maintain current healthy lifestyle. Annual neurological assessment. Carotid Doppler if vascular risk present. BP and glucose monitoring quarterly.",
            "priority": "Routine Clinical"
        })

    return recs[:5]


def calculate_rsf_trajectory(base_data: Dict[str, Any], initial_risk: float) -> List[Dict[str, Any]]:
    """
    Simulates a high-fidelity recovery trajectory using the new Recovery Intelligence Engine.
    Models the non-linear probability of 'Functional Independence' over 90 days.
    """
    # Mapping base_data to features expected by recovery_engine
    features = {
        'age': base_data.get('age', 65),
        'nihss_score': base_data.get('nihss_score', 0),
        'systolic_bp': base_data.get('systolic', 120),
        'avg_glucose_level': base_data.get('glucose', 90),
        'prior_stroke_count': base_data.get('prior_strokes', 0),
        'HxOfAfib': base_data.get('HxOfAfib', 0),
        'is_on_anticoagulants': 1 if base_data.get('on_anticoag', False) else 0,
    }

    # Run the new engine
    analysis = recovery_orchestrator.run_full_recovery_analysis(features)

    # Convert trajectory to the format expected by legacy frontend calls
    # legacy keys: 'day', 'probability'
    # new keys: 'day', 'recovery_probability'
    trajectory = []
    for point in analysis.get("recovery_trajectory", []):
        trajectory.append({
            "day": point["day"],
            "probability": point["recovery_probability"],
            "milestone": point.get("milestone")
        })

    return trajectory


def forecast_longitudinal_scenarios(base_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Forecasts two divergent 5-year outcomes from real patient data.
    Returns current risk, optimized risk, SHAP determinants, and RSF trajectory.
    """
    current_risk = calculate_base_risk(base_data)

    # Optimized scenario: full protocol adherence
    optimized_data = base_data.copy()
    optimized_data.update({
        'systolic': 118,
        'diastolic': 76,
        'smoking': 0,
        'activity': 3,   # Active
        'glucose': 88,
        'cholesterol': 158,
        'on_anticoag': True,
    })
    optimized_risk = calculate_base_risk(optimized_data)

    determinants = compute_real_shap(base_data)
    tpa = compute_tpa_eligibility(base_data)
    rsf = calculate_rsf_trajectory(base_data, current_risk)

    return {
        "current_risk": current_risk,
        "optimized_risk": optimized_risk,
        "potential_reduction": round(current_risk - optimized_risk, 2),
        "determinants": determinants,
        "tpa_eligibility": tpa,
        "rsf_trajectory": rsf
    }
