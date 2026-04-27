import os
from sqlalchemy.orm import Session
from app.db.database import engine, Base, SessionLocal
from app.db.models import Doctor, Patient, MedicalEvent, LabResult, Medication
from app.core import security
from datetime import datetime, timedelta

def initialize_database():
    print("Initializing Database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db = SessionLocal()
    
    try:
        # Create Admin Doctor
        doc = db.query(Doctor).filter_by(username="dr_smith").first()
        if not doc:
            doc = Doctor(
                username="dr_smith",
                full_name="Dr. Alexander Smith",
                hashed_password=security.get_password_hash("password123"),
                role="admin",
                department="Neurology",
                license_no="MED-928374"
            )
            db.add(doc)

        neuro_dept = db.query(Doctor).filter_by(username="NEURO_DEPT").first()
        if not neuro_dept:
            neuro_dept = Doctor(
                username="NEURO_DEPT",
                full_name="Neurology Department",
                hashed_password=security.get_password_hash("HOSPITAL_2024_SECURE"),
                role="admin",
                department="Neurology",
                license_no="DEPT-1000"
            )
            db.add(neuro_dept)

        db.commit()
        print("Created default doctors: dr_smith and NEURO_DEPT")

        # Assign pat to neuro_dept or doc
        primary_doc = neuro_dept or doc

        # Create Mock Patient
        pat = db.query(Patient).filter_by(patient_uid="SR-000001").first()
        if not pat:
            pat = Patient(
                patient_uid="SR-000001",
                full_name="Richard Roe",
                date_of_birth="1955-04-12",
                gender="Male",
                blood_type="O+",
                weight_kg=85.0,
                height_cm=175.0,
                phone="+1-555-0102",
                allergies="Penicillin",
                patient_category="geriatric",
                primary_doctor_id=primary_doc.id
            )
            db.add(pat)
            db.commit()

            # Add Medical Events
            e1 = MedicalEvent(
                patient_uid="SR-000001",
                event_date=datetime.utcnow() - timedelta(days=500),
                event_type="diagnosis",
                title="Diagnosed with Hypertension",
                description="Long-standing primary hypertension.",
                is_verified=True
            )
            e2 = MedicalEvent(
                patient_uid="SR-000001",
                event_date=datetime.utcnow() - timedelta(days=200),
                event_type="stroke_event",
                title="Ischemic Stroke (Left MCA)",
                description="Patient suffered focal neurological deficits. Treated with tPA.",
                nihss_score=14,
                is_verified=True
            )
            e3 = MedicalEvent(
                patient_uid="SR-000001",
                event_date=datetime.utcnow(),
                event_type="general",
                title="Current Admission",
                description="Presents with right-side weakness, facial droop, and expressive aphasia.",
                nihss_score=18,
                is_verified=True
            )
            db.add_all([e1, e2, e3])

            # Labs
            l1 = LabResult(patient_uid="SR-000001", test_name="systolic_bp", value="180", unit="mmHg", result_date=datetime.utcnow())
            l2 = LabResult(patient_uid="SR-000001", test_name="glucose", value="145", unit="mg/dL", result_date=datetime.utcnow())
            l3 = LabResult(patient_uid="SR-000001", test_name="inr", value="1.2", unit="", result_date=datetime.utcnow())
            db.add_all([l1, l2, l3])

            # Meds
            m1 = Medication(patient_uid="SR-000001", drug_name="Lisinopril", dosage="10mg", frequency="Daily", start_date=datetime.utcnow() - timedelta(days=500), is_active=True)
            db.add(m1)

            db.commit()
            print("Created mock patient SR-000001 with robust history.")

    except Exception as e:
        print(f"Error seeding DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    initialize_database()
