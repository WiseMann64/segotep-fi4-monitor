# PyInstaller onedir build. The LibreHardwareMonitor DLL is copied from
# resources/ and is intentionally not checked into source control.
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs


project_root = Path(SPECPATH)
src_root = project_root / "src"
resource_root = project_root / "resources"

a = Analysis(
    [str(src_root / "fi4_monitor" / "__main__.py")],
    pathex=[str(src_root)],
    binaries=collect_dynamic_libs("hid"),
    datas=[(str(resource_root), "resources")],
    hiddenimports=["clr"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FI4Monitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="FI4Monitor",
)
