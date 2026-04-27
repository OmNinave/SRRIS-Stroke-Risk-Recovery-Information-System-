"""
Lab Report Parser Service
==========================
Extracts structured data from pathology/biochemistry/hematology lab reports.
Pipeline:
  1. EasyOCR extracts raw text from the image
  2. Regex patterns identify lab test tables (name | value | unit | reference range)
  3. Auto-determines if values are Normal / Abnormal / Critical
  4. Returns structured list ready to insert as LabResult DB rows

Handles common Indian lab report formats:
  - Metro Plus Pathology, SRL Diagnostics, Dr Lal Pathlabs, Thyrocare etc.
  - Biochemistry, Hematology, Lipid Profile, Kidney Function, Liver Function
"""

import re
import os
from typing import List, Dict, Any, Optional

# ── Common Lab Test Reference Ranges (Indian clinical standards) ─────────────
KNOWN_RANGES = {
    "haemoglobin":    {"min": 12.0, "max": 17.0, "unit": "g/dL"},
    "hemoglobin":     {"min": 12.0, "max": 17.0, "unit": "g/dL"},
    "hb":             {"min": 12.0, "max": 17.0, "unit": "g/dL"},
    "rbc":            {"min": 4.5,  "max": 6.5,  "unit": "million/cmm"},
    "wbc":            {"min": 4000, "max": 11000, "unit": "/cmm"},
    "platelet":       {"min": 150000, "max": 400000, "unit": "/cmm"},
    "platelets":      {"min": 150000, "max": 400000, "unit": "/cmm"},
    "glucose":        {"min": 70,   "max": 110,  "unit": "mg/dL"},
    "blood glucose":  {"min": 70,   "max": 110,  "unit": "mg/dL"},
    "fasting":        {"min": 70,   "max": 100,  "unit": "mg/dL"},
    "urea":           {"min": 15,   "max": 45,   "unit": "mg/dL"},
    "creatinine":     {"min": 0.6,  "max": 1.4,  "unit": "mg/dL"},
    "uric acid":      {"min": 3.5,  "max": 7.5,  "unit": "mg/dL"},
    "sodium":         {"min": 135,  "max": 145,  "unit": "mmol/L"},
    "potassium":      {"min": 3.5,  "max": 5.0,  "unit": "mmol/L"},
    "cholesterol":    {"min": 0,    "max": 200,  "unit": "mg/dL"},
    "triglyceride":   {"min": 0,    "max": 150,  "unit": "mg/dL"},
    "hdl":            {"min": 40,   "max": 999,  "unit": "mg/dL"},
    "ldl":            {"min": 0,    "max": 130,  "unit": "mg/dL"},
    "bilirubin":      {"min": 0.2,  "max": 1.2,  "unit": "mg/dL"},
    "sgot":           {"min": 0,    "max": 40,   "unit": "U/L"},
    "sgpt":           {"min": 0,    "max": 45,   "unit": "U/L"},
    "alt":            {"min": 0,    "max": 45,   "unit": "U/L"},
    "ast":            {"min": 0,    "max": 40,   "unit": "U/L"},
    "tsh":            {"min": 0.4,  "max": 4.0,  "unit": "mIU/L"},
    "t3":             {"min": 80,   "max": 200,  "unit": "ng/dL"},
    "t4":             {"min": 5.0,  "max": 12.0, "unit": "µg/dL"},
}


def _determine_status(test_name: str, value_str: str, ref_low: Optional[str] = None, ref_high: Optional[str] = None) -> str:
    """Determine Normal/Abnormal/Critical based on value vs reference range."""
    try:
        # Extract numeric value
        val = float(re.sub(r'[^\d.]', '', value_str))

        # Try to parse provided reference range first
        if ref_low and ref_high:
            lo = float(re.sub(r'[^\d.]', '', ref_low))
            hi = float(re.sub(r'[^\d.]', '', ref_high))
            if val < lo * 0.7 or val > hi * 1.5:
                return "critical"
            if val < lo or val > hi:
                return "abnormal"
            return "normal"

        # Fall back to known ranges
        key = test_name.lower().strip()
        for known_key, known_range in KNOWN_RANGES.items():
            if known_key in key:
                lo = known_range["min"]
                hi = known_range["max"]
                if val < lo * 0.7 or val > hi * 1.5:
                    return "critical"
                if val < lo or val > hi:
                    return "abnormal"
                return "normal"
    except (ValueError, TypeError):
        pass
    return "normal"


