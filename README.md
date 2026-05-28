# 🧠 Stroke Risk & Recovery Intelligence System (SRRIS)
### *Advanced Causal AI Simulator & Clinical Decision Support System (CDSS)*

<div align="center">

[![GitHub Release](https://img.shields.io/github/v/release/OmNinave/SRRIS-Stroke-Risk-Recovery-Information-System-?color=blue&style=flat-square)](https://github.com/OmNinave/SRRIS-Stroke-Risk-Recovery-Information-System-)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch)](https://pytorch.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat-square&logo=tailwind-css)](https://tailwindcss.com)

</div>

---

## 🌟 Platform Overview

**SRRIS** is a clinical-grade decision support platform designed to assist medical practitioners in the diagnosis, prognosis, and rehabilitation of ischemic/hemorrhagic stroke patients. 

By decoupling a heavy, state-of-the-art Python ML/AI backend from a highly responsive Next.js glassmorphism frontend dashboard, SRRIS provides real-time diagnostic insights, ECG digitizing, MRI lesion recognition, and an interactive **Causal AI Sandbox** for "What-If" clinical simulations.

> [!NOTE]
> All AI models, GPU gates, NLP extraction pipelines, and cascading database operations are fully decoupled, containerized, and built using clinical-grade software standards.

---

## 📸 Interface Preview

<table border="0">
  <tr>
    <td width="50%">
      <p align="center"><b>🔐 Clinical Portal</b></p>
      <img src="docs/images/01_login.png" alt="Clinical Portal" width="100%"/>
    </td>
    <td width="50%">
      <p align="center"><b>📋 Patient Directory</b></p>
      <img src="docs/images/02_directory.png" alt="Patient Directory" width="100%"/>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <p align="center"><b>🩺 Patient Profile & Diagnostic Dashboard</b></p>
      <img src="docs/images/03_patient_profile.png" alt="Patient Profile Dashboard" width="100%"/>
    </td>
    <td width="50%">
      <p align="center"><b>🔮 Recovery Trajectory & Causal Sandbox</b></p>
      <img src="docs/images/04_recovery_intelligence.png" alt="Recovery Intelligence" width="100%"/>
    </td>
  </tr>
</table>

---

## 🏗️ Project Architecture

The system utilizes a modern decoupled monorepo structure:

```mermaid
graph TD
    subgraph Frontend [Next.js Dashboard - Port 3000]
        FD[Patient Directory] --> FP[Patient Profile Dashboard]
        FP --> RS[Causal AI Sandbox]
        FP --> DV[Document OCR Vault]
        FP --> RV[MRI Scan Viewer]
    end

    subgraph Backend [FastAPI Server - Port 8080]
        API[API Endpoints] --> AE[AI Diagnostic Engine]
        API --> RE[Recovery Engine & DoWhy]
        API --> VE[Vision & Radiology Service]
        API --> ED[ECG Digitizer]
        API --> DE[Cascading Delete Pipeline]
    end

    subgraph Database [SQLite Storage]
        DB[(srris_production_v5.db)]
    end

    subgraph Disk [Physical Storage]
        uploads[uploads/ directory]
    end

    FD -- REST API / SSE --> API
    API -- Read/Write --> DB
    DE -- Cascade Wipe --> DB
    DE -- Disk Wipe --> uploads
    VE -- Load Images --> uploads
```

---

## 🚀 Core Modules & AI Capabilities

### 1. 🔮 Recovery Trajectory & Causal Sandbox
*   **Survival Prognosis**: Uses an ensemble of survival classifiers to generate a 90-day clinical recovery trajectory curve, predicting mRS (modified Rankin Scale) score probabilities (Independent vs. Dependent vs. Deceased).
*   **DoWhy Causal AI Sandbox**: A highly interactive What-If simulator. Doctors can manipulate modifiable traits (e.g., Systolic BP, blood sugar levels, medication adherence) to see the counterfactual impact on 90-day recovery probability, while trait immutability checks prevent changes to non-modifiable factors (e.g., Age).

### 2. 🩻 Radiology CT/MRI Lesion Detector
*   **Multi-slice CNN Classifier**: Powered by a hybrid VGG19 + DenseNet121 ensemble model. Slice-by-slice analysis pinpoints ischemic or hemorrhagic stroke locations, rendering structural heatmaps directly to the clinical dashboard.

### 3. 📈 1D CNN ECG Digitizer
*   **Waveform Extractor**: Automatically scans hand-drawn or paper-printed ECG graphs, digitizing them into a standard 12-lead signal tensor (12 channels, 5000 samples) and classifying rhythm disturbances (Atrial Fibrillation, Arrhythmia, Normal Sinus Rhythm).

### 4. 📝 NLP OCR Discharge Summary Engine
*   **TrOCR & EasyOCR Multimodal Pipeline**: Converts handwritten clinical doctor notes and lab reports into highly structured JSON schemas, mapping out medications, past surgeries, and clinical events.

### 5. 🛡️ Secure Patient Expungement (HIPAA & GDPR Compliance)
*   **Credential-Gated Deletion**: Destructive deletion of clinical data requires active re-authentication of doctor passwords.
*   **Cascading Database Purge**: Safely removes all related child tables (`LabResults`, `Medications`, `ScanResults`, `DoctorOverrides`, `AuditLogs`) to guarantee zero orphaned records persist.
*   **Physical Disk Wipe**: Recursively deletes all uploads, raw clinical files, and generated AI images associated with the patient from the server disk.

---

## 🛠️ Installation & Setup

### Prerequisites
*   **Python 3.11** (Required for machine learning library alignment and native binary packages)
*   **Node.js 18+**

---

### 1. Backend Server Setup

1. **Navigate to the backend folder**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your environment variables**:
   Copy `.env.example` in the backend root to `.env` and set the required variables:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   JWT_SECRET_KEY=your_jwt_secret_key_here
   SRRIS_DEV=true
   ```

5. **Seed the database with mock scientific data**:
   ```bash
   python -m app.db.seed_scientific_data
   ```

6. **Train the machine learning models** (generates all essential local model binaries):
   ```bash
   python scripts/train_all_models.py
   ```

7. **Start the FastAPI server**:
   ```bash
   python run.py
   ```
   *The backend will boot up at `http://127.0.0.1:8080`.*

---

### 2. Frontend Next.js Setup

1. **Navigate to the frontend folder**:
   ```bash
   cd ../frontend
   ```

2. **Install Node packages**:
   ```bash
   npm install
   ```

3. **Run the Next.js development server**:
   ```bash
   npm run dev
   ```
   *Open `http://localhost:3000` in your browser.*

---

### 🔑 Clinical Demo Access
Once both services are running, you can access the clinical portal:
* **URL**: `http://localhost:3000`
* **Credentials**:

| Role | Username | Password |
|---|---|---|
| **Clinician Account** | `dr_smith` | `secure123` |
| **Departmental Portal** | `NEURO_DEPT` | `HOSPITAL_2024_SECURE` |

---

## 🧪 Testing

Run the complete automated API integration test suite:
```bash
# From the root directory:
python backend/tests/test_api.py
```
This script validates health status, doctor token authentication, patient schema details, AI summary cards, recovery trajectory calculations, DoWhy counterfactual simulation inputs, and CORS configuration.

---

## 👥 Development Team & Collaborators

The **SRRIS** platform is designed, developed, and maintained by:

* **Om Ninave** — *Lead System Architect*  
  [![GitHub](https://img.shields.io/badge/GitHub-OmNinave-181717?style=flat-square&logo=github)](https://github.com/OmNinave)  
  *Email:* `ninaveom28@gmail.com`

* **Manav Mendhe** — *Collaborator*  
  [![GitHub](https://img.shields.io/badge/GitHub-Manavdotexe-181717?style=flat-square&logo=github)](https://github.com/Manavdotexe)  
  *Email:* `manavmendhemm@gmail.com`

* **lavish Rahangdale** — *Collaborator*  
  [![GitHub](https://img.shields.io/badge/GitHub-Lavish911-181717?style=flat-square&logo=github)](https://github.com/Lavish911)  
  *Email:* `lavishr213@gmail.com`

* **Xashwathama** — *Collaborator*  
  [![GitHub](https://img.shields.io/badge/GitHub-Xashwathama-181717?style=flat-square&logo=github)](https://github.com/Xashwathama)  
  *Email:* `Krushnanagalkar111@gmail.com`

* **nihardeploy** — *Collaborator*  
  [![GitHub](https://img.shields.io/badge/GitHub-nihardeploy-181717?style=flat-square&logo=github)](https://github.com/nihardeploy)  
  *Email:* `Niharsalunke02@gmail.com`
