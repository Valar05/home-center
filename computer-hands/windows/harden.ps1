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
$RunnerEnsurePath = Join-Path $Root 'ensure-github-runner.ps1'
$RunnerReceiptPath = Join-Path $Root 'github-runner-receipt.json'
$HealthPath = Join-Path $Root 'cloud-health.json'
$ReceiptPath = Join-Path $Root 'hardening-receipt.json'
$FailurePath = Join-Path $Root 'hardening-failure.json'
$TaskName = 'HomeCenterComputerHands'
$WatchdogTaskName = 'HomeCenterComputerHandsWatchdog'
$SentinelTaskName = 'HomeCenterFortressSentinel'

New-Item -ItemType Directory -Force -Path $Root | Out-Null
Remove-Item -Force -LiteralPath $ReceiptPath -ErrorAction SilentlyContinue
Remove-Item -Force -LiteralPath $FailurePath -ErrorAction SilentlyContinue
trap {
  $failure=[ordered]@{
    schema='home-center-thecauldron-hardening-failure-v1'
    failedAt=(Get-Date).ToUniversalTime().ToString('o')
    machine=$env:COMPUTERNAME
    sourceRef=$SourceRef
    message=$_.Exception.Message
    scriptStackTrace=$_.ScriptStackTrace
  }
  try { [IO.File]::WriteAllText($FailurePath,($failure|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false)) } catch {}
  exit 1
}
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
  'computer-hands/windows/ensure-github-runner.ps1' = $RunnerEnsurePath
}
foreach($entry in $sourceFiles.GetEnumerator()){
  $source=Read-GitFile ([string]$entry.Key)
  $tokens=$null
  $errors=$null
  [System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors) | Out-Null
  if($errors.Count -gt 0){
    throw ("PowerShell parse failed for {0}: {1}" -f $entry.Key,(($errors|ForEach-Object{$_.Message}) -join '; '))
  }
  [IO.File]::WriteAllText([string]$entry.Value,$source,[Text.UTF8Encoding]::new($false))
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
if ([string]::IsNullOrWhiteSpace($RunnerPath)) {
  $RunnerPath = Join-Path $env:LOCALAPPDATA 'HomeCenter\GitHubRunner'
}

$thronePath=Join-Path $env:USERPROFILE 'bin\throne.ps1'
if(-not (Test-Path -LiteralPath $thronePath)){ $thronePath='' }

$cfg | Add-Member -NotePropertyName healthPath -NotePropertyValue $HealthPath -Force
$cfg | Add-Member -NotePropertyName runnerPath -NotePropertyValue ([string]$RunnerPath) -Force
$cfg | Add-Member -NotePropertyName runnerTaskName -NotePropertyValue 'HomeCenterGitHubRunner' -Force
$cfg | Add-Member -NotePropertyName thronePath -NotePropertyValue ([string]$thronePath) -Force
$cfg | Add-Member -NotePropertyName hardeningVersion -NotePropertyValue 'thecauldron-fortress-v1' -Force
$cfg | Add-Member -NotePropertyName hardeningSourceRef -NotePropertyValue $SourceRef -Force
[IO.File]::WriteAllText($ConfigPath,($cfg|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))

$ps=(Get-Command powershell.exe -ErrorAction Stop).Source
$currentIdentity=[Security.Principal.WindowsIdentity]::GetCurrent()
if(-not $currentIdentity.User){ throw 'Could not resolve current Windows user SID.' }
$userSid=$currentIdentity.User.Value
$principal=New-ScheduledTaskPrincipal -UserId $userSid -LogonType Interactive -RunLevel Limited
$logon=New-ScheduledTaskTrigger -AtLogOn -User $userSid
$repeat=New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -Hidden -MultipleInstances IgnoreNew
$sentinelSettings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -WakeToRun -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -Hidden -MultipleInstances IgnoreNew

# Prove the principal is schedulable before stopping a single working task.
$preflightName="HomeCenterFortressPrincipalPreflight-$PID"
$preflightAction=New-ScheduledTaskAction -Execute $ps -Argument '-NoLogo -NoProfile -NonInteractive -Command "exit 0"'
try {
  Register-ScheduledTask -TaskName $preflightName -Action $preflightAction -Trigger $repeat -Principal $principal -Settings $settings -Force | Out-Null
} finally {
  Unregister-ScheduledTask -TaskName $preflightName -Confirm:$false -ErrorAction SilentlyContinue
}

function Register-FortressTask([string]$Name,[string]$Script,[string]$Extra='',[object]$TaskSettings=$settings) {
  $arg = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" {1}' -f $Script,$Extra
  $action=New-ScheduledTaskAction -Execute $ps -Argument $arg
  $backupXml=$null
  $existing=Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  if($existing){ $backupXml=Export-ScheduledTask -TaskName $Name }
  try {
    if($existing){ Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue }
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger @($logon,$repeat) -Principal $principal -Settings $TaskSettings -Force | Out-Null
    Start-ScheduledTask -TaskName $Name
  } catch {
    $installError=$_.Exception
    if($backupXml){
      try {
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask -TaskName $Name -Xml $backupXml -Force | Out-Null
        Start-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
      } catch {}
    }
    throw $installError
  }
}

Register-FortressTask $TaskName $LaunchPath ('-ConfigPath "{0}"' -f $ConfigPath)
Register-FortressTask $WatchdogTaskName $WatchdogPath ('-ConfigPath "{0}" -TaskName "{1}" -StaleSeconds 120 -CheckSeconds 20 -RestartCooldownSeconds 90' -f $ConfigPath,$TaskName)
Register-FortressTask $SentinelTaskName $SentinelPath ('-ConfigPath "{0}" -WorkerTaskName "{1}" -WatchdogTaskName "{2}" -CheckSeconds 20 -CloudStaleSeconds 150' -f $ConfigPath,$TaskName,$WatchdogTaskName) $sentinelSettings

$power=[ordered]@{changed=$false;standbyAc=$null;hibernateAc=$null;lidCloseAc=$null;reactivate=$null}
if(-not $PreserveAcSleep){
  & powercfg.exe /change standby-timeout-ac 0 | Out-Null
  $power.standbyAc=$LASTEXITCODE
  & powercfg.exe /change hibernate-timeout-ac 0 | Out-Null
  $power.hibernateAc=$LASTEXITCODE
  & powercfg.exe /setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 0 | Out-Null
  $power.lidCloseAc=$LASTEXITCODE
  & powercfg.exe /setactive SCHEME_CURRENT | Out-Null
  $power.reactivate=$LASTEXITCODE
  $power.changed=($power.standbyAc -eq 0 -and $power.hibernateAc -eq 0 -and $power.lidCloseAc -eq 0 -and $power.reactivate -eq 0)
}

& $RunnerEnsurePath -ConfigPath $ConfigPath -RunnerRoot $RunnerPath | Out-Host
if (-not (Test-Path -LiteralPath $RunnerReceiptPath)) { throw 'GitHub runner bootstrap produced no receipt.' }
$runnerReceipt = Get-Content -LiteralPath $RunnerReceiptPath -Raw | ConvertFrom-Json
if (-not $runnerReceipt.ok) { throw 'GitHub runner bootstrap receipt is not green.' }

Start-Sleep -Seconds 8
$taskRows=@()
foreach($n in @($TaskName,$WatchdogTaskName,$SentinelTaskName,'HomeCenterGitHubRunner')){
  $t=Get-ScheduledTask -TaskName $n
  $i=Get-ScheduledTaskInfo -TaskName $n
  $taskRows += [ordered]@{name=$n;state=[string]$t.State;lastTaskResult=$i.LastTaskResult;lastRunTime=$i.LastRunTime.ToString('o');nextRunTime=$i.NextRunTime.ToString('o')}
}
$fileRows=@()
foreach($p in @($WorkerPath,$WatchdogPath,$SentinelPath,$LaunchPath,$RunnerEnsurePath)){
  $fileRows += [ordered]@{path=$p;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant()}
}
$health=Get-Item -LiteralPath $HealthPath -ErrorAction SilentlyContinue
$healthAgeSeconds=if($health){[Math]::Max(0,((Get-Date)-$health.LastWriteTime).TotalSeconds)}else{[double]::PositiveInfinity}
$cloudFresh=[bool]($health -and $healthAgeSeconds -lt 90)
$powerOk=[bool]($PreserveAcSleep -or $power.changed)
$result=[ordered]@{
  schema='home-center-thecauldron-hardening-receipt-v1'
  appliedAt=(Get-Date).ToUniversalTime().ToString('o')
  machine=$env:COMPUTERNAME
  user=[Environment]::UserName
  userSid=$userSid
  sourceRef=$SourceRef
  repoPath=$RepoPath
  workerId=[string]$cfg.workerId
  tokenDecrypt='ok'
  power=$power
  runnerPath=[string]$RunnerPath
  thronePath=[string]$thronePath
  cloudHealthPath=$HealthPath
  cloudHealthPresent=[bool]$health
  cloudHealthAgeSeconds=if([double]::IsPositiveInfinity($healthAgeSeconds)){'infinite'}else{[int]$healthAgeSeconds}
  runner=[ordered]@{name=[string]$runnerReceipt.runnerName;version=[string]$runnerReceipt.version;taskState=[string]$runnerReceipt.taskState;githubStatus=[string]$runnerReceipt.githubStatus;listenerPid=$runnerReceipt.listenerPid;ok=[bool]$runnerReceipt.ok}
  tasks=$taskRows
  files=$fileRows
  ok=[bool](@($taskRows|Where-Object{$_.state -ne 'Running'}).Count -eq 0 -and $runnerReceipt.ok -and $cloudFresh -and $powerOk)
}
[IO.File]::WriteAllText($ReceiptPath,($result|ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
Remove-Item -Force -LiteralPath $FailurePath -ErrorAction SilentlyContinue
$result | ConvertTo-Json -Depth 12
if(-not $result.ok){ throw 'THECAULDRON hardening receipt is not green.' }
