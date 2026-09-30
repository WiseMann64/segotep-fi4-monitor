"""Windows notification-area controls for the FI4 monitor."""

from __future__ import annotations

import logging
from threading import Event
from typing import Callable

import pystray
from PIL import Image, ImageDraw, ImageFont

from .console_logging import ConsoleLogging
from .display_frequency import DisplayFrequencyPreference
from .startup import StartupRegistration
from .temperature_unit import TemperatureUnitPreference


def _tray_image(unit: str) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (24, 31, 42, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (2, 2, 61, 61),
        radius=13,
        fill=(32, 42, 56, 255),
        outline=(71, 181, 255, 255),
        width=3,
    )
    try:
        font = ImageFont.truetype("segoeui.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    label = f"\u00b0{unit}"
    left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
    x = (64 - (right - left)) / 2 - left
    y = (64 - (bottom - top)) / 2 - top - 1
    draw.text((x, y), label, font=font, fill=(245, 248, 252, 255))
    return image


class MonitorTray:
    def __init__(
        self,
        unit: TemperatureUnitPreference,
        frequency: DisplayFrequencyPreference,
        startup: StartupRegistration,
        request_stop: Callable[[], None],
        logger: logging.Logger,
    ) -> None:
        self._unit = unit
        self._frequency = frequency
        self._startup = startup
        self._request_stop = request_stop
        self._logger = logger
        self._console = ConsoleLogging(logger)
        self._stopped = Event()
        menu = pystray.Menu(
            pystray.MenuItem("Temperature unit", None, enabled=False),
            pystray.MenuItem(
                "Celsius (\u00b0C)", self._set_celsius, checked=lambda _item: self._unit.current == "C"
            ),
            pystray.MenuItem(
                "Fahrenheit (\u00b0F)", self._set_fahrenheit, checked=lambda _item: self._unit.current == "F"
            ),
            pystray.MenuItem(
                self._frequency_menu_text,
                pystray.Menu(
                    pystray.MenuItem(
                        "5 Hz (200 ms)",
                        self._set_5_hz,
                        checked=lambda _item: self._frequency.interval_ms == 200,
                        radio=True,
                    ),
                    pystray.MenuItem(
                        "10 Hz (100 ms)",
                        self._set_10_hz,
                        checked=lambda _item: self._frequency.interval_ms == 100,
                        radio=True,
                    ),
                    pystray.MenuItem(
                        "20 Hz (50 ms)",
                        self._set_20_hz,
                        checked=lambda _item: self._frequency.interval_ms == 50,
                        radio=True,
                    ),
                ),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                self._console_menu_text,
                self._toggle_console,
                checked=lambda _item: self._console.enabled,
            ),
            pystray.MenuItem(
                "Run at Windows startup", self._toggle_startup, checked=self._startup_checked
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._exit),
        )
        self._icon = pystray.Icon(
            "FI4Monitor",
            _tray_image(unit.current),
            f"Segotep FI4 Monitor - \u00b0{unit.current}",
            menu,
        )

    def _frequency_menu_text(self, _item: pystray.MenuItem) -> str:
        return f"Payload frequency ({self._frequency.label})"

    def _set_frequency(self, frequency_hz: int) -> None:
        try:
            changed = self._frequency.set_hz(frequency_hz)
        except Exception:
            self._logger.exception("unable to save display frequency %s Hz", frequency_hz)
        else:
            if changed:
                self._logger.info("display payload frequency set to %s Hz", frequency_hz)
        self._icon.update_menu()

    def _set_5_hz(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._set_frequency(5)

    def _set_10_hz(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._set_frequency(10)

    def _set_20_hz(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._set_frequency(20)

    def _console_menu_text(self, _item: pystray.MenuItem) -> str:
        return "Close console logging" if self._console.enabled else "Open console logging"

    def _toggle_console(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        try:
            if self._console.enabled:
                self._console.disable()
            else:
                self._console.enable()
        except Exception:
            self._logger.exception("unable to toggle console logging")
        self._icon.update_menu()

    def _startup_checked(self, _item: pystray.MenuItem) -> bool:
        try:
            return self._startup.is_enabled()
        except OSError:
            return False

    def _set_unit(self, unit: str) -> None:
        try:
            changed = self._unit.set(unit)
        except Exception:
            self._logger.exception("unable to save temperature unit %s", unit)
            return
        if changed:
            self._icon.icon = _tray_image(unit)
            self._icon.title = f"Segotep FI4 Monitor - \u00b0{unit}"
            self._logger.info("temperature display changed to \u00b0%s", unit)
        self._icon.update_menu()

    def _set_celsius(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._set_unit("C")

    def _set_fahrenheit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._set_unit("F")

    def _toggle_startup(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        try:
            enabled = not self._startup.is_enabled()
            self._startup.set_enabled(enabled)
        except Exception:
            self._logger.exception("unable to update Windows startup setting")
        else:
            self._logger.info("run at Windows startup: %s", enabled)
        self._icon.update_menu()

    def _exit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._request_stop()
        self.stop()

    def stop(self) -> None:
        if self._stopped.is_set():
            return
        self._stopped.set()
        try:
            self._icon.stop()
        except RuntimeError:
            # Icon.stop() raises if the GUI loop has not started yet.
            pass

    def run(self) -> None:
        try:
            self._icon.run()
        finally:
            self._stopped.set()
            try:
                self._console.disable()
            except Exception:
                self._logger.exception("unable to close console logging")
