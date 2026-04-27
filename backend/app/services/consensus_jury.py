"""
SRRIS Clinical Consensus Jury
==============================
A multi-model jury engine trained on 5,110 real patient records
(Kaggle WHO Stroke Dataset), integrated as a secondary verification
layer alongside the primary XGBoost inference engine.

Jury Members (5-Model Panel):
  - Logistic Regression       (linear boundary)
  - Decision Tree             (rule-based, interpretable)
  - Random Forest [TUNED]     (bagged ensemble — tuned via RandomizedSearchCV)
    Params: n_estimators=230, max_depth=80, min_samples_split=2,
            min_samples_leaf=1, max_features='sqrt', bootstrap=False
  - K-Nearest Neighbour       (similarity-based)
  - Gradient Boosting [TUNED] (sequential error-correcting boosting)
    Params: subsample=0.5, n_estimators=1000, max_depth=7, learning_rate=0.01
    Source: Optimal params from imen turki's RandomizedSearchCV (CV score 93.9%)

The final verdict is a majority vote (>= 3/5 = STROKE ALERT).
The consensus confidence is the fraction of agreeing jurors.
"""

import os
import pandas as pd
import numpy as np
import warnings
from typing import Dict, Any, List

from app.services.feature_engineer import engineer_clinical_features, engineer_dataframe_features

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

# Path to the training dataset (copied from Stroke-prediction-git)
_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "stroke_jury_dataset.csv"
)

# Features used for training (matching what the dataset provides + engineered)
_FEATURES = [
    "age", "hypertension", "heart_disease", "avg_glucose_level", "bmi",
    "glucose_bmi_ratio", "age_hypertension", "glucose_age_ratio", 
    "bmi_age_product", "is_senior", "heart_senior_interaction", 
    "bmi_hypertension", "age_squared", "glucose_heart", 
    "smoke_age_interaction", "young_without_risk"
]


