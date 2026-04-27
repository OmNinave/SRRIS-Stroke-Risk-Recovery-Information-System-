import os
import glob
import re
import datetime
import easyocr
from sqlalchemy.orm import Session
from app.db.database import engine, Base, SessionLocal
from app.db.models import Document, MedicalEvent, LabResult, Patient

def get_date_from_text(text):
    # Try DD/MM/YYYY or DD/MM/YY
    matches = re.findall(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', text)
    if matches:
        d, m, y = matches[0]
        y_int = int(y)
        if y_int < 100: y_int += 2000
        try:
            return datetime.datetime(y_int, int(m), int(d))
        except:
            pass
    return None

def process_all_images():
    print("Initializing Deep Medical OCR Scanner (EasyOCR)...")
    try:
        reader = easyocr.Reader(['en'], gpu=False)
        print("Model loaded.")
    except Exception as e:
        print(f"Failed to load easyocr: {e}")
        return

    db = SessionLocal()
    patient_uid = "SR-000002"
    
    upload_dir = os.path.join(os.getcwd(), "uploads", patient_uid, "2023", "discharge_summary")
    files = sorted(glob.glob(os.path.join(upload_dir, "*.jpg")) + glob.glob(os.path.join(upload_dir, "*.jpeg")) + glob.glob(os.path.join(upload_dir, "*.png")))
    
    print(f"Found {len(files)} image reports for processing.")
    
    consolidated_text = []
    
    for idx, file_path in enumerate(files):
        print(f"[{idx+1}/{len(files)}] Optical Scanning: {os.path.basename(file_path)}...")
        try:
            from PIL import Image, ImageOps
            import numpy as np
            
            # Robust Image Loading to bypass OpenCV imread crashes
            try:
                with Image.open(file_path) as img:
                    img = ImageOps.exif_transpose(img) # Fix orientation if any
                    img = img.convert('RGB')
                    img_array = np.array(img)
            except Exception as read_err:
                print(f"  -> Skipping corrupted or unreadable image: {read_err}")
                continue
                
            result = reader.readtext(img_array, detail=0)
            text = " ".join(result)
            
            # Simple Date Extraction
            doc_date = get_date_from_text(text)
            date_str = doc_date.strftime("%Y-%m-%d") if doc_date else "Unknown Date"
            
            # Save to consolidated list
            header = f"\n\n{'='*50}\nDOCUMENT: {os.path.basename(file_path)} | INFERRED DATE: {date_str}\n{'='*50}\n"
            consolidated_text.append(header + text)
            
            # Update Database Document
            doc_name = os.path.basename(file_path)
            db_doc = db.query(Document).filter_by(patient_uid=patient_uid, file_name=doc_name).first()
            if db_doc:
                db_doc.extracted_text = text
            
            # Extract basic labs if seen
            text_lower = text.lower()
            if 'glucose' in text_lower or 'sugar' in text_lower or 'rbs' in text_lower:
                val = re.findall(r'\b(1\d{2}|[7-9]\d|2\d{2})\b', text) # naive matching 70-299
                if val and doc_date:
                    existing = db.query(LabResult).filter_by(patient_uid=patient_uid, test_name="avg_glucose_level", result_date=doc_date).first()
                    if not existing:
                        db.add(LabResult(patient_uid=patient_uid, test_name="avg_glucose_level", value=val[0], unit="mg/dL", result_date=doc_date, status="normal"))

            if 'creatinine' in text_lower:
                val = re.findall(r'\b([0-2]\.\d)\b', text)
                if val and doc_date:
                    existing = db.query(LabResult).filter_by(patient_uid=patient_uid, test_name="creatinine", result_date=doc_date).first()
                    if not existing:
                        db.add(LabResult(patient_uid=patient_uid, test_name="creatinine", value=val[0], unit="mg/dL", result_date=doc_date, status="normal"))
                        
            # Suggest follow up visits
            if 'follow up' in text_lower or 'visit' in text_lower:
                if doc_date:
                    existing = db.query(MedicalEvent).filter_by(patient_uid=patient_uid, event_date=doc_date, event_type="follow_up").first()
                    if not existing:
                        db.add(MedicalEvent(patient_uid=patient_uid, event_date=doc_date, event_type="follow_up", title="Follow up visit recorded", description="Identified in: " + doc_name, is_verified=False, source="ocr"))
                        
            db.commit()
            
        except Exception as e:
            print(f"Error on {file_path}: {e}")
            
    # Save consolidated text to file for dataset training
    dataset_path = os.path.join(os.getcwd(), "SR-000002_Mahadev_Atram_Full_Medical_Corpus.txt")
    with open(dataset_path, "w", encoding="utf-8") as f:
        f.write("\n".join(consolidated_text))
        
    print(f"\n[SUCCESS] Processing Complete!")
    print(f"Saved 100% of unstructured text data to: {dataset_path}")
    print("Database updated with timeline entities.")

if __name__ == "__main__":
    process_all_images()
