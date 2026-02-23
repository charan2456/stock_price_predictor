"""Ensemble model combining LSTM and XGBoost predictions.

Supports weighted averaging, stacking (meta-learner), and blending
strategies for combining predictions from heterogeneous base models.
"""

from __future__ import annotations

from typing import Any

import joblib
import numpy as np
from loguru import logger
from sklearn.linear_model import Ridge

from src.models.lstm_model import LSTMModel
from src.models.xgboost_model import XGBoostModel
from src.utils.config import get_config


class EnsembleModel:
    """Ensemble combining LSTM and XGBoost for robust predictions.

    Motivation:
        - LSTM captures sequential temporal patterns and non-linear dynamics
        - XGBoost excels at feature interactions and handles tabular data well
        - Ensemble reduces variance and improves generalization

    Strategies:
        - weighted: Fixed-weight averaging (configurable via YAML)
        - stacking: Train a meta-learner on base model predictions
        - blending: Holdout-based meta-learner training

    Attributes:
        lstm: LSTM base model.
        xgb: XGBoost base model.
        method: Ensemble strategy (weighted, stacking, blending).
        weights: Per-model weights (for weighted strategy).
        meta_learner: Meta-learner model (for stacking/blending).
    """

    def __init__(self) -> None:
        cfg = get_config()
        self.lstm = LSTMModel()
        self.xgb = XGBoostModel()
        self.method: str = cfg.training.ensemble.method
        self.weights: dict[str, float] = {
            "lstm": cfg.training.ensemble.weights.lstm,
            "xgboost": cfg.training.ensemble.weights.xgboost,
        }
        self.meta_learner: Ridge | None = None
        self._is_fitted = False

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Train both base models and optionally the meta-learner.

        Args:
            X_train: Training features.
            y_train: Training targets.
            X_val: Validation features.
            y_val: Validation targets.
            feature_names: Feature names for XGBoost importance.

        Returns:
            Combined training results from both models.
        """
        results: dict[str, Any] = {}

        # Train LSTM
        logger.info("=" * 40)
        logger.info("Training Base Model 1/2: LSTM")
        logger.info("=" * 40)
        lstm_history = self.lstm.fit(X_train, y_train, X_val, y_val)
        results["lstm"] = lstm_history

        # Train XGBoost
        logger.info("=" * 40)
        logger.info("Training Base Model 2/2: XGBoost")
        logger.info("=" * 40)
        xgb_results = self.xgb.fit(X_train, y_train, X_val, y_val, feature_names)
        results["xgboost"] = xgb_results

        # Train meta-learner for stacking
        if self.method == "stacking" and X_val is not None and y_val is not None:
            logger.info("Training stacking meta-learner...")
            self._fit_meta_learner(X_val, y_val)
            results["meta_learner"] = "ridge"

        self._is_fitted = True

        logger.info(
            "Ensemble training complete | Method: {m} | Weights: LSTM={wl}, XGB={wx}",
            m=self.method,
            wl=self.weights["lstm"],
            wx=self.weights["xgboost"],
        )

        return results

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate ensemble predictions.

        Args:
            X: Feature array.

        Returns:
            Ensemble predictions array.
        """
        if not self._is_fitted:
            raise RuntimeError("Ensemble not trained — call fit() first")

        # Get base model predictions
        lstm_preds = self.lstm.predict(X)
        xgb_preds = self.xgb.predict(X)

        # Align lengths (LSTM produces fewer predictions due to sequence length)
        min_len = min(len(lstm_preds), len(xgb_preds))
        lstm_preds = lstm_preds[-min_len:]
        xgb_preds = xgb_preds[-min_len:]

        # Combine predictions
        if self.method == "weighted":
            ensemble_preds = (
                self.weights["lstm"] * lstm_preds +
                self.weights["xgboost"] * xgb_preds
            )
        elif self.method == "stacking" and self.meta_learner is not None:
            meta_features = np.column_stack([lstm_preds, xgb_preds])
            ensemble_preds = self.meta_learner.predict(meta_features)
        else:
            # Default to simple average
            ensemble_preds = (lstm_preds + xgb_preds) / 2

        return ensemble_preds

    def _fit_meta_learner(self, X_val: np.ndarray, y_val: np.ndarray) -> None:
        """Train a meta-learner on validation set predictions."""
        lstm_preds = self.lstm.predict(X_val)
        xgb_preds = self.xgb.predict(X_val)

        min_len = min(len(lstm_preds), len(xgb_preds))
        lstm_preds = lstm_preds[-min_len:]
        xgb_preds = xgb_preds[-min_len:]
        y_meta = y_val[-min_len:]

        meta_features = np.column_stack([lstm_preds, xgb_preds])
        self.meta_learner = Ridge(alpha=1.0)
        self.meta_learner.fit(meta_features, y_meta)

        logger.info(
            "Meta-learner coefficients: LSTM={cl:.3f}, XGB={cx:.3f}",
            cl=self.meta_learner.coef_[0],
            cx=self.meta_learner.coef_[1],
        )

    def save(self, path: str) -> None:
        """Save all model components."""
        from pathlib import Path

        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        self.lstm.save(str(save_dir / "lstm"))
        self.xgb.save(str(save_dir / "xgboost"))

        # Save ensemble config
        ensemble_config = {
            "method": self.method,
            "weights": self.weights,
        }
        joblib.dump(ensemble_config, save_dir / "ensemble_config.pkl")

        if self.meta_learner is not None:
            joblib.dump(self.meta_learner, save_dir / "meta_learner.pkl")

        logger.info("Ensemble model saved to {path}", path=path)

    def load(self, path: str) -> None:
        """Load all model components."""
        from pathlib import Path

        load_dir = Path(path)

        self.lstm.load(str(load_dir / "lstm"))
        self.xgb.load(str(load_dir / "xgboost"))

        ensemble_config = joblib.load(load_dir / "ensemble_config.pkl")
        self.method = ensemble_config["method"]
        self.weights = ensemble_config["weights"]

        meta_path = load_dir / "meta_learner.pkl"
        if meta_path.exists():
            self.meta_learner = joblib.load(meta_path)

        self._is_fitted = True
        logger.info("Ensemble model loaded from {path}", path=path)
