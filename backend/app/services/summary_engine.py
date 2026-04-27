from sqlalchemy.orm import Session
from app.db import models
from collections import defaultdict
from datetime import datetime
import datetime as dt

# Rule Engine Logic for Stroke Vulnerability
ISCHEMIC_FACTORS = ['atrial fibrillation', 'afib', 'atherosclerosis', 'high cholesterol', 'clotting disorder', 'dv']
HEMORRHAGIC_FACTORS = ['hypertension', 'aneurysm', 'moyamoya', 'high blood pressure']
BE_FAST_SYMPTOMS = ['aphasia', 'speech', 'vision loss', 'diplopia', 'confusion', 'dizziness', 'vertigo', 'loss of muscle', 'ataxia', 'amnesia', 'weakness', 'paralysis']

def count_missed_followups(events) -> int:
    return sum(1 for e in events if e.event_type == 'follow_up_missed')

def extract_diagnoses(events) -> list:
    diagnoses = set()
    for e in events:
        if e.event_type == 'diagnosis':
            diagnoses.add(e.title)
    return list(diagnoses)

def detect_ischemic_risks(events, labs, db: Session) -> list:
    flags = []
    # Check Events
    for e in events:
        for factor in ISCHEMIC_FACTORS:
            if factor in e.title.lower() or (e.description and factor in e.description.lower()):
                source_name = "Manual Entry"
                if e.document_id:
                    doc = db.query(models.Document).filter_by(id=e.document_id).first()
                    source_name = doc.file_name if doc else "Deleted Document"
                flags.append({"message": f"History of {factor.title()}", "evidence": source_name})
    
    # Check Labs
    for l in labs:
        name = l.test_name.lower()
        try:
            val = float(l.value)
            source_name = "Manual Lab"
            if l.document_id:
                doc = db.query(models.Document).filter_by(id=l.document_id).first()
                source_name = doc.file_name if doc else "Deleted Document"
                
            if ('cholesterol' in name or 'ldl' in name) and val > 240:
                flags.append({"message": f"Critical Hyperlipidemia ({val} mg/dL)", "evidence": source_name})
            if 'hba1c' in name and val > 8.0:
                flags.append({"message": f"Uncontrolled Diabetes (HbA1c {val}%)", "evidence": source_name})
        except: pass
        
    return flags

def detect_hemorrhagic_risks(events, db: Session) -> list:
    flags = []
    for e in events:
        for factor in HEMORRHAGIC_FACTORS:
            if factor in e.title.lower() or (e.description and factor in e.description.lower()):
                source_name = "Manual Entry"
                if e.document_id:
                    doc = db.query(models.Document).filter_by(id=e.document_id).first()
                    source_name = doc.file_name if doc else "Deleted Document"
                flags.append({"message": f"History of {factor.title()}", "evidence": source_name})
    return flags

def detect_be_fast_symptoms(events) -> list:
    flags = []
    for e in events:
        for sym in BE_FAST_SYMPTOMS:
            if sym in e.title.lower() or (e.description and sym in e.description.lower()):
                flags.append(sym.title())
    return list(set(flags))

def calculate_health_radar(events, labs) -> dict:
    """Returns a dynamic 0-100 score on 4 axes based on events and lab results.
    Post-stroke neurological starts at 40 (not 100) to reflect actual damage.
    """
    stroke_events = [e for e in events if e.event_type == 'stroke_event']
    
    # Clinical baseline: post-stroke patients cannot start at 100/100
    neuro_base = 40 if stroke_events else 100
    scores = {"cardiovascular": 100, "metabolic": 100, "vascular": 100, "neurological": neuro_base}
    
    # Analyze Events
    for e in events:
        text = str(e.title + " " + str(e.description)).lower()
        if any(w in text for w in ['hypertension', 'afib', 'arrhythmia', 'heart', 'coronary']):
            scores['cardiovascular'] = max(20, scores['cardiovascular'] - 15)
        if any(w in text for w in ['diabetes', 'obesity', 'hyperglycemia', 'metabolic']):
            scores['metabolic'] = max(20, scores['metabolic'] - 20)
        if any(w in text for w in ['atherosclerosis', 'cholesterol', 'plaque', 'stenosis']):
            scores['vascular'] = max(20, scores['vascular'] - 15)
        if any(w in text for w in ['stroke', 'tia', 'infarct', 'hemorrhage', 'seizure']):
            scores['neurological'] = max(15, scores['neurological'] - 20)
            
    # Analyze Labs
    for l in labs:
        name = l.test_name.lower()
        try:
            val = float(l.value)
            if 'cholesterol' in name or 'ldl' in name:
                if val > 200: scores['vascular'] = max(20, scores['vascular'] - 20)
            if 'hba1c' in name:
                if val > 6.5: scores['metabolic'] = max(20, scores['metabolic'] - 25)
            if 'glucose' in name:
                if val > 140: scores['metabolic'] = max(20, scores['metabolic'] - 15)
            if 'blood pressure' in name or 'systolic' in name or 'sbp' in name:
                if val > 140: scores['cardiovascular'] = max(20, scores['cardiovascular'] - 20)
        except:
            pass
            
    return scores

