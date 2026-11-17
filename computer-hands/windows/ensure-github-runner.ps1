param(
  [string]$Repo = 'Valar05/home-center',
  [string]$RepoUrl = 'https://github.com/Valar05/home-center',
  [string]$RunnerName = 'THECAULDRON',
  [string]$RunnerRoot = "$env:LOCALAPPDATA\HomeCenter\GitHubRunner",
  [string]$TaskName = 'HomeCenterGitHubRunner',
  [string]$ConfigPath = "$env:LOCALAPPDATA\HomeCenter\ComputerHands\config.json",
  [string]$Version = '2.337.0',
  [string]$ExpectedSha256 = '1150692afa94e71f872017e254ea55b6eece1eece3fe7e3a6d4c93d0a1b85cfc'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'GitHub runner bootstrap requires Windows.' }

$gh = (Get-Command gh.exe -ErrorAction Stop).Source
$curl = (Get-Command curl.exe -ErrorAction Stop).Source
$asset = "actions-runner-win-x64-$Version.zip"
$releaseTag = "v$Version"
$downloadUrl = "https://github.com/actions/runner/releases/download/$releaseTag/$asset"
$stateRoot = Join-Path $env:LOCALAPPDATA 'HomeCenter\ComputerHands'
$receiptPath = Join-Path $stateRoot 'github-runner-receipt.json'
$failurePath = Join-Path $stateRoot 'github-runner-failure.json'
$logPath = Join-Path $stateRoot 'github-runner-bootstrap.log'
$zipPath = Join-Path $env:TEMP $asset
New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null
Remove-Item -Force -LiteralPath $receiptPath -ErrorAction SilentlyContinue
Remove-Item -Force -LiteralPath $failurePath -ErrorAction SilentlyContinue
trap {
  $failure=[ordered]@{
    schema='home-center-github-runner-failure-v1'
    failedAt=(Get-Date).ToUniversalTime().ToString('o')
    machine=$env:COMPUTERNAME
    runnerName=$RunnerName
    version=$Version
    message=$_.Exception.Message
    scriptStackTrace=$_.ScriptStackTrace
  }
  try { [IO.File]::WriteAllText($failurePath,($failure|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false)) } catch {}
  exit 1
}

function Log([string]$Message) {
  New-Item -ItemType Directory -Force -Path $stateRoot | Out-Null
  Add-Content -LiteralPath $logPath -Value ("{0} {1}" -f (Get-Date -Format o), $Message) -Encoding UTF8
}

function Get-RegisteredRunner {
  try {
    $inventory = (& $gh api "repos/$Repo/actions/runners" | Out-String | ConvertFrom-Json)
    return @($inventory.runners | Where-Object { $_.name -eq $RunnerName }) | Select-Object -First 1
  } catch {
    Log "runner_inventory_failed $($_.Exception.Message)"
    return $null
  }
}

$null = & $gh auth status 2>&1
if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI is not authenticated on THECAULDRON.' }

New-Item -ItemType Directory -Force -Path $RunnerRoot | Out-Null
$listenerPath = Join-Path $RunnerRoot 'bin\Runner.Listener.exe'
$configPath = Join-Path $RunnerRoot '.runner'

if (-not (Test-Path -LiteralPath $listenerPath)) {
  Remove-Item -Force -LiteralPath $zipPath -ErrorAction SilentlyContinue
  Log "download_begin tag=$releaseTag asset=$asset"
  & $curl -L --fail --retry 3 --retry-delay 2 --output $zipPath $downloadUrl
  if ($LASTEXITCODE -ne 0) { throw "Runner download failed with exit $LASTEXITCODE" }
  $actualSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLowerInvariant()
  if ($actualSha -ne $ExpectedSha256.ToLowerInvariant()) {
    Remove-Item -Force -LiteralPath $zipPath -ErrorAction SilentlyContinue
    throw "Runner SHA-256 mismatch expected=$ExpectedSha256 actual=$actualSha"
  }
  Get-ChildItem -LiteralPath $RunnerRoot -Force -ErrorAction SilentlyContinue |
    Remove-Item -Force -Recurse -ErrorAction Stop
  Expand-Archive -LiteralPath $zipPath -DestinationPath $RunnerRoot -Force
  Remove-Item -Force -LiteralPath $zipPath -ErrorAction SilentlyContinue
  if (-not (Test-Path -LiteralPath $listenerPath)) { throw "Runner.Listener.exe missing after verified extraction: $listenerPath" }
  Log "download_verified sha256=$actualSha"
} else {
  Log 'runner_payload_already_present'
}

