# Technical design

## Scope

FI4 Monitor is a small, headless Windows process. Its only v1 responsibility is to read CPU telemetry and periodically write a minimal, confirmed HID payload to the Segotep FI4 display.

The design deliberately keeps the protocol layer independent from sensor discovery. This makes packet tests deterministic and allows the telemetry backend to change without risking the FI4 wire format.

## Data flow

```text
LibreHardwareMonitor + psutil
            │
            ▼
      CpuTelemetry
            │  validate, convert, round, clamp
            ▼
    build_fi4_payload()  ->  64 bytes
            │
            ▼
  b"\x00" + payload     ->  65-byte hidapi write
            │
            ▼
      Segotep FI4 HID
```

The loop runs at the configured interval (default 200 ms) using `time.perf_counter()` and a monotonic deadline. It does not busy-poll at the USB endpoint's interval.

## FI4 protocol

The device is selected by VID `0x5131`, PID `0x2007`, with a preference for Usage Page `0xFF00` and Usage `0x01`.

The application builds a zeroed 64-byte payload:

| Offset | Meaning | Encoding |
| ---: | --- | --- |
| 0 | Header | `0x00` |
| 1 | Header | `0x01` |
| 2 | Header | `0x02` |
| 3 | Display temperature | integer, one byte |
| 5 | Unit | `0 = C`, `1 = F` |
| 6 | CPU utilization | integer `0..100` |
| 7 | Wattage lower part | `wattage % 100` |
| 34 | Wattage hundreds part | `wattage // 100` |

`hidapi.write()` receives a leading zero report-ID byte, so the actual write is 65 bytes: `b"\x00" + payload`.

No checksum, ACK, sequence number, or vendor packet replay is used in v1.

## Telemetry backend

`LibreHardwareMonitorProvider` loads `LibreHardwareMonitorLib.dll` through pythonnet and enables CPU hardware monitoring. `psutil.cpu_percent(interval=None)` supplies total CPU utilization.

Sensor selection is name-based and scored instead of using a fixed index. Temperature preference is approximately:

1. `CPU Package`
2. `Core (Tctl/Tdie)`
3. `CPU (Tctl/Tdie)`
4. `Package`

Power preference is approximately:

1. `CPU Package`
2. `Package Power`
3. `CPU Package Power`

The provider only accepts finite values. It fails with a recoverable telemetry error when a required sensor is not available, allowing the runner to retry after startup or a hardware-monitoring failure.

The DLL path resolution order is:

1. `FI4_LHM_DLL` environment variable.
2. `resources/LibreHardwareMonitorLib.dll` next to the source/project or bundled executable.

The exact LibreHardwareMonitor DLL and Python/.NET runtime combination must be validated on the target Windows image. The build deliberately uses `--onedir` to keep native loading debuggable.

## HID lifecycle and recovery

`Fi4Device` opens one handle and reuses it for all writes. On a failed write:

```text
close stale handle
  -> runner waits retry interval
  -> enumerate VID/PID again
  -> prefer matching usage page/usage
  -> open a fresh handle
```

The path is never hard-coded because Windows can assign a different path after USB reset or resume.

## Runner state model

The runner is intentionally single-threaded:

```text
START
  -> telemetry.start() retry until ready
  -> FI4 connect() retry until ready
  -> read -> normalize -> build -> write
  -> on failure: cleanup affected resource, log, retry
  -> STOP: close HID, close telemetry, flush logging
```

Temperature is kept internally in Celsius. Fahrenheit conversion happens immediately before payload construction. Package power must be finite and non-negative; all display values are rounded and clamped to protocol limits.

## Configuration and logging

The initial JSON configuration is intentionally small:

```json
{
  "temperature_unit": "C",
  "update_interval_ms": 200,
  "retry_interval_s": 1.0,
  "logging": true
}
```

The default config path is `%LOCALAPPDATA%\\FI4Monitor\\config.json`. Logs use a rotating file handler at `%LOCALAPPDATA%\\FI4Monitor\\fi4monitor.log`, limited to 1 MiB with two backups. Normal 5 Hz updates are not logged.

## Single instance and Segotep conflict

On Windows, the process creates `Global\\SegotepFI4Monitor` and falls back to a local mutex if the global namespace is unavailable. A second process exits immediately. The original Segotep application must be closed because two HID writers can produce flickering or alternating values.

## Packaging

PyInstaller's `FI4Monitor.spec` builds an onedir application with the `resources` directory included. A one-file build is intentionally not the first target because extraction and native/.NET DLL loading make recovery less transparent.

Before publishing a release:

- verify `hidapi` native binaries are present in `dist/FI4Monitor`;
- verify `LibreHardwareMonitorLib.dll` and its dependencies are present;
- run on a clean Windows machine without Python;
- record the LibreHardwareMonitor version and license in the release notes;
- test startup, sleep/resume, USB disable/enable, and several hours of refresh stability.

## Security and operational notes

- The app only opens the matched HID device and does not expose a network service.
- Do not run the Segotep application concurrently.
- Hardware-monitoring libraries may need elevated access on some systems; the application does not request elevation by default.
- Unknown exceptions are logged and treated as recoverable at the loop boundary, but a release should still add targeted handling when a concrete failure mode is discovered.

## Explicit v1 non-goals

RGB, fan/pump control, firmware flashing, generic cooler support, graphs, remote APIs, a heavy GUI, and automatic startup registration are out of scope.
