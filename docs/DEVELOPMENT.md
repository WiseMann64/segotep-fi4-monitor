# Development guide

## Local workflow

~~~powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\build_lhm.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
ruff check .
~~~

The protocol/config tests do not need a physical FI4. Hardware validation should be run on Windows with the original Segotep software stopped.

## Milestones

### M1 - Protocol driver

- Confirm the 64-byte payload layout against the FI4.
- Validate temperature, CPU load, and wattage encoding on hardware.

### M2 - Telemetry

- Compare CPU temperature and package power with a trusted monitoring tool.
- Confirm psutil utilization against Task Manager under idle and load.

### M3 - Recovery

- Start before the cooler is connected.
- Disable and re-enable the USB device.
- Test Windows sleep/resume and telemetry recovery.

### M4 - Packaging

- Build dist/FI4Monitor with scripts/build.ps1.
- Run on a clean Windows machine without Python.
- Confirm all native and .NET DLL dependencies are bundled.

### M5 - Tray and startup

- The Celsius/Fahrenheit tray menu and per-user Windows startup toggle are implemented.
- Validate both units on the FI4 and confirm the saved choice survives restart.
- Reboot and verify telemetry and USB startup recovery.

## Production checklist

- [ ] Segotep software is closed.
- [ ] Temperature is correct in Celsius and Fahrenheit.
- [ ] CPU load and package power are correct.
- [ ] No visible flicker at the configured interval.
- [ ] Several-hour run is stable.
- [ ] USB reset reconnects automatically.
- [ ] Sleep/resume reconnects automatically.
- [ ] Startup race is tolerated.
- [ ] Two instances cannot run together.
- [ ] Portable build runs without Python.
