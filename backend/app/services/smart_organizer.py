import os
import shutil
import time
from typing import Optional, Tuple

# All valid clinical categories
VALID_CATEGORIES = [
    "ECG_Signals",
    "Radiology_Scans",
    "Clinical_Reports",
    "Laboratory_Tests",
    "Doctor_Notes",
    "General_Records",
]

def categorize_file(filename: str) -> str:
    """Fallback: categorize by keywords in filename."""
    name = filename.lower()
    if any(k in name for k in ['ecg', 'ekg', 'signal', 'waveform', 'holter', 'electrocardiogram']):
        return "ECG_Signals"
    if any(k in name for k in ['mri', 'ct', 'xray', 'x-ray', 'scan', 'axial', 'coronal', 'sagittal', 'radiology', 'brain', 'chest', 'dicom']):
        return "Radiology_Scans"
    if any(k in name for k in ['discharge', 'admission', 'opd', 'clinical', 'history', 'summary', 'paper', 'prescription']):
        return "Clinical_Reports"
    if any(k in name for k in ['test', 'lab', 'blood', 'analysis', 'result', 'cbc', 'urine', 'culture', 'pathology', 'biochem']):
        return "Laboratory_Tests"
    if any(k in name for k in ['note', 'doctor', 'dr', 'physician', 'handwrite', 'consult', 'prescription', 'rx']):
        return "Doctor_Notes"
    return "General_Records"

def organize_document(
    patient_uid: str,
    file_path: str,
    filename: str,
    suggested_category: Optional[str] = None
) -> Tuple[str, str]:
    """
    Move a file from temp location to its correct clinical folder.
    
    Returns:
        Tuple of (category: str, final_absolute_path: str)
    """
    # Priority: use user-provided category if it's a known valid one, EXCEPT if it's the generic default
    if suggested_category and suggested_category in VALID_CATEGORIES and suggested_category != "General_Records":
        category = suggested_category
    else:
        # Fall back to keyword detection
        smart_cat = categorize_file(filename)
        # If smart detection found a specific category, use it. Otherwise use suggested (or General_Records)
        if smart_cat != "General_Records":
            category = smart_cat
        else:
            category = suggested_category if suggested_category else "General_Records"

    # Build destination
    base_uploads = os.path.join(os.getcwd(), "uploads")
    category_dir = os.path.join(base_uploads, patient_uid, category)
    os.makedirs(category_dir, exist_ok=True)

    target_path = os.path.join(category_dir, filename)

    # If already in place (same absolute path), return immediately
    if os.path.abspath(file_path) == os.path.abspath(target_path):
        return category, target_path

    # Handle filename collision
    if os.path.exists(target_path):
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(time.time())}{ext}"
        target_path = os.path.join(category_dir, filename)

    shutil.move(file_path, target_path)
    return category, target_path
