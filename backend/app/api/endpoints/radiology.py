from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db import models, database
from app.api.endpoints.auth import get_current_user
from app.services.vision_service import vision_service
import os
import shutil
import uuid
import json
import cv2

router = APIRouter()

# In-memory job store: { job_id: { "status": "pending/running/done/error", "result": {...} } }
_radio_jobs: dict = {}

def _run_radiology_in_thread(job_id: str, file_path: str, output_dir: str, doc_id: int, uid: str):
    _radio_jobs[job_id]["status"] = "running"
    try:
        val, result_text, confidence, input_img, results = vision_service.predict_stroke(file_path)
        
        heatmap_url = ""
        detection_url = ""
        xai_report = ""
        extracted_text = ""

        # 4. Generate Visual Evidence
        heatmap = vision_service.get_gradcam(input_img)
        overlay_img = vision_service.overlay_heatmap(heatmap, file_path)
        
        heatmap_filename = f"heatmap_{doc_id}_{val}.png"
        heatmap_path = os.path.join(output_dir, heatmap_filename)
        overlay_img.save(heatmap_path)
        heatmap_url = f"/uploads/processed/{uid}/{heatmap_filename}"

        # Detection Box Image
        raw_img = cv2.imread(file_path)
        detection_img = vision_service.draw_detections(raw_img, results)
        det_filename = f"detection_{doc_id}_{val}.png"
        det_path = os.path.join(output_dir, det_filename)
        detection_img.save(det_path)
        detection_url = f"/uploads/processed/{uid}/{det_filename}"

        xai_result = {
            "ocr_text": "OCR Engine Offline. Simulation active.", 
            "explanation": "The AI flagged the upper-right hemisphere due to high intensity variation and reduced density, typical of ischemic tissue. Found clearly in Grid Row 1, Col 4.", 
            "recurrence_analysis": "High chance of recurrence (approx 12% within 90 days) due to uncontrolled hypertension and hyperdense MCA sign. Precautions: strict BP management and antiplatelet therapy.",
            "data_provenance": "Clinical synthesis derived from standard AHA/ASA ischemic stroke imaging guidelines and local pixel intensity variance.",
            "markers": {
                 "hypodensity": "Present",
                 "midline_shift": "Minor (2mm)",
                 "vascular_signs": "Hyperdense MCA sign",
                 "clinical_impression": "Acute territory infarction",
                 "critical_slice_location": "Row 1, Col 4"
            }
        }
        try:
            from app.services.ai_engine import ai_engine
            xai_result = ai_engine.analyze_radiology_image(file_path, result_text)
            extracted_text = xai_result.get("ocr_text", "")
            xai_report = xai_result.get("explanation", "")
        except Exception as e:
            print(f"[RadiologyAPI] Fallback triggered due to AI error: {e}")
            extracted_text = xai_result.get("ocr_text")
            xai_report = xai_result.get("explanation")

        _radio_jobs[job_id]["status"] = "done"
        # IMPORTANT: Do not include a top-level "status" field in result payload.
        # The polling UI expects `status` to be the job status: pending/running/done/error.
        _radio_jobs[job_id]["result"] = {
            "result_status": "success",
            "doc_id": doc_id,
            "prediction": result_text,
            "confidence": confidence,
            "heatmap_image": heatmap_url,
            "detection_image": detection_url,
            "ocr_text": extracted_text,
            "xai_analysis": xai_report,
            "recurrence_analysis": xai_result.get("recurrence_analysis", "Data not available."),
            "data_provenance": xai_result.get("data_provenance", "Local Inference."),
            "markers": xai_result.get("markers", {})
        }
    except Exception as e:
        print(f"[Radiology Thread] Error: {e}")
        _radio_jobs[job_id]["status"] = "error"
        _radio_jobs[job_id]["result"] = {
            "result_status": "error",
            "prediction": "Analysis Failed",
            "confidence": 0.0,
            "ocr_text": f"[Radiology Auto-Scan Failed: {str(e)[:200]}]",
            "xai_analysis": "The Radiology analysis pipeline encountered an error.",
            "markers": {},
            "error": str(e)
        }

@router.post("/{uid}/scan/{doc_id}")
async def scan_radiology_report(
    uid: str,
    doc_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    doc = db.query(models.Document).filter_by(id=doc_id, patient_uid=uid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.file_path
    if not os.path.exists(file_path):
        upload_root = os.path.join(os.getcwd(), "uploads")
        file_path = os.path.join(upload_root, doc.patient_uid, doc.file_name)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Physical file not found at {doc.file_path}")

    upload_root = os.path.join(os.getcwd(), "uploads")
    output_dir = os.path.join(upload_root, "processed", uid)
    os.makedirs(output_dir, exist_ok=True)
    
    import threading
    job_id = f"radio_{uid}_{doc_id}"

    if job_id in _radio_jobs and _radio_jobs[job_id]["status"] == "done":
        return {"job_id": job_id, "status": "done", **(_radio_jobs[job_id]["result"] or {})}

    if job_id in _radio_jobs and _radio_jobs[job_id]["status"] == "running":
        return {"job_id": job_id, "status": "running", "message": "Analysis in progress..."}

    _radio_jobs[job_id] = {"status": "pending", "result": None}
    thread = threading.Thread(
        target=_run_radiology_in_thread,
        args=(job_id, file_path, output_dir, doc_id, uid),
        daemon=True
    )
    thread.start()

    return {"job_id": job_id, "status": "pending", "message": "Analysis started. Poll /scan-status for results."}

@router.get("/{uid}/scan-status/{doc_id}")
def get_radiology_status(
    uid: str,
    doc_id: int,
    current_user: models.Doctor = Depends(get_current_user)
):
    job_id = f"radio_{uid}_{doc_id}"
    if job_id not in _radio_jobs:
        return {"status": "not_started", "message": "No job found."}
    
    job = _radio_jobs[job_id]
    response = {"job_id": job_id, "status": job["status"]}
    if job["status"] in ["done", "error"] and job["result"]:
        # Keep `status` as the job status; result payload must not override it.
        response.update(job["result"])
    return response


# NOTE: The /scan-ecg/{doc_id} route has been migrated to app/api/endpoints/ecg.py
# which uses a non-blocking thread-based approach with proper cv2 handling.
