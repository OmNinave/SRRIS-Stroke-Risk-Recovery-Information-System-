from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.db import models, database
from app.api.endpoints.auth import get_current_user
from app.schemas import DocumentResponse
from app.services import smart_organizer
import shutil
import os
import re
import json
import threading
from datetime import datetime

router = APIRouter()

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── Background Processing Status Store (in-memory, per patient) ──────────────
_processing_status: dict = {}  # { uid: { "total": n, "done": n, "results": [...] } }
_bg_processing_lock = threading.Lock()

def get_or_init_status(uid: str, total: int = 0) -> dict:
    if uid not in _processing_status:
        _processing_status[uid] = {"total": total, "done": 0, "results": []}
    return _processing_status[uid]

# ─── Background Document Processing ───────────────────────────────────────────

def process_document_bg(doc_id: int, file_path: str, file_type: str, file_category: str, patient_uid: str, db: Session):
    print(f"[BG] Starting processing for Doc {doc_id} (Category: {file_category}, Type: {file_type})")
    with _bg_processing_lock:
        try:
            extracted_text = ""
            ai_result = None
            lab_rows = []
            doctor_findings = None
            
            status = _processing_status.get(patient_uid)

            # ── 1. ECG SIGNALS ──────────────────────────────────────────────────
            if file_category == "ECG_Signals":
                try:
                    from app.ai_modules.ecg_engine.inference_wrapper import predict_stroke_ecg
                    output_dir = os.path.join(UPLOAD_DIR, patient_uid, "ECG_Signals", "processed")
                    os.makedirs(output_dir, exist_ok=True)
                    ai_result = predict_stroke_ecg(file_path, output_dir)
                    prediction = ai_result.get('prediction', 'Unknown')
                    confidence = ai_result.get('confidence', 0)
                    markers = ai_result.get('markers', {})
                    hrv_text = ""
                    if markers:
                        hrv_text = " | ".join([f"{k}: {v}" for k, v in list(markers.items())[:4]])
                    extracted_text = (
                        f"🫀 ECG AI Analysis Complete\n"
                        f"Prediction: {prediction}\n"
                        f"Confidence: {confidence:.1%}\n"
                        f"Regional Markers: {hrv_text}\n"
                        f"{ai_result.get('xai_analysis', '')}"
                    )
                    print(f"[BG-ECG] Doc {doc_id}: {prediction} ({confidence:.1%})")
                except Exception as e:
                    extracted_text = f"[ECG Auto-Scan Failed: {str(e)[:150]}]"
                    print(f"[BG-ECG] Error for doc {doc_id}: {e}")

            # ── 2. LABORATORY TESTS ─────────────────────────────────────────────
            elif file_category == "Laboratory_Tests":
                raw_ocr = ""
                # OCR
                if file_type == "pdf":
                    try:
                        import pdfplumber
                        with pdfplumber.open(file_path) as pdf:
                            for page in pdf.pages:
                                t = page.extract_text()
                                if t: raw_ocr += t + "\n"
                        print(f"[BG-LAB] PDF text extraction done: {len(raw_ocr)} chars")
                    except Exception as e:
                        print(f"[BG-LAB] PDF error: {e}")
                
                if not raw_ocr.strip():
                    try:
                        from app.services.easyocr_runtime import readtext_image_file
                        raw_ocr = "\n".join(readtext_image_file(file_path, ['en'], detail=0))
                        print(f"[BG-LAB] EasyOCR extracted {len(raw_ocr)} chars")
                    except Exception as e:
                        raw_ocr = f"[OCR failed: {e}]"
                
                # Structured lab parsing
                from app.services.lab_parser import parse_lab_report, extract_lab_summary
                lab_rows = parse_lab_report(raw_ocr)
                extracted_text = extract_lab_summary(lab_rows) + "\n\n--- RAW OCR ---\n" + raw_ocr[:800]
                print(f"[BG-LAB] Parsed {len(lab_rows)} structured lab values")
                
                # Auto-create LabResult DB rows
                from datetime import datetime
                if lab_rows:
                    for row in lab_rows:
                        try:
                            new_lab = models.LabResult(
                                patient_uid=patient_uid,
                                document_id=doc_id,
                                test_name=row["test_name"],
                                value=str(row["value"]),
                                unit=row["unit"],
                                reference_range=row["reference_range"],
                                status=row["status"],
                                result_date=datetime.utcnow(),
                                ordered_by="Auto-Extracted (OCR)",
                                notes=f"Auto-extracted from uploaded lab report. Doc ID: {doc_id}"
                            )
                            db.add(new_lab)
                        except Exception as e:
                            print(f"[BG-LAB] Failed to save row {row}: {e}")
                    db.commit()
                    print(f"[BG-LAB] Saved {len(lab_rows)} LabResult rows for {patient_uid}")

            # ── 3. RADIOLOGY / MRI / CT ────────────────────────────────────────────────────
            elif file_category == "Radiology_Scans":
                try:
                    from app.services.vision_service import vision_service
                    val, result_text, confidence, input_img, results = vision_service.predict_stroke(file_path)

                    # Compute dominant stroke type from per-slice results
                    ischemic_count     = sum(1 for r in results if str(r.get('prediction','')) == 'Ischemic')
                    haemorrhagic_count = sum(1 for r in results if str(r.get('prediction','')) == 'Haemorrhagic')
                    normal_count       = sum(1 for r in results if str(r.get('prediction','')) == 'Normal')
                    total_slices       = len(results) if results else 1
                    stroke_slices_n    = ischemic_count + haemorrhagic_count

                    # Clean parseable prediction label
                    if ischemic_count >= haemorrhagic_count and ischemic_count > 0:
                        clean_prediction = "Ischemic Stroke"
                    elif haemorrhagic_count > 0:
                        clean_prediction = "Haemorrhagic Stroke"
                    else:
                        clean_prediction = "No Stroke Detected"

                    # volume_percentage = % of slices with stroke pathology
                    volume_pct = round(stroke_slices_n / total_slices * 100, 2)

                    # Human-readable XAI analysis
                    xai_text = (
                        f"VGG19 FastAI model analysed {total_slices} brain slice(s). "
                        f"Found {stroke_slices_n} abnormal slice(s): {ischemic_count} Ischemic, "
                        f"{haemorrhagic_count} Haemorrhagic, {normal_count} Normal. "
                        f"Dominant classification: {clean_prediction} "
                        f"(AI confidence {confidence:.1%}). "
                        f"Lesion burden: {volume_pct:.1f}% of scanned area."
                    )

                    extracted_text = (
                        f"\U0001f9e0 Radiology AI Analysis\n"
                        f"Prediction: {clean_prediction}\n"
                        f"Confidence: {confidence:.1%}\n"
                        f"Total Slices: {total_slices} | Stroke Slices: {stroke_slices_n}\n"
                        f"Ischemic: {ischemic_count} | Haemorrhagic: {haemorrhagic_count} | Normal: {normal_count}\n"
                        f"Model: VGG19 FastAI Brain Stroke v1"
                    )
                    ai_result = {"prediction": clean_prediction, "confidence": confidence}
                    print(f"[BG-RADIO] Doc {doc_id}: {clean_prediction} ({confidence:.1%}) - {stroke_slices_n}/{total_slices} stroke slices")

                    # Lesion center from first stroke-positive slice
                    cx, cy, side_val = 0.5, 0.5, "Unknown"
                    if results:
                        stroke_result_list = [r for r in results if str(r.get('prediction','')) in ['Ischemic', 'Haemorrhagic']]
                        if stroke_result_list:
                            s = stroke_result_list[0]
                            box = s['coords']
                            img_w = max(box[0] + box[2], 1)
                            cx = (box[0] + box[2] / 2) / img_w
                            cy = (box[1] + box[3] / 2) / max(box[1] + box[3], 1)
                            side_val = "Left" if cx < 0.5 else "Right"

                    new_scan = models.ScanResult(
                        patient_uid=patient_uid,
                        document_id=doc_id,
                        prediction=clean_prediction,
                        confidence=float(confidence),
                        volume_percentage=float(volume_pct),
                        side=side_val,
                        lesion_center_x=cx,
                        lesion_center_y=cy,
                        xai_analysis=xai_text
                    )
                    db.add(new_scan)
                    db.commit()
                except Exception as e:
                    extracted_text = f"[Radiology Scan - Use 'Run Smart AI Scan' in the Vault for deep analysis. Auto-scan error: {str(e)[:100]}]"
                    print(f"[BG-RADIO] Error for doc {doc_id}: {e}")

            # ── 4. DOCTOR NOTES (Handwriting OCR) ──────────────────────────────
            elif file_category == "Doctor_Notes":
                try:
                    from app.services.doctor_notes_ocr import ocr_handwritten_image, extract_clinical_terms
                    raw_text = ocr_handwritten_image(file_path)
                    clinical_findings = extract_clinical_terms(raw_text)
                    
                    summary_lines = [f"📝 Doctor Notes — Handwriting Recognized\n"]
                    if clinical_findings.get("diagnoses"):
                        summary_lines.append(f"Diagnoses: {', '.join(clinical_findings['diagnoses'])}")
                    if clinical_findings.get("medications"):
                        summary_lines.append(f"Medications: {', '.join(clinical_findings['medications'][:5])}")
                    if clinical_findings.get("vitals"):
                        for k, v in clinical_findings["vitals"].items():
                            summary_lines.append(f"{k.replace('_', ' ').title()}: {v}")
                    if clinical_findings.get("follow_up"):
                        summary_lines.append(f"Follow-up: {clinical_findings['follow_up']}")
                    if clinical_findings.get("instructions"):
                        summary_lines.append(f"Instructions: {'; '.join(clinical_findings['instructions'][:3])}")
                    summary_lines.append(f"\n--- FULL TEXT ---\n{raw_text}")
                    
                    extracted_text = "\n".join(summary_lines)
                    doctor_findings = clinical_findings
                    print(f"[BG-NOTES] Doc {doc_id}: extracted {len(raw_text)} chars")
                except Exception as e:
                    extracted_text = f"[Doctor Notes OCR failed: {str(e)[:150]}]"
                    print(f"[BG-NOTES] Error: {e}")

            # ── 5. CLINICAL REPORTS & GENERAL ───────────────────────────────────
            else:
                if file_type == "pdf":
                    try:
                        import pdfplumber
                        with pdfplumber.open(file_path) as pdf:
                            for page in pdf.pages:
                                t = page.extract_text()
                                if t: extracted_text += t + "\n"
                        print(f"[BG-OCR] PDF text extraction done: {len(extracted_text)} chars")
                    except Exception as e:
                        print(f"[BG-OCR] PDF error: {e}")
                
                if not extracted_text.strip() and file_type != "pdf":
                    try:
                        from app.services.easyocr_runtime import readtext_image_file
                        result = readtext_image_file(file_path, ['en'], detail=0)
                        extracted_text = "\n".join(result)
                        print(f"[BG-OCR] EasyOCR done for doc {doc_id}, {len(extracted_text)} chars")
                    except Exception as e:
                        extracted_text = f"[OCR Failed: {e}]"
            
            # ── Update DB record ────────────────────────────────────────────────
            db_doc = db.query(models.Document).filter_by(id=doc_id).first()
            if db_doc:
                db_doc.extracted_text = extracted_text
                
                # Date extraction
                import re
                from datetime import datetime
                date_val = datetime.utcnow()
                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}-[A-Za-z]{3}-\d{4})', extracted_text)
                if date_match:
                    try:
                        d_str = date_match.group(1)
                        if '-' in d_str and any(c.isalpha() for c in d_str):
                            date_val = datetime.strptime(d_str, "%d-%b-%Y")
                        else:
                            d_str = d_str.replace('-', '/')
                            date_val = datetime.strptime(d_str, '%d/%m/%Y' if len(d_str.split('/')[-1]) == 4 else '%d/%m/%y')
                    except Exception:
                        pass
                db_doc.upload_date = date_val
                db.commit()
                
                # Auto-create medical event from analysis
                evt_title = f"{file_category.replace('_', ' ')} — {date_val.strftime('%d %b %Y')}"
                if ai_result:
                    evt_title = f"AI: {ai_result.get('prediction', 'Analysis')} — {date_val.strftime('%d %b %Y')}"
                elif doctor_findings and doctor_findings.get("diagnoses"):
                    evt_title = f"Dr. Notes: {doctor_findings['diagnoses'][0][:50]}"
                elif lab_rows:
                    abnormal = [r for r in lab_rows if r.get('status') in ['abnormal', 'critical']]
                    if abnormal:
                        evt_title = f"⚠️ Abnormal Lab: {abnormal[0]['test_name']} — {date_val.strftime('%d %b %Y')}"
                    else:
                        evt_title = f"Lab Report ({len(lab_rows)} tests) — {date_val.strftime('%d %b %Y')}"
                
                new_event = models.MedicalEvent(
                    patient_uid=patient_uid,
                    document_id=doc_id,
                    event_date=date_val,
                    event_type="document_analysis",
                    title=evt_title,
                    description=extracted_text[:500],
                    source="ocr",
                    is_verified=False,
                    confidence=0.88
                )
                db.add(new_event)
                db.commit()
            
            # ── Update progress tracker ─────────────────────────────────────────
            if status is not None:
                status["done"] += 1
                status["results"].append({
                    "doc_id": doc_id,
                    "category": file_category,
                    "status": "done",
                    "preview": extracted_text[:120] if extracted_text else "",
                    "lab_count": len(lab_rows)
                })
                
        except Exception as e:
            print(f"[BG] Fatal error for doc {doc_id}: {e}")
            import traceback; traceback.print_exc()
            if patient_uid in _processing_status:
                _processing_status[patient_uid]["done"] += 1
        finally:
            db.close()


