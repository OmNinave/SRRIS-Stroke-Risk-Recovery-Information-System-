# 🧠 SRRIS: Stroke Risk Recovery Information System

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-black?style=for-the-badge&logo=github)](https://github.com/OmNinave/SRRIS-Stroke-Risk-Recovery-Information-System-.git)
![Medical AI](https://img.shields.io/badge/Medical-AI-blue?style=for-the-badge&logo=brain)
![Status](https://img.shields.io/badge/Status-Production--Ready-emerald?style=for-the-badge)

**SRRIS** is a high-fidelity Clinical Decision Support System (CDSS) designed for multimodal stroke diagnostics. It fuses radiological vision, clinical feature ensembles, and real-time LLM reasoning into a unified, high-density diagnostic cockpit.

---

## 🔬 Scientific & Technical Architecture

### 1. 🛡️ The Ensemble Consensus Jury (Stacking Engine)
At the core of SRRIS is a multi-model ensemble that synthesizes predictions from three distinct architectures:
- **XGBoost (Gradient Boosting)**: Optimized for capturing non-linear relationships in clinical biomarkers (Age, BP, Glucose).
- **Random Forest**: Utilized for robust generalization and reducing variance in high-dimensional medical data.
- **PyTorch Neural Network (Multi-Layer Perceptron)**: A 4-layer deep learning model designed to capture complex latent interactions between risk factors.
- **Consensus Logic**: A weighted probability threshold (Default: 70%) is enforced before a "High Risk" alert is triggered, reducing false positives in a clinical setting.

### 2. ☢️ Vision & Radiological Intelligence
SRRIS processes axial CT and MRI scans through a dual-stage vision pipeline:
- **FastAI (ResNet-Based)**: Performs rapid segmentation and classification of brain infarcts.
- **Gemini-2.0-Flash Integration**: Acts as a "Medical reasoning layer," analyzing scan findings to generate automated clinical impressions.
- **Grad-CAM Explainability**: Generates visual heatmaps to show clinicians exactly which pixels influenced the stroke detection.

### 3. 📉 Explainability (XAI) via SHAP
The system utilizes **SHAP (SHapley Additive exPlanations)** to provide "Local Interpretability" for every patient.
- **Feature Attribution**: Ranks the top 10 clinical determinants (e.g., Hypertension, NIHSS, Atrial Fibrillation) influencing a specific prediction.
- **Directional Analysis**: Visualizes factors as "Risk Drivers" (Red) or "Protective Factors" (Green).
- **Robust Parsing**: Built-in "Global Shield" to handle scientific notation and ensure zero-crash operations.

### 4. 🫀 ECG Waveform Digitization
- **OpenCV Digitizer**: Automatically extracts numerical signal traces (12 leads, 500ms intervals) from clinical ECG paper reports.
- **CatBoost Classifier**: Analyzes the digitized waveform for regional ischemic markers associated with vascular stroke vectors.

### 5. 🔮 Survival & Recovery Forecasting
- **Random Survival Forest (RSF)**: Simulates the 90-day functional independence trajectory of the patient.
- **tPA Eligibility**: Real-time screening against AHA/ASA 2023 guidelines (Window check, BP thresholds, Contraindication audit).
- **SBAR Synthesis**: Automatically generates professional "Situation, Background, Assessment, Recommendation" hand-off notes.

> [!IMPORTANT]
> **Model Weights Notice**: Due to GitHub's file size limits, some oversized pre-trained models (e.g., `vgg_unfrozen.weights.h5`) are excluded from this repository. Please refer to the training scripts in `backend/scripts/` to regenerate these weights locally or download them from the official research links.

---

## 🛠️ System Components

### 🏗️ Backend (FastAPI + Python 3.10+)
- **Streaming Pipeline**: Uses Server-Sent Events (SSE) to provide real-time diagnostic logs to the UI.
- **Database**: SQLite with SQLAlchemy ORM for patient history and audit logs.
- **Authentication**: JWT-based secure access for clinical staff.

### 🎨 Frontend (Next.js 16 + Tailwind CSS)
- **High-Density HUD**: A dark-mode diagnostic cockpit with Framer Motion animations.
- **Interactive Charts**: Real-time visualization of SHAP weights and survival curves.
- **Radiology Viewer**: Integrated DICOM-compatible visualization for brain scans.

---

## 📦 Installation & Setup

### 🔹 Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### 🔹 Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🧑‍⚕️ Clinical Demo Access
- **URL**: `http://localhost:3000`
- **Username**: `dr_smith`
- **Password**: `secure123`

---

## ⚖️ Disclaimer
*SRRIS is a research-grade Decision Support System. It is designed to assist, not replace, board-certified medical professionals. All AI diagnostics must be verified through clinical correlation.*

---
**Official Repository:** [OmNinave/SRRIS-Stroke-Risk-Recovery-Information-System-](https://github.com/OmNinave/SRRIS-Stroke-Risk-Recovery-Information-System-.git)
