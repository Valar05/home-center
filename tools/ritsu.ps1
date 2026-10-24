# PATH command: ritsu on | ritsu off | ritsu status
param([Parameter(Position=0)][ValidateSet('on','off','status')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$root = Join-Path $HOME 'Documents\Codex\Venice\PocketTTS'
switch ($Action) {
  'on'  { & (Join-Path $PSScriptRoot 'ritsu-on.ps1'); if (-not $?) { exit 1 } }
  'off' { & (Join-Path $PSScriptRoot 'ritsu-off.ps1'); if (-not $?) { exit 1 } }
  'status' {
    $marker = Join-Path $root 'RITSU_POCKET_MAINTENANCE'
    Write-Host ('Auto-restart inhibited: ' + (Test-Path -LiteralPath $marker))
    $listen = @(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 10205 -State Listen -ErrorAction SilentlyContinue)
    if ($listen.Count) { Write-Host ('Local port 10205 listening: PID(s) ' + (($listen | Select-Object -ExpandProperty OwningProcess -Unique) -join ', ')) }
    else { Write-Host 'Local port 10205 not listening.' }
  }
}
