"""
Doctor Notes Handwriting OCR Service
======================================
Uses Microsoft TrOCR (Transformer-based OCR) for handwritten text recognition.
Model: microsoft/trocr-base-handwritten (~400MB, downloads on first use)

Pipeline:
  1. Load image and split into line-height crops (text detection)
  2. Pass each crop through TrOCR → get text per line
  3. Combine lines into full text
  4. Apply medical NER to extract key clinical terms

Fallback: EasyOCR if TrOCR fails or is unavailable.
"""

import os
import numpy as np
from typing import List

from app.services.gpu_gate import gpu_enabled, gpu_gate

# ── TrOCR Singleton ─────────────────────────────────────────────────────────
_trocr_processor = None
_trocr_model = None
_trocr_ready = False
_trocr_device = "cpu"
_trocr_lock = None


def _load_trocr():
    """Load TrOCR model on first call (lazy loading to save startup time)."""
    global _trocr_processor, _trocr_model, _trocr_ready, _trocr_device, _trocr_lock
    if _trocr_lock is None:
        import threading
        _trocr_lock = threading.Lock()
    with _trocr_lock:
        if _trocr_ready:
            return True
    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        print("[TrOCR] Loading microsoft/trocr-base-handwritten (first run downloads ~400MB)...")
        _trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
        _trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
        _trocr_device = "cuda" if gpu_enabled() else "cpu"
        try:
            if _trocr_device == "cuda":
                with gpu_gate.use("trocr_init"):
                    _trocr_model.to(_trocr_device)
            else:
                _trocr_model.to(_trocr_device)
        except Exception as e:
            print(f"[TrOCR] Device move failed ({_trocr_device}), falling back to CPU: {e}")
            _trocr_device = "cpu"
        _trocr_ready = True
        print(f"[TrOCR] Model loaded successfully on {_trocr_device}.")
        return True
    except Exception as e:
        print(f"[TrOCR] Failed to load: {e}")
        return False


def _split_into_line_crops(image_pil, min_height=20, max_lines=30):
    """
    Split a document image into line-height crops for TrOCR.
    Uses horizontal projection profile to detect text rows.
    """
    import cv2
    import numpy as np
    from PIL import Image

    gray = np.array(image_pil.convert('L'))
    # Binarize
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Horizontal projection (row sum)
    h_proj = np.sum(binary, axis=1)
    
    # Find line boundaries (transitions from 0 to non-0)
    in_text = False
    line_starts = []
    line_ends = []
    
    for i, val in enumerate(h_proj):
        if val > 0 and not in_text:
            in_text = True
            line_starts.append(max(0, i - 3))
        elif val == 0 and in_text:
            in_text = False
            line_ends.append(min(gray.shape[0], i + 3))
    
    # If still in text at end
    if in_text:
        line_ends.append(gray.shape[0])
    
    # Merge very close lines (spacing < min_height)
    merged_starts = []
    merged_ends = []
    
    i = 0
    while i < len(line_starts):
        start = line_starts[i]
        end = line_ends[i] if i < len(line_ends) else gray.shape[0]
        
        while i + 1 < len(line_starts) and line_starts[i + 1] - end < min_height:
            i += 1
            end = line_ends[i] if i < len(line_ends) else gray.shape[0]
        
        if end - start >= min_height:
            merged_starts.append(start)
            merged_ends.append(end)
        i += 1
    
    # Crop into individual line images
    crops = []
    for start, end in zip(merged_starts[:max_lines], merged_ends[:max_lines]):
        crop = image_pil.crop((0, start, image_pil.width, end))
        crops.append(crop)
    
    return crops if crops else [image_pil]  # fallback to full image


def ocr_handwritten_image(image_path: str) -> str:
    """
    Main entry point: recognize handwritten text from a clinical notes image.
    Returns recognized text string.
    """
    from PIL import Image

    try:
        image_pil = Image.open(image_path).convert("RGB")
    except Exception as e:
        return f"[Error opening image: {e}]"
    
    # Try TrOCR first
    if _load_trocr():
        try:
            return _trocr_recognize(image_pil)
        except Exception as e:
            print(f"[TrOCR] Inference failed: {e}, falling back to EasyOCR")
    
    # Fallback: EasyOCR
    return _easyocr_fallback(image_path)


