from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="doctor")  # 'doctor','admin','readonly'
    full_name = Column(String)
    department = Column(String, nullable=True)
    license_no = Column(String, nullable=True)
    
class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(12), unique=True, nullable=False, index=True) # SR-000001
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(String) # Storing as string or Date
    gender = Column(String(10))
    blood_type = Column(String(5))
    weight_kg = Column(Float)
    height_cm = Column(Float)
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(Text)
    emergency_contact_name = Column(String(255))
    emergency_contact_phone = Column(String(20))
    allergies = Column(Text) # Comma-separated
    primary_doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    photo_url = Column(String(500))
    
    
    # Flags added for patient categorization
    ward_area = Column(String(100), nullable=True)
    bed_no = Column(String(50), nullable=True)
    primary_diagnosis = Column(String(255), nullable=True)
    patient_category = Column(String(30), default='adult') # 'adult','pediatric','geriatric','maternity'
    admission_type = Column(String(20), default='opd') # 'ipd','opd','emergency'
    is_in_isolation = Column(Boolean, default=False)
    isolation_reason = Column(String(100), nullable=True)
    dnr_status = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    events = relationship("MedicalEvent", back_populates="patient")
    medications = relationship("Medication", back_populates="patient")
    surgeries = relationship("Surgery", back_populates="patient")
    labs = relationship("LabResult", back_populates="patient")
    documents = relationship("Document", back_populates="patient")

class MedicalEvent(Base):
    __tablename__ = "medical_events"

    id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(12), ForeignKey("patients.patient_uid"))
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    event_date = Column(DateTime, nullable=False)
    event_type = Column(String(50))   
    title = Column(String(255), nullable=False)
    description = Column(Text)
    outcome = Column(Text)
    treating_doctor = Column(String(255))
    hospital_name = Column(String(255))
    discharge_date = Column(DateTime, nullable=True)
    discharge_recommendation = Column(Text)
    
    source = Column(String(20), default='manual') # 'manual','ocr','ai_inferred'
    is_verified = Column(Boolean, default=True)
    confidence = Column(Float, nullable=True)
    
    # Advanced metrics
    gcs_score = Column(Integer, nullable=True)
    nihss_score = Column(Integer, nullable=True)
    mrs_score = Column(Integer, nullable=True)
    pain_score = Column(Integer, nullable=True)
    fall_risk_score = Column(String(10), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="events")

class MedicalEventHistory(Base):
    __tablename__ = "medical_event_history"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("medical_events.id"))
    version_number = Column(Integer, nullable=False)
    snapshot = Column(Text) # JSON string
    edited_by = Column(Integer, ForeignKey("doctors.id"))
    edited_at = Column(DateTime, default=datetime.datetime.utcnow)
    edit_reason = Column(Text)

class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(12), ForeignKey("patients.patient_uid"))
    drug_name = Column(String(255), nullable=False)
    dosage = Column(String(100))
    frequency = Column(String(100))
    route = Column(String(50))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    prescribed_by = Column(String(255))
    indication = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="medications")

class Surgery(Base):
    __tablename__ = "surgeries"

    id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(12), ForeignKey("patients.patient_uid"))
    procedure_name = Column(String(255), nullable=False)
    surgery_date = Column(DateTime, nullable=False)
    hospital_name = Column(String(255))
    surgeon_name = Column(String(255))
    duration_hours = Column(Float)
    anaesthesia_type = Column(String(50))
    outcome = Column(Text)
    complications = Column(Text)
    recovery_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="surgeries")

class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(12), ForeignKey("patients.patient_uid"))
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    test_name = Column(String(255), nullable=False)
    value = Column(String(100))
    unit = Column(String(50))
    reference_range = Column(String(100))
    result_date = Column(DateTime, nullable=False)
    status = Column(String(20)) # normal, abnormal, critical
    ordered_by = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="labs")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(12), ForeignKey("patients.patient_uid"))
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10))
    category = Column(String(50))
    document_date = Column(DateTime)
    extracted_text = Column(Text)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    uploaded_by = Column(Integer, ForeignKey("doctors.id"))
    file_size_bytes = Column(Integer)
    
    source = Column(String(20), default='manual')
    is_verified = Column(Boolean, default=False)

    patient = relationship("Patient", back_populates="documents")
    scan_results = relationship("ScanResult", back_populates="document")

class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(12), ForeignKey("patients.patient_uid"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    prediction = Column(String(100))
    confidence = Column(Float)
    volume_percentage = Column(Float)
    side = Column(String(10)) # Left, Right, Bilateral
    lesion_center_x = Column(Float, nullable=True)
    lesion_center_y = Column(Float, nullable=True)
    ocr_text = Column(Text, nullable=True)
    xai_analysis = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="scan_results")

class DoctorOverride(Base):
    __tablename__ = "doctor_overrides"

    id = Column(Integer, primary_key=True, index=True)
    patient_uid = Column(String(12))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    ai_recommendation = Column(Text)
    doctor_decision = Column(Text)
    override_reason = Column(Text)
    was_overridden = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    patient_uid = Column(String(12))
    action = Column(String(255))
    ip_address = Column(String(50))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
