from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

class SurvivalRequest(BaseModel):
    patient_id: str
    stroke_severity_nihss: int

class TrajectoryPoint(BaseModel):
    day: int
    recovery_probability: float

class SurvivalResponse(BaseModel):
    trajectory: List[TrajectoryPoint]
    median_recovery_days: int

@router.post("/trajectory", response_model=SurvivalResponse)
def plot_survival(data: SurvivalRequest):
    # Here we would invoke scikit-survival Random Survival Forests (Step 7)
    # surv_funcs = survival_engine.predict_recovery_curve(patient_features)
    
    # Simulate a realistic right-skewed recovery curve
    trajectory = []
    base_prob = 0.1
    
    # The worse the stroke, the slower the physical recovery curve
    severity_penalty = data.stroke_severity_nihss * 0.02
    
    for day in range(0, 91, 5): # 90 day horizon, every 5 days
        # logarithmic recovery simulation
        prob = min(base_prob + (day ** 0.5) * 0.08 - severity_penalty, 0.95)
        prob = max(prob, 0.05) # Floor at 5%
        trajectory.append(TrajectoryPoint(day=day, recovery_probability=round(prob * 100, 2)))
        
    median_days = 45 + (data.stroke_severity_nihss * 2)
    
    return SurvivalResponse(
        trajectory=trajectory,
        median_recovery_days=median_days
    )
