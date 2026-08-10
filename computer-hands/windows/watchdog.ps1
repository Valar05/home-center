param(
  [string]$ConfigPath = "$env:LOCALAPPDATA\HomeCenter\ComputerHands\config.json",
  [string]$TaskName = 'HomeCenterComputerHands',
  [int]$StaleSeconds = 240,
  [int]$CheckSeconds = 30
)

$ErrorActionPreference = 'SilentlyContinue'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { exit 0 }

$root = Split-Path -Parent $ConfigPath
$watchdogLog = Join-Path $root 'watchdog.log'
function W([string]$Message) {
  Add-Content -LiteralPath $watchdogLog -Value ("{0} {1}" -f (Get-Date -Format o), $Message) -Encoding UTF8
  $info = Get-Item -LiteralPath $watchdogLog -ErrorAction SilentlyContinue
  if ($info -and $info.Length -gt 512KB) {
    Get-Content -LiteralPath $watchdogLog -Tail 500 | Set-Content -LiteralPath "$watchdogLog.tmp" -Encoding UTF8
    Move-Item -Force "$watchdogLog.tmp" $watchdogLog
  }
}

W "watchdog_start pid=$PID staleSeconds=$StaleSeconds checkSeconds=$CheckSeconds"
while ($true) {
  try {
    $cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    $progressProperty = $cfg.PSObject.Properties['progressPath']
    $progressPath = if ($progressProperty -and $progressProperty.Value) { [string]$progressProperty.Value } else { Join-Path $root 'progress.json' }
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $progress = Get-Item -LiteralPath $progressPath -ErrorAction SilentlyContinue
    $ageSeconds = if ($progress) { [Math]::Max(0, ((Get-Date) - $progress.LastWriteTime).TotalSeconds) } else { [double]::PositiveInfinity }
    if ($task.State -eq 'Running' -and $ageSeconds -gt $StaleSeconds) {
      W ("stale_worker ageSeconds={0:N0}; restarting task" -f $ageSeconds)
      Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
      Start-Sleep -Seconds 1
      Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
      Start-Sleep -Seconds 10
      $after = Get-Item -LiteralPath $progressPath -ErrorAction SilentlyContinue
      if ($after) { W "restart_progress_seen modified=$($after.LastWriteTime.ToString('o'))" }
      else { W 'restart_progress_missing' }
    } elseif ($task.State -ne 'Running') {
      W "worker_task_state=$($task.State); starting task"
      Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    }
  } catch {
    W ("watchdog_error " + $_.Exception.Message)
  }
  Start-Sleep -Seconds ([Math]::Max(10, $CheckSeconds))
}
