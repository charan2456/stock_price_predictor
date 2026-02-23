"""LSTM (Long Short-Term Memory) model for time-series stock prediction.

Implements a PyTorch LSTM with configurable layers, dropout,
and sequence length. Supports both regression (return prediction)
and classification (direction prediction) modes.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
import torch.nn as nn
from loguru import logger
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset


class LSTMNetwork(nn.Module):
    """Multi-layer LSTM network with dropout regularization.

    Architecture:
        Input → LSTM Layers → Dropout → Fully Connected → Output

    Args:
        input_size: Number of input features per timestep.
        hidden_size: Number of LSTM hidden units.
        num_layers: Number of stacked LSTM layers.
        dropout: Dropout probability between LSTM layers.
        output_size: Number of output neurons (1 for regression).
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        output_size: int = 1,
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, output_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Input tensor of shape (batch_size, sequence_length, input_size).

        Returns:
            Output tensor of shape (batch_size, output_size).
        """
        # LSTM output: (batch_size, seq_len, hidden_size)
        lstm_out, _ = self.lstm(x)
        # Take the last timestep output
        last_hidden = lstm_out[:, -1, :]
        out = self.dropout(last_hidden)
        out = self.fc(out)
        return out


class LSTMModel:
    """High-level LSTM model wrapper with training, prediction, and serialization.

    Handles data preparation (sequence creation, scaling), training loop
    with early stopping, and model persistence.

    Attributes:
        config: Model hyperparameters from config.
        model: PyTorch LSTMNetwork instance.
        scaler: Feature scaler for normalization.
        device: Compute device (cuda/mps/cpu).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        from src.utils.config import get_config

        cfg = get_config()
        self.config = config or {
            "hidden_size": cfg.training.lstm.hidden_size,
            "num_layers": cfg.training.lstm.num_layers,
            "dropout": cfg.training.lstm.dropout,
            "learning_rate": cfg.training.lstm.learning_rate,
            "batch_size": cfg.training.lstm.batch_size,
            "epochs": cfg.training.lstm.epochs,
            "early_stopping_patience": cfg.training.lstm.early_stopping_patience,
            "sequence_length": cfg.training.lstm.sequence_length,
        }

        self.model: LSTMNetwork | None = None
        self.scaler = StandardScaler()
        self.sequence_length = self.config["sequence_length"]
        self._best_state: dict | None = None

        # Device selection
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")

    def _create_sequences(
        self, features: np.ndarray, targets: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Create overlapping sequences for LSTM input.

        Args:
            features: Feature array of shape (n_samples, n_features).
            targets: Target array of shape (n_samples,).

        Returns:
            Tuple of (X, y) where X has shape (n_sequences, seq_len, n_features)
            and y has shape (n_sequences,).
        """
        X, y = [], []
        for i in range(len(features) - self.sequence_length):
            X.append(features[i : i + self.sequence_length])
            y.append(targets[i + self.sequence_length])
        return np.array(X), np.array(y)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> dict[str, list[float]]:
        """Train the LSTM model.

        Args:
            X_train: Training features (n_samples, n_features).
            y_train: Training targets (n_samples,).
            X_val: Validation features (optional).
            y_val: Validation targets (optional).

        Returns:
            Dict with training history (train_loss, val_loss per epoch).
        """
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val) if X_val is not None else None

        # Create sequences
        X_seq, y_seq = self._create_sequences(X_train_scaled, y_train)

        if X_val_scaled is not None and y_val is not None:
            X_val_seq, y_val_seq = self._create_sequences(X_val_scaled, y_val)
        else:
            X_val_seq, y_val_seq = None, None

        # Initialize model
        n_features = X_seq.shape[2]
        self.model = LSTMNetwork(
            input_size=n_features,
            hidden_size=self.config["hidden_size"],
            num_layers=self.config["num_layers"],
            dropout=self.config["dropout"],
        ).to(self.device)

        # Training setup
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config["learning_rate"],
            weight_decay=1e-5,
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=5
        )
        criterion = nn.MSELoss()

        # DataLoader
        train_dataset = TensorDataset(
            torch.FloatTensor(X_seq),
            torch.FloatTensor(y_seq),
        )
        train_loader = DataLoader(
            train_dataset, batch_size=self.config["batch_size"], shuffle=True
        )

        # Training loop
        history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}
        best_val_loss = float("inf")
        patience_counter = 0

        logger.info(
            "Training LSTM | {params} params | {device}",
            params=sum(p.numel() for p in self.model.parameters()),
            device=self.device,
        )

        for epoch in range(self.config["epochs"]):
            # Train
            self.model.train()
            train_losses = []
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)

                optimizer.zero_grad()
                predictions = self.model(batch_X).squeeze()
                loss = criterion(predictions, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                train_losses.append(loss.item())

            avg_train_loss = np.mean(train_losses)
            history["train_loss"].append(avg_train_loss)

            # Validate
            val_loss = avg_train_loss
            if X_val_seq is not None:
                self.model.eval()
                with torch.no_grad():
                    val_X = torch.FloatTensor(X_val_seq).to(self.device)
                    val_y = torch.FloatTensor(y_val_seq).to(self.device)
                    val_pred = self.model(val_X).squeeze()
                    val_loss = criterion(val_pred, val_y).item()
                history["val_loss"].append(val_loss)
            else:
                history["val_loss"].append(avg_train_loss)

            scheduler.step(val_loss)

            # Logging
            if (epoch + 1) % 10 == 0:
                logger.info(
                    "Epoch {e}/{total} | Train Loss: {tl:.6f} | Val Loss: {vl:.6f}",
                    e=epoch + 1,
                    total=self.config["epochs"],
                    tl=avg_train_loss,
                    vl=val_loss,
                )

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self._best_state = self.model.state_dict().copy()
            else:
                patience_counter += 1
                if patience_counter >= self.config["early_stopping_patience"]:
                    logger.info("Early stopping at epoch {e}", e=epoch + 1)
                    self.model.load_state_dict(self._best_state)
                    break

        logger.info("LSTM training complete | Best val loss: {vl:.6f}", vl=best_val_loss)
        return history

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate predictions.

        Args:
            X: Feature array (n_samples, n_features).

        Returns:
            Predictions array (n_sequences,).
        """
        if self.model is None:
            raise RuntimeError("Model not trained — call fit() first")

        X_scaled = self.scaler.transform(X)
        X_seq, _ = self._create_sequences(X_scaled, np.zeros(len(X_scaled)))

        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_seq).to(self.device)
            predictions = self.model(X_tensor).squeeze().cpu().numpy()

        return predictions

    def save(self, path: str) -> None:
        """Save model weights and scaler."""
        import joblib
        from pathlib import Path

        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        torch.save(self.model.state_dict(), save_dir / "lstm_weights.pt")
        joblib.dump(self.scaler, save_dir / "lstm_scaler.pkl")
        joblib.dump(self.config, save_dir / "lstm_config.pkl")
        logger.info("LSTM model saved to {path}", path=path)

    def load(self, path: str) -> None:
        """Load model weights and scaler."""
        import joblib
        from pathlib import Path

        load_dir = Path(path)
        self.config = joblib.load(load_dir / "lstm_config.pkl")
        self.scaler = joblib.load(load_dir / "lstm_scaler.pkl")

        # Need to know input size — infer from scaler
        n_features = self.scaler.n_features_in_
        self.model = LSTMNetwork(
            input_size=n_features,
            hidden_size=self.config["hidden_size"],
            num_layers=self.config["num_layers"],
            dropout=self.config["dropout"],
        ).to(self.device)
        self.model.load_state_dict(torch.load(load_dir / "lstm_weights.pt", map_location=self.device))
        self.model.eval()
        logger.info("LSTM model loaded from {path}", path=path)
