from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# --- Patients ---
class PatientBase(BaseModel):
    full_name: str
    date_of_birth: str
    gender: str
    blood_type: str
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    allergies: Optional[str] = None
    ward_area: Optional[str] = None
    bed_no: Optional[str] = None
    primary_diagnosis: Optional[str] = None
    patient_category: Optional[str] = 'adult'
    admission_type: Optional[str] = 'opd'
    is_in_isolation: Optional[bool] = False
    isolation_reason: Optional[str] = None
    dnr_status: Optional[bool] = False

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: int
    patient_uid: str
    photo_url: Optional[str] = None
    created_at: datetime
    primary_doctor_id: Optional[int] = None

    class Config:
        from_attributes = True

# --- Medical Events ---
class MedicalEventBase(BaseModel):
    event_date: datetime
    event_type: str
    title: str
    description: Optional[str] = None
    outcome: Optional[str] = None
    treating_doctor: Optional[str] = None
    hospital_name: Optional[str] = None
    discharge_date: Optional[datetime] = None
    discharge_recommendation: Optional[str] = None
    source: Optional[str] = 'manual'
    is_verified: Optional[bool] = True
    confidence: Optional[float] = None
    gcs_score: Optional[int] = None
    nihss_score: Optional[int] = None
    mrs_score: Optional[int] = None
    pain_score: Optional[int] = None
    fall_risk_score: Optional[str] = None

class MedicalEventCreate(MedicalEventBase):
    pass

class MedicalEventResponse(MedicalEventBase):
    id: int
    patient_uid: str
    created_at: datetime

    class Config:
        from_attributes = True

class MedicalEventUpdate(BaseModel):
    event_date: Optional[datetime] = None
    event_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    outcome: Optional[str] = None
    treating_doctor: Optional[str] = None
    hospital_name: Optional[str] = None
    discharge_date: Optional[datetime] = None
    discharge_recommendation: Optional[str] = None
    is_verified: Optional[bool] = None
    gcs_score: Optional[int] = None
    nihss_score: Optional[int] = None
    mrs_score: Optional[int] = None
    pain_score: Optional[int] = None
    fall_risk_score: Optional[str] = None
    edit_reason: Optional[str] = None # required when updating

# --- Medications ---
class MedicationBase(BaseModel):
    drug_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    prescribed_by: Optional[str] = None
    indication: Optional[str] = None
    is_active: Optional[bool] = True

class MedicationCreate(MedicationBase):
    pass

class MedicationResponse(MedicationBase):
    id: int
    patient_uid: str
    created_at: datetime

    class Config:
        from_attributes = True

class MedicationUpdate(BaseModel):
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

# --- Surgeries ---
class SurgeryBase(BaseModel):
    procedure_name: str
    surgery_date: datetime
    hospital_name: Optional[str] = None
    surgeon_name: Optional[str] = None
    duration_hours: Optional[float] = None
    anaesthesia_type: Optional[str] = None
    outcome: Optional[str] = None
    complications: Optional[str] = None
    recovery_notes: Optional[str] = None

class SurgeryCreate(SurgeryBase):
    pass

class SurgeryResponse(SurgeryBase):
    id: int
    patient_uid: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Lab Results ---
class LabResultBase(BaseModel):
    test_name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    result_date: datetime
    status: Optional[str] = None
    ordered_by: Optional[str] = None
    notes: Optional[str] = None

class LabResultCreate(LabResultBase):
    pass

class LabResultResponse(LabResultBase):
    id: int
    patient_uid: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Documents ---
class DocumentResponse(BaseModel):
    id: int
    patient_uid: str
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    category: Optional[str] = None
    document_date: Optional[datetime] = None
    extracted_text: Optional[str] = None
    upload_date: datetime
    file_size_bytes: Optional[int] = None
    source: Optional[str] = 'manual'
    is_verified: Optional[bool] = False

    class Config:
        from_attributes = True

# --- AI Prediction / Diagnostic ---
class PredictionInput(BaseModel):
    patient_uid: str

class OverrideInput(BaseModel):
    ai_recommendation: str
    doctor_decision: str
    override_reason: str

# --- Doctor / Auth ---
class DoctorResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    department: Optional[str] = None
    license_no: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str
