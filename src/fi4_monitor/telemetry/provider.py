"""Telemetry abstraction used by the update loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class TelemetryError(RuntimeError):
    """A recoverable telemetry backend error."""


@dataclass(frozen=True)
class CpuTelemetry:
    temperature_c: float
    utilization_percent: float
    package_power_w: float


class TelemetryProvider(Protocol):
    def start(self) -> None:
        ...

    def read(self) -> CpuTelemetry:
        ...

    def close(self) -> None:
        ...
