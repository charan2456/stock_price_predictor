"""Tests for core modules."""

import numpy as np
import pandas as pd
import pytest

from src.utils.config import Config


class TestConfig:
    """Test configuration loading."""

    def setup_method(self):
        Config.reset()

    def test_config_loads(self):
        cfg = Config()
        assert cfg.project.name == "market-sentiment-engine"

    def test_config_singleton(self):
        cfg1 = Config()
        cfg2 = Config()
        assert cfg1 is cfg2

    def test_config_tickers(self):
        cfg = Config()
        assert isinstance(cfg.data.tickers, list)
        assert "AAPL" in cfg.data.tickers

    def test_config_training_params(self):
        cfg = Config()
        assert cfg.training.lstm.hidden_size > 0
        assert cfg.training.xgboost.n_estimators > 0


class TestTechnicalIndicators:
    """Test technical indicator computation."""

    def _make_ohlcv(self, n: int = 100) -> pd.DataFrame:
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        return pd.DataFrame({
            "open": close + np.random.randn(n) * 0.1,
            "high": close + abs(np.random.randn(n) * 0.5),
            "low": close - abs(np.random.randn(n) * 0.5),
            "close": close,
            "volume": np.random.randint(1000000, 10000000, n).astype(float),
        })

    def test_rsi_computation(self):
        from src.features.technical_indicators import TechnicalIndicators
        Config.reset()
        ti = TechnicalIndicators()
        df = self._make_ohlcv()
        result = ti.compute(df)
        assert "rsi_14" in result.columns
        # RSI should be 0-100
        valid_rsi = result["rsi_14"].dropna()
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()

    def test_macd_computation(self):
        from src.features.technical_indicators import TechnicalIndicators
        Config.reset()
        ti = TechnicalIndicators()
        df = self._make_ohlcv(n=50)
        result = ti.compute(df)
        assert "macd" in result.columns
        assert "macd_signal" in result.columns
        assert "macd_histogram" in result.columns

    def test_bollinger_bands(self):
        from src.features.technical_indicators import TechnicalIndicators
        Config.reset()
        ti = TechnicalIndicators()
        df = self._make_ohlcv()
        result = ti.compute(df)
        assert "bb_upper" in result.columns
        assert "bb_lower" in result.columns
        # Upper band should be above lower band
        valid = result[["bb_upper", "bb_lower"]].dropna()
        assert (valid["bb_upper"] >= valid["bb_lower"]).all()


class TestBacktester:
    """Test backtesting engine."""

    def test_perfect_predictions(self):
        from src.backtesting.backtester import Backtester
        Config.reset()
        bt = Backtester()

        # Perfect predictions should yield positive return
        actual = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.01])
        predictions = actual.copy()  # Perfect foresight

        result = bt.run(predictions, actual)
        assert result.total_return > 0
        assert result.win_rate == 1.0  # All trades should win

    def test_all_flat(self):
        from src.backtesting.backtester import Backtester
        Config.reset()
        bt = Backtester()

        # Predict negative = stay flat = 0 return
        actual = np.array([0.01, 0.02, 0.01])
        predictions = np.array([-0.01, -0.02, -0.01])

        result = bt.run(predictions, actual)
        assert result.total_return == 0.0
        assert result.total_trades == 0


class TestXGBoostModel:
    """Test XGBoost model."""

    def test_fit_predict(self):
        from src.models.xgboost_model import XGBoostModel
        Config.reset()

        model = XGBoostModel(config={
            "n_estimators": 10,
            "max_depth": 3,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 1,
            "reg_alpha": 0.0,
            "reg_lambda": 1.0,
            "early_stopping_rounds": 5,
        })

        np.random.seed(42)
        X = np.random.randn(100, 10)
        y = X[:, 0] * 0.5 + np.random.randn(100) * 0.1

        model.fit(X[:80], y[:80], X[80:], y[80:])
        preds = model.predict(X[80:])

        assert len(preds) == 20
        assert not np.isnan(preds).any()

    def test_feature_importance(self):
        from src.models.xgboost_model import XGBoostModel
        Config.reset()

        model = XGBoostModel(config={
            "n_estimators": 10, "max_depth": 3, "learning_rate": 0.1,
            "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 1,
            "reg_alpha": 0.0, "reg_lambda": 1.0, "early_stopping_rounds": 5,
        })

        X = np.random.randn(100, 5)
        y = X[:, 0] * 2 + np.random.randn(100) * 0.1
        names = ["important", "noise1", "noise2", "noise3", "noise4"]

        model.fit(X, y, feature_names=names)
        top = model.get_top_features(3)
        assert len(top) == 3
        # The first feature should be most important
        assert top.iloc[0]["feature"] == "important"
