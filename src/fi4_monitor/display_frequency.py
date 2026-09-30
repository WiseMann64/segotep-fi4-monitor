"""Thread-safe, persistent payload-frequency preference shared with the tray."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from .config import save_display_interval


class DisplayFrequencyPreference:
    FREQUENCY_INTERVALS_MS = {5: 200, 10: 100, 20: 50}

    def __init__(self, interval_ms: int, config_path: Path) -> None:
        if not 50 <= interval_ms <= 1000:
            raise ValueError("display interval must be between 50 and 1000 ms")
        self._interval_ms = interval_ms
        self._config_path = config_path
        self._lock = Lock()

    @property
    def interval_ms(self) -> int:
        with self._lock:
            return self._interval_ms

    @property
    def current_hz(self) -> float:
        return 1000.0 / self.interval_ms

    @property
    def label(self) -> str:
        interval_ms = self.interval_ms
        for frequency_hz, option_interval_ms in self.FREQUENCY_INTERVALS_MS.items():
            if interval_ms == option_interval_ms:
                return f"{frequency_hz} Hz"
        return f"{1000.0 / interval_ms:.1f} Hz"

    def set_hz(self, frequency_hz: int) -> bool:
        try:
            interval_ms = self.FREQUENCY_INTERVALS_MS[frequency_hz]
        except KeyError as exc:
            raise ValueError("frequency must be 5, 10, or 20 Hz") from exc

        with self._lock:
            if interval_ms == self._interval_ms:
                return False
            save_display_interval(self._config_path, interval_ms)
            self._interval_ms = interval_ms
        return True
