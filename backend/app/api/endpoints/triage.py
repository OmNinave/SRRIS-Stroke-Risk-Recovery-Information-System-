"""
SRRIS Phase 3 — Triage API Endpoint
Ambulance/EMT triage endpoint using GravitationalKMeans risk clustering.
Route: POST /api/v1/triage/assess
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, root_validator, model_validator
from typing import Optional
import joblib, os, numpy as np
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# ── Input Schema ────────────────────────────────────────────────────
class TriageInput(BaseModel):
    age: float = Field(..., ge=0, le=120, description="Patient age in years")
    systolic_bp: float = Field(..., ge=60, le=300, description="Systolic blood pressure (mmHg)")
    diastolic_bp: float = Field(..., ge=30, le=200, description="Diastolic blood pressure (mmHg)")
    glucose: float = Field(..., ge=30, le=700, description="Blood glucose level (mg/dL)")
    has_hypertension: int = Field(0, ge=0, le=1)
    has_diabetes: int = Field(0, ge=0, le=1)
    prior_stroke: int = Field(0, ge=0, le=1)
    is_conscious: int = Field(1, ge=0, le=1, description="1=conscious, 0=unconscious")
    smoking: int = Field(0, ge=0, le=1)
    heart_disease: int = Field(0, ge=0, le=1)
    response_time_mins: Optional[float] = Field(None, description="ETA to hospital in minutes")

    @model_validator(mode='after')
    def check_bp(self):
        if self.diastolic_bp >= self.systolic_bp:
            raise ValueError('diastolic_bp must be less than systolic_bp')
        return self

# ── Load srris_medical.pkl if available ─────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))
_MODEL_PATH = os.path.join(_BASE, "..", "..", "models", "srris_medical.pkl")
_bundle = None
if os.path.exists(_MODEL_PATH):
    try:
        _bundle = joblib.load(_MODEL_PATH)
        print("[Triage] srris_medical.pkl loaded for triage inference.")
    except Exception as e:
        print(f"[Triage] Warning: could not load srris_medical.pkl: {e}")

def _compute_triage_risk(data: TriageInput) -> dict:
    """
    Compute triage risk using srris_medical if available,
    otherwise use clinical rule-based scoring (validated AHA risk factors).
    """
    # Rule-based clinical score (always computed as reference)
    score = 0.0
    flags = []

    if data.age >= 65:
        score += 25; flags.append("Age >= 65 (major risk)")
    elif data.age >= 55:
        score += 15; flags.append("Age 55-64 (moderate risk)")

    if data.systolic_bp >= 180:
        score += 30; flags.append("Severe hypertension (SBP >= 180)")
    elif data.systolic_bp >= 140:
        score += 15; flags.append("Stage 2 hypertension (SBP >= 140)")

    if data.glucose >= 200:
        score += 20; flags.append("Hyperglycaemia (glucose >= 200)")
    elif data.glucose >= 140:
        score += 10; flags.append("Elevated glucose (140-199)")

    if data.prior_stroke:
        score += 25; flags.append("History of prior stroke")
    if data.has_hypertension:
        score += 10; flags.append("Known hypertension")
    if data.has_diabetes:
        score += 10; flags.append("Known diabetes")
    if data.heart_disease:
        score += 15; flags.append("Heart disease")
    if data.smoking:
        score += 8;  flags.append("Active smoker")
    if not data.is_conscious:
        score += 20; flags.append("CRITICAL: Unconscious")

    # Cap at 100
    rule_score = min(score, 100.0)

    # Try ml model
    ml_score = None
    if _bundle:
        try:
            scaler  = _bundle["scaler"]
            model   = _bundle["model"]
            imp     = _bundle.get("imputer")
            feat_names = _bundle.get("feature_names", [])

            row = {
                "gender": 0,
                "age": data.age,
                "hypertension": data.has_hypertension,
                "heart_disease": data.heart_disease,
                "ever_married": 1 if data.age > 25 else 0,
                "work_type": 0,
                "Residence_type": 1,
                "avg_glucose_level": data.glucose,
                "bmi": 28.0,  # default if not provided
                "smoking_status": data.smoking,
            }
            import pandas as pd
            df_row = pd.DataFrame([row])
            if imp:
                df_row = pd.DataFrame(imp.transform(df_row), columns=list(row.keys()))
            # add interaction features
            df_row['glucose_bmi_ratio']        = df_row['avg_glucose_level'] / (df_row['bmi'] + 1e-6)
            df_row['age_hypertension']         = df_row['age'] * df_row['hypertension']
            df_row['bmi_age_product']          = df_row['bmi'] * df_row['age']
            df_row['is_senior']                = (df_row['age'] > 60).astype(int)
            df_row['heart_senior_interaction'] = df_row['heart_disease'] * df_row['is_senior']
            df_row['age_squared']              = df_row['age'] ** 2
            df_row['glucose_heart']            = df_row['avg_glucose_level'] * df_row['heart_disease']
            df_row['smoke_age_interaction']    = df_row['smoking_status'] * df_row['age']

            if feat_names:
                df_row = df_row.reindex(columns=feat_names, fill_value=0)
            X_sc = scaler.transform(df_row)
            ml_prob = model.predict_proba(X_sc)[0][1] * 100
            ml_score = round(ml_prob, 1)
        except Exception as e:
            print(f"[Triage] ML inference failed: {e}")

    # Final risk = weighted blend
    if ml_score is not None:
        final_score = round(0.6 * ml_score + 0.4 * rule_score, 1)
        method = "ML + Clinical Rules"
    else:
        final_score = round(rule_score, 1)
        method = "Clinical Rules Only"

    # Risk tier
    if final_score >= 70:
        tier = "CRITICAL"
        action = "Activate stroke team NOW. Direct to CT-capable hospital. Consider thrombectomy center."
        priority = 1
    elif final_score >= 45:
        tier = "HIGH"
        action = "Priority transport. Alert stroke unit. Begin BP monitoring."
        priority = 2
    elif final_score >= 25:
        tier = "MODERATE"
        action = "Monitor vitals. Transport within 60 min. Notify ER."
        priority = 3
    else:
        tier = "LOW"
        action = "Standard transport. Document all vitals. Reassess en route."
        priority = 4

    # ETA warning
    eta_warning = None
    if data.response_time_mins and data.response_time_mins > 270:
        eta_warning = "WARNING: ETA exceeds 4.5h tPA window. Thrombectomy may be only option."

    return {
        "risk_score": final_score,
        "risk_tier": tier,
        "priority_level": priority,
        "action": action,
        "flags": flags,
        "rule_based_score": round(rule_score, 1),
        "ml_score": ml_score,
        "method": method,
        "eta_warning": eta_warning
    }


from fastapi import Request

@router.post("/assess")
@limiter.limit("60/minute")
def triage_assess(request: Request, data: TriageInput):
    """
    SRRIS Ambulance Triage Endpoint.
    Input: minimal vitals collectable in an ambulance.
    Output: risk tier, priority level, action recommendation, ETA warning.
    No authentication required — accessible by EMTs in the field.
    """
    result = _compute_triage_risk(data)
    return {
        "status": "OK",
        "patient_summary": {
            "age": data.age,
            "systolic_bp": data.systolic_bp,
            "glucose": data.glucose,
            "is_conscious": bool(data.is_conscious),
        },
        "triage": result
    }


@router.get("/status")
def triage_status():
    """Check if ML model is loaded for triage."""
    return {
        "ml_model_loaded": _bundle is not None,
    }
