"""Per-user Windows startup registration."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "FI4Monitor"


def _command_line(arguments: list[str]) -> str:
    if getattr(sys, "frozen", False):
        command = [sys.executable, *arguments]
    else:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        interpreter = pythonw if pythonw.exists() else Path(sys.executable)
        command = [str(interpreter), "-m", "fi4_monitor", *arguments]
    return subprocess.list2cmdline(command)


class StartupRegistration:
    def __init__(self, arguments: list[str] | None = None) -> None:
        self._arguments = list(arguments or [])

    @staticmethod
    def _winreg():
        if os.name != "nt":
            raise OSError("Windows startup registration is only available on Windows")
        import winreg

        return winreg

    def is_enabled(self) -> bool:
        winreg = self._winreg()
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _ = winreg.QueryValueEx(key, RUN_VALUE)
        except FileNotFoundError:
            return False
        return value == _command_line(self._arguments)

    def set_enabled(self, enabled: bool) -> None:
        winreg = self._winreg()
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(
                    key, RUN_VALUE, 0, winreg.REG_SZ, _command_line(self._arguments)
                )
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE)
                except FileNotFoundError:
                    pass
