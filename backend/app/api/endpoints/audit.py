from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import models, database
from app.api.endpoints.auth import get_current_user

router = APIRouter()

@router.get("/")
def get_audit_logs(
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    if current_user.role != "admin":
        return {"error": "Unauthorized. Admin role required."}
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(100).all()
    return logs
