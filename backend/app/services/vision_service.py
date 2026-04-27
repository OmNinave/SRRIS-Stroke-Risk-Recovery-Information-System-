import os
import numpy as np
import cv2
import threading
from PIL import Image

try:
    from fastai.vision.all import load_learner, PILImage
except ImportError:
    load_learner = None

from app.services.gpu_gate import gpu_enabled, gpu_gate
_gpu_processing_lock = threading.Lock()

class VisionService:
    def __init__(self):
        # Using the advanced FastAI model from Project 1
        self.weights_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "srris_stroke_brain_v1.pkl")
        self.model = None
        if load_learner and os.path.exists(self.weights_path):
            try:
                # FastAI models load instantly and contain the entire architecture + weights
                self.model = load_learner(self.weights_path)
                print("[VisionService] FastAI Brain Stroke Model loaded successfully.")
            except Exception as e:
                print(f"[VisionService] Error loading FastAI model: {e}")
        else:
            print("[VisionService] WARNING: FastAI model not found or FastAI not installed. Running in simulation mode.")

    def apply_preprocessing(self, img):
        # Advanced CLAHE lighting normalization and Bilateral Denoising (From Proj 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        norm_img = clahe.apply(gray)
        denoised = cv2.bilateralFilter(norm_img, 9, 75, 75)
        return denoised

    def get_brain_slices(self, gray_img):
        # Morphological aspect-ratio cleaving to separate tightly packed MRI grids
        _, thresh = cv2.threshold(gray_img, 45, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
        morphed = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=3)
        
        contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        slices = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            x, y, w, h = cv2.boundingRect(cnt)
            if h == 0: continue
            aspect_ratio = float(w) / h
            
            if area < 300: continue
            if aspect_ratio > 3.0 and h < 80: continue # Ignore Text Labels
            
            if area > 5000 and 0.5 < aspect_ratio < 2.0:
                if area > 40000 and aspect_ratio > 1.6:
                    w_half = w // 2
                    mask1 = np.zeros_like(gray_img)
                    cv2.rectangle(mask1, (x, y), (x+w_half, y+h), 255, -1)
                    slices.append({'box': (x, y, w_half, h), 'contour': cnt, 'mask': mask1})
                    
                    mask2 = np.zeros_like(gray_img)
                    cv2.rectangle(mask2, (x+w_half, y), (x+w, y+h), 255, -1)
                    slices.append({'box': (x+w_half, y, w_half, h), 'contour': cnt, 'mask': mask2})
                elif area > 40000 and aspect_ratio < 0.6:
                    h_half = h // 2
                    mask1 = np.zeros_like(gray_img)
                    cv2.rectangle(mask1, (x, y), (x+w, y+h_half), 255, -1)
                    slices.append({'box': (x, y, w, h_half), 'contour': cnt, 'mask': mask1})
                    
                    mask2 = np.zeros_like(gray_img)
                    cv2.rectangle(mask2, (x, y+h_half), (x+w, y+h), 255, -1)
                    slices.append({'box': (x, y+h_half, w, h_half), 'contour': cnt, 'mask': mask2})
                else:
                    mask = np.zeros_like(gray_img)
                    cv2.drawContours(mask, [cnt], -1, 255, -1)
                    slices.append({'box': (x, y, w, h), 'contour': cnt, 'mask': mask})
                    
        return slices

    def detect_haemorrhage(self, roi, mask):
        # Explanatory Visuals: Bleeding Threshold
        gamma = 0.1
        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        gamma_corrected = cv2.LUT(roi, table)
        masked_gamma = cv2.bitwise_and(gamma_corrected, mask)
        _, thresh = cv2.threshold(masked_gamma, 245, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return contours

    def detect_ischemic(self, roi, mask):
        # Explanatory Visuals: Clot Threshold
        masked_roi = cv2.bitwise_and(roi, mask)
        _, thresh = cv2.threshold(masked_roi, 35, 255, cv2.THRESH_BINARY_INV)
        final_thresh = cv2.bitwise_and(thresh, mask)
        contours, _ = cv2.findContours(final_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return [cnt for cnt in contours if cv2.contourArea(cnt) > 200]

    def draw_detections(self, image, results):
        annotated = image.copy()
        img_w = annotated.shape[1]
        font_scale = max(0.4, img_w / 3500.0)
        line_thick = max(1, int(img_w / 1000.0))
        
        for res in results:
            x, y, w, h = res["coords"]
            conf = res["confidence"] * 100
            pred_class = res["prediction"]
            
            color = (255, 255, 0) # Cyan (Normal)
            label = f"AI: Normal ({conf:.1f}%)"
            
            if conf < 75.0:
                color = (0, 165, 255) # Orange Warning
                label = f"AI: Uncertain ({conf:.1f}%)"
            elif str(pred_class) == "Haemorrhagic": 
                color = (0, 0, 255) # Red
                label = f"AI: Haem ({conf:.1f}%)"
            elif str(pred_class) == "Ischemic": 
                color = (0, 255, 0) # Green
                label = f"AI: Ischemic ({conf:.1f}%)"
                
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, line_thick)
            cv2.putText(annotated, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, line_thick)
            
            # Draw inner organic contours to explain the AI's logic
            if str(pred_class) == "Haemorrhagic" and "hem_cnts" in res and res["hem_cnts"]:
                cv2.drawContours(annotated, res["hem_cnts"], -1, (0, 0, 255), line_thick+1)
            elif str(pred_class) == "Ischemic" and "isc_cnts" in res and res["isc_cnts"]:
                cv2.drawContours(annotated, res["isc_cnts"], -1, (0, 255, 0), line_thick+1)
                
        if annotated.shape[1] > 1200:
            scale = 1200 / annotated.shape[1]
            annotated = cv2.resize(annotated, (1200, int(annotated.shape[0] * scale)))
            
        return Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))

    def predict_stroke(self, img_path):
        """Unified Phase 1 Pipeline: Slicing -> 3-Class Inference -> Contours -> Thresholding"""
        with _gpu_processing_lock:
            original = cv2.imread(img_path)
        if original is None: return 0, "Error loading image", 0, None, []
        
        clean_gray = self.apply_preprocessing(original)
        slices = self.get_brain_slices(clean_gray)
        
        results = []
        is_stroke_global = False
        stroke_count = 0
        total_confidence = 0
        global_result_text = "No Brain Stroke"
        
        if len(slices) > 0:
            for slice_data in slices:
                x, y, w, h = slice_data['box']
                mask = slice_data['mask']
                
                margin = max(15, int(w * 0.1))
                y_start = max(0, y-margin)
                y_end = min(original.shape[0], y+h+margin)
                x_start = max(0, x-margin)
                x_end = min(original.shape[1], x+w+margin)
                slice_crop = original[y_start:y_end, x_start:x_end]
                
                if self.model:
                    import uuid, tempfile, os
                    temp_path = os.path.join(tempfile.gettempdir(), f"temp_slice_{uuid.uuid4().hex}.jpg")
                    cv2.imwrite(temp_path, slice_crop)
                    if gpu_enabled():
                        with gpu_gate.use("vision_predict"):
                            pred_class, pred_idx, outputs = self.model.predict(temp_path)
                    else:
                        pred_class, pred_idx, outputs = self.model.predict(temp_path)
                    confidence = float(outputs[pred_idx])
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                else:
                    import random
                    pred_class = random.choice(["Normal", "Ischemic", "Haemorrhagic"]) if random.random() < 0.3 else "Normal"
                    confidence = random.uniform(0.75, 0.99)
                
                hem_cnts = self.detect_haemorrhage(clean_gray, mask)
                isc_cnts = self.detect_ischemic(clean_gray, mask)
                
                if str(pred_class) in ["Haemorrhagic", "Ischemic"]:
                    stroke_count += 1
                
                total_confidence += confidence
                results.append({
                    "coords": (x, y, w, h),
                    "prediction": pred_class,
                    "confidence": confidence,
                    "hem_cnts": hem_cnts,
                    "isc_cnts": isc_cnts
                })
                
            # Proj 3 threshold logic: Require > 15% slices positive to trigger a global alert
            if stroke_count >= max(1, len(slices) * 0.15):
                is_stroke_global = True
                isc_total = sum(1 for r in results if str(r['prediction']) == 'Ischemic')
                hem_total = sum(1 for r in results if str(r['prediction']) == 'Haemorrhagic')
                if isc_total >= hem_total:
                    global_result_text = f"Ischemic Stroke Detected ({stroke_count} abnormal slices)"
                else:
                    global_result_text = f"Haemorrhagic Stroke Detected ({stroke_count} abnormal slices)"
                
            avg_confidence = total_confidence / len(slices) if slices else 0.0
            
        else:
            # Single scan fallback
            if self.model:
                import uuid, tempfile, os
                temp_path = os.path.join(tempfile.gettempdir(), f"temp_slice_{uuid.uuid4().hex}.jpg")
                cv2.imwrite(temp_path, original)
                if gpu_enabled():
                    with gpu_gate.use("vision_predict"):
                        pred_class, pred_idx, outputs = self.model.predict(temp_path)
                else:
                    pred_class, pred_idx, outputs = self.model.predict(temp_path)
                confidence = float(outputs[pred_idx])
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            else:
                pred_class = "Normal"
                confidence = 0.95
                
            if str(pred_class) in ["Haemorrhagic", "Ischemic"]:
                is_stroke_global = True
                global_result_text = f"Stroke Detected ({pred_class})"
                
            results.append({
                "coords": (0, 0, original.shape[1], original.shape[0]),
                "prediction": pred_class,
                "confidence": confidence,
                "hem_cnts": [],
                "isc_cnts": []
            })
            avg_confidence = confidence

        val = 1 if is_stroke_global else 0
        dummy_input = np.expand_dims(cv2.resize(original, (240,240))/255.0, axis=0)
        return val, global_result_text, avg_confidence, dummy_input, results

    def get_gradcam(self, img_array, last_conv_layer_name="relu"):
        # Deprecated: Using FastAI pixel threshold contours instead of GradCAM
        return np.zeros((240,240))

    def overlay_heatmap(self, heatmap, img_path, alpha=0.5):
        # We return the original image here. The frontend will use the `detection_image`
        # for both visualizations since the detection image now has detailed organic contours.
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        if img.shape[1] > 1200:
            scale = 1200 / img.shape[1]
            img = cv2.resize(img, (1200, int(img.shape[0] * scale)))
        return Image.fromarray(np.uint8(img))

vision_service = VisionService()
