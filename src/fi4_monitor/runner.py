"""Single-threaded telemetry-to-HID update loop."""

from __future__ import annotations

import logging
import math
import time
from threading import Event
from typing import Callable

from .config import AppConfig
from .device import Fi4Device, HidDeviceError
from .protocol import build_fi4_payload
from .telemetry.provider import CpuTelemetry, TelemetryError, TelemetryProvider


def _bounded_int(value: float, lower: int, upper: int, label: str) -> int:
    if not math.isfinite(value):
        raise TelemetryError(f"{label} was not finite")
    return max(lower, min(upper, round(value)))


def payload_from_telemetry(stats: CpuTelemetry, unit: str) -> bytes:
    temperature_c = stats.temperature_c
    if not math.isfinite(temperature_c):
        raise TelemetryError("temperature was not finite")
    display_temperature = temperature_c if unit == "C" else temperature_c * 9 / 5 + 32
    temperature = _bounded_int(display_temperature, 0, 255, "temperature")
    cpu_load = _bounded_int(stats.utilization_percent, 0, 100, "CPU utilization")
    wattage = _bounded_int(stats.package_power_w, 0, 999, "CPU package power")
    if stats.package_power_w < 0:
        raise TelemetryError("CPU package power was negative")
    return build_fi4_payload(temperature, unit, cpu_load, wattage)


class MonitorRunner:
    def __init__(
        self,
        config: AppConfig,
        telemetry: TelemetryProvider,
        device: Fi4Device,
        logger: logging.Logger,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.config = config
        self.telemetry = telemetry
        self.device = device
        self.logger = logger
        self.clock = clock
        self.stop_event = Event()

    def stop(self) -> None:
        self.stop_event.set()

    def _sleep_until(self, deadline: float) -> None:
        remaining = deadline - self.clock()
        if remaining > 0:
            self.stop_event.wait(remaining)

    def run(self) -> None:
        telemetry_started = False
        next_update = self.clock()
        self.logger.info("application start")

        try:
            while not self.stop_event.is_set():
                self._sleep_until(next_update)
                if self.stop_event.is_set():
                    break
                next_update += self.config.update_interval_s

                try:
                    if not telemetry_started:
                        self.telemetry.start()
                        telemetry_started = True
                        self.logger.info("telemetry backend initialized")
                        selected = getattr(self.telemetry, "selected_sensor_names", None)
                        if selected is not None:
                            self.logger.info("selected sensors: temperature=%s power=%s", *selected())

                    if not self.device.connected:
                        self.device.connect()
                        self.logger.info("FI4 connected")

                    stats = self.telemetry.read()
                    self.device.write(payload_from_telemetry(stats, self.config.temperature_unit))
                except HidDeviceError as exc:
                    self.logger.warning("FI4 disconnected or write failed: %s", exc)
                    self.device.close()
                    next_update = self.clock() + self.config.retry_interval_s
                except TelemetryError as exc:
                    self.logger.warning("telemetry failure: %s", exc)
                    if telemetry_started:
                        self.telemetry.close()
                        telemetry_started = False
                    self.device.close()
                    next_update = self.clock() + self.config.retry_interval_s
                except Exception:
                    self.logger.exception("unexpected update failure")
                    self.device.close()
                    if telemetry_started:
                        self.telemetry.close()
                        telemetry_started = False
                    next_update = self.clock() + self.config.retry_interval_s

                if next_update < self.clock():
                    next_update = self.clock() + self.config.update_interval_s
        finally:
            self.device.close()
            self.telemetry.close()
            self.logger.info("application shutdown")
