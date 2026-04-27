import os
import sys
import random
import datetime

# Add the parent directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import SessionLocal
from app.db.models import Patient

def generate_demo_patients():
    db = SessionLocal()
    
    # Base patient data for perturbation
    base_data = {
        "full_name": "Demo Patient",
        "date_of_birth": "1960-01-01",
        "gender": "Male",
        "blood_type": "O+",
        "weight_kg": 75.0,
        "height_cm": 170.0,
        "phone": "+1-555-0101",
        "email": "demo@example.com",
        "address": "123 Medical Drive",
        "emergency_contact_name": "Relative",
        "emergency_contact_phone": "+1-555-0102",
        "allergies": "None",
        "ward_area": "Neurology",
        "bed_no": "Bed-01",
        "primary_diagnosis": "Acute Ischemic Stroke",
        "patient_category": "geriatric",
        "admission_type": "emergency"
    }

    first_names = ["James", "Robert", "John", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

    count = db.query(Patient).count()
    start_id = count + 1

    for i in range(5): # Generate 5 new patients
        new_patient = Patient(
            patient_uid=f"SR-{start_id + i:06d}",
            full_name=f"{random.choice(first_names)} {random.choice(last_names)}",
            date_of_birth=f"{random.randint(1940, 1980):04d}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            gender=random.choice(["Male", "Female"]),
            blood_type=random.choice(["A+", "O+", "B+", "AB+", "A-", "O-"]),
            weight_kg=round(random.uniform(60.0, 100.0), 1),
            height_cm=round(random.uniform(150.0, 190.0), 1),
            phone=f"+1-555-{random.randint(1000, 9999)}",
            email=f"demo{i}@example.com",
            address=f"{random.randint(100, 999)} Random St",
            ward_area=random.choice(["Neurology", "Cardiology", "ICU"]),
            bed_no=f"Bed-{random.randint(10, 99)}",
            primary_diagnosis=random.choice(["Acute Ischemic Stroke", "Hemorrhagic Stroke", "TIA"]),
            patient_category=random.choice(["adult", "geriatric"])
        )
        db.add(new_patient)

    try:
        db.commit()
        print("Generated 5 new demo patients via data perturbation.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    generate_demo_patients()
