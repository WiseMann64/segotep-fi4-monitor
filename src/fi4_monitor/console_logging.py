"""Attach a live logging console to the windowed Windows app."""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from pathlib import Path
from typing import TextIO

from .config import default_app_dir


class ConsoleLogging:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._enabled = False
        self._allocated_console = False
        self._kernel32 = None
        self._handler: logging.StreamHandler[TextIO] | None = None
        self._stream: TextIO | None = None
        self._previous_stdout: TextIO | None = None
        self._previous_stderr: TextIO | None = None
        self._previous_level: int | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @staticmethod
    def _disable_close_button(kernel32: object) -> None:
        try:
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.GetSystemMenu.argtypes = [wintypes.HWND, wintypes.BOOL]
            user32.GetSystemMenu.restype = wintypes.HMENU
            user32.EnableMenuItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
            user32.EnableMenuItem.restype = wintypes.UINT
            user32.DrawMenuBar.argtypes = [wintypes.HWND]
            user32.DrawMenuBar.restype = wintypes.BOOL

            kernel = kernel32
            kernel.GetConsoleWindow.restype = wintypes.HWND
            window = kernel.GetConsoleWindow()
            if window:
                menu = user32.GetSystemMenu(window, False)
                if menu:
                    user32.EnableMenuItem(menu, 0xF060, 0x0001)
                    user32.DrawMenuBar(window)
        except (AttributeError, OSError):
            pass

    def enable(self) -> None:
        if self._enabled:
            return
        if os.name != "nt":
            raise OSError("console logging is only available on Windows")

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.AllocConsole.restype = ctypes.c_int
        allocated = bool(kernel32.AllocConsole())
        if not allocated and ctypes.get_last_error() != 5:
            raise ctypes.WinError(ctypes.get_last_error())
        self._allocated_console = allocated
        self._kernel32 = kernel32

        self._previous_stdout = sys.stdout
        self._previous_stderr = sys.stderr
        self._previous_level = self._logger.level
        try:
            stream = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
            self._stream = stream
            sys.stdout = stream
            sys.stderr = stream
            if allocated:
                kernel32.SetConsoleTitleW.argtypes = [ctypes.c_wchar_p]
                kernel32.SetConsoleTitleW.restype = ctypes.c_int
                kernel32.SetConsoleTitleW("FI4 Monitor - live logging")
                self._disable_close_button(kernel32)

            handler = logging.StreamHandler(stream)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            self._handler = handler
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.DEBUG)
            self._enabled = True

            print("FI4 Monitor live logging. Use the tray menu to close this console.")
            self._print_recent_log()
            self._logger.info("console logging enabled")
        except Exception:
            self._restore_console()
            raise

    def _print_recent_log(self) -> None:
        if self._stream is None:
            return
        for handler in self._logger.handlers:
            handler.flush()

        log_path = default_app_dir() / "fi4monitor.log"
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            self._stream.write("No previous log file is available. Showing live logs only.\n")
            return

        if not lines:
            self._stream.write("The previous log file is empty. Showing live logs only.\n")
            return
        self._stream.write("--- recent log entries ---\n")
        self._stream.write("\n".join(lines[-60:]) + "\n")
        self._stream.write("--- live log follows ---\n")

    def _restore_console(self) -> None:
        handler, self._handler = self._handler, None
        if handler is not None:
            self._logger.removeHandler(handler)
            handler.close()

        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.flush()
            except OSError:
                pass

        sys.stdout = self._previous_stdout
        sys.stderr = self._previous_stderr
        self._previous_stdout = None
        self._previous_stderr = None

        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass

        if self._allocated_console and self._kernel32 is not None:
            self._kernel32.FreeConsole()
        self._allocated_console = False
        self._kernel32 = None
        self._enabled = False

    def disable(self) -> None:
        if not self._enabled:
            return
        self._logger.info("console logging disabled")
        if self._previous_level is not None:
            self._logger.setLevel(self._previous_level)
        self._restore_console()
        self._previous_level = None
