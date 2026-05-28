from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import models, database
from app.api.endpoints.auth import get_current_user
from app.schemas import PredictionInput, OverrideInput
from typing import Dict, Any

router = APIRouter()

def prepare_ai_features(uid: str, db: Session) -> Dict[str, Any]:
    patient = db.query(models.Patient).filter_by(patient_uid=uid).first()
    events = db.query(models.MedicalEvent).filter_by(patient_uid=uid).all()
    meds = db.query(models.Medication).filter_by(patient_uid=uid, is_active=True).all()

    from sqlalchemy import func
    subq = db.query(models.LabResult.test_name, func.max(models.LabResult.result_date).label('max_date')).filter_by(patient_uid=uid).group_by(models.LabResult.test_name).subquery()
    latest_labs = db.query(models.LabResult).join(subq, (models.LabResult.test_name == subq.c.test_name) & (models.LabResult.result_date == subq.c.max_date)).all()

    # Issue 3 Fix: Extract valid float numbers (including negatives and scientific notation)
    import re as _re
    def _parse_lab_value(raw: str) -> float | None:
        match = _re.search(r'-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?', str(raw))
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
        return None

    lab_dict = {}
    for l in latest_labs:
        v = _parse_lab_value(l.value)
        if v is not None:
            lab_dict[l.test_name.lower()] = v
    # Calculate actual age
    import datetime
    today = datetime.date.today()
    age = 60.0
    if patient and patient.date_of_birth:
        try:
            dob = datetime.datetime.strptime(patient.date_of_birth, '%Y-%m-%d').date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except ValueError:
            pass

    # Calculate required features
    stroke_events = [e for e in events if e.event_type == 'stroke_event']

    # Adherence
    from app.services.summary_engine import count_missed_followups
    missed = count_missed_followups(events)
    adherence_score = 1.0 - (min(missed, 10) / 10.0)

    # Check DAMA
    dama_events = [e for e in events if 'dama' in e.title.lower() or 'against medical advice' in str(e.description).lower()]
    if dama_events:
        adherence_score = 0.0  # Immediate 0 adherence if patient left against medical advice

    # Days since last stroke
    days_since_stroke = 9999
    if stroke_events:
        last_stroke_date = max([e.event_date for e in stroke_events])
        days_since_stroke = (datetime.datetime.utcnow() - last_stroke_date).days

    # Chronic bools
    chronics = set([e.title.lower() for e in events if e.event_type == 'diagnosis'])
    has_hypertension = 1 if any('hypertension' in c for c in chronics) else 0
    has_heart_disease = 1 if any('heart disease' in c or 'cad' in c for c in chronics) else 0

    # Anticoagulants
    anticoag_drugs = ['warfarin','apixaban','rivaroxaban','dabigatran','heparin']
    is_on_anticoag = 1 if any(any(d in m.drug_name.lower() for d in anticoag_drugs) for m in meds) else 0

    # ── BUG FIX 0.1: Smoking — parse real EHR history, NOT hypertension ──
    smoking_keywords = ['smokes', 'smoker', 'tobacco', 'formerly smoked', 'ex-smoker', 'cigarette']
    smoking_cessation_drugs = ['varenicline', 'champix', 'chantix', 'nicotine', 'bupropion', 'zyban']
    has_smoking_event = any(
        any(kw in str(e.description).lower() or kw in e.title.lower() for kw in smoking_keywords)
        for e in events
    )
    has_smoking_med = any(
        any(d in m.drug_name.lower() for d in smoking_cessation_drugs) for m in meds
    )
    has_smoking = 1 if (has_smoking_event or has_smoking_med) else 0

    # ── BUG FIX 0.3: Afib & Seizure — extract from EHR instead of hardcoding 0 ──
    afib_drugs = ['warfarin', 'apixaban', 'rivaroxaban', 'dabigatran', 'digoxin', 'amiodarone']
    afib_keywords = ['atrial fibrillation', 'afib', ' af ', 'a.fib', 'flutter']
    seizure_keywords = ['seizure', 'epilepsy', 'convulsion', 'epileptic', 'status epilepticus']

    has_afib = 1 if (
        any(any(d in m.drug_name.lower() for d in afib_drugs) for m in meds) or
        any(any(kw in str(e.description).lower() or kw in e.title.lower() for kw in afib_keywords) for e in events)
    ) else 0

    has_seizure = 1 if any(
        any(kw in str(e.description).lower() or kw in e.title.lower() for kw in seizure_keywords)
        for e in events
    ) else 0

    packet = {
        # Original ai_engine keys
        "age": float(age),
        "gender": patient.gender if patient else "male",
        "systolic_bp": lab_dict.get('systolic_bp', 120.0),
        "avg_glucose_level": lab_dict.get('glucose', 100.0),
        "bmi": lab_dict.get('bmi', 25.0),
        "hypertension": has_hypertension,
        "heart_disease": has_heart_disease,
        # BUG FIX 0.1: smoking_status now from real EHR parse
        "smoking_status": "smokes" if has_smoking else "never smoked",
        "prior_stroke_count": len(stroke_events),
        "days_since_last_stroke": days_since_stroke,
        "medication_adherence_score": adherence_score,
        "inr_value": lab_dict.get('inr', 1.0),
        "is_on_anticoagulants": is_on_anticoag,
        "platelet_count": lab_dict.get('platelet count', 250000),
        "nihss_score": max([e.nihss_score for e in events if e.nihss_score is not None] + [0]),
        # BUG FIX 0.2: LKN safe default = 99h (forces tPA ineligible) instead of 3.5h (forces eligible)
        "lkn_hours": 99.0,

        # diagnostic_engine specific keys mapping
        "systolic": lab_dict.get('systolic_bp', 120.0),
        "diastolic": lab_dict.get('diastolic_bp', 80.0),
        "glucose": lab_dict.get('glucose', 100.0),
        "cholesterol": lab_dict.get('cholesterol', 180.0),
        # BUG FIX 0.1: smoking now from real EHR, not hypertension
        "smoking": has_smoking,
        "prior_strokes": len(stroke_events),
        # BUG FIX 0.3: Afib and Seizure now from real EHR
        "HxOfAfib": has_afib,
        "HxOfSeizure": has_seizure,
        # v2.0 Extensions
        "current_medications": ", ".join([m.drug_name for m in meds])
    }

    # Attempt to parse explicit LKN hours from deep stroke event descriptions
    for e in stroke_events:
        import re
        match = re.search(r'LKN\s*[:=]?\s*(\d+(?:\.\d+)?)', str(e.description))
        if match:
            packet["lkn_hours"] = float(match.group(1))
            break

    return packet

