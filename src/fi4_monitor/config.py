"""Small JSON configuration model."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Invalid user configuration."""


@dataclass(frozen=True)
class AppConfig:
    temperature_unit: str = "C"
    update_interval_ms: int = 200
    retry_interval_s: float = 1.0
    logging: bool = True

    @property
    def update_interval_s(self) -> float:
        return self.update_interval_ms / 1000.0

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "AppConfig":
        unit = str(raw.get("temperature_unit", "C")).strip().upper()
        if unit not in {"C", "F"}:
            raise ConfigError("temperature_unit must be C or F")

        try:
            interval_ms = int(raw.get("update_interval_ms", 200))
            retry_interval_s = float(raw.get("retry_interval_s", 1.0))
        except (TypeError, ValueError) as exc:
            raise ConfigError("interval values must be numeric") from exc

        if not 100 <= interval_ms <= 5000:
            raise ConfigError("update_interval_ms must be between 100 and 5000")
        if not 0.1 <= retry_interval_s <= 60:
            raise ConfigError("retry_interval_s must be between 0.1 and 60")

        logging = raw.get("logging", True)
        if not isinstance(logging, bool):
            raise ConfigError("logging must be true or false")

        return cls(unit, interval_ms, retry_interval_s, logging)


def default_app_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "FI4Monitor"
    return Path.home() / ".fi4monitor"


def default_config_path() -> Path:
    return default_app_dir() / "config.json"


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or default_config_path()
    if not config_path.exists():
        return AppConfig()

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"unable to read config: {config_path}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config root must be a JSON object")
    return AppConfig.from_mapping(raw)
