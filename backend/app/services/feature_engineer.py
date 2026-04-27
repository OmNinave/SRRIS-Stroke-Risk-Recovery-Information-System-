import pandas as pd
import numpy as np

def engineer_clinical_features(data: dict) -> dict:
    """
    Applies the 9 advanced interaction features from stroke-risk-prediction-ml 
    to the raw patient data before model inference.
    """
    enriched_data = data.copy()
    
    # Safe getters with defaults
    age = float(data.get('age', 50.0))
    bmi = float(data.get('bmi', 25.0))
    glucose = float(data.get('avg_glucose_level', 100.0) or data.get('BloodSugar', 100.0))
    hypertension = float(data.get('hypertension', 0) or data.get('HTN', 0))
    heart_disease = float(data.get('heart_disease', 0))
    
    # Smoking logic mapping
    smoking = data.get('smoking_status', 'Unknown')
    smoking_val = 1.0 if str(smoking).lower() in ['smokes', 'formerly smoked', 'true', '1'] else 0.0

    # 1. glucose_bmi_ratio
    enriched_data['glucose_bmi_ratio'] = glucose / bmi if bmi > 0 else 0.0
    
    # 2. age_hypertension
    enriched_data['age_hypertension'] = age * hypertension
    
    # 3. glucose_age_ratio
    enriched_data['glucose_age_ratio'] = glucose / age if age > 0 else 0.0
    
    # 4. bmi_age_product
    enriched_data['bmi_age_product'] = bmi * age
    
    # 5. is_senior
    is_senior = 1.0 if age > 60 else 0.0
    enriched_data['is_senior'] = is_senior
    
    # 6. heart_senior_interaction
    enriched_data['heart_senior_interaction'] = heart_disease * is_senior
    
    # 7. bmi_hypertension
    enriched_data['bmi_hypertension'] = bmi * hypertension
    
    # 8. age_squared
    enriched_data['age_squared'] = age ** 2
    
    # 9. glucose_heart
    enriched_data['glucose_heart'] = glucose * heart_disease
    
    # 10. smoke_age_interaction
    enriched_data['smoke_age_interaction'] = smoking_val * age
    
    # 11. young_without_risk (Safe young baseline)
    young_no_risk = 1.0 if (age < 35 and hypertension == 0 and heart_disease == 0 and glucose < 120 and bmi < 25) else 0.0
    enriched_data['young_without_risk'] = young_no_risk

    return enriched_data

def engineer_dataframe_features(df: __import__('pandas').DataFrame) -> __import__('pandas').DataFrame:
    """
    Vectorized version of engineer_clinical_features for pandas DataFrames.
    Used during model training and bulk evaluation.
    """
    df_out = df.copy()
    
    bmi = df_out['bmi']
    age = df_out['age']
    glucose = df_out['avg_glucose_level']
    htn = df_out['hypertension']
    heart = df_out['heart_disease']
    
    # Map smoking if present
    if 'smoking_status' in df_out.columns:
        smoking = df_out['smoking_status'].str.lower().isin(['smokes', 'formerly smoked', 'true', '1']).astype(float)
    else:
        smoking = 0.0
        
    df_out['glucose_bmi_ratio'] = np.where(bmi > 0, glucose / bmi, 0.0)
    df_out['age_hypertension'] = age * htn
    df_out['glucose_age_ratio'] = np.where(age > 0, glucose / age, 0.0)
    df_out['bmi_age_product'] = bmi * age
    
    df_out['is_senior'] = (age > 60).astype(float)
    df_out['heart_senior_interaction'] = heart * df_out['is_senior']
    df_out['bmi_hypertension'] = bmi * htn
    df_out['age_squared'] = age ** 2
    df_out['glucose_heart'] = glucose * heart
    df_out['smoke_age_interaction'] = smoking * age
    
    df_out['young_without_risk'] = ((age < 35) & (htn == 0) & (heart == 0) & (glucose < 120) & (bmi < 25)).astype(float)
    
    return df_out
