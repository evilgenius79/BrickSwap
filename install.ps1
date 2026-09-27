$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Have($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Write-Host "BrickSwap installer"

if (-not (Have "winget")) {
    Write-Host "winget missing. Install App Installer from the Microsoft Store, then re-run."
    exit 1
}

if (-not (Have "ffmpeg")) {
    Write-Host "Installing ffmpeg..."
    winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
}

if (-not (Have "py") -and -not (Have "python")) {
    Write-Host "Installing Python 3.12..."
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
}

$py = "py"
if (-not (Have "py")) { $py = "python" }

if (-not (Test-Path ".\.venv")) {
    & $py -3.12 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -r requirements.txt

@"
@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" run.py
"@ | Set-Content -Encoding ASCII ".\start_brickswap.bat"

Write-Host ""
Write-Host "App install done. ComfyUI + Wan 2.2 Animate is a separate step; see README.md."
Write-Host "Launch with start_brickswap.bat"
Write-Host "First action after launch: Preview masks. Do not run a full clip yet."
