# Technical design

## Scope

FI4 Monitor reads CPU telemetry and periodically writes a presentation-smoothed HID payload to the Segotep FI4 display. Raw samples remain available to debug logging and the tray console.

## Data flow

~~~text
LibreHardwareMonitor + psutil
            |
            v
  telemetry sampler thread
            |
            v
      raw CpuTelemetry ------> DEBUG log / tray console
            |
            v
   DisplaySmoother (EMA)
            |
            v
   unit conversion, rounding, clamp
            |
            v
   latest 64-byte payload cache
            |
            v
   HID sender thread (200 ms default)
            |
            v
  b"\x00" + payload -> 65-byte hidapi write
            |
            v
      Segotep FI4 HID
~~~

Sensor sampling targets the configured interval (default 200 ms). The independent HID sender repeats the latest payload at the tray-selected transport rate, defaulting to 5 Hz (200 ms). The tray offers 5, 10, and 20 Hz; changes apply immediately and persist in config.json. Separately, LCD values are refreshed every 0.2 to 1.5 seconds (default 0.5 seconds, selectable in 0.1-second steps). Sensor sampling and smoothing continue at their configured interval, while the sender keeps writing the last LCD payload between value refreshes. Slow LHM reads no longer delay keep-alive packets. A cached sample older than five seconds is treated as stale and sending pauses until fresh telemetry arrives. The smoother uses measured elapsed time between sensor samples.

## Display smoothing

Smoothing is a presentation layer only. The telemetry provider and CpuTelemetry retain the raw sensor values; only a separate CpuTelemetry copy is passed to payload conversion. The first sample seeds the display values directly, avoiding a slow ramp on startup.

The smoother applies these time constants:

| Signal | Rising tau | Falling tau |
| --- | ---: | ---: |
| CPU temperature | 0.75 s | 2.0 s |
| CPU package power | 0.5 s | 1.25 s |
| CPU load | 0.75 s | 0.75 s |

For each sample, alpha is computed as 1 - exp(-dt / tau), with dt taken from the monotonic sample timestamps. Conversion to Fahrenheit, integer rounding, and protocol clamping happen only after smoothing. Sustained values therefore converge to the raw reading while short spikes are damped.

Set FI4_LOG_LEVEL=DEBUG to write both raw and filtered values into the rotating log file. Normal logging remains at INFO, so the sample loop does not fill the log under standard operation. The tray item Open console logging allocates a Windows console, shows recent log lines, then streams current INFO and DEBUG messages.

## FI4 protocol

The device is selected by VID 0x5131, PID 0x2007, with a preference for Usage Page 0xFF00 and Usage 0x01.

The application builds a zeroed 64-byte payload:

| Offset | Meaning | Encoding |
| ---: | --- | --- |
| 0 | Header | 0x00 |
| 1 | Header | 0x01 |
| 2 | Header | 0x02 |
| 3 | Display temperature | integer, one byte |
| 5 | Unit | 0 = C, 1 = F |
| 6 | CPU utilization | integer 0..100 |
| 7 | Wattage lower part | wattage % 100 |
| 34 | Wattage hundreds part | wattage // 100 |

hidapi.write() receives a leading zero report-ID byte, so the actual write is 65 bytes.

## Telemetry backend

LibreHardwareMonitorProvider explicitly initializes Python.NET with CoreCLR before loading LibreHardwareMonitorLib.dll, then enables CPU hardware monitoring. This avoids Python.NET selecting no runtime on Windows. If loading fails, the telemetry warning includes the underlying exception. The assembly is built locally from official tag v0.9.6 for .NET 8 by scripts/build_lhm.ps1. That script copies the assembly and its runtime dependencies into resources/.

psutil.cpu_percent(interval=None) supplies total CPU utilization. Temperature is held internally in Celsius. Sensor selection prefers CPU Package, Core (Tctl/Tdie), CPU (Tctl/Tdie), and Package for temperature. It prefers CPU Package, Package Power, and CPU Package Power for power.

Only finite readings are accepted. Missing sensors and read failures trigger retry instead of terminating the monitor.

## HID lifecycle and recovery

Fi4Device opens one handle and reuses it for all writes. On a failed write, the runner closes the handle, waits for the retry interval, enumerates VID/PID again, and opens a fresh handle. Device paths are not hard-coded.

## Tray and Windows startup

The tray exposes Celsius, Fahrenheit, Open console logging, Run at Windows startup, and Exit. The console shows the recent log tail and live logger output; closing it is done through the tray menu so it does not terminate the monitoring process.

Selecting a unit updates the FI4 payload on the next monitor tick and persists the choice in %LOCALAPPDATA%\FI4Monitor\config.json. Startup registration is an optional per-user value in HKCU\Software\Microsoft\Windows\CurrentVersion\Run. The tray can toggle it; --install-startup and --remove-startup provide equivalent command-line operations.

## Configuration and logging

The default config is %LOCALAPPDATA%\FI4Monitor\config.json:

~~~json
{
  "temperature_unit": "C",
  "update_interval_ms": 200,
  "display_interval_ms": 200,
  "display_change_interval_ms": 500,
  "retry_interval_s": 1.0,
  "logging": true
}
~~~

Logs use a rotating file at %LOCALAPPDATA%\FI4Monitor\fi4monitor.log, limited to 1 MiB with two backups. The console menu temporarily enables DEBUG output to its window.

## Packaging

PyInstaller builds an onedir app so native HID, pythonnet, tray, and .NET DLL dependencies remain together in dist/FI4Monitor. The spec collects pystray backends and bundles the resources/ directory.

The original Segotep application should be closed because two HID writers can produce flickering or alternating values. Hardware monitoring may need elevated access on some systems; FI4 Monitor does not request elevation by default.