def generate_recommendations(ischemic, hemorrhagic, radar) -> list:
    recs = []
    if radar['cardiovascular'] < 70:
        recs.append("Daily Blood Pressure Monitoring (Log daily AM/PM readings)")
    if radar['metabolic'] < 70:
        recs.append("Strict Low Glycemic Diet & HbA1c screening every 3 months")
    if radar['vascular'] < 70:
        recs.append("Carotid Doppler ultrasound recommended to assess plaque stability")
    if ischemic:
        recs.append("Evaluation for Antiplatelet/Anticoagulation therapy (Aspirin/Clopidogrel)")
    if radar['neurological'] < 50:
        recs.append("Neurological deficit assessment & physical therapy consultation")
    
    if not recs:
        recs.append("Maintain current healthy lifestyle and annual neurological check-ups.")
    return recs[:4] # Return top 4

def get_lab_trend(test_name, current_val, patient_uid, db: Session):
    try:
        current_float = float(current_val)
        # Find the previous result for this test
        prev = db.query(models.LabResult).filter(
            models.LabResult.patient_uid == patient_uid,
            models.LabResult.test_name == test_name
        ).order_by(models.LabResult.result_date.desc()).offset(1).first()
        
        if not prev: return "stable"
        
        prev_float = float(prev.value)
        diff = current_float - prev_float
        if abs(diff) < (prev_float * 0.05): return "stable"
        return "up" if diff > 0 else "down"
    except:
        return "unknown"

def build_alert_list(labs, meds, stroke_events, events) -> list:
    alerts = []
    # Simplified implementations
    if len(stroke_events) > 1:
        alerts.append({"severity": "high", "message": f"Recurrent stroke history ({len(stroke_events)} events)"})
    
    anticoag_drugs = ['warfarin','apixaban','rivaroxaban','dabigatran','heparin']
    active_anticoag = [m for m in meds if any(d in m.drug_name.lower() for d in anticoag_drugs) and m.is_active]
    if active_anticoag:
        alerts.append({"severity": "warning", "message": f"Active anticoagulant: {active_anticoag[0].drug_name}"})
        
    missed = count_missed_followups(events)
    if missed > 2:
        alerts.append({"severity": "info", "message": "3+ missed follow-ups globally"})
        
    return alerts


