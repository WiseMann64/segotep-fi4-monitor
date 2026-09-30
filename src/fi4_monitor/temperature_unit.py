"""Thread-safe, persistent display-unit preference shared with the tray."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from .config import save_temperature_unit


class TemperatureUnitPreference:
    def __init__(self, unit: str, config_path: Path) -> None:
        self._unit = unit.strip().upper()
        if self._unit not in {"C", "F"}:
            raise ValueError("temperature unit must be C or F")
        self._config_path = config_path
        self._lock = Lock()

    @property
    def current(self) -> str:
        with self._lock:
            return self._unit

    def set(self, unit: str) -> bool:
        normalized = unit.strip().upper()
        if normalized not in {"C", "F"}:
            raise ValueError("temperature unit must be C or F")
        with self._lock:
            if normalized == self._unit:
                return False
            save_temperature_unit(self._config_path, normalized)
            self._unit = normalized
        return True
