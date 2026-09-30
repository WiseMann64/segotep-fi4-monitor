# Segotep FI4 Monitor

Portable Windows background monitor for CPU temperature, CPU utilization, and CPU package power on the Segotep FI4 Digital display.

The app reads sensors through LibreHardwareMonitor, writes the confirmed FI4 HID payload, and exposes a small system tray menu for the temperature unit, live diagnostics, and Windows startup setting.

## Features

- CPU temperature, utilization, and package power on the FI4 display.
- Display-only EMA smoothing, with faster response to rising temperature and power.
- Independent HID keep-alive sender, defaulting to 5 Hz, with 5, 10, and 20 Hz tray options.
- LCD value changes can be paced from 0.2 to 1.5 seconds in 0.1-second steps; the default is 0.5 seconds.
- System tray switch for Celsius or Fahrenheit. The choice applies immediately and is saved in the config.
- Open or close a live console from the tray. It shows recent log lines and live telemetry/device errors.
- Optional per-user Windows startup registration from the tray, or with command-line flags.
- Reconnect handling for FI4 USB resets and telemetry startup races.
- Portable PyInstaller onedir build.

RGB/fan control and firmware updates are not included. Hardware validation still requires a Windows PC with the FI4 attached.

## Requirements

- Windows 10/11 x64
- Python 3.11 or later
- Git and .NET SDK 8 or later to build LibreHardwareMonitor from source
- FI4 connected over USB
- [PawnIO driver installed](https://github.com/namazso/PawnIO.Setup/releases) for CPU sensor access through LibreHardwareMonitor

## Build LibreHardwareMonitor locally

The build script fetches the official v0.9.6 source, compiles LibreHardwareMonitorLib for .NET 8, and copies the assembly and its runtime DLL dependencies into resources.

~~~powershell
.\scripts\build_lhm.ps1
~~~

The source checkout and compiler output are placed under the Windows temporary directory. The app expects resources\LibreHardwareMonitorLib.dll.

## Development run

~~~powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m fi4_monitor
~~~

Config defaults to %LOCALAPPDATA%\FI4Monitor\config.json. You can pass another config file with --config. Logs are written to %LOCALAPPDATA%\FI4Monitor\fi4monitor.log.

Right-click the tray icon to switch between Celsius and Fahrenheit, open console logging, enable or disable Windows startup, or exit. The unit selection is persisted in the active config file. Set FI4_LOG_LEVEL=DEBUG to also write raw and smoothed values into the log file.

For command-line startup setup:

~~~powershell
python -m fi4_monitor --install-startup
python -m fi4_monitor --remove-startup
~~~

The startup entry is per-user under HKCU\Software\Microsoft\Windows\CurrentVersion\Run; no administrator access is needed.

## Portable build

~~~powershell
.\scripts\build.ps1
~~~

The output is dist\FI4Monitor\FI4Monitor.exe. It includes the LHM assemblies and tray dependencies and can be moved as a folder.

Close or disable Segotep Digital before running this app so both programs do not write to the FI4 at the same time.
