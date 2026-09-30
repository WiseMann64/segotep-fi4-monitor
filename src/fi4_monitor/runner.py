"""Independent telemetry sampling and fixed-rate HID keep-alive loops."""

from __future__ import annotations

import logging
import math
import time
from threading import Event, Lock, Thread
from typing import Callable

from .config import AppConfig
from .device import Fi4Device, HidDeviceError
from .display_smoothing import DisplaySmoother
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
    MAX_SAMPLE_AGE_S = 5.0

    def __init__(
        self,
        config: AppConfig,
        telemetry: TelemetryProvider,
        device: Fi4Device,
        logger: logging.Logger,
        clock: Callable[[], float] = time.perf_counter,
        temperature_unit: Callable[[], str] | None = None,
        display_interval_ms: Callable[[], int] | None = None,
    ) -> None:
        self.config = config
        self.telemetry = telemetry
        self.device = device
        self.logger = logger
        self.clock = clock
        self.temperature_unit = temperature_unit or (lambda: config.temperature_unit)
        self.display_interval_ms = display_interval_ms or (lambda: config.display_interval_ms)
        self.display_smoother = DisplaySmoother()
        self.stop_event = Event()
        self._payload_lock = Lock()
        self._latest_payload: bytes | None = None
        self._latest_sample_time: float | None = None

    def stop(self) -> None:
        self.stop_event.set()

    def _wait_until(self, deadline: float) -> None:
        remaining = deadline - self.clock()
        if remaining > 0:
            self.stop_event.wait(remaining)

    def _set_latest_payload(self, payload: bytes, sample_time: float) -> None:
        with self._payload_lock:
            self._latest_payload = payload
            self._latest_sample_time = sample_time

    def _get_latest_payload(self) -> tuple[bytes | None, float | None]:
        with self._payload_lock:
            return self._latest_payload, self._latest_sample_time

    def _sample_loop(self) -> None:
        telemetry_started = False
        next_sample = self.clock()
        previous_sample_time: float | None = None
        self.logger.info("telemetry sampler started")

        try:
            while not self.stop_event.is_set():
                self._wait_until(next_sample)
                if self.stop_event.is_set():
                    break

                try:
                    if not telemetry_started:
                        self.telemetry.start()
                        telemetry_started = True
                        self.display_smoother.reset()
                        previous_sample_time = None
                        self.logger.info("telemetry backend initialized")
                        selected = getattr(self.telemetry, "selected_sensor_names", None)
                        if selected is not None:
                            self.logger.info(
                                "selected sensors: temperature=%s power=%s", *selected()
                            )

                    read_started = self.clock()
                    raw_stats = self.telemetry.read()
                    sample_time = self.clock()
                    display_stats = self.display_smoother.update(raw_stats, sample_time)
                    payload = payload_from_telemetry(display_stats, self.temperature_unit())
                    self._set_latest_payload(payload, sample_time)

                    read_ms = (sample_time - read_started) * 1000.0
                    sample_gap_ms = (
                        0.0
                        if previous_sample_time is None
                        else (sample_time - previous_sample_time) * 1000.0
                    )
                    previous_sample_time = sample_time
                    self.logger.debug(
                        "raw telemetry temp_c=%.2f load=%.1f%% power_w=%.2f; "
                        "display temp_c=%.2f load=%.1f%% power_w=%.2f; "
                        "read_ms=%.0f sample_gap_ms=%.0f",
                        raw_stats.temperature_c,
                        raw_stats.utilization_percent,
                        raw_stats.package_power_w,
                        display_stats.temperature_c,
                        display_stats.utilization_percent,
                        display_stats.package_power_w,
                        read_ms,
                        sample_gap_ms,
                    )

                    next_sample += self.config.update_interval_s
                    now = self.clock()
                    if next_sample < now:
                        next_sample = now
                except TelemetryError as exc:
                    self.logger.warning("telemetry failure: %s", exc)
                    if telemetry_started:
                        self.telemetry.close()
                        telemetry_started = False
                    self.display_smoother.reset()
                    previous_sample_time = None
                    next_sample = self.clock() + self.config.retry_interval_s
                except Exception:
                    self.logger.exception("unexpected telemetry sampling failure")
                    if telemetry_started:
                        self.telemetry.close()
                        telemetry_started = False
                    self.display_smoother.reset()
                    previous_sample_time = None
                    next_sample = self.clock() + self.config.retry_interval_s
        finally:
            try:
                self.telemetry.close()
            except Exception:
                self.logger.exception("unable to close telemetry backend")
            self.logger.info("telemetry sampler stopped")

    def _write_loop(self) -> None:
        interval_ms = self.display_interval_ms()
        interval = interval_ms / 1000.0
        next_write = self.clock()
        retry_after = 0.0
        sample_stale = False
        packet_count = 0
        report_started = self.clock()
        self.logger.info(
            "display sender started: rate_hz=%.1f interval_ms=%d",
            1000.0 / interval_ms,
            interval_ms,
        )

        while not self.stop_event.is_set():
            self._wait_until(next_write)
            if self.stop_event.is_set():
                break

            now = self.clock()
            payload, sample_time = self._get_latest_payload()
            if payload is not None and sample_time is not None:
                sample_age = now - sample_time
                if sample_age > self.MAX_SAMPLE_AGE_S:
                    if not sample_stale:
                        self.logger.warning(
                            "telemetry sample stale (age=%.2fs); pausing FI4 writes", sample_age
                        )
                        self.device.close()
                    sample_stale = True
                else:
                    if sample_stale:
                        self.logger.info("telemetry sampling resumed; FI4 writes resumed")
                    sample_stale = False
                    if now >= retry_after:
                        try:
                            if not self.device.connected:
                                self.device.connect()
                                self.logger.info("FI4 connected")
                            self.device.write(payload)
                            packet_count += 1
                        except HidDeviceError as exc:
                            self.logger.warning("FI4 disconnected or write failed: %s", exc)
                            self.device.close()
                            retry_after = self.clock() + self.config.retry_interval_s
                        except Exception:
                            self.logger.exception("unexpected FI4 write failure")
                            self.device.close()
                            retry_after = self.clock() + self.config.retry_interval_s

            now = self.clock()
            if now - report_started >= 1.0:
                if packet_count:
                    latest_payload, latest_sample_time = self._get_latest_payload()
                    sample_age_ms = (
                        max(0.0, now - latest_sample_time) * 1000.0
                        if latest_payload is not None and latest_sample_time is not None
                        else 0.0
                    )
                    self.logger.debug(
                        "HID keep-alive rate=%.1f packets/s sample_age_ms=%.0f",
                        packet_count / (now - report_started),
                        sample_age_ms,
                    )
                packet_count = 0
                report_started = now

            current_interval_ms = self.display_interval_ms()
            interval_changed = current_interval_ms != interval_ms
            if interval_changed:
                interval_ms = current_interval_ms
                interval = interval_ms / 1000.0
                self.logger.info(
                    "display payload frequency changed: rate_hz=%.1f interval_ms=%d",
                    1000.0 / interval_ms,
                    interval_ms,
                )

            if now < retry_after:
                next_write = retry_after
            elif interval_changed:
                next_write = now + interval
            else:
                next_write += interval
                if next_write <= now:
                    next_write = now + interval

    def run(self) -> None:
        self.logger.info("application start")
        sampler = Thread(
            target=self._sample_loop,
            name="fi4-telemetry-sampler",
            daemon=True,
        )
        sampler.start()

        try:
            self._write_loop()
        finally:
            self.stop_event.set()
            sampler.join(timeout=4.0)
            if sampler.is_alive():
                self.logger.warning("telemetry sampler did not stop within four seconds")
            self.device.close()
            self.logger.info("application shutdown")
