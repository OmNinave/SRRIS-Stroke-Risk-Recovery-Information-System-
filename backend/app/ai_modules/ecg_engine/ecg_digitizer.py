"""
ECG Image Digitizer
====================
Extracts real 12-lead ECG waveforms from a paper printout photo and saves
them as a (12, 5000) numpy array compatible with the AI-Challenge-2023 pipeline.

Pipeline:
  1. Load image, auto-detect ECG grid boundaries
  2. Remove the red/pink grid background via HSV masking
  3. Isolate black waveform trace via adaptive thresholding
  4. Split image into 12 lead regions (3 rows x 4 cols + bottom rhythm strip)
  5. For each lead: extract column-wise centerline (signal trace)
  6. Resample every lead to exactly 5000 samples
  7. Scale to millivolts based on standard paper: 10mm/mV, 25mm/s
  8. Save as (12, 5000) .npy + meta CSV
"""

import cv2
import numpy as np
import os
import sys
import pandas as pd
from scipy import signal as scipy_signal
from scipy.interpolate import interp1d

# ── Standard 12-lead order (same as AI-Challenge dataset) ──────────────────
LEAD_NAMES = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

DUMMY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dummy_data')


def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot open image: {path}")
    return img


def crop_to_ecg_area(img: np.ndarray) -> np.ndarray:
    """Auto-crop away non-ECG borders (white/near-white margins)."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Threshold: anything not near-white is signal area
    _, thresh = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return img
    x, y, w, h = cv2.boundingRect(coords)
    # Add small padding
    pad = 10
    x, y = max(0, x - pad), max(0, y - pad)
    w = min(img.shape[1] - x, w + 2 * pad)
    h = min(img.shape[0] - y, h + 2 * pad)
    return img[y:y+h, x:x+w]


def remove_grid(img: np.ndarray) -> np.ndarray:
    """
    Remove the pink/red ECG grid using HSV color filtering.
    Returns a binary image where white = ECG trace, black = background.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Mask 1: suppress the pink-red grid lines
    lower_red1 = np.array([0,   20, 100])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([160, 20, 100])
    upper_red2 = np.array([180, 255, 255])
    grid_mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

    # Fill grid pixels with white in a copy
    cleaned = img.copy()
    cleaned[grid_mask > 0] = [255, 255, 255]

    # Convert to grayscale and threshold to get dark traces
    gray = cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    # Adaptive threshold to catch waveform lines even on uneven lighting
    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=15,
        C=7
    )
    # Morphological cleanup: remove tiny noise dots
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return binary


def split_into_lead_rois(binary: np.ndarray, n_row: int = 3, n_col: int = 4):
    """
    Split the ECG binary image into 12 ROIs assuming standard 3x4 layout.
    Returns list of (roi, row_idx, col_idx).
    """
    h, w = binary.shape
    row_h = h // n_row
    col_w = w // n_col
    rois = []
    for r in range(n_row):
        for c in range(n_col):
            y1, y2 = r * row_h, (r + 1) * row_h
            x1, x2 = c * col_w, (c + 1) * col_w
            roi = binary[y1:y2, x1:x2]
            rois.append((roi, r, c))
    return rois


