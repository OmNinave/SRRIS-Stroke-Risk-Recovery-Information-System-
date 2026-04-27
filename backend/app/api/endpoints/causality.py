from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, conlist, validator
from typing import Dict, Any, Optional

from app.services.ai_engine import ai_engine

router = APIRouter()

class TreatmentData(BaseModel):
    patient_id: str
    patient_features: Dict[str, Any]
    interventions: Dict[str, float]
    
    @validator('interventions')
    def validate_interventions(cls, v):
        immutable_traits = ['age', 'gender', 'prior_stroke_count', 'heart_disease', 'diabetes']
        for trait in immutable_traits:
            if trait in v:
                raise ValueError(f"Causal Violation: Cannot intervene on immutable trait '{trait}'.")
        return v

class CausalResponse(BaseModel):
    treatment: str
    baseline_probability: float
    counterfactual_probability: float
    absolute_risk_reduction: float
    is_out_of_distribution: bool
    ood_warning: Optional[str]
    counterfactual_shap_values: list
    counterfactual_trajectory: list
    simulated_clinical_note: Dict[str, Any]

@router.post("/simulate", response_model=CausalResponse)
def simulate_causality(data: TreatmentData):
    """
    Executes a clinical Counterfactual Simulation via the Advanced Causal Engine.
    Requires patient baseline vector + intended numerical interventions.
    """
    try:
        results = ai_engine.simulate_intervention(data.patient_features, data.interventions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    if results.get("error"):
        raise HTTPException(status_code=400, detail=results.get("message"))
        
    return CausalResponse(
        treatment="Custom Clinical Intervention",  # Or derive from interventions keys
        baseline_probability=results["baseline_probability"],
        counterfactual_probability=results["counterfactual_probability"],
        absolute_risk_reduction=results["absolute_risk_reduction"],
        is_out_of_distribution=results["is_out_of_distribution"],
        ood_warning=results["ood_warning"],
        counterfactual_shap_values=results["counterfactual_shap_values"],
        counterfactual_trajectory=results["counterfactual_trajectory"],
        simulated_clinical_note=results["simulated_clinical_note"]
    )