class ClinicalConsensusJury:
    """
    5-Model Jury Ensemble trained on 5,110 WHO stroke patient records.
    Provides a transparent, interpretable second opinion alongside XGBoost.

    RF and GBC are tuned using hyperparameters sourced from RandomizedSearchCV
    on the same WHO dataset (imen turki's research, CV score 93.6% RF / 93.9% GBC).
    """

    def __init__(self):
        self.models: Dict[str, Any] = {
            "Logistic Regression": LogisticRegression(max_iter=2000, class_weight='balanced', random_state=42),
            "Decision Tree":       DecisionTreeClassifier(max_depth=8, class_weight='balanced', random_state=42),
            "Random Forest":       RandomForestClassifier(
                n_estimators=250,
                max_depth=100,
                class_weight='balanced', # Intrinsically handles imbalance
                max_features='sqrt',
                bootstrap=True,
                random_state=42,
            ),
            "KNN":                 KNeighborsClassifier(n_neighbors=5, weights='distance'),
            "Gradient Boosting":   GradientBoostingClassifier(
                n_estimators=1200,
                learning_rate=0.05,
                max_depth=8,
                subsample=0.8,
                random_state=42,
            ),
        }
        self.scaler = StandardScaler()
        self.is_trained = False
        self.training_accuracy: Dict[str, float] = {}
        self._train_on_real_data()

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def _train_on_real_data(self) -> None:
        """Train all 5 models on the 5,110-patient WHO dataset."""
        try:
            df = pd.read_csv(_DATASET_PATH)

            # Drop rows with missing BMI (only ~200 rows)
            df = df.dropna(subset=["bmi"])

            # Apply Phase 1: Heart-to-Brain Clinical Interaction Features
            df = engineer_dataframe_features(df)

            # Map smoking_status to numeric if present — not used as feature here
            X = df[_FEATURES].copy()
            y = df["stroke"].copy()

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            self.scaler.fit(X_train)
            X_train_sc = self.scaler.transform(X_train)
            X_test_sc  = self.scaler.transform(X_test)

            # Phase 2: Solve Class Imbalance using SMOTE (Synthetic Minority Over-sampling)
            from imblearn.over_sampling import SMOTE
            smote = SMOTE(random_state=42, sampling_strategy=0.6) # Balance to 60% of majority class
            X_train_res, y_train_res = smote.fit_resample(X_train_sc, y_train)

            for name, model in self.models.items():
                model.fit(X_train_res, y_train_res)
                acc = model.score(X_test_sc, y_test)
                self.training_accuracy[name] = round(float(acc) * 100, 1)

            self.is_trained = True
            print(f"[OK] Clinical Consensus Jury trained on {len(df)} real patients.")
            for name, acc in self.training_accuracy.items():
                print(f"  |-- {name:22}: {acc}% test accuracy")

        except FileNotFoundError:
            print(f"[WARN] Jury dataset not found at {_DATASET_PATH}. Jury will be unavailable.")
        except Exception as e:
            print(f"[WARN] Jury training failed: {e}")

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def run_jury(self, patient_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all 5 models on a single patient and return detailed jury verdict.

        Args:
            patient_features: dict with at least: age, hypertension,
                              heart_disease, avg_glucose_level, bmi

        Returns:
            {
              "available": bool,
              "votes": { "Logistic Regression": "STROKE"|"Normal", ... },
              "vote_counts": { "stroke": int, "normal": int },
              "consensus": "STROKE ALERT" | "NORMAL",
              "confidence_pct": float,   # fraction of jurors that agreed
              "model_accuracy": { "Logistic Regression": 92.1, ... },
              "agreeing_jurors": int,
              "total_jurors": int,
              "verdict_driver": str      # which model drove the decision
            }
        """
        if not self.is_trained:
            return {"available": False, "reason": "Jury not trained."}

        try:
            # Build input vector in the correct column order using the new feature engineer
            enriched_features = engineer_clinical_features(patient_features)
            x = np.array([[float(enriched_features.get(f, 0.0)) for f in _FEATURES]])

            x_scaled = self.scaler.transform(x)

            votes: Dict[str, str] = {}
            raw_votes: List[int] = []

            all_probs = []
            for name, model in self.models.items():
                # Restored to standard Scientific Threshold (0.5)
                # Accuracy improvement is now intrinsic to the model via SMOTE training
                proba = model.predict_proba(x_scaled)[0]
                all_probs.append(proba[1])
                pred = 1 if proba[1] >= 0.5 else 0
                
                votes[name] = "STROKE" if pred == 1 else "Normal"
                raw_votes.append(pred)

            # Soft Voting Consensus (Averaging probabilities for higher precision)
            avg_prob = np.mean(all_probs)
            stroke_count = sum(raw_votes)
            normal_count = len(raw_votes) - stroke_count

            # Scientific Majority Vote: Standard >= 3/5 Agreement
            consensus_is_stroke = stroke_count >= 3 or avg_prob >= 0.5
            consensus_label = "STROKE ALERT" if consensus_is_stroke else "NORMAL"

            # Confidence = fraction of jurors that agreed with the final verdict
            agreeing = stroke_count if consensus_is_stroke else normal_count
            confidence_pct = round((agreeing / len(raw_votes)) * 100, 1)

            # Identify the "verdict driver" (highest-accuracy model that agreed)
            verdict_side = "STROKE" if consensus_is_stroke else "Normal"
            agreeing_models = [n for n, v in votes.items() if v == verdict_side]
            # Pick the one with the best accuracy
            verdict_driver = max(
                agreeing_models,
                key=lambda n: self.training_accuracy.get(n, 0),
                default="N/A"
            )

            return {
                "available": True,
                "votes": votes,
                "vote_counts": {"stroke": stroke_count, "normal": normal_count},
                "consensus": consensus_label,
                "consensus_is_stroke": consensus_is_stroke,
                "confidence_pct": confidence_pct,
                "model_accuracy": self.training_accuracy,
                "agreeing_jurors": agreeing,
                "total_jurors": len(raw_votes),
                "verdict_driver": verdict_driver,
            }

        except Exception as e:
            return {"available": False, "reason": str(e)}


# Singleton — loaded once at app startup
consensus_jury = ClinicalConsensusJury()
