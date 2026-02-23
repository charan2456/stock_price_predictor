"""XGBoost model for stock return prediction.

Gradient-boosted decision tree model with built-in feature importance
analysis, hyperparameter configuration via YAML, and MLflow-compatible
serialization.
"""

from __future__ import annotations

from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from loguru import logger
from sklearn.preprocessing import StandardScaler

from src.utils.config import get_config


class XGBoostModel:
    """XGBoost regressor for stock return prediction.

    Provides a scikit-learn-compatible interface with built-in
    feature importance analysis, early stopping, and model persistence.

    Attributes:
        config: Hyperparameters from config.
        model: Trained XGBRegressor instance.
        scaler: Feature scaler.
        feature_importance: DataFrame of feature importances.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = get_config()
        self.config = config or {
            "n_estimators": cfg.training.xgboost.n_estimators,
            "max_depth": cfg.training.xgboost.max_depth,
            "learning_rate": cfg.training.xgboost.learning_rate,
            "subsample": cfg.training.xgboost.subsample,
            "colsample_bytree": cfg.training.xgboost.colsample_bytree,
            "min_child_weight": cfg.training.xgboost.min_child_weight,
            "reg_alpha": cfg.training.xgboost.reg_alpha,
            "reg_lambda": cfg.training.xgboost.reg_lambda,
            "early_stopping_rounds": cfg.training.xgboost.early_stopping_rounds,
        }

        self.model: xgb.XGBRegressor | None = None
        self.scaler = StandardScaler()
        self.feature_importance: pd.DataFrame = pd.DataFrame()
        self._feature_names: list[str] = []

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        feature_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Train the XGBoost model.

        Args:
            X_train: Training features.
            y_train: Training targets.
            X_val: Validation features (for early stopping).
            y_val: Validation targets.
            feature_names: Optional list of feature names.

        Returns:
            Training results including best iteration and metrics.
        """
        self._feature_names = feature_names or [f"f_{i}" for i in range(X_train.shape[1])]

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val) if X_val is not None else None

        # Initialize model
        self.model = xgb.XGBRegressor(
            n_estimators=self.config["n_estimators"],
            max_depth=self.config["max_depth"],
            learning_rate=self.config["learning_rate"],
            subsample=self.config["subsample"],
            colsample_bytree=self.config["colsample_bytree"],
            min_child_weight=self.config["min_child_weight"],
            reg_alpha=self.config["reg_alpha"],
            reg_lambda=self.config["reg_lambda"],
            tree_method="hist",  # Fast histogram-based method
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )

        # Fit with early stopping
        eval_set = [(X_train_scaled, y_train)]
        if X_val_scaled is not None and y_val is not None:
            eval_set.append((X_val_scaled, y_val))

        logger.info("Training XGBoost | {n} estimators | max_depth={d}", n=self.config["n_estimators"], d=self.config["max_depth"])

        self.model.fit(
            X_train_scaled,
            y_train,
            eval_set=eval_set,
            verbose=False,
        )

        # Compute feature importance
        self._compute_importance()

        best_iteration = self.model.best_iteration if hasattr(self.model, "best_iteration") else self.config["n_estimators"]

        logger.info(
            "XGBoost training complete | Best iteration: {iter} | "
            "Top features: {top}",
            iter=best_iteration,
            top=", ".join(self.feature_importance.head(5)["feature"].tolist()),
        )

        return {
            "best_iteration": best_iteration,
            "feature_importance": self.feature_importance,
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate predictions.

        Args:
            X: Feature array.

        Returns:
            Predictions array.
        """
        if self.model is None:
            raise RuntimeError("Model not trained — call fit() first")

        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def _compute_importance(self) -> None:
        """Compute and store feature importance rankings."""
        if self.model is None:
            return

        importance = self.model.feature_importances_
        self.feature_importance = pd.DataFrame(
            {
                "feature": self._feature_names,
                "importance": importance,
            }
        ).sort_values("importance", ascending=False).reset_index(drop=True)

    def get_top_features(self, n: int = 20) -> pd.DataFrame:
        """Get top N most important features.

        Args:
            n: Number of top features to return.

        Returns:
            DataFrame with feature names and importance scores.
        """
        return self.feature_importance.head(n)

    def save(self, path: str) -> None:
        """Save model and scaler."""
        from pathlib import Path

        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, save_dir / "xgboost_model.pkl")
        joblib.dump(self.scaler, save_dir / "xgboost_scaler.pkl")
        joblib.dump(self.config, save_dir / "xgboost_config.pkl")
        joblib.dump(self._feature_names, save_dir / "xgboost_features.pkl")
        self.feature_importance.to_csv(save_dir / "feature_importance.csv", index=False)
        logger.info("XGBoost model saved to {path}", path=path)

    def load(self, path: str) -> None:
        """Load model and scaler."""
        from pathlib import Path

        load_dir = Path(path)
        self.model = joblib.load(load_dir / "xgboost_model.pkl")
        self.scaler = joblib.load(load_dir / "xgboost_scaler.pkl")
        self.config = joblib.load(load_dir / "xgboost_config.pkl")
        self._feature_names = joblib.load(load_dir / "xgboost_features.pkl")
        self._compute_importance()
        logger.info("XGBoost model loaded from {path}", path=path)
