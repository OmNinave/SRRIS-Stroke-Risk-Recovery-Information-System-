from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import logging

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# ── Structured logging setup ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("srris")

# Load Environment Variables (API Keys, etc.)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if not os.path.exists(env_path):
    # Fallback to repo root .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=env_path)

from app.db import models, database
from app.api.endpoints import auth, patients, medical_history, documents, predict, audit, recovery, radiology, analytics, ecg, triage

# Initialize SQLite Database Tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="SRRIS Medical Intelligence Platform", version="4.0.0")

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount Uploads for Static Access (Processed Scans, Heatmaps)
uploads_abs_path = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_abs_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_abs_path), name="uploads")

@app.middleware("http")
async def log_requests(request, call_next):
    response = await call_next(request)
    # Only log non-200 responses to keep console clean in production
    if response.status_code >= 400:
        logger.warning("%s %s → %s", request.method, request.url.path, response.status_code)
    return response

# Setup CORS to allow Next.js frontend
allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
env_origins = os.getenv("CORS_ORIGINS")
if env_origins:
    allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()]

is_dev = os.getenv("SRRIS_DEV", "false").lower() == "true"
allow_origin_regex = r"https?://.*\.trycloudflare\.com" if is_dev else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI Models refreshed — cloudpickle v3.0.0 — 2026-05-11T02:41

@app.get("/")
def read_root():
    return {"message": "Welcome to SRRIS Preventive Intelligence Platform"}

@app.get("/health/models")
def model_health(current_user=Depends(auth.get_current_user)):
    """Diagnostic endpoint — reports which ML models are loaded. Requires authentication."""
    from app.services import recovery_engine

    ro_bundle = recovery_engine._RECOVERY_OUTCOME_BUNDLE
    spe_bundle = recovery_engine._SPE_RF_BUNDLE

    return {
        "engine1_recovery_outcome_ml": {
            "status": "loaded" if ro_bundle is not None else "failed",
            "cv_accuracy": float(ro_bundle.get("cv_accuracy", 0)) if ro_bundle else None,
        },
        "engine2_strokepredict_rf": {
            "status": "loaded" if spe_bundle is not None else "failed",
            "n_features": spe_bundle.n_features_in_ if spe_bundle else None,
        }
    }

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patient Identity Layer"])
app.include_router(medical_history.router, prefix="/api/v1/patients", tags=["Medical History Store"])
app.include_router(documents.router, prefix="/api/v1/patients", tags=["Document Ingestion"])
app.include_router(radiology.router, prefix="/api/v1/patients", tags=["Radiology Scanning"])
app.include_router(ecg.router, prefix="/api/v1/patients", tags=["ECG Signal Diagnostic"])
app.include_router(predict.router, prefix="/api/v1/patients", tags=["AI Diagnostic Engine"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Security & Audit"])
app.include_router(recovery.router, prefix="/api/v1/patients", tags=["Recovery Intelligence Engine"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Clinical Analytics"])
app.include_router(triage.router, prefix="/api/v1/triage", tags=["Ambulance Triage"])
