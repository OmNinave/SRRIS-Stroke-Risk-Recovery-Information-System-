import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import VGG19, DenseNet121
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Flatten, Dense, Dropout, GlobalAveragePooling2D
import imutils
import threading

# Shared lock for GPU processing
_radiology_gpu_lock = threading.Lock()

def configure_radiology_gpu():
    if tf:
        try:
            gpus = tf.config.list_physical_devices('GPU')
            if gpus:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
                print("[RadiologyService] GPU Memory Growth Enabled.")
        except Exception as e:
            print(f"[RadiologyService] GPU Config Error: {e}")

configure_radiology_gpu()

class RadiologyService:
    def __init__(self, weights_path=None, architecture="densenet121"):
        self.img_size = 224
        self.architecture = architecture
        if architecture == "densenet121":
            self.model = self._build_densenet121()
        else:
            self.model = self._build_vgg19()
            
        if weights_path and os.path.exists(weights_path):
            try:
                self.model.load_weights(weights_path, skip_mismatch=True)
                print(f"Radiology AI: Loaded {architecture} weights from {weights_path}")
            except Exception as e:
                print(f"Radiology AI: Weight load error ({e}), initializing fallback.")
        else:
            print(f"Radiology AI: Weights for {architecture} not found, running in Simulation Mode.")

    def _build_vgg19(self):
        base_model = VGG19(weights='imagenet', include_top=False, input_shape=(self.img_size, self.img_size, 3))
        for layer in base_model.layers:
            layer.trainable = False
        
        x = Flatten()(base_model.output)
        x = Dense(512, activation='relu')(x)
        x = Dropout(0.5)(x)
        output = Dense(1, activation='sigmoid')(x)
        return Model(inputs=base_model.input, outputs=output)

    def _build_densenet121(self):
        """SOTA Medical Image Classification Architecture"""
        base_model = DenseNet121(weights='imagenet', include_top=False, input_shape=(self.img_size, self.img_size, 3))
        for layer in base_model.layers:
            layer.trainable = False
            
        x = GlobalAveragePooling2D()(base_model.output)
        x = Dense(256, activation='relu')(x)
        x = Dropout(0.3)(x)
        output = Dense(1, activation='sigmoid')(x)
        return Model(inputs=base_model.input, outputs=output)

    def generate_gradcam_heatmap(self, image_array, last_conv_layer_name="relu"):
        """
        Placeholder for Grad-CAM explainability logic. 
        Will visualize which brain regions triggered the stroke detection.
        """
        # In a real clinical environment, we compute gradients of the top predicted class 
        # with respect to the output feature map of the last convolutional layer.
        # For now, we return a simulated heatmap overlay coordinate.
        return {"x": 112, "y": 112, "intensity": 0.85}

    def crop_brain_contour(self, image):
        """Standardizes input scans by removing skull and non-brain tissue."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(gray, 45, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.erode(thresh, None, iterations=2)
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        if not cnts: return image
        
        c = max(cnts, key=cv2.contourArea)
        extLeft = tuple(c[c[:, :, 0].argmin()][0])
        extRight = tuple(c[c[:, :, 0].argmax()][0])
        extTop = tuple(c[c[:, :, 1].argmin()][0])
        extBot = tuple(c[c[:, :, 1].argmax()][0])
        
        new_image = image[extTop[1]:extBot[1], extLeft[0]:extRight[0]]
        return new_image

    def analyze_scan_grid(self, image_path, output_annotated_path=None):
        """Processes a composite medical grid with sequential locking."""
        with _radiology_gpu_lock:
            # 1. Segment Grid
            image = cv2.imread(image_path)
        if image is None: return {"error": "Invalid Image"}
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        results = []
        annotated = image.copy()
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 50 and h > 50 and w < (image.shape[1] * 0.8):
                # Process single tile
                tile = image[y:y+h, x:x+w]
                tile_cropped = self.crop_brain_contour(tile)
                
                # Model Inference
                tile_resized = cv2.resize(tile_cropped, (self.img_size, self.img_size)) / 255.0
                prediction = self.model.predict(np.expand_dims(tile_resized, axis=0))[0][0]
                
                is_stroke = prediction > 0.5
                results.append({
                    "coords": (x, y, w, h),
                    "confidence": float(prediction),
                    "is_stroke": bool(is_stroke)
                })
                
                # Visual Annotation
                color = (0, 0, 255) if is_stroke else (0, 255, 0)
                label = "ALERT: STROKE" if is_stroke else "NORMAL"
                cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 4)
                cv2.putText(annotated, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if output_annotated_path:
            cv2.imwrite(output_annotated_path, annotated)
            
        return {
            "total_tiles": len(results),
            "stroke_detected": any(r["is_stroke"] for r in results),
            "detections": results,
            "annotated_image": output_annotated_path
        }
