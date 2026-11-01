param(
  [string]$RepoPath = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Computer Hands repair requires Windows.' }
# Repair is intentionally callable through the existing authenticated SSH recovery lane.
# DPAPI token decryption below remains the authority check for the Windows user.

if ([string]::IsNullOrWhiteSpace($RepoPath)) {
  $candidate = Join-Path (Get-Location) 'home-center'
  if (Test-Path -LiteralPath (Join-Path $candidate '.git')) { $RepoPath = $candidate }
  elseif (Test-Path -LiteralPath (Join-Path (Get-Location) '.git')) { $RepoPath = (Get-Location).Path }
  else { throw 'Could not locate the authenticated home-center Git clone. Run from the workspace directory or pass -RepoPath.' }
}

$Root = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'HomeCenter\ComputerHands'
$WorkerPath = Join-Path $Root 'home-center-hands.ps1'
$WatchdogPath = Join-Path $Root 'watchdog.ps1'
$LaunchPath = Join-Path $Root 'launch.ps1'
$ConfigPath = Join-Path $Root 'config.json'
$TokenPath = Join-Path $Root 'worker-token.dpapi'
$StartupLog = Join-Path $Root 'startup.log'
$WorkerLog = Join-Path $Root 'worker.log'
$ProgressPath = Join-Path $Root 'progress.json'
$TaskName = 'HomeCenterComputerHands'
$WatchdogTaskName = 'HomeCenterComputerHandsWatchdog'

New-Item -ItemType Directory -Force -Path $Root | Out-Null
if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "Missing Computer Hands config: $ConfigPath" }
if (-not (Test-Path -LiteralPath $TokenPath)) { throw "Missing registered DPAPI worker token: $TokenPath" }

# Pull only remote refs. Never merge, checkout, stash, reset, or alter the worktree.
& git -C $RepoPath fetch --quiet origin main
if ($LASTEXITCODE -ne 0) { throw 'git fetch origin main failed.' }
$workerText = & git -C $RepoPath show 'origin/main:computer-hands/windows/home-center-hands.ps1'
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($workerText -join "`n"))) { throw 'Could not read worker from origin/main.' }
$workerText | Set-Content -LiteralPath $WorkerPath -Encoding UTF8
$watchdogText = & git -C $RepoPath show 'origin/main:computer-hands/windows/watchdog.ps1'
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($watchdogText -join "`n"))) { throw 'Could not read watchdog from origin/main.' }
$watchdogText | Set-Content -LiteralPath $WatchdogPath -Encoding UTF8

$launch = @'
param([string]$ConfigPath)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $ConfigPath
$startup = Join-Path $root 'startup.log'
function S([string]$m) { Add-Content -LiteralPath $startup -Value ("{0} {1}" -f (Get-Date -Format o), $m) -Encoding UTF8 }
try {
  S "launcher_start pid=$PID user=$([Environment]::UserName) interactive=$([Environment]::UserInteractive)"
  $worker = Join-Path $root 'home-center-hands.ps1'
  if (-not (Test-Path -LiteralPath $worker)) { throw "Worker missing: $worker" }
  & $worker -ConfigPath $ConfigPath
  S "worker_returned exit=$LASTEXITCODE"
} catch {
  S ("startup_failure " + $_.Exception.ToString())
  throw
}
'@
$launch | Set-Content -LiteralPath $LaunchPath -Encoding UTF8

# Validate the registered token can still be decrypted as this Windows user.
$cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
if (-not $cfg.origin -or -not $cfg.workerId -or -not $cfg.tokenPath) { throw 'Computer Hands config is incomplete.' }
$driveProgress = Get-PSDrive -PSProvider FileSystem | ForEach-Object { Join-Path $_.Root 'My Drive\Venice Runtime\Venice Reconstruction' } | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($driveProgress) { $ProgressPath = Join-Path $driveProgress 'LOCAL_HANDS_PROGRESS.json' }
$cfg | Add-Member -NotePropertyName progressPath -NotePropertyValue $ProgressPath -Force
[IO.File]::WriteAllText($ConfigPath, ($cfg | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
$secure = (Get-Content -LiteralPath $TokenPath -Raw).Trim() | ConvertTo-SecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  if ([string]::IsNullOrWhiteSpace($plain)) { throw 'DPAPI worker token decrypted empty.' }
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

Remove-Item -LiteralPath $StartupLog -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $WorkerLog -Force -ErrorAction SilentlyContinue

$ps = (Get-Command powershell.exe -ErrorAction Stop).Source
$arg = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$LaunchPath`" -ConfigPath `"$ConfigPath`""
$action = New-ScheduledTaskAction -Execute $ps -Argument $arg
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -Hidden
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

$watchdogArg = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WatchdogPath`" -ConfigPath `"$ConfigPath`" -TaskName `"$TaskName`""
$watchdogAction = New-ScheduledTaskAction -Execute $ps -Argument $watchdogArg
Stop-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $WatchdogTaskName -Action $watchdogAction -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $WatchdogTaskName
Start-Sleep -Seconds 6

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName
$result = [ordered]@{
  ok = $true
  taskState = [string]$task.State
  watchdogState = [string](Get-ScheduledTask -TaskName $WatchdogTaskName).State
  watchdogPath = $WatchdogPath
  lastTaskResult = $info.LastTaskResult
  root = $Root
  configOrigin = [string]$cfg.origin
  workerId = [string]$cfg.workerId
  tokenDecrypt = 'ok'
  startupLog = if (Test-Path -LiteralPath $StartupLog) { @(Get-Content -LiteralPath $StartupLog -Tail 30) } else { @('startup.log missing') }
  workerLog = if (Test-Path -LiteralPath $WorkerLog) { @(Get-Content -LiteralPath $WorkerLog -Tail 30) } else { @('worker.log missing') }
  progressPath = $ProgressPath
  progress = if (Test-Path -LiteralPath $ProgressPath) { Get-Content -LiteralPath $ProgressPath -Raw } else { 'progress missing' }
}
$result | ConvertTo-Json -Depth 6