def _parse_reference_range(ref_str: str):
    """Parse '70-110' or '< 200' or '> 40' into (low, high) tuple."""
    if not ref_str:
        return None, None
    ref_str = ref_str.strip()
    
    # Range format: "70-110" or "70 - 110" or "70 to 110"
    match = re.match(r'([\d.]+)\s*[-–to]+\s*([\d.]+)', ref_str, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    
    # Less than: "< 200" → (0, 200)
    match = re.match(r'<\s*([\d.]+)', ref_str)
    if match:
        return "0", match.group(1)
    
    # Greater than: "> 40" → (40, 999999)
    match = re.match(r'>\s*([\d.]+)', ref_str)
    if match:
        return match.group(1), "999999"
    
    return None, None


def parse_lab_report(ocr_text: str) -> List[Dict[str, Any]]:
    """
    Parse OCR text from a lab report into structured LabResult records.
    Returns a list of dicts compatible with the LabResult DB model.
    """
    results = []
    lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]

    # Pattern 1: "Test Name    Value    Unit    Ref Range"
    # Match lines that contain a numeric value with optional unit
    row_pattern = re.compile(
        r'^(.{3,40}?)\s{2,}([\d.]+\s*[HhLl\*]?)\s{1,}([a-zA-Z/%µ]*)\s{0,}([\d.\-<> ]*)?$'
    )

    # Pattern 2: "Test Name : Value Unit (Ref: Low-High)"
    colon_pattern = re.compile(
        r'^(.{3,40}?)\s*[:=]\s*([\d.]+)\s*([a-zA-Z/%µ]*)\s*(?:\(?(?:Ref|Reference|Normal)?:?\s*([\d.\-–<> ]+)\)?)?'
    )

    for line in lines:
        # Skip header rows, section titles
        if re.match(r'^(test|investigation|analyte|parameter|result|reference|biological|normal|description|unit|report|patient|doctor|date|lab|hospital|sr\.?\s*no\.?|s\.?\s*no\.?)', 
                    line, re.IGNORECASE):
            continue
        if len(line) < 5 or not re.search(r'\d', line):
            continue

        matched = False
        for pattern in [row_pattern, colon_pattern]:
            m = pattern.match(line)
            if m:
                test_name = m.group(1).strip(' .,:-')
                value_str = m.group(2).strip()
                unit = m.group(3).strip() if len(m.groups()) > 2 else ""
                ref_str = m.group(4).strip() if len(m.groups()) > 3 and m.group(4) else ""

                ref_low, ref_high = _parse_reference_range(ref_str)
                status = _determine_status(test_name, value_str, ref_low, ref_high)

                ref_range_display = ""
                if ref_low and ref_high and ref_high != "999999":
                    ref_range_display = f"{ref_low} - {ref_high} {unit}".strip()
                elif ref_str:
                    ref_range_display = ref_str

                results.append({
                    "test_name": test_name,
                    "value": value_str,
                    "unit": unit,
                    "reference_range": ref_range_display,
                    "status": status
                })
                matched = True
                break

    # Fallback for EasyOCR vertical text (1 value per line)
    if not results and len(lines) > 5:
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # If next line is a number
            if i + 1 < len(lines) and re.match(r'^[\d.]+$', lines[i+1].strip()):
                test_name = line
                if not re.search(r'(Date|Time|Age|ID|No\.|Number|Page)', test_name, re.IGNORECASE) and len(test_name) > 1:
                    val_line = lines[i+1].strip()
                    unit_line = ""
                    ref_line = ""
                    advance = 2
                    
                    if i + 2 < len(lines):
                        p_unit = lines[i+2].strip()
                        if not re.match(r'^[\d.]+$', p_unit) and "-" not in p_unit and len(p_unit) <= 15:
                            unit_line = p_unit
                            advance = 3
                            if i + 3 < len(lines):
                                p_ref = lines[i+3].strip()
                                if "-" in p_ref or "<" in p_ref or ">" in p_ref or re.search(r'\d', p_ref):
                                    ref_line = p_ref
                                    advance = 4
                        elif "-" in p_unit or "<" in p_unit or ">" in p_unit:
                            ref_line = p_unit
                            advance = 3
                    
                    ref_low, ref_high = _parse_reference_range(ref_line)
                    status = _determine_status(test_name, val_line, ref_low, ref_high)
                    
                    results.append({
                        "test_name": test_name,
                        "value": val_line,
                        "unit": unit_line,
                        "reference_range": ref_line,
                        "status": status
                    })
                    i += advance
                    continue
            i += 1

    return results


def extract_lab_summary(results: List[Dict]) -> str:
    """Generate a human-readable summary of lab findings."""
    if not results:
        return "No structured lab data could be extracted."
    
    abnormal = [r for r in results if r["status"] in ["abnormal", "critical"]]
    normal = [r for r in results if r["status"] == "normal"]
    
    lines = [f"Lab Report Summary: {len(results)} tests extracted."]
    
    if abnormal:
        lines.append(f"\n⚠️ ABNORMAL VALUES ({len(abnormal)}):")
        for r in abnormal:
            flag = "🔴 CRITICAL" if r["status"] == "critical" else "🟡 ABNORMAL"
            lines.append(f"  {flag} — {r['test_name']}: {r['value']} {r['unit']} (Ref: {r['reference_range']})")
    
    if normal:
        lines.append(f"\n✅ NORMAL VALUES ({len(normal)}):")
        for r in normal[:5]:  # Show first 5 normal
            lines.append(f"  {r['test_name']}: {r['value']} {r['unit']}")
        if len(normal) > 5:
            lines.append(f"  ... and {len(normal) - 5} more normal values.")
    
    return "\n".join(lines)
