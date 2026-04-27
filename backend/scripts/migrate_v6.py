import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), "..", "srris_production_v5.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE patients ADD COLUMN ward_area VARCHAR(100)')
    except Exception as e: print(e)
    try:
        c.execute('ALTER TABLE patients ADD COLUMN bed_no VARCHAR(50)')
    except Exception as e: print(e)
    try:
        c.execute('ALTER TABLE patients ADD COLUMN primary_diagnosis VARCHAR(255)')
    except Exception as e: print(e)
    
    try:
        c.execute("UPDATE patients SET ward_area='Neurology ICU', bed_no='Bed-14', primary_diagnosis='Acute Ischemic Stroke (L MCA)' WHERE patient_uid='SR-000002'")
        conn.commit()
    except Exception as e: print(e)
    
    conn.close()
    print("DB Altered Successfully.")

if __name__ == "__main__":
    migrate()
