"""HID discovery and lifecycle for the Segotep FI4."""

from __future__ import annotations

from types import ModuleType
from typing import Any

from .protocol import build_hid_report

VID = 0x5131
PID = 0x2007
USAGE_PAGE = 0xFF00
USAGE = 0x01


class HidDeviceError(RuntimeError):
    """A recoverable HID discovery, connection, or write failure."""


class Fi4Device:
    def __init__(self, hid_module: ModuleType | Any | None = None) -> None:
        self._hid = hid_module
        self._handle: Any | None = None
        self._path: Any | None = None

    @property
    def connected(self) -> bool:
        return self._handle is not None

    @staticmethod
    def _candidate_sort_key(info: dict[str, Any]) -> tuple[int, str]:
        preferred = int(
            info.get("usage_page", -1) == USAGE_PAGE and info.get("usage", -1) == USAGE
        )
        return (-preferred, str(info.get("path", "")))

    def _module(self) -> ModuleType | Any:
        if self._hid is None:
            try:
                import hid
            except ImportError as exc:  # pragma: no cover - depends on target environment
                raise HidDeviceError("hidapi is not installed") from exc
            self._hid = hid
        return self._hid

    def find_path(self) -> Any:
        try:
            devices = list(self._module().enumerate(VID, PID))
        except Exception as exc:
            raise HidDeviceError("unable to enumerate FI4 HID devices") from exc

        if not devices:
            raise HidDeviceError(f"FI4 not found (VID=0x{VID:04x}, PID=0x{PID:04x})")

        devices.sort(key=self._candidate_sort_key)
        return devices[0].get("path")

    def connect(self) -> None:
        if self.connected:
            return

        path = self.find_path()
        try:
            handle = self._module().device()
            handle.open_path(path)
        except Exception as exc:
            self.close()
            raise HidDeviceError("unable to open FI4 HID device") from exc

        self._handle = handle
        self._path = path

    def write(self, payload: bytes) -> None:
        if not self.connected:
            self.connect()

        report = build_hid_report(payload)
        try:
            written = self._handle.write(report)
            if isinstance(written, int) and written < len(report):
                raise HidDeviceError(f"short HID write: {written}/{len(report)} bytes")
        except HidDeviceError:
            raise
        except Exception as exc:
            raise HidDeviceError("FI4 HID write failed") from exc

    def close(self) -> None:
        handle, self._handle = self._handle, None
        self._path = None
        if handle is not None:
            try:
                handle.close()
            except Exception:
                # The handle is already stale; the runner will reconnect on the next tick.
                pass
