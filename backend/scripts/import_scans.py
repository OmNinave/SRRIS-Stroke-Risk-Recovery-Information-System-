import os
import sys
import shutil
import datetime

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy.orm import Session
from app.db import models, database

DOWNLOADS_DIR = r"C:\Users\ninav\Downloads\MAHADEV ATRAM"
UPLOAD_DIR = os.path.join(os.getcwd(), "..", "uploads", "SR-000002")

os.makedirs(UPLOAD_DIR, exist_ok=True)

db = database.SessionLocal()

# Scan downloads directory
for folder in os.listdir(DOWNLOADS_DIR):
    folder_path = os.path.join(DOWNLOADS_DIR, folder)
    
    if os.path.isdir(folder_path):
        category_name = folder  # e.g., 'CT_Sinus_Coronal_Skull_View'
        
        for file in os.listdir(folder_path):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                src_path = os.path.join(folder_path, file)
                
                # Copy to local uploads
                unique_filename = f"{folder}_{file}"
                dst_path = os.path.join(UPLOAD_DIR, unique_filename)
                
                shutil.copy2(src_path, dst_path)
                
                # Check if already exists in DB
                existing = db.query(models.Document).filter_by(patient_uid="SR-000002", file_name=unique_filename).first()
                if not existing:
                    new_doc = models.Document(
                        patient_uid="SR-000002",
                        file_name=unique_filename,
                        file_path=dst_path,
                        file_type="jpg",
                        category=category_name,
                        uploaded_by=1,
                        file_size_bytes=os.path.getsize(dst_path),
                        document_date=datetime.datetime.utcnow(),
                        extracted_text=f"[Radiological Scan Slice from {category_name}. Ready for 3D or deep learning reconstruction analysis.]"
                    )
                    db.add(new_doc)
        
        db.commit()

# Also update existing documents that might have null categories to "Clinical Reports"
db.query(models.Document).filter(models.Document.category == None).update({"category": "Clinical Reports"})
db.commit()

print("Successfully imported DICOM/JPG scans as Document Folders.")
db.close()
