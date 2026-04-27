from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

# Load Environment Variables (API Keys, etc.)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

from app.db import models, database
from app.api.endpoints import auth, patients, medical_history, documents, predict, audit, radiology, analytics, ecg

# Initialize SQLite Database Tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="SRRIS Medical Intelligence Platform", version="4.0.0")

# Mount Uploads for Static Access (Processed Scans, Heatmaps)
import os
uploads_abs_path = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_abs_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_abs_path), name="uploads")

# Setup CORS to allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://.*\.trycloudflare\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI Models refreshed successfully!

@app.get("/")
def read_root():
    return {"message": "Welcome to SRRIS Preventive Intelligence Platform"}

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patient Identity Layer"])
app.include_router(medical_history.router, prefix="/api/v1/patients", tags=["Medical History Store"])
app.include_router(documents.router, prefix="/api/v1/patients", tags=["Document Ingestion"])
app.include_router(radiology.router, prefix="/api/v1/patients", tags=["Radiology Scanning"])
app.include_router(ecg.router, prefix="/api/v1/patients", tags=["ECG Signal Diagnostic"])
app.include_router(predict.router, prefix="/api/v1/patients", tags=["AI Diagnostic Engine"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Security & Audit"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Clinical Analytics"])
