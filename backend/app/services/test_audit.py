import os
import sys
import json

# Add parent of app to path (which is backend)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.services.ai_engine import ai_engine
from app.db.database import SessionLocal
from app.api.endpoints.predict import prepare_ai_features

def test_atram():
    uid = 'SR-000002'
    db = SessionLocal()
    clinical_data = prepare_ai_features(uid, db)
    
    print(f"--- [SRRIS] CLINICAL AUDIT START for {uid} ---")
    pipeline_results = ai_engine.run_full_diagnostic_pipeline(clinical_data)
    
    for stage in pipeline_results:
        print(f"\n[{stage['stage']}]")
        print(f"  {stage['message']}")
        if stage.get('data'):
            if 'findings' in stage['data']:
                for f in stage['data']['findings']:
                    print(f"    - {f}")
            elif 'probability' in stage['data']:
                print(f"  Risk Probability: {stage['data']['probability']}%")
    db.close()

if __name__ == "__main__":
    test_atram()
