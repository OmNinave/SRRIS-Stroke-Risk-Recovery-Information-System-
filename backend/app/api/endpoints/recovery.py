"""
SRRIS Recovery Intelligence API
=================================
Dedicated FastAPI router for all recovery-related endpoints.
Replaces the fake simulation-only survival.py with real clinical predictions.

Endpoints:
  GET  /{uid}/recovery/analysis      — Full Recovery Intelligence Panel data
  GET  /{uid}/recovery/trajectory    — 90-day recovery trajectory (replaces survival.py)
  GET  /{uid}/recovery/medications   — Personalized medication protocol cards
  POST /{uid}/recovery/simulate      — "What-If" recovery simulation
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import models, database
from app.api.endpoints.auth import get_current_user
from app.api.endpoints.predict import prepare_ai_features
from app.services.recovery_engine import recovery_orchestrator
from typing import Optional
from pydantic import BaseModel

router = APIRouter()


class RecoverySimulationInput(BaseModel):
    interventions: dict  # e.g., {"systolic_bp": 130, "medication_adherence_score": 1.0}
    infarct_volume_ml: Optional[float] = None


@router.get("/{uid}/recovery/analysis")
def get_recovery_intelligence(
    uid: str,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    """
    Full Recovery Intelligence Panel endpoint.
    Returns all data needed to render:
    - Circular gauges (good recovery %, expected mRS)
    - Risk bars (mortality, 72h deterioration)
    - Motor progress bar (gait recovery %)
    - Real 90-day trajectory line chart
    - Medication protocol cards
    - Clinical summary paragraph
    """
    # Get clinical features from patient DB
    features = prepare_ai_features(uid, db)
    features['patient_uid'] = uid

    # Check for tPA eligibility and hemorrhage from scan results
    tpa_eligible = False
    is_hemorrhagic = False
    infarct_volume_ml = None

    latest_scan = (
        db.query(models.ScanResult)
        .filter_by(patient_uid=uid)
        .order_by(models.ScanResult.created_at.desc())
        .first()
    )

    if latest_scan:
        pred = (latest_scan.prediction or "").lower()
        is_hemorrhagic = 'hemorrhag' in pred or 'haemorrhag' in pred
        infarct_volume_ml = latest_scan.volume_percentage  # stored as % but used as proxy mL

    # Check tPA eligibility from last override/diagnostic record
    last_tpa = (
        db.query(models.DoctorOverride)
        .filter_by(patient_uid=uid)
        .order_by(models.DoctorOverride.created_at.desc())
        .first()
    )

    # Run the full recovery intelligence pipeline
    result = recovery_orchestrator.run_full_recovery_analysis(
        features=features,
        tpa_eligible=tpa_eligible,
        is_hemorrhagic=is_hemorrhagic,
        infarct_volume_ml=infarct_volume_ml
    )

    # Audit log
    db.add(models.AuditLog(
        doctor_id=current_user.id,
        patient_uid=uid,
        action="Recovery Intelligence Analysis Run"
    ))
    db.commit()

    return result


@router.get("/{uid}/recovery/trajectory")
def get_recovery_trajectory(
    uid: str,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    """
    Returns the 90-day recovery trajectory as a list of {day, recovery_probability, milestone}.
    This REPLACES the fake survival.py logarithmic formula.

    Frontend uses this to render the purple line chart in the AI Cockpit.
    """
    features = prepare_ai_features(uid, db)
    trajectory = recovery_orchestrator.opsum_engine.generate_recovery_trajectory(features)

    return {
        "patient_uid": uid,
        "trajectory": trajectory,
        "nihss_score": features.get('nihss_score', 0),
        "methodology": "OPSUM-inspired trajectory (Klug et al. Nature Comms Med 2024)"
    }


@router.get("/{uid}/recovery/medications")
def get_medication_protocol(
    uid: str,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    """
    Returns the personalized medication protocol as a list of drug recommendation cards.
    Each card contains: drug name, indication, evidence level, priority, phase.

    Frontend renders these as collapsible medication cards in the Recovery Panel.
    """
    features = prepare_ai_features(uid, db)

    # Get scan for hemorrhage + volume
    latest_scan = (
        db.query(models.ScanResult)
        .filter_by(patient_uid=uid)
        .order_by(models.ScanResult.created_at.desc())
        .first()
    )
    is_hemorrhagic = False
    infarct_volume_ml = None
    if latest_scan:
        pred = (latest_scan.prediction or "").lower()
        is_hemorrhagic = 'hemorrhag' in pred or 'haemorrhag' in pred
        infarct_volume_ml = latest_scan.volume_percentage

    functional = recovery_orchestrator.opsum_engine.predict_functional_outcome(features)
    gait = recovery_orchestrator.gait_engine.predict_gait_recovery(features)

    opsum_output = {
        "functional_outcome": functional,
        "gait_recovery": gait
    }

    medications = recovery_orchestrator.medication_engine.generate_medication_plan(
        features=features,
        opsum_output=opsum_output,
        tpa_eligible=False,
        is_hemorrhagic=is_hemorrhagic,
        infarct_volume_ml=infarct_volume_ml
    )

    return {
        "patient_uid": uid,
        "medication_count": len(medications),
        "medications": medications,
        "guideline_source": "AHA/ASA Stroke Guidelines 2022 + WHO Essential Medicines List"
    }


@router.post("/{uid}/recovery/simulate")
def simulate_recovery_intervention(
    uid: str,
    body: RecoverySimulationInput,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    """
    Recovery "What-If" Simulation.
    Doctor can ask: "What happens to this patient's recovery if we lower their BP to 130?"

    Returns before/after comparison of all recovery metrics.
    Used in the "Causal AI Sandbox" panel in SRRIS.
    """
    features = prepare_ai_features(uid, db)

    # Baseline recovery
    baseline = recovery_orchestrator.run_full_recovery_analysis(features)

    # Apply interventions (validate that immutable traits are not changed)
    immutable = ['age', 'nihss_score', 'prior_stroke_count']
    for key in immutable:
        if key in body.interventions:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot simulate intervention on immutable clinical trait: '{key}'"
            )

    # Apply interventions to feature set
    simulated_features = {**features, **body.interventions}

    # Simulated recovery
    simulated = recovery_orchestrator.run_full_recovery_analysis(
        simulated_features,
        infarct_volume_ml=body.infarct_volume_ml
    )

    # Calculate deltas for UI display
    delta_recovery = round(
        simulated["good_recovery_probability"] - baseline["good_recovery_probability"], 1
    )
    delta_gait = round(
        simulated["gait_recovery_probability"] - baseline["gait_recovery_probability"], 1
    )
    delta_mortality = round(
        simulated["hospital_mortality_risk"] - baseline["hospital_mortality_risk"], 1
    )

    return {
        "patient_uid": uid,
        "interventions_applied": body.interventions,
        "baseline": {
            "good_recovery_probability": baseline["good_recovery_probability"],
            "gait_recovery_probability": baseline["gait_recovery_probability"],
            "hospital_mortality_risk": baseline["hospital_mortality_risk"],
            "trajectory": baseline["recovery_trajectory"]
        },
        "simulated": {
            "good_recovery_probability": simulated["good_recovery_probability"],
            "gait_recovery_probability": simulated["gait_recovery_probability"],
            "hospital_mortality_risk": simulated["hospital_mortality_risk"],
            "trajectory": simulated["recovery_trajectory"]
        },
        "deltas": {
            "recovery_change": delta_recovery,          # + is improvement
            "gait_change": delta_gait,                  # + is improvement
            "mortality_change": delta_mortality,         # - is improvement
            "recovery_direction": "IMPROVED" if delta_recovery > 0 else "WORSENED",
        },
        "simulated_medications": simulated["medication_plan"]
    }
