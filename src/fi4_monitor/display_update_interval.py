"""Thread-safe, persistent interval for changing values shown on the LCD."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from .config import save_display_change_interval


class DisplayUpdateIntervalPreference:
    INTERVALS_MS = tuple(range(200, 1501, 100))

    def __init__(self, interval_ms: int, config_path: Path) -> None:
        if interval_ms not in self.INTERVALS_MS:
            raise ValueError("LCD update interval must be 200?1500 ms in 100 ms steps")
        self._interval_ms = interval_ms
        self._config_path = config_path
        self._lock = Lock()

    @property
    def interval_ms(self) -> int:
        with self._lock:
            return self._interval_ms

    @property
    def label(self) -> str:
        return f"{self.interval_ms / 1000:.1f} s"

    def set_interval_ms(self, interval_ms: int) -> bool:
        if interval_ms not in self.INTERVALS_MS:
            raise ValueError("LCD update interval must be between 200 and 1500 ms")

        with self._lock:
            if interval_ms == self._interval_ms:
                return False
            save_display_change_interval(self._config_path, interval_ms)
            self._interval_ms = interval_ms
        return True
