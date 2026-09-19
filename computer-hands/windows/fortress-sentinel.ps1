param(
  [string]$ConfigPath = "$env:LOCALAPPDATA\HomeCenter\ComputerHands\config.json",
  [string]$WorkerTaskName = 'HomeCenterComputerHands',
  [string]$WatchdogTaskName = 'HomeCenterComputerHandsWatchdog',
  [int]$CheckSeconds = 20,
  [int]$CloudStaleSeconds = 150,
  [int]$LowBatteryReleasePercent = 20
)

$ErrorActionPreference = 'SilentlyContinue'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { exit 0 }

$root = Split-Path -Parent $ConfigPath
$log = Join-Path $root 'fortress-sentinel.log'
$statePath = Join-Path $root 'fortress-sentinel-health.json'
$lastWorkerRestart = [DateTime]::MinValue
$lastRunnerStart = [DateTime]::MinValue
$lastThroneLaunch = [DateTime]::MinValue

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class FortressPower {
  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern uint SetThreadExecutionState(uint esFlags);
  public const uint ES_CONTINUOUS = 0x80000000;
  public const uint ES_SYSTEM_REQUIRED = 0x00000001;
}
'@

function L([string]$Message) {
  Add-Content -LiteralPath $log -Value ("{0} {1}" -f (Get-Date -Format o), $Message) -Encoding UTF8
  $i=Get-Item -LiteralPath $log -ErrorAction SilentlyContinue
  if($i -and $i.Length -gt 1MB){
    Get-Content -LiteralPath $log -Tail 1000 | Set-Content -LiteralPath "$log.tmp" -Encoding UTF8
    Move-Item -Force "$log.tmp" $log
  }
}

function Get-PowerState {
  $onAc=$true
  $batteryPercent=$null
  try {
    $rows=@(Get-CimInstance -Namespace root\wmi -Class BatteryStatus -ErrorAction Stop)
    if($rows.Count -gt 0){
      $onAc=[bool]($rows | Where-Object { $_.PowerOnline } | Select-Object -First 1)
    }
  } catch {}

  try {
    $battery=Get-CimInstance Win32_Battery -ErrorAction Stop | Select-Object -First 1
    if($battery -and $battery.EstimatedChargeRemaining -ne $null){
      $batteryPercent=[int]$battery.EstimatedChargeRemaining
    }
  } catch {}

  # Uptime wins during ordinary battery use. At critically low battery, release
  # the execution-state hold so Windows can protect the machine instead of
  # Fortress driving it into a hard power loss.
  $holdAwake=[bool]($onAc -or $batteryPercent -eq $null -or $batteryPercent -gt $LowBatteryReleasePercent)
  return [ordered]@{
    acPower=$onAc
    batteryPercent=$batteryPercent
    lowBatteryReleasePercent=$LowBatteryReleasePercent
    sleepInhibited=$holdAwake
  }
}

function Ensure-Task([string]$Name) {
  try {
    $t=Get-ScheduledTask -TaskName $Name -ErrorAction Stop
    if($t.State -ne 'Running'){
      L "task_start name=$Name previous=$($t.State)"
      Start-ScheduledTask -TaskName $Name -ErrorAction Stop
    }
    return [string](Get-ScheduledTask -TaskName $Name).State
  } catch {
    L "task_error name=$Name detail=$($_.Exception.Message)"
    return 'missing_or_error'
  }
}

function Start-RunnerIfNeeded([object]$Cfg) {
  $listener=@(Get-Process -Name 'Runner.Listener' -ErrorAction SilentlyContinue)
  if($listener.Count -gt 0){ return @{state='running';pid=$listener[0].Id} }

  $taskProperty=$Cfg.PSObject.Properties['runnerTaskName']
  $runnerTaskName=if($taskProperty -and $taskProperty.Value){[string]$taskProperty.Value}else{''}
  if($runnerTaskName){
    try {
      $task=Get-ScheduledTask -TaskName $runnerTaskName -ErrorAction Stop
      if(((Get-Date)-$lastRunnerStart).TotalSeconds -ge 90){
        if($task.State -eq 'Running'){
          Stop-ScheduledTask -TaskName $runnerTaskName -ErrorAction SilentlyContinue
          Start-Sleep -Seconds 1
          L "runner_task_recycle_no_listener name=$runnerTaskName"
        }
        Start-ScheduledTask -TaskName $runnerTaskName -ErrorAction Stop
        $script:lastRunnerStart=Get-Date
        return @{state='task_started';task=$runnerTaskName}
      }
      return @{state='task_waiting';task=$runnerTaskName}
    } catch {
      L "runner_task_error name=$runnerTaskName detail=$($_.Exception.Message)"
    }
  }

  $services=@(Get-Service -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'actions.runner*' })
  foreach($svc in $services){
    if($svc.Status -ne 'Running'){
      try { Start-Service -Name $svc.Name -ErrorAction Stop; L "runner_service_started name=$($svc.Name)" } catch { L "runner_service_start_failed name=$($svc.Name) detail=$($_.Exception.Message)" }
    }
  }
  $listener=@(Get-Process -Name 'Runner.Listener' -ErrorAction SilentlyContinue)
  if($listener.Count -gt 0){ return @{state='running_service';pid=$listener[0].Id} }

  $runnerProperty=$Cfg.PSObject.Properties['runnerPath']
  $runnerPath=if($runnerProperty -and $runnerProperty.Value){[string]$runnerProperty.Value}else{''}
  if($runnerPath -and (Test-Path -LiteralPath (Join-Path $runnerPath 'run.cmd'))){
    if(((Get-Date)-$lastRunnerStart).TotalSeconds -ge 90){
      try {
        Start-Process -FilePath (Join-Path $runnerPath 'run.cmd') -WorkingDirectory $runnerPath -WindowStyle Hidden
        $script:lastRunnerStart=Get-Date
        L "runner_process_started path=$runnerPath"
        return @{state='started';path=$runnerPath}
      } catch { L "runner_process_start_failed detail=$($_.Exception.Message)" }
    }
    return @{state='waiting_after_start';path=$runnerPath}
  }
  return @{state='not_configured'}
}

