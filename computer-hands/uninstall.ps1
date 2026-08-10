param(
  [switch]$KeepConfig
)

$ErrorActionPreference = 'Stop'
$InstallDir = Join-Path $env:LOCALAPPDATA 'HomeCenterHands'
$ConfigPath = Join-Path $InstallDir 'config.json'
$TaskName = 'HomeCenterHands'

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
  try { Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue } catch { }
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

if ($KeepConfig) {
  Get-ChildItem -LiteralPath $InstallDir -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -ne $ConfigPath } |
    Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
} else {
  Remove-Item -LiteralPath $InstallDir -Force -Recurse -ErrorAction SilentlyContinue
}

[ordered]@{
  ok = $true
  taskRemoved = $true
  installRemoved = (-not (Test-Path -LiteralPath $InstallDir))
  configKept = [bool]$KeepConfig
  fileLayer = 'drive_sync'
} | ConvertTo-Json -Depth 4
