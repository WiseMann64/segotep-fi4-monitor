$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$tag = "v0.9.6"
$sourceRoot = Join-Path $env:TEMP ("FI4Monitor-LHM-" + [guid]::NewGuid().ToString("N"))
$repository = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor.git"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required to fetch the LibreHardwareMonitor source."
}
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw "The .NET SDK is required to compile LibreHardwareMonitor."
}

Write-Host "Fetching LibreHardwareMonitor $tag source..."
git clone --depth 1 --branch $tag $repository $sourceRoot
if ($LASTEXITCODE -ne 0) {
    throw "Unable to fetch LibreHardwareMonitor source."
}

$libraryProject = Join-Path $sourceRoot "LibreHardwareMonitorLib\LibreHardwareMonitorLib.csproj"
Write-Host "Compiling LibreHardwareMonitorLib for .NET 8..."
dotnet build $libraryProject --configuration Release --framework net8.0 -p:Platform=x64 -p:CopyLocalLockFileAssemblies=true
if ($LASTEXITCODE -ne 0) {
    throw "LibreHardwareMonitorLib build failed."
}

$buildOutput = Join-Path $sourceRoot "bin\Release\x64\net8.0"
$mainDll = Join-Path $buildOutput "LibreHardwareMonitorLib.dll"
if (-not (Test-Path -LiteralPath $mainDll)) {
    throw "Build completed but LibreHardwareMonitorLib.dll was not found at $buildOutput."
}

$resourceRoot = Join-Path $projectRoot "resources"
New-Item -ItemType Directory -Force -Path $resourceRoot | Out-Null
Get-ChildItem -LiteralPath $buildOutput -Filter "*.dll" -File | Copy-Item -Destination $resourceRoot -Force
Copy-Item -LiteralPath $mainDll -Destination (Join-Path $resourceRoot "LibreHardwareMonitorLib.dll") -Force
Set-Content -LiteralPath (Join-Path $resourceRoot "LibreHardwareMonitor.version.txt") -Value "$tag (built locally for net8.0)" -Encoding utf8

$notice = Join-Path $sourceRoot "THIRD-PARTY-NOTICES.txt"
if (Test-Path -LiteralPath $notice) {
    Copy-Item -LiteralPath $notice -Destination (Join-Path $resourceRoot "LibreHardwareMonitor-THIRD-PARTY-NOTICES.txt") -Force
}
$license = Join-Path $sourceRoot "LICENSE"
if (Test-Path -LiteralPath $license) {
    Copy-Item -LiteralPath $license -Destination (Join-Path $resourceRoot "LibreHardwareMonitor-LICENSE.txt") -Force
}

Write-Host "Built LibreHardwareMonitor dependencies copied to $resourceRoot"
