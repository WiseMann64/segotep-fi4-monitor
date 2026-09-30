# PyInstaller onedir build, including LibreHardwareMonitor and tray backends.
import importlib.util
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH)
src_root = project_root / "src"
resource_root = project_root / "resources"
hid_module = importlib.util.find_spec("hid")
if hid_module is None or hid_module.origin is None:
    raise RuntimeError("hidapi extension was not found in the build environment")

a = Analysis(
    [str(src_root / "fi4_monitor" / "__main__.py")],
    pathex=[str(src_root)],
    binaries=[(hid_module.origin, ".")],
    datas=[(str(resource_root), "resources")],
    hiddenimports=["clr", *collect_submodules("pystray")],
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
