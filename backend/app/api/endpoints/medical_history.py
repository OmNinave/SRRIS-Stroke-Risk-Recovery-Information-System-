from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List
from app.db import models, database
from app.api.endpoints.auth import get_current_user
from app.schemas import (
    MedicalEventCreate, MedicalEventResponse, MedicalEventUpdate,
    MedicationCreate, MedicationResponse, MedicationUpdate,
    SurgeryCreate, SurgeryResponse,
    LabResultCreate, LabResultResponse
)
import json

router = APIRouter()

# ── Medical Events ─────────────────────────────────────────
@router.post("/{uid}/events", response_model=MedicalEventResponse)
def add_medical_event(uid: str, event: MedicalEventCreate, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    from app.services.deduplication import check_duplicate
    if check_duplicate(uid, event.event_date, event.title, db):
        raise HTTPException(status_code=409, detail="A similar medical event within ±7 days already exists.")
        
    db_event = models.MedicalEvent(**event.dict(), patient_uid=uid)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@router.get("/{uid}/events", response_model=List[MedicalEventResponse])
def get_medical_events(uid: str, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    return db.query(models.MedicalEvent).filter_by(patient_uid=uid).order_by(models.MedicalEvent.event_date.asc()).all()

@router.put("/{uid}/events/{event_id}", response_model=MedicalEventResponse)
def update_medical_event(uid: str, event_id: int, event_update: MedicalEventUpdate, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    db_event = db.query(models.MedicalEvent).filter_by(id=event_id, patient_uid=uid).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Medical event not found.")
        
    # Save old version to history
    old_data = {c.name: str(getattr(db_event, c.name)) for c.table.columns in models.MedicalEvent.__table__.columns}
    
    last_hist = db.query(models.MedicalEventHistory).filter_by(event_id=event_id).order_by(models.MedicalEventHistory.version_number.desc()).first()
    v_num = last_hist.version_number + 1 if last_hist else 1
    
    history_entry = models.MedicalEventHistory(
        event_id=event_id,
        version_number=v_num,
        snapshot=json.dumps(old_data),
        edited_by=current_user.id,
        edit_reason=event_update.edit_reason or "Update"
    )
    db.add(history_entry)
    
    # Update new fields
    update_data = event_update.dict(exclude_unset=True)
    update_data.pop('edit_reason', None)
    for k, v in update_data.items():
        setattr(db_event, k, v)
        
    db.commit()
    db.refresh(db_event)
    return db_event

# ── Medications ─────────────────────────────────────────
@router.post("/{uid}/medications", response_model=MedicationResponse)
def add_medication(uid: str, med: MedicationCreate, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    db_med = models.Medication(**med.dict(), patient_uid=uid)
    db.add(db_med)
    db.commit()
    db.refresh(db_med)
    return db_med

@router.get("/{uid}/medications", response_model=List[MedicationResponse])
def get_medications(uid: str, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    return db.query(models.Medication).filter_by(patient_uid=uid).order_by(desc(models.Medication.is_active), desc(models.Medication.start_date)).all()

@router.put("/{uid}/medications/{med_id}", response_model=MedicationResponse)
def update_medication(uid: str, med_id: int, med_update: MedicationUpdate, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    db_med = db.query(models.Medication).filter_by(id=med_id, patient_uid=uid).first()
    if not db_med:
        raise HTTPException(status_code=404, detail="Medication not found.")
    for k, v in med_update.dict(exclude_unset=True).items():
        setattr(db_med, k, v)
    db.commit()
    db.refresh(db_med)
    return db_med

# ── Surgeries ─────────────────────────────────────────
@router.post("/{uid}/surgeries", response_model=SurgeryResponse)
def add_surgery(uid: str, surg: SurgeryCreate, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    db_surg = models.Surgery(**surg.dict(), patient_uid=uid)
    db.add(db_surg)
    db.commit()
    db.refresh(db_surg)
    return db_surg

@router.get("/{uid}/surgeries", response_model=List[SurgeryResponse])
def get_surgeries(uid: str, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    return db.query(models.Surgery).filter_by(patient_uid=uid).order_by(desc(models.Surgery.surgery_date)).all()

# ── Labs ─────────────────────────────────────────
@router.post("/{uid}/labs", response_model=LabResultResponse)
def add_lab_result(uid: str, lab: LabResultCreate, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    db_lab = models.LabResult(**lab.dict(), patient_uid=uid)
    db.add(db_lab)
    db.commit()
    db.refresh(db_lab)
    return db_lab

@router.get("/{uid}/labs", response_model=List[LabResultResponse])
def get_labs(uid: str, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    return db.query(models.LabResult).filter_by(patient_uid=uid).order_by(desc(models.LabResult.result_date)).all()

@router.get("/{uid}/labs/latest")
def get_latest_labs(uid: str, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    # Group by test_name and get the latest
    from sqlalchemy import func
    subq = db.query(models.LabResult.test_name, func.max(models.LabResult.result_date).label('max_date')).filter_by(patient_uid=uid).group_by(models.LabResult.test_name).subquery()
    latest_labs = db.query(models.LabResult).join(subq, (models.LabResult.test_name == subq.c.test_name) & (models.LabResult.result_date == subq.c.max_date)).all()
    # return simple dictionary for UI
    return {l.test_name: {"value": l.value, "unit": l.unit, "status": l.status} for l in latest_labs}