function Ensure-Throne([object]$Cfg) {
  $p=$Cfg.PSObject.Properties['thronePath']
  $path=if($p -and $p.Value){[string]$p.Value}else{''}
  if(-not $path -or -not (Test-Path -LiteralPath $path)){ return @{state='not_configured'} }
  try {
    $status=& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $path status 2>&1 | Out-String
    if($status -match 'state=running'){ return @{state='running'} }
    if(((Get-Date)-$lastThroneLaunch).TotalSeconds -ge 90){
      & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $path launch 2>&1 | ForEach-Object { L "throne_launch $_" }
      $script:lastThroneLaunch=Get-Date
      return @{state='launch_requested'}
    }
    return @{state='waiting_after_launch'}
  } catch { L "throne_error detail=$($_.Exception.Message)"; return @{state='error'} }
}

function Ensure-Tailscale {
  try {
    $svc=Get-Service -Name 'Tailscale' -ErrorAction Stop
    if($svc.Status -ne 'Running'){
      try { Start-Service -Name 'Tailscale' -ErrorAction Stop; L 'tailscale_started' } catch { L "tailscale_start_failed detail=$($_.Exception.Message)" }
    }
    return [string](Get-Service -Name 'Tailscale').Status
  } catch { return 'missing_or_error' }
}

L "sentinel_start pid=$PID"
while($true){
  try {
    $cfg=Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    $powerState=Get-PowerState
    if($powerState.sleepInhibited){
      [void][FortressPower]::SetThreadExecutionState([FortressPower]::ES_CONTINUOUS -bor [FortressPower]::ES_SYSTEM_REQUIRED)
    } else {
      [void][FortressPower]::SetThreadExecutionState([FortressPower]::ES_CONTINUOUS)
    }

    $workerTaskState=Ensure-Task $WorkerTaskName
    $watchdogTaskState=Ensure-Task $WatchdogTaskName

    $hp=$cfg.PSObject.Properties['healthPath']
    $healthPath=if($hp -and $hp.Value){[string]$hp.Value}else{Join-Path $root 'cloud-health.json'}
    $health=Get-Item -LiteralPath $healthPath -ErrorAction SilentlyContinue
    $healthAge=if($health){[Math]::Max(0,((Get-Date)-$health.LastWriteTime).TotalSeconds)}else{[double]::PositiveInfinity}
    if($workerTaskState -eq 'Running' -and $healthAge -gt $CloudStaleSeconds -and ((Get-Date)-$lastWorkerRestart).TotalSeconds -ge 120){
      L ("worker_restart_stale_cloud ageSeconds={0:N0}" -f $healthAge)
      Stop-ScheduledTask -TaskName $WorkerTaskName -ErrorAction SilentlyContinue
      Start-Sleep -Seconds 1
      Start-ScheduledTask -TaskName $WorkerTaskName -ErrorAction SilentlyContinue
      $lastWorkerRestart=Get-Date
    }

    $runner=Start-RunnerIfNeeded $cfg
    $throne=Ensure-Throne $cfg
    $tailscale=Ensure-Tailscale
    $state=[ordered]@{
      schema='home-center-cauldron-fortress-sentinel-v1'
      updatedAt=(Get-Date).ToUniversalTime().ToString('o')
      machine=$env:COMPUTERNAME
      pid=$PID
      acPower=[bool]$powerState.acPower
      batteryPercent=$powerState.batteryPercent
      lowBatteryReleasePercent=[int]$powerState.lowBatteryReleasePercent
      sleepInhibited=[bool]$powerState.sleepInhibited
      workerTask=$workerTaskState
      watchdogTask=$watchdogTaskState
      cloudHealthPath=$healthPath
      cloudHealthAgeSeconds=if([double]::IsPositiveInfinity($healthAge)){'infinite'}else{[int]$healthAge}
      runner=$runner
      throne=$throne
      tailscale=$tailscale
    }
    [IO.File]::WriteAllText("$statePath.tmp",($state|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
    Move-Item -Force "$statePath.tmp" $statePath
  } catch { L "sentinel_error detail=$($_.Exception.Message)" }
  Start-Sleep -Seconds ([Math]::Max(10,$CheckSeconds))
}
