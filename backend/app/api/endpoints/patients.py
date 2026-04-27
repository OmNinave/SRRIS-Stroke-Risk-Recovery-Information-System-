from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from app.db import models, database
from app.api.endpoints.auth import get_current_user
from app.schemas import PatientCreate, PatientResponse, PatientBase

router = APIRouter()

def generate_patient_uid(db: Session) -> str:
    last_patient = db.query(models.Patient).order_by(models.Patient.id.desc()).first()
    if not last_patient:
        return "SR-000001"
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
