from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db import models, database
from app.api.endpoints.auth import get_current_user
import os
import threading

router = APIRouter()

# In-memory job store: { job_id: { "status": "pending/running/done/error", "result": {...} } }
_ecg_jobs: dict = {}

def _run_ecg_in_thread(job_id: str, file_path: str, output_dir: str):
    """Run ECG analysis in a separate thread to prevent blocking uvicorn worker."""
    _ecg_jobs[job_id]["status"] = "running"
    try:
        from app.ai_modules.ecg_engine.inference_wrapper import predict_stroke_ecg
        result = predict_stroke_ecg(file_path, output_dir)
        _ecg_jobs[job_id]["status"] = "done"
        _ecg_jobs[job_id]["result"] = result
    except Exception as e:
        print(f"[ECG Thread] Error: {e}")
        _ecg_jobs[job_id]["status"] = "error"
        _ecg_jobs[job_id]["result"] = {
            "prediction": "Analysis Failed",
            "confidence": 0.0,
            "ocr_text": f"[ECG Auto-Scan Failed: {str(e)[:200]}]",
            "xai_analysis": "The ECG analysis pipeline encountered an error. Please ensure the image quality is sufficient.",
            "markers": {},
            "error": str(e)
        }


@router.post("/{uid}/scan-ecg/{doc_id}")
def scan_ecg_report(
    uid: str,
    doc_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    """
    Starts ECG scan as a non-blocking background job.
    Returns job_id immediately. Poll /ecg-status/{job_id} for result.
    """
    doc = db.query(models.Document).filter_by(id=doc_id, patient_uid=uid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="ECG document not found.")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="ECG file not found on server.")

    output_dir = os.path.join(os.getcwd(), "uploads", uid, "ECG_Signals", "processed")
    os.makedirs(output_dir, exist_ok=True)

    job_id = f"ecg_{uid}_{doc_id}"

    # If a job already exists and is done, return cached result
    if job_id in _ecg_jobs and _ecg_jobs[job_id]["status"] == "done":
        return {"job_id": job_id, "status": "done", **_ecg_jobs[job_id]["result"]}

    # If already running, just report
    if job_id in _ecg_jobs and _ecg_jobs[job_id]["status"] == "running":
        return {"job_id": job_id, "status": "running", "message": "ECG analysis in progress..."}

    # Start new job in background thread
    _ecg_jobs[job_id] = {"status": "pending", "result": None}
    thread = threading.Thread(
        target=_run_ecg_in_thread,
        args=(job_id, doc.file_path, output_dir),
        daemon=True
    )
    thread.start()

    return {"job_id": job_id, "status": "pending", "message": "ECG analysis started. Poll /ecg-status for results."}


@router.get("/{uid}/ecg-status/{doc_id}")
def get_ecg_status(
    uid: str,
    doc_id: int,
    current_user: models.Doctor = Depends(get_current_user)
):
    """Poll this endpoint to get ECG job status + result when ready."""
    job_id = f"ecg_{uid}_{doc_id}"
    if job_id not in _ecg_jobs:
        return {"status": "not_started", "message": "No ECG job found. Start one via POST /scan-ecg."}
    
    job = _ecg_jobs[job_id]
    response = {"job_id": job_id, "status": job["status"]}
    if job["status"] in ["done", "error"] and job["result"]:
        response.update(job["result"])
    return response
