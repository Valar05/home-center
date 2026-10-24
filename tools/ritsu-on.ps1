# Resume the existing Ritsu Pocket TTS supervisor. Does not touch other services.
$ErrorActionPreference = 'Stop'
$root = Join-Path $HOME 'Documents\Codex\Venice\PocketTTS'
if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw "Pocket TTS installation not found: $root" }
$marker = Join-Path $root 'RITSU_POCKET_MAINTENANCE'
if (Test-Path -LiteralPath $marker) { Remove-Item -LiteralPath $marker -Force }
Write-Host 'Ritsu Pocket maintenance mode OFF. Existing supervisor can restart the API (normally within 15 seconds).'
$listener = @(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 10205 -State Listen -ErrorAction SilentlyContinue)
if ($listener.Count) { Write-Host 'Port 10205 already listening; check the service identity before assuming Ritsu is ready.' }
else { Write-Host 'No listener yet. If it does not start, check that the existing Ritsu supervisor startup task is running.' }
