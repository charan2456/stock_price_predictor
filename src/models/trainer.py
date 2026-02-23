"""Model training orchestrator with MLflow experiment tracking.

Manages the full training lifecycle: data splitting, model training,
evaluation, MLflow logging, and model registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import TimeSeriesSplit

from src.models.ensemble import EnsembleModel
from src.utils.config import DATA_DIR, MODELS_DIR, get_config


class Trainer:
    """MLflow-instrumented training orchestrator.

    Manages the complete training pipeline:
        1. Load feature-engineered data
        2. Time-series aware train/val/test split
        3. Train ensemble model (LSTM + XGBoost)
        4. Evaluate with standard metrics
        5. Log everything to MLflow
        6. Save best model to registry

    Attributes:
        config: Training configuration.
        model: Ensemble model instance.
    """

    def __init__(self) -> None:
        self.cfg = get_config()
        self.model = EnsembleModel()

    def run(self, data_path: str | None = None) -> dict[str, Any]:
        """Execute the full training pipeline.

        Args:
            data_path: Path to feature-engineered parquet file.
                      Defaults to data/processed/features.parquet.

        Returns:
            Dict with training results and evaluation metrics.
        """
        # Load data
        if data_path is None:
            data_path = str(DATA_DIR / "processed" / "features.parquet")

        logger.info("Loading features from {p}", p=data_path)
        df = pd.read_parquet(data_path)

        # Prepare features and target
        target_col = self.cfg.training.target
        exclude_cols = {"date", "ticker", "next_day_return", "next_day_direction", "next_5day_return"}
        feature_cols = [c for c in df.columns if c not in exclude_cols]

        X = df[feature_cols].values
        y = df[target_col].values
        feature_names = feature_cols

        logger.info(
            "Dataset: {n} samples, {f} features, target={t}",
            n=len(X),
            f=len(feature_cols),
            t=target_col,
        )

        # Time-series split (no data leakage!)
        test_size = int(len(X) * self.cfg.training.test_size)
        val_size = int(len(X) * self.cfg.training.validation_size)
        train_size = len(X) - test_size - val_size

        X_train, y_train = X[:train_size], y[:train_size]
        X_val, y_val = X[train_size : train_size + val_size], y[train_size : train_size + val_size]
        X_test, y_test = X[train_size + val_size :], y[train_size + val_size :]

        logger.info(
            "Split: Train={tr}, Val={v}, Test={te}",
            tr=len(X_train),
            v=len(X_val),
            te=len(X_test),
        )

        # MLflow tracking
        mlflow.set_tracking_uri(self.cfg.mlflow.tracking_uri)
        mlflow.set_experiment(self.cfg.mlflow.experiment_name)

        with mlflow.start_run(run_name=f"ensemble_{target_col}") as run:
            # Log parameters
            mlflow.log_param("target", target_col)
            mlflow.log_param("n_features", len(feature_cols))
            mlflow.log_param("train_size", len(X_train))
            mlflow.log_param("val_size", len(X_val))
            mlflow.log_param("test_size", len(X_test))
            mlflow.log_param("ensemble_method", self.cfg.training.ensemble.method)
            mlflow.log_param("lstm_hidden_size", self.cfg.training.lstm.hidden_size)
            mlflow.log_param("lstm_num_layers", self.cfg.training.lstm.num_layers)
            mlflow.log_param("xgb_n_estimators", self.cfg.training.xgboost.n_estimators)
            mlflow.log_param("xgb_max_depth", self.cfg.training.xgboost.max_depth)

            # Train
            logger.info("=" * 60)
            logger.info("Starting ensemble training")
            logger.info("=" * 60)

            train_results = self.model.fit(
                X_train, y_train, X_val, y_val, feature_names
            )

            # Evaluate on test set
            logger.info("Evaluating on test set...")
            predictions = self.model.predict(X_test)

            # Align predictions with test targets
            min_len = min(len(predictions), len(y_test))
            predictions = predictions[-min_len:]
            y_test_aligned = y_test[-min_len:]

            metrics = self._compute_metrics(y_test_aligned, predictions)

            # Log metrics to MLflow
            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)

            # Log feature importance
            if hasattr(self.model.xgb, "feature_importance") and not self.model.xgb.feature_importance.empty:
                importance_path = str(MODELS_DIR / "feature_importance.csv")
                self.model.xgb.feature_importance.to_csv(importance_path, index=False)
                mlflow.log_artifact(importance_path)

            # Save model
            model_path = str(MODELS_DIR / "ensemble_latest")
            self.model.save(model_path)
            mlflow.log_artifacts(model_path, artifact_path="model")

            # Log results
            logger.info("=" * 60)
            logger.info("Training Results")
            logger.info("=" * 60)
            for name, value in metrics.items():
                logger.info("  {name}: {value:.6f}", name=name, value=value)
            logger.info("MLflow Run ID: {id}", id=run.info.run_id)
            logger.info("Model saved to: {path}", path=model_path)
            logger.info("=" * 60)

            return {
                "metrics": metrics,
                "train_results": train_results,
                "run_id": run.info.run_id,
                "model_path": model_path,
            }

    def _compute_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> dict[str, float]:
        """Compute evaluation metrics.

        Args:
            y_true: Ground truth values.
            y_pred: Predicted values.

        Returns:
            Dict of metric names and values.
        """
        metrics = {
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "r2": float(r2_score(y_true, y_pred)),
        }

        # MAPE (handle zero values)
        try:
            metrics["mape"] = float(mean_absolute_percentage_error(y_true, y_pred))
        except Exception:
            metrics["mape"] = float("nan")

        # Directional accuracy (did we predict the correct direction?)
        direction_correct = np.sign(y_true) == np.sign(y_pred)
        metrics["directional_accuracy"] = float(direction_correct.mean())

        # Sharpe-like ratio of predictions
        pred_returns = y_pred
        if len(pred_returns) > 1 and np.std(pred_returns) > 0:
            metrics["prediction_sharpe"] = float(
                np.mean(pred_returns) / np.std(pred_returns) * np.sqrt(252)
            )
        else:
            metrics["prediction_sharpe"] = 0.0

        return metrics


def main() -> None:
    """CLI entry point for model training."""
    from src.utils.logger import setup_logger

    setup_logger()
    trainer = Trainer()
    results = trainer.run()


if __name__ == "__main__":
    main()
