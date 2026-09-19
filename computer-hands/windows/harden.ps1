param(
  [Parameter(Mandatory=$true)][string]$RepoPath,
  [string]$SourceRef = 'origin/main',
  [string]$RunnerPath = '',
  [switch]$PreserveAcSleep
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'THECAULDRON hardening requires Windows.' }
if (-not (Test-Path -LiteralPath (Join-Path $RepoPath '.git'))) { throw "Authenticated Home Center clone not found: $RepoPath" }

$Root = Join-Path $env:LOCALAPPDATA 'HomeCenter\ComputerHands'
$ConfigPath = Join-Path $Root 'config.json'
$TokenPath = Join-Path $Root 'worker-token.dpapi'
$WorkerPath = Join-Path $Root 'home-center-hands.ps1'
$WatchdogPath = Join-Path $Root 'watchdog.ps1'
$SentinelPath = Join-Path $Root 'fortress-sentinel.ps1'
$LaunchPath = Join-Path $Root 'launch.ps1'
$HealthPath = Join-Path $Root 'cloud-health.json'
$ReceiptPath = Join-Path $Root 'hardening-receipt.json'
$TaskName = 'HomeCenterComputerHands'
$WatchdogTaskName = 'HomeCenterComputerHandsWatchdog'
$SentinelTaskName = 'HomeCenterFortressSentinel'

New-Item -ItemType Directory -Force -Path $Root | Out-Null
if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "Missing Computer Hands config: $ConfigPath" }
if (-not (Test-Path -LiteralPath $TokenPath)) { throw "Missing DPAPI worker token: $TokenPath" }

$secure = (Get-Content -LiteralPath $TokenPath -Raw).Trim() | ConvertTo-SecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  if ([string]::IsNullOrWhiteSpace($plain)) { throw 'DPAPI worker token decrypted empty.' }
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

function Read-GitFile([string]$Path) {
  $spec = $SourceRef + ':' + $Path
  $text = & git -C $RepoPath show $spec
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($text -join [Environment]::NewLine))) {
    throw "Could not read $Path from $SourceRef"
  }
  return ($text -join [Environment]::NewLine) + [Environment]::NewLine
}

$sourceFiles = [ordered]@{
  'computer-hands/windows/home-center-hands.ps1' = $WorkerPath
  'computer-hands/windows/watchdog.ps1' = $WatchdogPath
  'computer-hands/windows/fortress-sentinel.ps1' = $SentinelPath
  'computer-hands/windows/launch.ps1' = $LaunchPath
}
foreach($entry in $sourceFiles.GetEnumerator()){
  [IO.File]::WriteAllText([string]$entry.Value,(Read-GitFile ([string]$entry.Key)),[Text.UTF8Encoding]::new($false))
}

$cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
if (-not $cfg.origin -or -not $cfg.workerId -or -not $cfg.tokenPath) { throw 'Computer Hands config is incomplete.' }

if ([string]::IsNullOrWhiteSpace($RunnerPath)) {
  $rp=$cfg.PSObject.Properties['runnerPath']
  if($rp -and $rp.Value){ $RunnerPath=[string]$rp.Value }
}
if ([string]::IsNullOrWhiteSpace($RunnerPath)) {
  $candidates=@(
    'C:\actions-runner',
    (Join-Path $env:USERPROFILE 'actions-runner'),
    (Join-Path $env:USERPROFILE 'actions-runner-home-center'),
    (Join-Path $env:USERPROFILE 'workspace\actions-runner'),
    (Join-Path $env:USERPROFILE 'workspace\home-center-runner')
  )
  $RunnerPath=$candidates | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'run.cmd') } | Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace($RunnerPath)) {
  $runnerMarker=Get-ChildItem -LiteralPath $env:USERPROFILE -Filter '.runner' -File -Recurse -Depth 5 -ErrorAction SilentlyContinue | Select-Object -First 1
  if($runnerMarker -and (Test-Path -LiteralPath (Join-Path $runnerMarker.DirectoryName 'run.cmd'))){ $RunnerPath=$runnerMarker.DirectoryName }
}

$thronePath=Join-Path $env:USERPROFILE 'bin\throne.ps1'
if(-not (Test-Path -LiteralPath $thronePath)){ $thronePath='' }

