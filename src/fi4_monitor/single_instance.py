"""Windows mutex based single-instance guard."""

from __future__ import annotations

import ctypes
import os
from typing import Any


class SingleInstance:
    def __init__(self, name: str = "SegotepFI4Monitor") -> None:
        self.name = name
        self._handle: Any | None = None
        self._already_exists = False

    def acquire(self) -> bool:
        if os.name != "nt":
            return True

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.GetLastError.restype = ctypes.c_ulong

        for mutex_name in (f"Global\\{self.name}", f"Local\\{self.name}"):
            handle = kernel32.CreateMutexW(None, False, mutex_name)
            if handle:
                self._handle = (kernel32, handle)
                self._already_exists = kernel32.GetLastError() == 183
                return not self._already_exists
        return False

    def close(self) -> None:
        if self._handle is None:
            return
        kernel32, handle = self._handle
        kernel32.CloseHandle(handle)
        self._handle = None
