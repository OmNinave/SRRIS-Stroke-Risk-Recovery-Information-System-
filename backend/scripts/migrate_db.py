"""
SRRIS Database Migration Script
Run from: backend/
Command: python scripts/migrate_db.py

Safely adds missing columns to the existing SQLite database
without dropping any data. Safe to run multiple times (idempotent).
"""
import os
import sqlite3

# Resolve the DB path exactly as database.py does
_DB_DIR = os.path.dirname(os.path.abspath(__file__))   # .../scripts/
_DB_PATH = os.path.join(_DB_DIR, "..", "srris_production_v5.db")
_DB_PATH = os.path.normpath(_DB_PATH)

print("=" * 60)
print("SRRIS DATABASE MIGRATION")
print(f"Target DB: {_DB_PATH}")
print("=" * 60)

if not os.path.exists(_DB_PATH):
    print("[ERROR] Database file not found. Start the server once first to create it.")
    exit(1)

conn = sqlite3.connect(_DB_PATH)
cursor = conn.cursor()

# ── Whitelist guard against SQL injection ──────────────────────────
# Only tables and types that are known to exist in our schema are allowed.
_ALLOWED_TABLES = {"patients", "medical_events", "medical_history", "doctors",
                   "medications", "surgeries", "lab_results", "documents", "scan_results"}
_ALLOWED_TYPES  = {"VARCHAR", "TEXT", "INTEGER", "FLOAT", "BOOLEAN", "DATETIME"}

def _validate_identifier(value: str, allowed: set, label: str):
    """Raises ValueError if value is not in the allowed whitelist — prevents SQL injection."""
    if value.upper() not in {a.upper() for a in allowed}:
        raise ValueError(f"[SECURITY] Unsafe {label}: '{value}'. Must be one of: {allowed}")

# ── Helper: add a column only if it doesn't already exist ──────────
def add_column_if_missing(table: str, column: str, col_type: str, default=None):
    # Security: validate table name and column type against whitelist
    _validate_identifier(table, _ALLOWED_TABLES, "table name")
    _validate_identifier(col_type.split("(")[0], _ALLOWED_TYPES, "column type")

    cursor.execute("SELECT name FROM pragma_table_info(?)", (table,))
    existing = [row[0] for row in cursor.fetchall()]
    if column not in existing:
        if default is not None:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT '{default}'")
        else:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"  [ADDED]   {table}.{column} ({col_type})")
    else:
        print(f"  [EXISTS]  {table}.{column} — skipped")


# ── Migrations: patients table ──────────────────────────────────────
print("\n[patients] Checking columns...")
add_column_if_missing("patients", "ethnicity",          "VARCHAR",  "Unknown")
add_column_if_missing("patients", "photo_url",          "VARCHAR",  "")
add_column_if_missing("patients", "ward_area",          "VARCHAR",  "")
add_column_if_missing("patients", "bed_no",             "VARCHAR",  "")
add_column_if_missing("patients", "primary_diagnosis",  "VARCHAR",  "")
add_column_if_missing("patients", "patient_category",   "VARCHAR",  "General")
add_column_if_missing("patients", "admission_type",     "VARCHAR",  "Elective")
add_column_if_missing("patients", "is_in_isolation",    "BOOLEAN",  "0")
add_column_if_missing("patients", "isolation_reason",   "TEXT",     "")
add_column_if_missing("patients", "dnr_status",         "BOOLEAN",  "0")

# ── Migrations: medical_history table ──────────────────────────────
print("\n[medical_history] Checking columns...")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='medical_history'")
if cursor.fetchone():
    add_column_if_missing("medical_history", "nihss_score",             "FLOAT",   "0")
    add_column_if_missing("medical_history", "lkn_hours",               "FLOAT",   "99.0")
    add_column_if_missing("medical_history", "is_hemorrhagic",          "BOOLEAN", "0")
    add_column_if_missing("medical_history", "ethnicity",               "VARCHAR", "Unknown")
    add_column_if_missing("medical_history", "smoking",                 "INTEGER", "0")
    add_column_if_missing("medical_history", "alcohol_use",             "BOOLEAN", "0")
    add_column_if_missing("medical_history", "physical_activity_level", "VARCHAR", "Moderate")
    add_column_if_missing("medical_history", "medication_adherence_score","FLOAT",  "0.8")
    add_column_if_missing("medical_history", "platelet_count",          "FLOAT",   "250000")
    add_column_if_missing("medical_history", "inr_value",               "FLOAT",   "1.0")
    add_column_if_missing("medical_history", "days_since_last_stroke",  "FLOAT",   "9999")
    add_column_if_missing("medical_history", "systolic_bp",             "FLOAT",   "120")
    add_column_if_missing("medical_history", "diastolic_bp",            "FLOAT",   "80")
else:
    print("  [SKIP] medical_history table not found — will be created on server start.")

# ── Commit and close ────────────────────────────────────────────────
conn.commit()
conn.close()

print("\n" + "=" * 60)
print("MIGRATION COMPLETE — Restart the backend server.")
print("=" * 60)