# BUG FIX 0.5: Analyze endpoint now requires authentication
@router.get("/{uid}/analyze")
def run_diagnostic_pipeline(
    uid: str,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    """Full AI diagnostic pipeline. Requires authenticated doctor session."""
    clinical_data = prepare_ai_features(uid, db)

    # BUG FIX 0.5: Audit log — record who triggered the diagnostic run
    db.add(models.AuditLog(
        doctor_id=current_user.id,
        patient_uid=uid,
        action="Initiated Full AI Diagnostic Pipeline"
    ))
    db.commit()

    from fastapi.responses import StreamingResponse
    import json

    def event_stream():
        from app.services.ai_engine import ai_engine
        pipeline_results = ai_engine.run_full_diagnostic_pipeline(clinical_data)
        for stage in pipeline_results:
            yield f"data: {json.dumps(stage)}\n\n"
            import time
            time.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.post("/{uid}/override")
def override_ai_recommendation(
    uid: str,
    override: OverrideInput,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    db_override = models.DoctorOverride(
        patient_uid=uid,
        doctor_id=current_user.id,
        ai_recommendation=override.ai_recommendation,
        doctor_decision=override.doctor_decision,
        override_reason=override.override_reason,
        was_overridden=True
    )
    db.add(db_override)
    db.commit()
    db.refresh(db_override)

    # Audit log
    db.add(models.AuditLog(doctor_id=current_user.id, patient_uid=uid, action=f"Overrode AI: {override.override_reason}"))
    db.commit()

    return db_override
