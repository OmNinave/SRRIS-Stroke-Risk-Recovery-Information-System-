from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import database
from app.services.analytics_service import analytics_service
from typing import List, Dict, Any
import datetime

router = APIRouter()

@router.get("/gpu-status")
def get_gpu_status():
    from app.services.gpu_gate import gpu_gate

    return gpu_gate.status()

@router.get("/patient/{uid}/trends")
def get_patient_trends(
    uid: str,
    year: int = Query(None),
    db: Session = Depends(database.get_db)
):
    """
    Returns monthly stroke event counts and risk marker averages for a specific patient.
    """
    return analytics_service.get_monthly_stroke_trends(db, uid, year)

@router.get("/patient/{uid}/benchmarks")
def get_patient_benchmarks(
    uid: str,
    db: Session = Depends(database.get_db)
):
    """
    Returns comparison of latest patient health metrics against clinical benchmarks.
    """
    return analytics_service.get_patient_benchmarks(db, uid)

@router.get("/summary")
def get_global_summary(
    db: Session = Depends(database.get_db)
):
    """
    Returns global system-wide summary stats.
    """
    from app.db import models
    from sqlalchemy import func
    
    total_patients = db.query(models.Patient).count()
    total_events = db.query(models.MedicalEvent).count()
    stroke_events = db.query(models.MedicalEvent).filter_by(event_type='stroke_event').count()
    
    return {
        "total_patients": total_patients,
        "total_medical_events": total_events,
        "stroke_detection_rate": round((stroke_events / total_events * 100), 2) if total_events > 0 else 0
    }
