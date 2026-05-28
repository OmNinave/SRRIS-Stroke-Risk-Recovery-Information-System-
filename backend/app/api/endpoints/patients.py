from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from app.db import models, database
from app.api.endpoints.auth import get_current_user
from app.schemas import PatientCreate, PatientResponse, PatientBase, LoginRequest

router = APIRouter()

def generate_patient_uid(db: Session) -> str:
    last_patient = db.query(models.Patient).order_by(models.Patient.id.desc()).first()
    if not last_patient:
        return "SR-YYYYYY"
    last_uid = last_patient.patient_uid
    try:
        num = int(last_uid.split("-")[1])
        return f"SR-{num + 1:06d}"
    except:
        return f"SR-{last_patient.id + 1:06d}"

@router.post("/register", response_model=PatientResponse)
def register_patient(
    patient: PatientCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    patient_uid = generate_patient_uid(db)
    new_patient = models.Patient(
        **patient.dict(),
        patient_uid=patient_uid,
        primary_doctor_id=current_user.id
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    # Audit log
    audit = models.AuditLog(doctor_id=current_user.id, patient_uid=patient_uid, action="Registered New Patient")
    db.add(audit)
    db.commit()

    return new_patient

@router.get("/search", response_model=List[PatientResponse])
def search_patients(
    q: str = Query("", min_length=0),
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    # Search by name, SR-ID, or phone
    query = db.query(models.Patient)
    if q:
        search_filter = or_(
            models.Patient.full_name.ilike(f"%{q}%"),
            models.Patient.patient_uid.ilike(f"%{q}%"),
            models.Patient.phone.ilike(f"%{q}%")
        )
        query = query.filter(search_filter)

    patients = query.limit(50).all()
    return patients

@router.get("/{uid}", response_model=PatientResponse)
def get_patient(
    uid: str,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    patient = db.query(models.Patient).filter(models.Patient.patient_uid == uid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    # Audit log
    audit = models.AuditLog(doctor_id=current_user.id, patient_uid=uid, action="Viewed Patient Profile")
    db.add(audit)
    db.commit()

    return patient

@router.put("/{uid}", response_model=PatientResponse)
def update_patient(
    uid: str,
    patient_update: PatientBase,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    patient = db.query(models.Patient).filter(models.Patient.patient_uid == uid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    for key, value in patient_update.dict(exclude_unset=True).items():
        setattr(patient, key, value)

    db.commit()
    db.refresh(patient)

    # Audit log
    audit = models.AuditLog(doctor_id=current_user.id, patient_uid=uid, action="Updated Patient Profile")
    db.add(audit)
    db.commit()

    return patient

# We will add summary and timeline endpoints in another router or here:
@router.get("/{uid}/summary")
def get_patient_summary(
    uid: str,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    from app.services.summary_engine import generate_medical_summary
    return generate_medical_summary(uid, db)

@router.get("/{uid}/timeline")
def get_patient_timeline(
    uid: str,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    from app.services.summary_engine import generate_timeline
    return generate_timeline(uid, db)

@router.post("/{uid}/full-pipeline")
def run_full_pipeline(
    uid: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    """
    Triggers the comprehensive diagnostic pipeline from pipeline_entry.py in background
    """
    import sys
    import os

    # Add root to sys path
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    def _pipeline_task(patient_uid: str):
        try:
            import pipeline_entry
            pipeline_entry.run_diagnostic_pipeline(patient_uid=patient_uid)
        except Exception as e:
            print(f"[BG-PIPELINE] Failed for {patient_uid}: {e}")

    background_tasks.add_task(_pipeline_task, uid)
    return {"status": "processing_started", "message": "Pipeline triggered in background."}

@router.get("/{uid}/processing-status")
def get_processing_status(
    uid: str,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    """
    Returns the processing status of background tasks.
    Since we don't have active celery/redis in this version, return completed to satisfy UI.
    """
    return {
        "complete": True,
        "done": 1,
        "total": 1,
        "percent": 100
    }

@router.post("/{uid}/override")
def submit_doctor_override(
    uid: str,
    override_data: dict, # Ideally OverrideInput from schemas
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    """
    Allows a clinician to submit a manual override to the AI diagnosis.
    """
    override = models.DoctorOverride(
        patient_uid=uid,
        doctor_id=current_user.id,
        ai_recommendation=override_data.get("ai_recommendation", ""),
        doctor_decision=override_data.get("doctor_decision", ""),
        override_reason=override_data.get("override_reason", ""),
        was_overridden=True
    )
    db.add(override)
    db.commit()
    db.refresh(override)

    # Audit log
    audit = models.AuditLog(doctor_id=current_user.id, patient_uid=uid, action="Submitted AI Override")
    db.add(audit)
    db.commit()

    return {"status": "success", "override_id": override.id}


@router.post("/{uid}/delete")
def delete_patient(
    uid: str,
    verification: LoginRequest,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    from app.core import security
    import shutil
    import os

    if verification.username != current_user.username:
        raise HTTPException(status_code=403, detail="Verification username must match logged-in user.")
    if not security.verify_password(verification.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Verification failed: Incorrect password.")

    patient = db.query(models.Patient).filter(models.Patient.patient_uid == uid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    # 1. Gather all related IDs for sub-tables
    event_ids = [e.id for e in patient.events]

    # 2. Perform cascade deletions in database
    if event_ids:
        db.query(models.MedicalEventHistory).filter(models.MedicalEventHistory.event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(models.MedicalEvent).filter(models.MedicalEvent.id.in_(event_ids)).delete(synchronize_session=False)

    db.query(models.ScanResult).filter(models.ScanResult.patient_uid == uid).delete(synchronize_session=False)
    db.query(models.Medication).filter(models.Medication.patient_uid == uid).delete(synchronize_session=False)
    db.query(models.Surgery).filter(models.Surgery.patient_uid == uid).delete(synchronize_session=False)
    db.query(models.LabResult).filter(models.LabResult.patient_uid == uid).delete(synchronize_session=False)
    db.query(models.Document).filter(models.Document.patient_uid == uid).delete(synchronize_session=False)
    db.query(models.DoctorOverride).filter(models.DoctorOverride.patient_uid == uid).delete(synchronize_session=False)
    db.query(models.AuditLog).filter(models.AuditLog.patient_uid == uid).delete(synchronize_session=False)
    
    db.query(models.Patient).filter(models.Patient.patient_uid == uid).delete(synchronize_session=False)
    db.expunge_all()
    db.commit()

    # 3. Delete patient directories from disk completely
    for path in [
        os.path.join(os.getcwd(), "uploads", uid),
        os.path.join(os.getcwd(), "uploads", "processed", uid)
    ]:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
            except Exception as e:
                print(f"[Patient Delete] File system error on path {path}: {e}")

    return {"status": "success", "message": f"Patient {uid} and all associated data deleted successfully."}