def _trocr_recognize(image_pil) -> str:
    """Run TrOCR on line crops of the image."""
    import torch
    
    crops = _split_into_line_crops(image_pil)
    recognized_lines = []
    
    for crop in crops:
        try:
            pixel_values = _trocr_processor(crop, return_tensors="pt").pixel_values
            if _trocr_device == "cuda":
                pixel_values = pixel_values.to(_trocr_device)
                with gpu_gate.use("trocr_generate"):
                    with torch.no_grad():
                        generated_ids = _trocr_model.generate(pixel_values, max_new_tokens=128)
            else:
                with torch.no_grad():
                    generated_ids = _trocr_model.generate(pixel_values, max_new_tokens=128)
            text = _trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            if text.strip():
                recognized_lines.append(text.strip())
        except Exception as e:
            print(f"[TrOCR] Line crop failed: {e}")
            continue
    
    if recognized_lines:
        return "\n".join(recognized_lines)
    return "[TrOCR produced no output — image may be too blurry or low contrast]"


def _easyocr_fallback(image_path: str) -> str:
    """Fallback to EasyOCR for handwriting (less accurate but always available)."""
    try:
        from app.services.easyocr_runtime import readtext_image_file
        results = readtext_image_file(image_path, ['en'], detail=0, paragraph=True)
        return "\n".join(results) if results else "[EasyOCR: No text detected]"
    except Exception as e:
        return f"[OCR Failed: {e}]"


def extract_clinical_terms(text: str) -> dict:
    """
    Simple rule-based medical NER to extract key info from doctor notes.
    Returns dict with findings, medications, diagnoses, instructions.
    """
    import re
    
    findings = {
        "medications": [],
        "diagnoses": [],
        "vitals": {},
        "instructions": [],
        "follow_up": None
    }
    
    lines = text.lower().split('\n')
    
    # Medication patterns: "Tab. Amlodipine 5mg OD" etc.
    med_pattern = re.compile(r'\b(tab\.?|cap\.?|inj\.?|syp\.?|drops?)\s+([a-z]+(?:\s+\d+\s*mg)?)', re.IGNORECASE)
    for line in lines:
        for m in med_pattern.finditer(line):
            findings["medications"].append(m.group(0).strip())
    
    # Vital patterns
    bp_match = re.search(r'bp\s*[:\-]?\s*(\d{2,3}/\d{2,3})', text, re.IGNORECASE)
    if bp_match:
        findings["vitals"]["blood_pressure"] = bp_match.group(1)
    
    hr_match = re.search(r'(?:hr|pulse|heart rate)\s*[:\-]?\s*(\d{2,3})\s*(?:bpm|/min)?', text, re.IGNORECASE)
    if hr_match:
        findings["vitals"]["heart_rate"] = hr_match.group(1) + " bpm"
    
    temp_match = re.search(r'temp(?:erature)?\s*[:\-]?\s*(\d{2,3}(?:\.\d)?)\s*[°]?[FC]?', text, re.IGNORECASE)
    if temp_match:
        findings["vitals"]["temperature"] = temp_match.group(1)
    
    # Follow-up
    fu_match = re.search(r'follow.?up\s+(?:in|after|on)?\s*(\d+\s*(?:days?|weeks?|months?))', text, re.IGNORECASE)
    if fu_match:
        findings["follow_up"] = fu_match.group(1)
    
    # Diagnoses (lines after "Diagnosis:", "Impression:", "D/D:")
    for line in lines:
        if re.match(r'(diagnosis|impression|d\/d|assessment)\s*:', line, re.IGNORECASE):
            diag = re.sub(r'^(diagnosis|impression|d\/d|assessment)\s*:\s*', '', line, flags=re.IGNORECASE).strip()
            if diag:
                findings["diagnoses"].append(diag)
    
    # Instructions (lines with advice keywords)
    for line in lines:
        if any(kw in line for kw in ['avoid', 'rest', 'diet', 'exercise', 'restrict', 'advise']):
            findings["instructions"].append(line.strip())
    
    return findings
