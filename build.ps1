param([string]$Python = "$PSScriptRoot\.venv\Scripts\python.exe")
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath $Python)) { throw 'Create .venv and install requirements-dev.txt first.' }
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
& $Python -m PyInstaller --noconfirm --windowed --onedir --name ModelDock --icon assets\modeldock.ico --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
& $Python tools\prepare_release.py
if ($LASTEXITCODE -ne 0) { throw 'Preparing release failed.' }
$zipPath = Join-Path $PSScriptRoot 'dist\ModelDock-0.1.0-windows-x64.zip'
Compress-Archive -LiteralPath (Join-Path $PSScriptRoot 'dist\ModelDock') -DestinationPath $zipPath -Force
$digest = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
"$digest  ModelDock-0.1.0-windows-x64.zip" | Set-Content -LiteralPath "$zipPath.sha256" -Encoding ascii
Write-Host "Release ready: $zipPath"
