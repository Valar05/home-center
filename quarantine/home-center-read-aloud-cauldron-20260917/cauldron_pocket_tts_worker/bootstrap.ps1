param([string]$InstallRoot = "$env:LOCALAPPDATA\Ferravine\PocketTtsWorker\v2")
$ErrorActionPreference = "Stop"
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $InstallRoot ".venv"
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Copy-Item (Join-Path $SourceRoot "render_section.py") $InstallRoot -Force
Copy-Item (Join-Path $SourceRoot "requirements.txt") $InstallRoot -Force
Copy-Item (Join-Path $SourceRoot "pocket_tts_render_v2.py") $InstallRoot -Force
py -3.12 -m venv $Venv
$Python = Join-Path $Venv "Scripts\python.exe"
& $Python -m pip install --disable-pip-version-check -r (Join-Path $InstallRoot "requirements.txt")
& $Python -c "import pocket_tts; print('CAULDRON_POCKET_TTS_READY')"
Set-Content -Path (Join-Path $InstallRoot "READY-v2.json") -Value '{"status":"ready","contractVersion":"pocket-tts-render-v2"}' -Encoding UTF8
Write-Host "THECAULDRON Pocket TTS renderer installed at $InstallRoot"
Write-Host "It opens no listener and controls no playback; Home Center invokes it over SSH per section."