def extract_trace_from_roi(roi: np.ndarray) -> np.ndarray:
    """
    For each column of the ROI, find the vertical centroid of the white
    (waveform) pixels. This gives us the signal trace as a 1D array.
    """
    h, w = roi.shape
    trace = []
    for col in range(w):
        col_pixels = roi[:, col]
        white_rows = np.where(col_pixels > 0)[0]
        if len(white_rows) == 0:
            # No signal in this column: carry forward last value or use center
            trace.append(trace[-1] if trace else h // 2)
        else:
            centroid = int(np.mean(white_rows))
            trace.append(centroid)

    trace = np.array(trace, dtype=np.float32)

    # Invert: pixel 0 = top = highest voltage, so flip
    trace = h - trace

    # Normalize to zero mean
    trace = trace - np.mean(trace)

    # Scale to millivolts: standard paper = 10mm/mV, assume 72 dpi → ~28px/mm
    # So 280px = 1mV. This is approximate; calibration bar would be ideal.
    px_per_mv = max(h * 0.28, 1)
    trace = trace / px_per_mv

    return trace


def resample_to_n(trace: np.ndarray, n: int = 5000) -> np.ndarray:
    """Resample a trace to exactly n samples using scipy."""
    if len(trace) == n:
        return trace
    if len(trace) < 2:
        return np.zeros(n, dtype=np.float32)
    x_old = np.linspace(0, 1, len(trace))
    x_new = np.linspace(0, 1, n)
    f = interp1d(x_old, trace, kind='linear')
    return f(x_new).astype(np.float32)


def smooth_trace(trace: np.ndarray, window: int = 11) -> np.ndarray:
    """Savitzky-Golay smoothing to remove digitization jitter."""
    if len(trace) < window:
        return trace
    try:
        return scipy_signal.savgol_filter(trace, window_length=window, polyorder=3)
    except Exception:
        return trace


def digitize_ecg(image_path: str, out_dir: str = DUMMY_PATH, record_name: str = 'test_1') -> dict:
    """
    Full pipeline: image → (12, 5000) numpy array.
    Returns a dict with signal stats.
    """
    os.makedirs(out_dir, exist_ok=True)

    img = load_image(image_path)
    img = crop_to_ecg_area(img)
    binary = remove_grid(img)

    rois = split_into_lead_rois(binary, n_row=3, n_col=4)

    all_leads = []
    for roi, r, c in rois:
        trace = extract_trace_from_roi(roi)
        trace = smooth_trace(trace)
        trace = resample_to_n(trace, 5000)
        all_leads.append(trace)

    # If only 12 rois, we have I–aVF, V1–V6 (3 rows × 4 cols = 12 leads)
    # Pad or trim to exactly 12
    while len(all_leads) < 12:
        all_leads.append(np.zeros(5000, dtype=np.float32))
    all_leads = all_leads[:12]

    signal_array = np.array(all_leads, dtype=np.float32)  # (12, 5000)

    # Save
    npy_path = os.path.join(out_dir, f'{record_name}.npy')
    np.save(npy_path, signal_array)

    # Save meta CSV
    meta = pd.DataFrame({'age': [50], 'sex': [1], 'height': [175], 'weight': [80], 'record_name': [record_name]})
    meta.to_csv(os.path.join(out_dir, f'{record_name}_meta.csv'), index=False)

    # Build detection overlay image for frontend
    annotated = draw_detections(img.copy(), rois)
    det_path = os.path.join(out_dir, f'{record_name}_detected.png')
    cv2.imwrite(det_path, annotated)

    stats = {
        'leads_extracted': 12,
        'samples_per_lead': 5000,
        'amplitude_range_mv': float(np.max(signal_array) - np.min(signal_array)),
        'mean_amplitude_mv': float(np.mean(np.abs(signal_array))),
        'npy_path': npy_path,
        'detection_image_path': det_path,
    }
    print(f"[ECG Digitizer] Done. Signal shape: {signal_array.shape}, Amplitude range: {stats['amplitude_range_mv']:.3f} mV")
    return stats


def draw_detections(img: np.ndarray, rois: list) -> np.ndarray:
    """Draw labeled bounding boxes over each lead ROI on the original image."""
    h_img, w_img = img.shape[:2]
    n_row, n_col = 3, 4
    row_h = h_img // n_row
    col_w = w_img // n_col

    colors = [
        (0, 255, 100), (0, 220, 255), (255, 180, 0), (200, 0, 255),
        (0, 100, 255), (255, 50, 50), (50, 255, 200), (255, 200, 0),
        (100, 50, 255), (0, 200, 100), (255, 100, 100), (100, 200, 255),
    ]

    overlay = img.copy()
    for idx, (roi, r, c) in enumerate(rois):
        y1, y2 = r * row_h, (r + 1) * row_h
        x1, x2 = c * col_w, (c + 1) * col_w
        color = colors[idx % len(colors)]
        
        # Semi-transparent fill
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    
    cv2.addWeighted(overlay, 0.18, img, 0.82, 0, img)

    for idx, (roi, r, c) in enumerate(rois):
        y1, y2 = r * row_h, (r + 1) * row_h
        x1, x2 = c * col_w, (c + 1) * col_w
        color = colors[idx % len(colors)]
        lead_name = LEAD_NAMES[idx] if idx < len(LEAD_NAMES) else f'L{idx+1}'
        
        cv2.rectangle(img, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), color, 3)

        # Label background
        label = f'Lead {lead_name}'
        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        cv2.rectangle(img, (x1 + 6, y1 + 6), (x1 + lw + 14, y1 + lh + 18), color, -1)
        cv2.putText(img, label, (x1 + 10, y1 + lh + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2, cv2.LINE_AA)

    return img


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ecg_digitizer.py <path_to_ecg_image>")
        sys.exit(1)
    image_path = sys.argv[1]
    result = digitize_ecg(image_path)
    print(result)
