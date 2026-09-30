$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$lhmDll = Join-Path $projectRoot "resources\LibreHardwareMonitorLib.dll"
if (-not (Test-Path -LiteralPath $lhmDll)) {
    & (Join-Path $PSScriptRoot "build_lhm.ps1")
}

if (-not (Test-Path -LiteralPath $lhmDll)) {
    throw "LibreHardwareMonitorLib.dll was not produced by scripts/build_lhm.ps1."
}

python -m pip install -r requirements-dev.txt
python -m pytest
python -m PyInstaller --clean --noconfirm FI4Monitor.spec

Write-Host "Portable build ready at dist\FI4Monitor"
