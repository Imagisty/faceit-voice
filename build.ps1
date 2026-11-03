$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

cargo build --release --manifest-path (Join-Path $PSScriptRoot 'parser\Cargo.toml')
if ($LASTEXITCODE -ne 0) { throw 'Rust parser build failed.' }

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
}

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -m pip install --disable-pip-version-check -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

$runtime = Join-Path $PSScriptRoot 'vendor\demo-fixer\qjs.exe'
if ((Get-FileHash -LiteralPath $runtime -Algorithm SHA256).Hash -ne 'FF03398D74EA6E6BD3A8E58058F7003225ABCAC229D7D57775B7AAAE812A49C7') {
    throw 'Bundled QuickJS runtime checksum mismatch.'
}

$icon = Join-Path $PSScriptRoot 'faceit_voice.ico'
$parser = Join-Path $PSScriptRoot 'parser\target\release\faceit_voice_parser.exe'
& $python -m PyInstaller `
    --noconfirm --clean --onefile --windowed `
    --name FACEIT-Voice `
    --icon $icon `
    --add-data "${icon};." `
    --add-data "vendor\demo-fixer;vendor\demo-fixer" `
    --add-binary "${parser};." `
    --exclude-module demoparser2 `
    --exclude-module pyarrow `
    --exclude-module polars `
    --exclude-module pandas `
    --exclude-module numpy `
    faceit_voice_gui.pyw
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

Write-Host "Built: $PSScriptRoot\dist\FACEIT-Voice.exe"
