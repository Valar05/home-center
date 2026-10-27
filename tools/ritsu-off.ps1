# ritsu-off.ps1
# Stop only the identified Ritsu Pocket TTS repertoire service on THECAULDRON.
# The maintenance marker keeps its existing supervisor from restarting the API.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Join-Path $HOME 'Documents\Codex\Venice\PocketTTS'
$marker = Join-Path $root 'RITSU_POCKET_MAINTENANCE'
$server = Join-Path $root 'ritsu_pocket_repertoire_server_v2.py'
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    throw "Pocket TTS directory not found: $root. Nothing stopped."
}
# Persist the inhibit first. The supervisor checks this marker every 15 seconds.
New-Item -ItemType File -Path $marker -Force | Out-Null
Write-Host 'Ritsu Pocket auto-restart inhibited.'
# Identify the exact listening process. Do not use broad Python, uvicorn, or port-only kills.
$listener = @(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 10205 -State Listen -ErrorAction SilentlyContinue)
$ids = @($listener | Select-Object -ExpandProperty OwningProcess -Unique)
$stopped = $false
foreach ($idCandidate in $ids) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $idCandidate" -ErrorAction SilentlyContinue
    if (-not $proc) { continue }
    $cmd = [string]$proc.CommandLine
    if ($cmd -notmatch 'ritsu_pocket_repertoire_server_v2\.py' -or $cmd -notmatch 'PocketTTS') {
        Write-Warning "Port 10205 is owned by PID $idCandidate, but it is not the expected Ritsu server. Leaving it alone."
        continue
    }
    Stop-Process -Id $idCandidate -ErrorAction Stop
    Write-Host "Stopped Ritsu Pocket TTS PID $idCandidate."
    $stopped = $true
}
if (-not $stopped) {
    Write-Host 'No confirmed Ritsu Pocket server was stopped (it may already be off).'
}
Write-Host "Inhibit marker: $marker"
