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
            "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
            "Decision Tree":       DecisionTreeClassifier(max_depth=6, random_state=42),
            "Random Forest":       RandomForestClassifier(
                n_estimators=230, max_depth=80, min_samples_split=2,
                min_samples_leaf=1, max_features='sqrt', bootstrap=False, random_state=42,
            ),
            "KNN":               KNeighborsClassifier(n_neighbors=7),
            "Gradient Boosting": GradientBoostingClassifier(
                n_estimators=1000, learning_rate=0.01, max_depth=7,
                subsample=0.5, random_state=42,
            ),
        }
        self.scaler = StandardScaler()
        self.is_trained = False
        self.training_accuracy: Dict[str, float] = {}

        # Issue 2 Fix: Load from disk cache to avoid 30-60s cold-start retrain
        self._cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models", "jury_cache")
        os.makedirs(self._cache_dir, exist_ok=True)
        if not self._load_from_cache():
            self._train_on_real_data()
            self._save_to_cache()

    def _load_from_cache(self) -> bool:
        """Load jury models from disk cache. Returns True if successful."""
        import joblib as _jl
        try:
            cache_file = os.path.join(self._cache_dir, "jury_bundle.pkl")
            if not os.path.exists(cache_file):
                return False
            bundle = _jl.load(cache_file)
            self.models   = bundle["models"]
            self.scaler   = bundle["scaler"]
            self.training_accuracy = bundle.get("accuracy", {})
            self.is_trained = True
            print("[OK] Consensus Jury loaded from disk cache (instant startup).")
            return True
        except Exception as e:
            print(f"[WARN] Jury cache load failed: {e}. Will retrain.")
            return False

    def _save_to_cache(self) -> None:
        """Persist jury models to disk so next startup skips retraining."""
        import joblib as _jl
        try:
            cache_file = os.path.join(self._cache_dir, "jury_bundle.pkl")
            _jl.dump({"models": self.models, "scaler": self.scaler,
                      "accuracy": self.training_accuracy}, cache_file)
            print(f"[OK] Consensus Jury cached to disk: {cache_file}")
        except Exception as e:
            print(f"[WARN] Could not cache jury: {e}")

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

            for name, model in self.models.items():
                model.fit(X_train_sc, y_train)
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

            for name, model in self.models.items():
                # Phase 1 Upgrade: Enforce strict 0.7 Clinical Threshold
                proba = model.predict_proba(x_scaled)[0]
                pred = 1 if proba[1] >= 0.7 else 0

                votes[name] = "STROKE" if pred == 1 else "Normal"
                raw_votes.append(pred)

            stroke_count = sum(raw_votes)
            normal_count = len(raw_votes) - stroke_count

            # Majority vote threshold: >= 3 out of 5 for STROKE ALERT
            # (3/5 = 60% agreement required — clinically conservative threshold)
            consensus_is_stroke = stroke_count >= 3
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
