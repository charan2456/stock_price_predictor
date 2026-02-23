"""Configuration management.

Loads YAML config files with environment variable overrides and provides
a typed, singleton configuration object used across all modules.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
#  Paths
# ──────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT_DIR / "configs"
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models" / "artifacts"
LOGS_DIR = ROOT_DIR / "logs"


def _ensure_dirs() -> None:
    """Create required directories if they don't exist."""
    for d in [DATA_DIR / "raw", DATA_DIR / "processed", MODELS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
#  Config Loader
# ──────────────────────────────────────────────


class Config:
    """Singleton configuration loaded from YAML with env-var overrides.

    Usage:
        >>> cfg = Config()
        >>> cfg.data.tickers
        ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        >>> cfg.training.lstm.hidden_size
        128
    """

    _instance: Config | None = None
    _data: dict[str, Any] = {}

    def __new__(cls, config_path: str | None = None) -> Config:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(config_path)
        return cls._instance

    def _load(self, config_path: str | None = None) -> None:
        """Load config from YAML file, then overlay env-var overrides."""
        if config_path is None:
            env = os.getenv("MSE_ENV", "default")
            config_path = str(CONFIG_DIR / f"{env}.yaml")

        with open(config_path) as f:
            self._data = yaml.safe_load(f)

        # Environment variable overrides (higher priority)
        self._apply_env_overrides()
        _ensure_dirs()

    def _apply_env_overrides(self) -> None:
        """Override config values with environment variables.

        Convention: MSE_<SECTION>_<KEY> → config[section][key]
        Example:    MSE_SERVING_PORT=9000 → config.serving.port = 9000
        """
        for key, value in os.environ.items():
            if not key.startswith("MSE_"):
                continue
            parts = key[4:].lower().split("_", 1)
            if len(parts) == 2 and parts[0] in self._data:
                section, param = parts
                if param in self._data[section]:
                    target_type = type(self._data[section][param])
                    try:
                        self._data[section][param] = target_type(value)
                    except (ValueError, TypeError):
                        pass  # Skip invalid type conversions

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return super().__getattribute__(name)
        if name in self._data:
            value = self._data[name]
            if isinstance(value, dict):
                return _DictWrapper(value)
            return value
        raise AttributeError(f"Config has no section '{name}'")

    def to_dict(self) -> dict[str, Any]:
        """Return raw config dictionary."""
        return self._data.copy()

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — useful for testing."""
        cls._instance = None
        cls._data = {}


class _DictWrapper:
    """Allows dot-notation access on nested config dicts."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return super().__getattribute__(name)
        if name in self._data:
            value = self._data[name]
            if isinstance(value, dict):
                return _DictWrapper(value)
            return value
        raise AttributeError(f"Config section has no key '{name}'")

    def __repr__(self) -> str:
        return f"ConfigSection({self._data})"


def get_config(config_path: str | None = None) -> Config:
    """Get or create the global config singleton."""
    return Config(config_path)
