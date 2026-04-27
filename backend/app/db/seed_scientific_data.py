import random
import datetime
import numpy as np
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from app.db import models

# Seed configuration
NUM_PATIENTS = 500
DOCTOR_USERNAME = "dr_smith"

def get_random_name():
    first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", 
                   "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", 
                  "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_scientific_data():
    # 0. Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Ensure Departmental Access (Hospital Level) exists
        hospital_user = db.query(models.User).filter(models.User.username == "NEURO_DEPT").first()
        if not hospital_user:
            from app.core import security
            hospital_user = models.User(
                username="NEURO_DEPT",
                hashed_password=security.get_password_hash("HOSPITAL_2024_SECURE"),
                full_name="Neurology Department Portal",
                role="HOSPITAL",
                specialty="General"
            )
            db.add(hospital_user)

        # 2. Ensure a default doctor exists
        doctor = db.query(models.User).filter(models.User.username == DOCTOR_USERNAME).first()
        if not doctor:
            from app.core import security
            doctor = models.User(
                username=DOCTOR_USERNAME,
                hashed_password=security.get_password_hash("secure123"),
                full_name="Dr. Smith",
                role="DOCTOR",
                specialty="Neurologist"
            )
            db.add(doctor)
            db.commit()
            db.refresh(doctor)

        print(f"Starting seed of {NUM_PATIENTS} patients...")

        for i in range(NUM_PATIENTS):
            p_id = f"SR-{1000 + i}"
            
            # Use distributions to make data look "real"
            # Older people have higher stroke risk
            age = float(np.random.normal(55, 15))
            age = max(18, min(95, age))
            
            # Probabilities skewed by age
            prob_factor = (age - 18) / (95 - 18)
            hypertension = 1 if random.random() < (0.1 + 0.3 * prob_factor) else 0
            heart_disease = 1 if random.random() < (0.05 + 0.2 * prob_factor) else 0
            
            # BMI and Glucose correlations
            bmi = float(np.random.normal(28 + 5 * prob_factor, 5))
            bmi = max(15, min(50, bmi))
            
            glucose = float(np.random.normal(100 + 40 * prob_factor if hypertension else 100, 30))
            glucose = max(50, min(300, glucose))
            
            gender = random.choice(["Male", "Female", "Other"])
            work = random.choice(["Private", "Self-employed", "Govt_job", "Never_worked"])
            residence = random.choice(["Urban", "Rural"])
            smoking = random.choice(["formerly smoked", "never smoked", "smokes", "Unknown"])
            
            # Recovery metrics (only if age/risk is high, some have stroke markers)
            is_stroke_patient = random.random() < (0.05 + 0.2 * prob_factor)
            nihss = random.randint(5, 25) if is_stroke_patient else random.randint(0, 4)
            mrs = random.randint(2, 5) if is_stroke_patient else random.randint(0, 1)

            dob = (datetime.datetime.now() - datetime.timedelta(days=int(age * 365))).strftime("%Y-%m-%d")

            patient = models.Patient(
                patient_id=p_id,
                full_name=get_random_name(),
                date_of_birth=dob,
                gender=gender,
                hypertension=hypertension,
                heart_disease=heart_disease,
                ever_married="Yes" if age > 25 else "No",
                work_type=work,
                residence_type=residence,
                smoking_status=smoking,
                nihss_admission=nihss,
                mrs_baseline=mrs
            )
            db.add(patient)
            db.flush() # Get ID for records

            # Create 1-3 medical records for each patient (longitudinal data)
            num_records = random.randint(1, 3)
            for j in range(num_records):
                # Calculate a "Calculated Risk" based on features
                # Simple linear combo + noise to simulate an AI model
                risk_score = (age/100 * 0.3) + (hypertension * 0.2) + (heart_disease * 0.2) + (bmi/50 * 0.1) + (glucose/300 * 0.2)
                risk_score = max(0.01, min(0.99, risk_score + random.uniform(-0.05, 0.05)))
                
                risk_level = "High" if risk_score > 0.6 else "Elevated" if risk_score > 0.3 else "Nominal"
                
                sys_bp = 120 + (hypertension * 30) + random.randint(-10, 20)
                dia_bp = 80 + (hypertension * 15) + random.randint(-5, 10)

                # Recovery insight (simulation)
                survival_90d = max(0.6, min(0.99, 1.0 - (nihss/50) - (age/200)))

                record = models.MedicalRecord(
                    patient_id=p_id,
                    doctor_id=doctor.id,
                    age=age,
                    bmi=bmi,
                    avg_glucose_level=glucose,
                    systolic_bp=float(sys_bp),
                    diastolic_bp=float(dia_bp),
                    nihss_score=nihss,
                    mrs_predicted=mrs,
                    clinical_notes=f"Patient presents with {smoking} smoking status. " + 
                                   (f"Hypertension managed." if hypertension else "No chronic hypertension."),
                    calculated_risk_percent=float(risk_score * 100),
                    nlp_extracted_score=float(risk_score * 0.9),
                    risk_level_string=risk_level,
                    survival_probability_90d=float(survival_90d * 100)
                )
                db.add(record)

        db.commit()
        print("✓ Successfully seeded 500 scientific patient records.")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_scientific_data()
