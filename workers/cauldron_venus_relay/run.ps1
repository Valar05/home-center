$ErrorActionPreference = "Stop"
$InstallRoot = Join-Path $env:LOCALAPPDATA "Fortress\VenusCauldronRelay\v1"
$env:HOME_CENTER_VENUS_RELAY_ORIGIN = (Get-Content (Join-Path $InstallRoot ".worker-origin") -Raw).Trim()
$env:HOME_CENTER_VENUS_MODELS = (Get-Content (Join-Path $InstallRoot ".worker-models") -Raw).Trim()
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
& py -3.12 (Join-Path $InstallRoot "worker.py")