$cfg | Add-Member -NotePropertyName healthPath -NotePropertyValue $HealthPath -Force
$cfg | Add-Member -NotePropertyName runnerPath -NotePropertyValue ([string]$RunnerPath) -Force
$cfg | Add-Member -NotePropertyName thronePath -NotePropertyValue ([string]$thronePath) -Force
$cfg | Add-Member -NotePropertyName hardeningVersion -NotePropertyValue 'thecauldron-fortress-v1' -Force
$cfg | Add-Member -NotePropertyName hardeningSourceRef -NotePropertyValue $SourceRef -Force
[IO.File]::WriteAllText($ConfigPath,($cfg|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))

$ps=(Get-Command powershell.exe -ErrorAction Stop).Source
$user="$env:USERDOMAIN\$env:USERNAME"
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$logon=New-ScheduledTaskTrigger -AtLogOn -User $user
$repeat=New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -Hidden -MultipleInstances IgnoreNew

function Register-FortressTask([string]$Name,[string]$Script,[string]$Extra='') {
  $arg = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" {1}' -f $Script,$Extra
  $action=New-ScheduledTaskAction -Execute $ps -Argument $arg
  Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  Register-ScheduledTask -TaskName $Name -Action $action -Trigger @($logon,$repeat) -Principal $principal -Settings $settings -Force | Out-Null
  Start-ScheduledTask -TaskName $Name
}

Register-FortressTask $TaskName $LaunchPath ('-ConfigPath "{0}"' -f $ConfigPath)
Register-FortressTask $WatchdogTaskName $WatchdogPath ('-ConfigPath "{0}" -TaskName "{1}" -StaleSeconds 120 -CheckSeconds 20 -RestartCooldownSeconds 90' -f $ConfigPath,$TaskName)
Register-FortressTask $SentinelTaskName $SentinelPath ('-ConfigPath "{0}" -WorkerTaskName "{1}" -WatchdogTaskName "{2}" -CheckSeconds 20 -CloudStaleSeconds 150' -f $ConfigPath,$TaskName,$WatchdogTaskName)

$power=[ordered]@{changed=$false;standbyAc=$null;hibernateAc=$null}
if(-not $PreserveAcSleep){
  & powercfg.exe /change standby-timeout-ac 0 | Out-Null
  $power.standbyAc=$LASTEXITCODE
  & powercfg.exe /change hibernate-timeout-ac 0 | Out-Null
  $power.hibernateAc=$LASTEXITCODE
  $power.changed=($power.standbyAc -eq 0 -and $power.hibernateAc -eq 0)
}

Start-Sleep -Seconds 8
$taskRows=@()
foreach($n in @($TaskName,$WatchdogTaskName,$SentinelTaskName)){
  $t=Get-ScheduledTask -TaskName $n
  $i=Get-ScheduledTaskInfo -TaskName $n
  $taskRows += [ordered]@{name=$n;state=[string]$t.State;lastTaskResult=$i.LastTaskResult;lastRunTime=$i.LastRunTime.ToString('o');nextRunTime=$i.NextRunTime.ToString('o')}
}
$fileRows=@()
foreach($p in @($WorkerPath,$WatchdogPath,$SentinelPath,$LaunchPath)){
  $fileRows += [ordered]@{path=$p;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant()}
}
$health=Get-Item -LiteralPath $HealthPath -ErrorAction SilentlyContinue
$result=[ordered]@{
  schema='home-center-thecauldron-hardening-receipt-v1'
  appliedAt=(Get-Date).ToUniversalTime().ToString('o')
  machine=$env:COMPUTERNAME
  user=[Environment]::UserName
  sourceRef=$SourceRef
  repoPath=$RepoPath
  workerId=[string]$cfg.workerId
  tokenDecrypt='ok'
  power=$power
  runnerPath=[string]$RunnerPath
  thronePath=[string]$thronePath
  cloudHealthPath=$HealthPath
  cloudHealthPresent=[bool]$health
  tasks=$taskRows
  files=$fileRows
  ok=[bool](@($taskRows|Where-Object{$_.state -ne 'Running'}).Count -eq 0)
}
[IO.File]::WriteAllText($ReceiptPath,($result|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
$result | ConvertTo-Json -Depth 12
