# Segotep FI4 Monitor

Portable Windows background monitor untuk menampilkan CPU temperature, CPU utilization, dan CPU package power pada **Segotep FI4 Digital**.

Repository ini adalah starter implementation yang mengikuti protokol FI4 yang sudah terverifikasi. Driver protocol dan HID sudah dipisahkan serta diuji; backend telemetry LibreHardwareMonitor disiapkan sebagai dependency runtime/build yang harus ditempelkan ke package portable.

## Status

- Implemented: payload builder 64-byte, HID report framing, device discovery, reconnect loop, config, logging, single-instance mutex, PyInstaller onedir spec.
- Implemented: dynamic CPU sensor matching melalui LibreHardwareMonitor.
- Belum termasuk: tray UI, RGB/fan/pump control, firmware update, installer, dan upload release otomatis.
- Hardware validation tetap harus dilakukan pada Windows dengan FI4 terpasang.

## Quick start (development)

Persyaratan:

- Windows 10/11 x64
- Python 3.11+
- FI4 tersambung via USB
- `LibreHardwareMonitorLib.dll` yang kompatibel dengan versi Python/.NET yang dipakai

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m pytest
```

Jalankan setelah menyalin DLL monitoring ke `resources/LibreHardwareMonitorLib.dll`:

```powershell
python -m fi4_monitor
```

Config default dibaca dari `%LOCALAPPDATA%\FI4Monitor\config.json`. Untuk percobaan awal, salin [config.example.json](config.example.json) ke lokasi tersebut atau gunakan:

```powershell
python -m fi4_monitor --config .\config.example.json
```

Log berada di `%LOCALAPPDATA%\FI4Monitor\fi4monitor.log`.

## Build portable Windows

```powershell
.\scripts\build.ps1
```

Output utama berada di `dist\FI4Monitor\FI4Monitor.exe`. Build menggunakan `--onedir` karena lebih mudah memuat `hidapi`, pythonnet, dan native/.NET monitoring dependency secara stabil. Folder hasil build dapat langsung dipindahkan ke komputer target.

Sebelum build, pastikan file berikut tersedia:

```text
resources\LibreHardwareMonitorLib.dll
```

Detail dependency dan keputusan packaging ada di [docs/TECHNICAL.md](docs/TECHNICAL.md).

## Penggunaan di Windows

1. Tutup atau nonaktifkan Segotep Digital agar tidak ada dua proses yang menulis ke HID yang sama.
2. Jalankan `FI4Monitor.exe` dari folder portable.
3. Jika sudah stabil, buat shortcut ke `FI4Monitor.exe` di `shell:startup`.

Aplikasi tidak mengubah Windows startup secara otomatis. Device yang belum siap saat login, USB reset, sleep/resume, dan kegagalan write sementara akan ditangani dengan retry.

## Struktur repository

```text
src/fi4_monitor/
├── protocol.py                  # payload FI4 murni
├── device.py                    # discovery, open, write, reconnect
├── runner.py                    # scheduler dan recovery loop
├── config.py                    # JSON config
├── logging_setup.py             # rotating file log
├── single_instance.py           # Windows mutex
└── telemetry/
    ├── provider.py              # abstraction + data model
    └── libre_hardware_monitor.py
tests/                           # unit tests tanpa hardware
docs/TECHNICAL.md                # architecture dan deployment notes
resources/                       # external LHM DLL, tidak di-commit
FI4Monitor.spec                  # PyInstaller onedir build
```

## Roadmap pengembangan

1. Validasi protocol dan refresh rate pada hardware nyata.
2. Cocokkan sensor CPU package temperature/power dengan beberapa vendor CPU.
3. Uji sleep/resume, USB disable/enable, dan startup race.
4. Tambahkan smoke test Windows untuk build portable.
5. Pertimbangkan tray UI minimal setelah core loop stabil.

## Kontribusi

Lihat [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) untuk workflow, milestone, dan validation checklist.
