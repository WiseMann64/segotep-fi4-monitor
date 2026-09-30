"""Presentation-only EMA smoothing for the FI4 display."""

from __future__ import annotations

import math

from .telemetry.provider import CpuTelemetry, TelemetryError


def _alpha(dt: float, tau: float) -> float:
    if not math.isfinite(dt) or dt < 0:
        raise TelemetryError("smoothing interval must be finite and non-negative")
    if not math.isfinite(tau) or tau <= 0:
        raise ValueError("smoothing time constant must be finite and positive")
    return -math.expm1(-dt / tau)


def ema(previous: float, current: float, dt: float, tau: float) -> float:
    """Apply an exponential moving average using the measured sample interval."""
    alpha = _alpha(dt, tau)
    return previous + alpha * (current - previous)


def asymmetric_ema(
    previous: float,
    current: float,
    dt: float,
    rise_tau: float,
    fall_tau: float,
) -> float:
    """Use a faster response when rising and a slower response when falling."""
    tau = rise_tau if current > previous else fall_tau
    return ema(previous, current, dt, tau)


class DisplaySmoother:
    """Smooth display values while leaving each raw CpuTelemetry sample untouched."""

    TEMPERATURE_RISE_TAU_S = 0.75
    TEMPERATURE_FALL_TAU_S = 2.0
    POWER_RISE_TAU_S = 0.5
    POWER_FALL_TAU_S = 1.25
    LOAD_TAU_S = 0.75

    def __init__(self) -> None:
        self._previous: CpuTelemetry | None = None
        self._last_sample_time: float | None = None

    def reset(self) -> None:
        self._previous = None
        self._last_sample_time = None

    def update(self, raw: CpuTelemetry, sample_time: float) -> CpuTelemetry:
        raw_values = (
            raw.temperature_c,
            raw.utilization_percent,
            raw.package_power_w,
            sample_time,
        )
        if not all(math.isfinite(value) for value in raw_values):
            raise TelemetryError("raw telemetry or sample time was not finite")
        if raw.package_power_w < 0:
            raise TelemetryError("CPU package power was negative")

        previous = self._previous
        last_sample_time = self._last_sample_time
        if previous is None or last_sample_time is None:
            filtered = CpuTelemetry(
                raw.temperature_c,
                raw.utilization_percent,
                raw.package_power_w,
            )
        else:
            dt = sample_time - last_sample_time
            if dt < 0:
                raise TelemetryError("smoothing clock moved backwards")
            filtered = CpuTelemetry(
                temperature_c=asymmetric_ema(
                    previous.temperature_c,
                    raw.temperature_c,
                    dt,
                    self.TEMPERATURE_RISE_TAU_S,
                    self.TEMPERATURE_FALL_TAU_S,
                ),
                utilization_percent=ema(
                    previous.utilization_percent,
                    raw.utilization_percent,
                    dt,
                    self.LOAD_TAU_S,
                ),
                package_power_w=asymmetric_ema(
                    previous.package_power_w,
                    raw.package_power_w,
                    dt,
                    self.POWER_RISE_TAU_S,
                    self.POWER_FALL_TAU_S,
                ),
            )

        self._previous = filtered
        self._last_sample_time = sample_time
        return filtered
