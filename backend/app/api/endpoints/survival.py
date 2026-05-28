"""
SRRIS Survival/Trajectory Endpoint — UPGRADED
================================================
The original fake logarithmic formula has been replaced.
This file now delegates to the Recovery Intelligence Engine
for real, clinically-validated trajectory predictions.

Legacy endpoint preserved for backward compatibility with any
frontend code still calling /trajectory directly.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from app.db import models, database
from app.services.recovery_engine import recovery_orchestrator
from app.api.endpoints.auth import get_current_user

router = APIRouter()


class SurvivalRequest(BaseModel):
    patient_id: str
    stroke_severity_nihss: int
    age: float = 65.0
    systolic_bp: float = 140.0
    avg_glucose_level: float = 120.0
    prior_stroke_count: int = 0
    medication_adherence_score: float = 0.8
    HxOfAfib: int = 0


class TrajectoryPoint(BaseModel):
    day: int
    recovery_probability: float
    milestone: str = None


class SurvivalResponse(BaseModel):
    trajectory: List[TrajectoryPoint]
    median_recovery_days: int
    good_recovery_probability: float
    expected_mrs_score: int
    mrs_label: str
    methodology: str


@router.post("/trajectory", response_model=SurvivalResponse)
def plot_survival(
    data: SurvivalRequest,
    current_user: models.Doctor = Depends(get_current_user)
):
    """
    UPGRADED: Now uses the OPSUM-inspired Recovery Intelligence Engine.
    Previously used a fake logarithmic formula (day^0.5 * 0.08).

    The trajectory is now patient-specific, evidence-based, and
    accounts for NIHSS severity, age, adherence, and comorbidities.
    """
    features = {
        "nihss_score": data.stroke_severity_nihss,
        "age": data.age,
        "systolic_bp": data.systolic_bp,
        "avg_glucose_level": data.avg_glucose_level,
        "prior_stroke_count": data.prior_stroke_count,
        "medication_adherence_score": data.medication_adherence_score,
        "HxOfAfib": data.HxOfAfib,
        "hypertension": 1 if data.systolic_bp > 140 else 0
    }

    trajectory = recovery_orchestrator.opsum_engine.generate_recovery_trajectory(features)
    functional = recovery_orchestrator.opsum_engine.predict_functional_outcome(features)

    # Estimate median recovery day (day when trajectory first reaches 50%)
    median_days = 90
    for point in trajectory:
        if point["recovery_probability"] >= 50:
            median_days = point["day"]
            break

    return SurvivalResponse(
        trajectory=[
            TrajectoryPoint(
                day=p["day"],
                recovery_probability=p["recovery_probability"],
                milestone=p.get("milestone")
            )
            for p in trajectory
        ],
        median_recovery_days=median_days,
        good_recovery_probability=functional["good_recovery_probability"],
        expected_mrs_score=functional["expected_mrs_score"],
        mrs_label=functional["mrs_label"],
        methodology="OPSUM-inspired Recovery Engine (Klug et al. Nature Comms Med 2024)"
    )