$registered = Get-RegisteredRunner
$needRegistration = (-not (Test-Path -LiteralPath $configPath)) -or (-not $registered)
if ($needRegistration) {
  Log 'registration_begin'
  if (Test-Path -LiteralPath $configPath) {
    # Stale local registration with no server-side runner. Preserve diagnostics, then reset local registration markers.
    $stale = Join-Path $stateRoot ("runner-stale-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force -Path $stale | Out-Null
    foreach ($name in @('.runner','.credentials','.credentials_rsaparams')) {
      $p = Join-Path $RunnerRoot $name
      if (Test-Path -LiteralPath $p) { Move-Item -Force -LiteralPath $p -Destination (Join-Path $stale $name) }
    }
  }

  # Registration token is intentionally consumed entirely inside this process and never emitted.
  $registrationToken = (& $gh api -X POST "repos/$Repo/actions/runners/registration-token" --jq '.token' | Out-String).Trim()
  if ([string]::IsNullOrWhiteSpace($registrationToken)) { throw 'GitHub returned an empty runner registration token.' }
  try {
    Push-Location $RunnerRoot
    $help = (& .\config.cmd --help 2>&1 | Out-String)
    $args = @(
      '--unattended',
      '--replace',
      '--url', $RepoUrl,
      '--token', $registrationToken,
      '--name', $RunnerName,
      '--labels', 'THECAULDRON',
      '--work', '_work'
    )
    if ($help -match '--disableupdate') { $args += '--disableupdate' }
    & .\config.cmd @args
    if ($LASTEXITCODE -ne 0) { throw "config.cmd failed with exit $LASTEXITCODE" }
  } finally {
    Pop-Location -ErrorAction SilentlyContinue
    $registrationToken = $null
  }
  $registered = Get-RegisteredRunner
  if (-not $registered) { throw 'Runner registration did not appear in GitHub inventory.' }
  Log "registration_ok id=$($registered.id)"
}

$userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if ([string]::IsNullOrWhiteSpace($userSid)) { throw 'Could not resolve current Windows SID for runner task.' }
$principal = New-ScheduledTaskPrincipal -UserId $userSid -LogonType Interactive -RunLevel Limited
$logon = New-ScheduledTaskTrigger -AtLogOn -User $userSid
$repeat = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -Hidden -MultipleInstances IgnoreNew
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/d /s /c "run.cmd"' -WorkingDirectory $RunnerRoot

$backupXml = $null
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) { $backupXml = Export-ScheduledTask -TaskName $TaskName }
try {
  if ($existingTask) { Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue }
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($logon,$repeat) -Principal $principal -Settings $settings -Force | Out-Null
  Start-ScheduledTask -TaskName $TaskName
} catch {
  $taskError = $_.Exception
  if ($backupXml) {
    try {
      Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
      Register-ScheduledTask -TaskName $TaskName -Xml $backupXml -Force | Out-Null
      Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    } catch {}
  }
  throw $taskError
}

$deadline = (Get-Date).AddSeconds(45)
$listener = $null
$registered = $null
while ((Get-Date) -lt $deadline) {
  $listener = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq 'Runner.Listener.exe' -and $_.ExecutablePath -eq $listenerPath } |
    Select-Object -First 1
  $registered = Get-RegisteredRunner
  if ($listener -and $registered -and $registered.status -eq 'online') { break }
  Start-Sleep -Seconds 2
}

if (Test-Path -LiteralPath $ConfigPath) {
  $cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
  $cfg | Add-Member -NotePropertyName runnerPath -NotePropertyValue $RunnerRoot -Force
  $cfg | Add-Member -NotePropertyName runnerTaskName -NotePropertyValue $TaskName -Force
  $cfg | Add-Member -NotePropertyName runnerVersion -NotePropertyValue $Version -Force
  $cfgTemp = "$ConfigPath.tmp"
  [IO.File]::WriteAllText($cfgTemp,($cfg | ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
  Move-Item -Force $cfgTemp $ConfigPath
}

$task = Get-ScheduledTask -TaskName $TaskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
$registered = Get-RegisteredRunner
$listener = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -eq 'Runner.Listener.exe' -and $_.ExecutablePath -eq $listenerPath } |
  Select-Object -First 1

$receipt = [ordered]@{
  schema = 'home-center-github-runner-receipt-v1'
  verifiedAt = (Get-Date).ToUniversalTime().ToString('o')
  machine = $env:COMPUTERNAME
  runnerName = $RunnerName
  runnerRoot = $RunnerRoot
  version = $Version
  asset = $asset
  assetSha256 = $ExpectedSha256.ToLowerInvariant()
  listenerSha256 = if (Test-Path -LiteralPath $listenerPath) { (Get-FileHash -Algorithm SHA256 -LiteralPath $listenerPath).Hash.ToLowerInvariant() } else { $null }
  taskName = $TaskName
  taskState = [string]$task.State
  taskLastResult = $taskInfo.LastTaskResult
  listenerPid = if ($listener) { [int]$listener.ProcessId } else { $null }
  githubRunnerId = if ($registered) { [int64]$registered.id } else { $null }
  githubStatus = if ($registered) { [string]$registered.status } else { 'missing' }
  githubBusy = if ($registered) { [bool]$registered.busy } else { $false }
  ok = [bool]($listener -and $registered -and $registered.status -eq 'online' -and $task.State -eq 'Running')
}
[IO.File]::WriteAllText($receiptPath,($receipt | ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
Remove-Item -Force -LiteralPath $failurePath -ErrorAction SilentlyContinue
$receipt | ConvertTo-Json -Depth 10
if (-not $receipt.ok) { throw 'GitHub runner did not reach registered online state.' }
