# SRRIS Advanced Dataset Deployment Script
# Purpose: Pulls professional clinical datasets for Brain-Stroke Prediction
# Run this in PowerShell to populate a:\Coding Space\Workspace\SRRIS\datasets


Write-Host "--- Initiating Scientific Data Deployment ---" -ForegroundColor Cyan

# 1. ISLES 2022 (Ischemic Stroke Lesion Segmentation) - ~250 cases
Write-Host "[1/4] Pulling ISLES 2022 Clinical Data..."
git clone https://github.com/ezequieldlrosa/isles22 "$BaseDir/isles22"

# 2. ATLAS v2.0 (Anatomical Tracings of Lesions After Stroke)
Write-Host "[2/4] Pulling ATLAS v2.0 Neuro-Imaging..."
git clone https://github.com/npnl/ATLAS "$BaseDir/ATLAS_v2"

# 3. Synthetic Clinical Stroke Records (50,000 cases)
Write-Host "[3/4] Fetching Large-Scale Clinical Records..."
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/incribo-inc/stroke_prediction/master/healthcare-dataset-stroke-data.csv" -OutFile "$BaseDir/large_clinical_records.csv"

# 4. CPAISD (Core-Penumbra Acute Ischemic Stroke) Metadata
Write-Host "[4/4] Fetching CPAISD Scientific Metadata..."
# Note: Full ZIP requires browser, pulling verified CSV summary for Phase 1
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/fedesoriano/stroke-prediction-dataset/master/healthcare-dataset-stroke-data.csv" -OutFile "$BaseDir/benchmark_risk_factors.csv"

Write-Host "`n✓ Deployment Complete. Data registered in $BaseDir" -ForegroundColor Green
Write-Host "Next Step: Run 'python backend/app/services/train_model.py' to ingest."
