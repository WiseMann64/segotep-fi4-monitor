$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$lhmDll = Join-Path $projectRoot "resources\LibreHardwareMonitorLib.dll"
if (-not (Test-Path -LiteralPath $lhmDll)) {
    throw "Missing resources\LibreHardwareMonitorLib.dll. Copy a compatible LibreHardwareMonitor library before building."
}

python -m pip install -r requirements-dev.txt
python -m pytest
python -m PyInstaller --clean --noconfirm FI4Monitor.spec

Write-Host "Portable build ready at dist\FI4Monitor"
