from datetime import timedelta
from sqlalchemy.orm import Session
from app.db import models

def check_duplicate(patient_uid: str, event_date, title: str, db: Session) -> bool:
    """Check if an event within ±7 days with a similar title already exists."""
    window_start = event_date - timedelta(days=7)
    window_end = event_date + timedelta(days=7)
    
    # Fuzzy match threshold: at least start matches
    title_prefix = title[:20] if len(title) > 20 else title
    
    existing = db.query(models.MedicalEvent).filter(
        models.MedicalEvent.patient_uid == patient_uid,
        models.MedicalEvent.event_date >= window_start,
        models.MedicalEvent.event_date <= window_end,
        models.MedicalEvent.title.ilike(f"%{title_prefix}%")
    ).first()
    
    return existing is not None
