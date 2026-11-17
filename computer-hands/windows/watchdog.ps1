param(
  [string]$ConfigPath = "$env:LOCALAPPDATA\HomeCenter\ComputerHands\config.json",
  [string]$TaskName = 'HomeCenterComputerHands',
  [int]$StaleSeconds = 120,
  [int]$CheckSeconds = 20,
  [int]$RestartCooldownSeconds = 90
)

$ErrorActionPreference = 'SilentlyContinue'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { exit 0 }

$root = Split-Path -Parent $ConfigPath
$watchdogLog = Join-Path $root 'watchdog.log'
$watchdogHeartbeat = Join-Path $root 'watchdog-health.json'
$lastRestart = [DateTime]::MinValue

function W([string]$Message) {
  Add-Content -LiteralPath $watchdogLog -Value ("{0} {1}" -f (Get-Date -Format o), $Message) -Encoding UTF8
  $info = Get-Item -LiteralPath $watchdogLog -ErrorAction SilentlyContinue
  if ($info -and $info.Length -gt 512KB) {
    Get-Content -LiteralPath $watchdogLog -Tail 500 | Set-Content -LiteralPath "$watchdogLog.tmp" -Encoding UTF8
    Move-Item -Force "$watchdogLog.tmp" $watchdogLog
  }
}

function Write-WatchdogHeartbeat([object]$State) {
  try {
    $payload = [ordered]@{
      schema='home-center-computer-hands-watchdog-health-v1'
      updatedAt=(Get-Date).ToUniversalTime().ToString('o')
      pid=$PID
      workerTask=$TaskName
      state=$State
    } | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText("$watchdogHeartbeat.tmp", $payload, [Text.UTF8Encoding]::new($false))
    Move-Item -Force "$watchdogHeartbeat.tmp" $watchdogHeartbeat
  } catch {}
}

function Restart-Worker([string]$Reason) {
  $now = Get-Date
  if (($now - $lastRestart).TotalSeconds -lt $RestartCooldownSeconds) {
    W "restart_suppressed reason=$Reason cooldownSeconds=$RestartCooldownSeconds"
    return
  }
  $script:lastRestart = $now
  W "restart_worker reason=$Reason"
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
  Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
}

W "watchdog_start pid=$PID staleSeconds=$StaleSeconds checkSeconds=$CheckSeconds cooldownSeconds=$RestartCooldownSeconds"
while ($true) {
  try {
    $cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    $healthProperty = $cfg.PSObject.Properties['healthPath']
    $healthPath = if ($healthProperty -and $healthProperty.Value) { [string]$healthProperty.Value } else { Join-Path $root 'cloud-health.json' }
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $health = Get-Item -LiteralPath $healthPath -ErrorAction SilentlyContinue
    $ageSeconds = if ($health) { [Math]::Max(0, ((Get-Date) - $health.LastWriteTime).TotalSeconds) } else { [double]::PositiveInfinity }

    Write-WatchdogHeartbeat @{
      workerTaskState=[string]$task.State
      cloudHealthPath=$healthPath
      cloudHealthAgeSeconds=if([double]::IsPositiveInfinity($ageSeconds)){'infinite'}else{[int]$ageSeconds}
    }

    if ($task.State -ne 'Running') {
      Restart-Worker "task_state_$($task.State)"
    } elseif ($ageSeconds -gt $StaleSeconds) {
      Restart-Worker ("cloud_health_stale_{0:N0}s" -f $ageSeconds)
    }
  } catch {
    W ("watchdog_error " + $_.Exception.Message)
  }
  Start-Sleep -Seconds ([Math]::Max(10, $CheckSeconds))
}
