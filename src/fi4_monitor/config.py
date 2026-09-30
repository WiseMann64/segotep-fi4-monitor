"""Small JSON configuration model."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any


class ConfigError(ValueError):
    """Invalid user configuration."""


@dataclass(frozen=True)
class AppConfig:
    temperature_unit: str = "C"
    update_interval_ms: int = 200
    retry_interval_s: float = 1.0
    logging: bool = True
    display_interval_ms: int = 200
    display_change_interval_ms: int = 500

    @property
    def update_interval_s(self) -> float:
        return self.update_interval_ms / 1000.0

    @property
    def display_interval_s(self) -> float:
        return self.display_interval_ms / 1000.0

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "AppConfig":
        unit = str(raw.get("temperature_unit", "C")).strip().upper()
        if unit not in {"C", "F"}:
            raise ConfigError("temperature_unit must be C or F")

        try:
            interval_ms = int(raw.get("update_interval_ms", 200))
            retry_interval_s = float(raw.get("retry_interval_s", 1.0))
            display_interval_ms = int(raw.get("display_interval_ms", 200))
            display_change_interval_ms = int(raw.get("display_change_interval_ms", 500))
        except (TypeError, ValueError) as exc:
            raise ConfigError("interval values must be numeric") from exc

        if not 100 <= interval_ms <= 5000:
            raise ConfigError("update_interval_ms must be between 100 and 5000")
        if not 0.1 <= retry_interval_s <= 60:
            raise ConfigError("retry_interval_s must be between 0.1 and 60")
        if not 50 <= display_interval_ms <= 1000:
            raise ConfigError("display_interval_ms must be between 50 and 1000")
        if not 200 <= display_change_interval_ms <= 1500 or display_change_interval_ms % 100:
            raise ConfigError("display_change_interval_ms must be 200?1500 in 100 ms steps")

        logging = raw.get("logging", True)
        if not isinstance(logging, bool):
            raise ConfigError("logging must be true or false")

        return cls(
            unit,
            interval_ms,
            retry_interval_s,
            logging,
            display_interval_ms,
            display_change_interval_ms,
        )


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


_CONFIG_WRITE_LOCK = Lock()


def _save_config_value(path: Path, key: str, value: Any) -> None:
    with _CONFIG_WRITE_LOCK:
        raw: dict[str, Any] = {}
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ConfigError(f"unable to update config: {path}") from exc
            if not isinstance(existing, dict):
                raise ConfigError("config root must be a JSON object")
            raw = existing

        raw[key] = value
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(f"{path.name}.tmp")
        try:
            temporary_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)


def save_temperature_unit(path: Path, unit: str) -> None:
    """Persist the tray-selected display unit without discarding other settings."""
    normalized = unit.strip().upper()
    if normalized not in {"C", "F"}:
        raise ConfigError("temperature_unit must be C or F")
    _save_config_value(path, "temperature_unit", normalized)


def save_display_interval(path: Path, interval_ms: int) -> None:
    """Persist the tray-selected HID payload interval."""
    if not 50 <= interval_ms <= 1000:
        raise ConfigError("display_interval_ms must be between 50 and 1000")
    _save_config_value(path, "display_interval_ms", interval_ms)


def save_display_change_interval(path: Path, interval_ms: int) -> None:
    """Persist how often new telemetry values are published to the LCD."""
    if not 200 <= interval_ms <= 1500 or interval_ms % 100:
        raise ConfigError("display_change_interval_ms must be 200?1500 in 100 ms steps")
    _save_config_value(path, "display_change_interval_ms", interval_ms)
