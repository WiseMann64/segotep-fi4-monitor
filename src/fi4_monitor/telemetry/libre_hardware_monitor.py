"""LibreHardwareMonitor + psutil telemetry provider."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from .provider import CpuTelemetry, TelemetryError


class LibreHardwareMonitorProvider:
    TEMPERATURE_PREFERENCES = (
        "cpu package",
        "core (tctl/tdie)",
        "cpu (tctl/tdie)",
        "package",
    )
    POWER_PREFERENCES = (
        "cpu package",
        "package power",
        "cpu package power",
    )

    def __init__(self, dll_path: Path | None = None) -> None:
        self._dll_path = dll_path
        self._computer: Any | None = None
        self._temperature_sensor: Any | None = None
        self._power_sensor: Any | None = None
        self._sensor_type_temperature: Any | None = None
        self._sensor_type_power: Any | None = None

    @staticmethod
    def _default_dll_path() -> Path:
        override = os.environ.get("FI4_LHM_DLL")
        if override:
            return Path(override)
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS) / "resources" / "LibreHardwareMonitorLib.dll"
        return Path(__file__).resolve().parents[3] / "resources" / "LibreHardwareMonitorLib.dll"

    def _load_runtime(self) -> tuple[Any, Any, Any]:
        dll_path = self._dll_path or self._default_dll_path()
        if not dll_path.exists():
            raise TelemetryError(f"LibreHardwareMonitorLib.dll not found: {dll_path}")

        try:
            import pythonnet

            if pythonnet.get_runtime_info() is None:
                pythonnet.load("coreclr")

            import clr

            clr.AddReference(str(dll_path))
            from LibreHardwareMonitor.Hardware import Computer, SensorType
            from LibreHardwareMonitor.PawnIo import PawnIo
            import psutil
            pawnio_installed = bool(PawnIo.IsInstalled)
        except Exception as exc:  # pragma: no cover - requires Windows/.NET runtime
            detail = f"{type(exc).__name__}: {exc}"
            raise TelemetryError(
                f"unable to load LibreHardwareMonitor/pythonnet ({detail})"
            ) from exc

        if not pawnio_installed:
            raise TelemetryError(
                "CPU sensor access requires the PawnIO driver. Install it from "
                "https://github.com/namazso/PawnIO.Setup/releases"
            )
        return Computer, SensorType, psutil

    @staticmethod
    def _iter_hardware(hardware: Any) -> Iterable[Any]:
        yield hardware
        for child in getattr(hardware, "SubHardware", ()) or ():
            yield from LibreHardwareMonitorProvider._iter_hardware(child)

    def _sensor_candidates(self, sensor_type: Any) -> list[Any]:
        candidates: list[Any] = []
        for hardware in getattr(self._computer, "Hardware", ()) or ():
            for item in self._iter_hardware(hardware):
                for sensor in getattr(item, "Sensors", ()) or ():
                    if getattr(sensor, "SensorType", None) == sensor_type:
                        candidates.append(sensor)
        return candidates

    @staticmethod
    def _score(name: str, preferences: tuple[str, ...]) -> int:
        normalized = name.strip().lower()
        for index, preference in enumerate(preferences):
            if normalized == preference:
                return 10_000 - index * 100
            if preference in normalized:
                return 5_000 - index * 100
        return 0

    def _select_sensor(self, sensors: list[Any], preferences: tuple[str, ...]) -> Any:
        ranked = sorted(
            (
                (self._score(str(getattr(sensor, "Name", "")), preferences), sensor)
                for sensor in sensors
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked or ranked[0][0] == 0:
            wanted = ", ".join(preferences)
            raise TelemetryError(f"no matching telemetry sensor found; expected one of: {wanted}")
        return ranked[0][1]

    def _discover_sensors(self) -> None:
        self._temperature_sensor = self._select_sensor(
            self._sensor_candidates(self._sensor_type_temperature),
            self.TEMPERATURE_PREFERENCES,
        )
        self._power_sensor = self._select_sensor(
            self._sensor_candidates(self._sensor_type_power),
            self.POWER_PREFERENCES,
        )

    def start(self) -> None:
        self.close()
        Computer, sensor_type, psutil = self._load_runtime()
        del psutil  # imported here so a missing dependency is reported during start()

        try:
            computer = Computer()
            computer.IsCpuEnabled = True
            computer.Open()
        except Exception as exc:  # pragma: no cover - requires Windows/.NET runtime
            raise TelemetryError("unable to open LibreHardwareMonitor") from exc

        self._computer = computer
        self._sensor_type_temperature = sensor_type.Temperature
        self._sensor_type_power = sensor_type.Power
        try:
            self._discover_sensors()
        except Exception:
            self.close()
            raise

    def read(self) -> CpuTelemetry:
        if self._computer is None or self._temperature_sensor is None or self._power_sensor is None:
            raise TelemetryError("telemetry provider is not started")

        stage = "update hardware"
        try:
            for hardware in getattr(self._computer, "Hardware", ()) or ():
                for item in self._iter_hardware(hardware):
                    item.Update()

            stage = f"read temperature sensor {self._temperature_sensor.Name!s}"
            temperature = float(self._temperature_sensor.Value)

            stage = f"read power sensor {self._power_sensor.Name!s}"
            power = float(self._power_sensor.Value)

            stage = "read CPU utilization"
            import psutil
            utilization = float(psutil.cpu_percent(interval=None))
        except Exception as exc:  # pragma: no cover - requires Windows/.NET runtime
            detail = f"{type(exc).__name__}: {exc}"
            raise TelemetryError(f"unable to {stage} ({detail})") from exc

        values = (temperature, utilization, power)
        if not all(math.isfinite(value) for value in values):
            raise TelemetryError("CPU telemetry returned NaN or infinity")
        if power < 0:
            raise TelemetryError("CPU package power was negative")
        return CpuTelemetry(temperature, utilization, power)

    def selected_sensor_names(self) -> tuple[str, str]:
        return (
            str(getattr(self._temperature_sensor, "Name", "")),
            str(getattr(self._power_sensor, "Name", "")),
        )

    def close(self) -> None:
        if self._computer is not None:
            try:
                self._computer.Close()
            except Exception:
                pass
        self._computer = None
        self._temperature_sensor = None
        self._power_sensor = None
        self._sensor_type_temperature = None
        self._sensor_type_power = None