# ─── Upload Endpoint ───────────────────────────────────────────────────────────

@router.post("/{uid}/documents/upload", response_model=DocumentResponse)
def upload_document(
    uid: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = "General_Records",
    db: Session = Depends(database.get_db),
    current_user: models.Doctor = Depends(get_current_user)
):
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["pdf", "jpg", "png", "jpeg", "tiff"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: pdf, jpg, png, jpeg, tiff.")

    # Save to temp first
    temp_dir = os.path.join(UPLOAD_DIR, uid, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Smart Organizer: returns (category, actual_final_path)
    smart_category, final_path = smart_organizer.organize_document(
        uid, temp_path, file.filename, suggested_category=category
    )

    # Use actual filename (may differ if collision renamed it)
    actual_filename = os.path.basename(final_path)
    file_size = os.path.getsize(final_path)

    new_doc = models.Document(
        patient_uid=uid,
        file_name=actual_filename,
        file_path=final_path,
        file_type=ext,
        category=smart_category,
        uploaded_by=current_user.id,
        file_size_bytes=file_size
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # Initialize or increment processing tracker
    if uid not in _processing_status:
        _processing_status[uid] = {"total": 1, "done": 0, "results": []}
    else:
        _processing_status[uid]["total"] += 1

    # Background task with category-aware processing
    db_bg = database.SessionLocal()
    background_tasks.add_task(
        process_document_bg,
        new_doc.id, final_path, ext, smart_category, uid, db_bg
    )

    return new_doc


# ─── Processing Progress Endpoint ─────────────────────────────────────────────

@router.get("/{uid}/processing-status")
@router.get("/{uid}/documents/processing-status")
def get_processing_status(
    uid: str,
    current_user: models.Doctor = Depends(get_current_user)
):
    """Returns how many documents have been processed out of total uploaded."""
    status = _processing_status.get(uid, {"total": 0, "done": 0, "results": []})
    pct = (status["done"] / status["total"] * 100) if status["total"] > 0 else 100
    return {
        "total": status["total"],
        "done": status["done"],
        "percent": round(pct, 1),
        "complete": status["done"] >= status["total"],
        "results": status["results"][-5:]  # Last 5 results
    }


# ─── Standard CRUD ────────────────────────────────────────────────────────────

@router.get("/{uid}/documents", response_model=list[DocumentResponse])
def list_documents(uid: str, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    docs = db.query(models.Document).filter_by(patient_uid=uid).all()
    return docs

@router.get("/{uid}/documents/{doc_id}")
def serve_document(uid: str, doc_id: int, db: Session = Depends(database.get_db)):
    from fastapi.responses import FileResponse
    doc = db.query(models.Document).filter_by(id=doc_id, patient_uid=uid).first()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on server.")
    return FileResponse(doc.file_path, filename=doc.file_name)

@router.delete("/{uid}/documents/{doc_id}")
def delete_document(uid: str, doc_id: int, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    doc = db.query(models.Document).filter_by(id=doc_id, patient_uid=uid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        os.remove(doc.file_path)
    except FileNotFoundError:
        pass
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully."}

@router.post("/{uid}/documents/reprocess/{doc_id}")
def reprocess_document(uid: str, doc_id: int, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db), current_user: models.Doctor = Depends(get_current_user)):
    doc = db.query(models.Document).filter_by(id=doc_id, patient_uid=uid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    print(f"[API] Manual reprocessing triggered for Doc {doc_id} by user {current_user.username}")
    db_bg = database.SessionLocal()
    background_tasks.add_task(
        process_document_bg,
        doc.id, doc.file_path, doc.file_type, doc.category, uid, db_bg
    )
    return {"status": "processing_started", "message": "Manual re-processing triggered in background."}
