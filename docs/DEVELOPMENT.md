# Development guide

## Local workflow

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
ruff check .
```

Protocol and config tests do not need a physical FI4. Hardware tests must be run on Windows with the original Segotep software stopped.

## Milestones

### M1 — protocol driver

- Unit-test 64-byte payload construction.
- Test 47 W, 100 W, 104 W, and 123 W encoding.
- Confirm 50 C / 50% / 50 W on hardware for several minutes.

### M2 — utilization

- Confirm psutil total utilization is mapped to 0–100.
- Compare the displayed load with Task Manager under idle and load.

### M3 — real telemetry

- Confirm selected temperature and package power sensors against a trusted monitoring tool.
- Test Intel and AMD naming variants if available.

### M4 — recovery

- Start before the cooler is connected.
- Disable/enable the USB device.
- Test Windows sleep/resume.
- Temporarily make telemetry unavailable and confirm retry without process exit.

### M5 — packaging

- Build `dist/FI4Monitor` with PyInstaller.
- Run on a clean Windows machine without Python.
- Confirm no DLL is loaded from the development environment by accident.

### M6 — startup

- Add a shortcut to `shell:startup`.
- Reboot and verify that telemetry and USB startup races recover automatically.

## Production checklist

- [ ] Segotep software is closed.
- [ ] Temperature is correct in Celsius.
- [ ] Temperature is correct in Fahrenheit.
- [ ] CPU load is correct.
- [ ] Wattage below 100 W is correct.
- [ ] Wattage at and above 100 W is correct.
- [ ] No visible flicker at the configured interval.
- [ ] Several-hour run is stable.
- [ ] USB reset reconnects automatically.
- [ ] Sleep/resume reconnects automatically.
- [ ] Startup race is tolerated.
- [ ] Two instances cannot run together.
- [ ] Log rotation works.
- [ ] Portable build runs without Python.