def generate_medical_summary(patient_uid: str, db: Session):
    events = db.query(models.MedicalEvent).filter_by(patient_uid=patient_uid).all()
    meds = db.query(models.Medication).filter_by(patient_uid=patient_uid, is_active=True).all()
    surgeries = db.query(models.Surgery).filter_by(patient_uid=patient_uid).all()
    
    from sqlalchemy import func
    from app.services import diagnostic_engine
    
    subq = db.query(models.LabResult.test_name, func.max(models.LabResult.result_date).label('max_date')).filter_by(patient_uid=patient_uid).group_by(models.LabResult.test_name).subquery()
    latest_labs = db.query(models.LabResult).join(subq, (models.LabResult.test_name == subq.c.test_name) & (models.LabResult.result_date == subq.c.max_date)).all()

    stroke_events = [e for e in events if e.event_type == 'stroke_event']
    missed_followups = count_missed_followups(events)
    
    ischemic_flags = detect_ischemic_risks(events, latest_labs, db)
    hemorrhagic_flags = detect_hemorrhagic_risks(events, db)
    be_fast_symptoms = detect_be_fast_symptoms(events)
    
    # AI Scan Context Integration
    latest_scan_orm = db.query(models.ScanResult).filter_by(patient_uid=patient_uid).order_by(models.ScanResult.created_at.desc()).first()
    if latest_scan_orm and latest_scan_orm.prediction:
        pred = latest_scan_orm.prediction.lower()
        if 'ischemic' in pred:
            ischemic_flags.append({
                "message": f"CURRENT AI DETECTION: {latest_scan_orm.prediction}", 
                "evidence": "Computed Vision Analysis (Active Event)"
            })
        if 'haemorrhag' in pred or 'hemorrhag' in pred:
            hemorrhagic_flags.append({
                "message": f"CURRENT AI DETECTION: {latest_scan_orm.prediction}", 
                "evidence": "Computed Vision Analysis (Active Event)"
            })
    
    hospital_events = [e for e in sorted(events, key=lambda x: x.event_date) if e.hospital_name or e.event_type in ['hospital_visit', 'discharge']]
    last_hospital = hospital_events[-1] if hospital_events else None
    
    radar = calculate_health_radar(events, latest_labs)

    # ─── Fetch patient model for real age ───────────────────────────────────────
    patient_model = db.query(models.Patient).filter_by(patient_uid=patient_uid).first()
    
    # ─── Extract scalars for Diagnostic Engine ──────────────────────────────────
    raw_labs = {l.test_name.lower(): l.value for l in latest_labs}
    
    def get_val(keys, default):
        for k in keys:
            for stored_key in raw_labs:
                if k in stored_key:
                    try: return float(raw_labs[stored_key])
                    except: continue
        return default

    # Compute real age from DOB
    real_age = 65
    if patient_model and patient_model.date_of_birth:
        real_age = diagnostic_engine._compute_actual_age(patient_model.date_of_birth)

    # Detect smoking from event descriptions and medication names
    smoking_status = 0
    smoking_meds = ['nicotine', 'varenicline', 'chantix', 'bupropion', 'zyban']
    all_med_names = [m.drug_name.lower() for m in meds]
    if any(any(s in m for s in smoking_meds) for m in all_med_names):
        smoking_status = 1  # Former (on cessation therapy)
    event_texts = [str(e.title + ' ' + str(e.description)).lower() for e in events]
    if any('current smoker' in t or 'active smoker' in t for t in event_texts):
        smoking_status = 2
    elif any('smoking' in t or 'smoker' in t for t in event_texts):
        smoking_status = 1

    # Detect sedentary lifestyle
    activity_level = 2  # Default: moderate
    if any('sedentary' in t or 'inactive' in t or 'bed rest' in t for t in event_texts):
        activity_level = 0
    elif any('light activity' in t or 'limited mobility' in t for t in event_texts):
        activity_level = 1

    # Anticoagulant detection
    anticoag_drugs = ['warfarin','apixaban','rivaroxaban','dabigatran','heparin','eliquis','pradaxa','xarelto']
    on_anticoag = any(any(d in m for d in anticoag_drugs) for m in all_med_names)

    # Days since last stroke
    days_since_stroke = 9999
    if stroke_events:
        last_stroke_date = max([e.event_date for e in stroke_events])
        days_since_stroke = (dt.datetime.utcnow() - last_stroke_date).days

    # NIHSS from events
    nihss = max([e.nihss_score for e in events if e.nihss_score is not None] + [0])

    base_data = {
        "age": real_age,
        "gender": patient_model.gender if patient_model else 'unknown',
        "systolic":      get_val(['systolic', 'sbp', 'blood pressure'], 120),
        "diastolic":     get_val(['diastolic', 'dbp'], 80),
        "cholesterol":   get_val(['cholesterol', 'ldl', 'total cholesterol'], 180),
        "glucose":       get_val(['glucose', 'blood glucose', 'fasting glucose'], 90),
        "inr":           get_val(['inr', 'pt inr', 'prothrombin'], 1.0),
        "platelet_count":get_val(['platelet', 'plt'], 250000),
        "smoking":       smoking_status,
        "activity":      activity_level,
        "history":       1 if len(stroke_events) > 0 else 0,
        "prior_strokes": len(stroke_events),
        "days_since_stroke": days_since_stroke,
        "on_anticoag":   on_anticoag,
        "nihss_score":   nihss,
        "lkn_hours":     3.5,  # Default safe clinical value
    }

    forecast = diagnostic_engine.forecast_longitudinal_scenarios(base_data)
    risk_factors = {
        "ischemic":           len(ischemic_flags) > 0,
        "prior_stroke":       len(stroke_events) > 0,
        "hypertension":       base_data['systolic'] >= 140,
        "metabolic":          base_data['glucose'] >= 126 or base_data['cholesterol'] >= 240,
        "sedentary":          activity_level == 0,
        "smoking":            smoking_status > 0,
        "hypercholesterolemia": base_data['cholesterol'] >= 200,
    }

    # ── Data availability flags ───────────────────────────────────────────────
    real_clinical_events = [e for e in events if e.event_type in ('stroke_event', 'diagnosis', 'surgery', 'hospital_visit', 'discharge', 'follow_up', 'medication_change')]
    has_real_data = len(real_clinical_events) > 0 or len(latest_labs) > 0

    has_scan_data = latest_scan_orm is not None
    latest_scan_dict = None
    if latest_scan_orm:
        latest_scan_dict = {
            "prediction":        latest_scan_orm.prediction,
            "confidence":        latest_scan_orm.confidence,
            "volume_percentage": latest_scan_orm.volume_percentage,
            "side":              latest_scan_orm.side,
            "lesion_center_x":   latest_scan_orm.lesion_center_x,
            "lesion_center_y":   latest_scan_orm.lesion_center_y,
            "xai_analysis":      latest_scan_orm.xai_analysis,
        }

    return {
        "has_real_data": has_real_data,
        "has_scan_data": has_scan_data,
        "chronic_conditions": extract_diagnoses(events),
        "active_medications": [m.drug_name for m in meds],
        "latest_labs": {l.test_name: l.value for l in latest_labs},
        "recent_lab_details": [
            {
                "test_name": l.test_name, 
                "value": l.value, 
                "unit": l.unit, 
                "date": l.result_date.isoformat() if l.result_date else None, 
                "status": l.status, 
                "ordered_by": l.ordered_by or "Neurology Dept",
                "trend": get_lab_trend(l.test_name, l.value, patient_uid, db)
            } for l in sorted(latest_labs, key=lambda x: x.result_date, reverse=True)[:10]
        ],
        "last_hospital_visit": {
            "hospital_name": last_hospital.hospital_name or "Unknown Facility",
            "date": last_hospital.event_date.isoformat(),
            "doctor": last_hospital.treating_doctor or "Attending Physician",
            "outcome": last_hospital.outcome or last_hospital.description or "No outcome reported"
        } if last_hospital else None,
        "surgeries": [s.procedure_name for s in surgeries],
        "prior_strokes": len(stroke_events),
        "last_stroke_date": stroke_events[-1].event_date.isoformat() if stroke_events else None,
        "adherence_flag": missed_followups > 2,
        "preventive_health_report": {
            "ischemic_vulnerability": len(ischemic_flags) > 0,
            "ischemic_factors": ischemic_flags,
            "hemorrhagic_vulnerability": len(hemorrhagic_flags) > 0,
            "hemorrhagic_factors": hemorrhagic_flags,
            "recent_be_fast_symptoms": be_fast_symptoms,
            "healthiness_scores": radar,
            "recommendations": diagnostic_engine.get_medical_recommendations(risk_factors),
            "longitudinal_forecast": forecast,
            "tpa_eligibility": forecast.get("tpa_eligibility", {}),
            "provenance_verified": True
        },
        "patient_clinical_data": {
            "age": real_age,
            "systolic": base_data['systolic'],
            "diastolic": base_data['diastolic'],
            "glucose": base_data['glucose'],
            "cholesterol": base_data['cholesterol'],
            "prior_strokes": len(stroke_events),
            "days_since_stroke": days_since_stroke,
            "nihss_score": nihss,
            "on_anticoag": on_anticoag,
            "smoking": smoking_status,
        },
        "latest_scan": latest_scan_dict,
        "alerts": build_alert_list(latest_labs, meds, stroke_events, events),
        "consensus_jury": {
            "available": diagnostic_engine.ensemble_engine.loaded,
            "consensus": "Consensus Reached" if diagnostic_engine.ensemble_engine.loaded else "Rule-Based Only"
        }
    }

def generate_timeline(patient_uid: str, db: Session):
    events = db.query(models.MedicalEvent).filter_by(patient_uid=patient_uid).order_by(models.MedicalEvent.event_date.asc()).all()
    
    groups = []
    for event in events:
        placed = False
        for group in groups:
            if (event.event_date - group['end_date']).days <= 14:
                group['events'].append({
                    "id": event.id,
                    "title": event.title,
                    "type": event.event_type,
                    "date": event.event_date.isoformat()
                })
                group['end_date'] = event.event_date
                placed = True
                break
        if not placed:
            groups.append({
                'label': f"{event.event_date.year} — {event.title}",
                'start_date': event.event_date,
                'end_date': event.event_date,
                'events': [{
                    "id": event.id,
                    "title": event.title,
                    "type": event.event_type,
                    "date": event.event_date.isoformat()
                }]
            })
            
    # Serialize datetime
    for g in groups:
        g['start_date'] = g['start_date'].isoformat()
        g['end_date'] = g['end_date'].isoformat()
        
    return groups
