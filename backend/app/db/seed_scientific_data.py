"""
seed_scientific_data.py
Generates 500 synthetic (fake) patients with statistically realistic stroke risk profiles.
Uses the CURRENT schema: Doctor, Patient, MedicalEvent, LabResult.
Run from: backend/  →  python -m app.db.seed_scientific_data
"""
import os
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
load_dotenv(dotenv_path=env_path)
import random
import datetime
import numpy as np
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from app.db import models

# ── Seed configuration ──────────────────────────────────────────────
NUM_PATIENTS = 500
DOCTOR_USERNAME = "dr_smith"

# Stroke risk threshold — patients above this score are flagged High risk
HIGH_RISK_THRESHOLD = 0.6

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Taylor", "Thomas", "Harris", "Jackson", "White",
]

def _random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_scientific_data():
    # 0. Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Ensure a Departmental Access account exists (uses Doctor model — correct)
        hospital_user = db.query(models.Doctor).filter(
            models.Doctor.username == "NEURO_DEPT"
        ).first()
        if not hospital_user:
            from app.core import security
            hospital_user = models.Doctor(
                username="NEURO_DEPT",
                hashed_password=security.get_password_hash("HOSPITAL_2024_SECURE"),
                full_name="Neurology Department Portal",
                role="admin",
                department="Neurology",
                license_no="DEPT-1000",
            )
            db.add(hospital_user)

        # 2. Ensure a default doctor exists (uses Doctor model — correct)
        doctor = db.query(models.Doctor).filter(
            models.Doctor.username == DOCTOR_USERNAME
        ).first()
        if not doctor:
            from app.core import security
            doctor = models.Doctor(
                username=DOCTOR_USERNAME,
                hashed_password=security.get_password_hash("secure123"),
                full_name="Dr. Alexander Smith",
                role="admin",
                department="Neurology",
                license_no="MED-928374",
            )
            db.add(doctor)
            db.commit()
            db.refresh(doctor)

        print(f"[SEED] Starting seed of {NUM_PATIENTS} synthetic patients...")

        for i in range(NUM_PATIENTS):
            uid = f"SR-{1000 + i:06d}"

            # ── Statistically realistic distributions ────────────────
            age = float(np.clip(np.random.normal(55, 15), 18, 95))
            prob_factor = (age - 18) / (95 - 18)

            hypertension = 1 if random.random() < (0.1 + 0.3 * prob_factor) else 0
            heart_disease = 1 if random.random() < (0.05 + 0.2 * prob_factor) else 0
            bmi  = float(np.clip(np.random.normal(28 + 5 * prob_factor, 5), 15, 50))
            glucose = float(np.clip(
                np.random.normal(100 + 40 * prob_factor if hypertension else 100, 30),
                50, 300,
            ))

            gender   = random.choice(["Male", "Female"])
            smoking  = random.choice(["formerly smoked", "never smoked", "smokes", "Unknown"])

            is_stroke_patient = random.random() < (0.05 + 0.2 * prob_factor)
            nihss = random.randint(5, 25) if is_stroke_patient else random.randint(0, 4)

            dob = (
                datetime.datetime.now() - datetime.timedelta(days=int(age * 365))
            ).strftime("%Y-%m-%d")

            # ── Patient record (uses Patient model — correct) ─────────
            patient = models.Patient(
                patient_uid=uid,
                full_name=_random_name(),
                date_of_birth=dob,
                gender=gender,
                patient_category="geriatric" if age >= 65 else "adult",
                primary_diagnosis="Acute Ischemic Stroke" if is_stroke_patient else "Stroke Risk Screening",
                primary_doctor_id=doctor.id,
            )
            db.add(patient)
            db.flush()

            # ── Lab results (systolic_bp, diastolic_bp, glucose, bmi) ─
            sys_bp  = 120 + (hypertension * 30) + random.randint(-10, 20)
            dia_bp  = 80  + (hypertension * 15) + random.randint(-5, 10)

            labs = [
                models.LabResult(patient_uid=uid, test_name="systolic_bp",   value=str(sys_bp),           unit="mmHg",   result_date=datetime.datetime.utcnow()),
                models.LabResult(patient_uid=uid, test_name="diastolic_bp",  value=str(dia_bp),           unit="mmHg",   result_date=datetime.datetime.utcnow()),
                models.LabResult(patient_uid=uid, test_name="glucose",        value=f"{glucose:.1f}",     unit="mg/dL",  result_date=datetime.datetime.utcnow()),
                models.LabResult(patient_uid=uid, test_name="bmi",            value=f"{bmi:.1f}",         unit="kg/m²",  result_date=datetime.datetime.utcnow()),
                models.LabResult(patient_uid=uid, test_name="hypertension",   value=str(hypertension),    unit="flag",   result_date=datetime.datetime.utcnow()),
                models.LabResult(patient_uid=uid, test_name="heart_disease",  value=str(heart_disease),   unit="flag",   result_date=datetime.datetime.utcnow()),
            ]
            db.add_all(labs)

            # ── Medical event (uses MedicalEvent model — correct) ──────
            risk_score = (
                (age / 100 * 0.3) +
                (hypertension * 0.2) +
                (heart_disease * 0.2) +
                (bmi / 50 * 0.1) +
                (glucose / 300 * 0.2)
            )
            risk_score = float(np.clip(risk_score + random.uniform(-0.05, 0.05), 0.01, 0.99))
            risk_level = "High" if risk_score > HIGH_RISK_THRESHOLD else "Elevated" if risk_score > 0.3 else "Nominal"

            event = models.MedicalEvent(
                patient_uid=uid,
                event_date=datetime.datetime.utcnow(),
                event_type="stroke_event" if is_stroke_patient else "general",
                title="Acute Ischemic Stroke" if is_stroke_patient else "Stroke Risk Screening",
                description=(
                    f"Patient presents with {smoking} smoking status. "
                    + ("Hypertension managed." if hypertension else "No chronic hypertension.")
                    + f" Calculated stroke risk: {risk_level} ({risk_score*100:.1f}%)."
                ),
                nihss_score=nihss if is_stroke_patient else 0,
                is_verified=True,
                source="ai_inferred",
            )
            db.add(event)

        db.commit()
        print(f"[SEED] ✓ Successfully seeded {NUM_PATIENTS} synthetic patient records.")

    except Exception as e:
        db.rollback()
        print(f"[SEED] ✗ Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    generate_scientific_data()
