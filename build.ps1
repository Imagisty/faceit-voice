$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
}

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -m pip install --disable-pip-version-check -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

$icon = Join-Path $PSScriptRoot 'faceit_voice.ico'
& $python -m PyInstaller `
    --noconfirm --clean --onefile --windowed `
    --name FACEIT-Voice `
    --icon $icon `
    --add-data "${icon};." `
    --hidden-import demoparser2 `
    --hidden-import zstandard `
    --hidden-import pyarrow `
    --hidden-import polars `
    faceit_voice_gui.pyw
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

Write-Host "Built: $PSScriptRoot\dist\FACEIT-Voice.exe"
