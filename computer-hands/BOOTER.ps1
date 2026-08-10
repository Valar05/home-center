param(
  [ValidateSet('Install','Repair','Diagnose','Uninstall')]
  [string]$Mode = 'Install',

  [string]$BootstrapCode = '',
  [string]$WorkerId = 'windows-hands-01',
  [string]$Origin = 'https://us-central1-home-center-dclar.cloudfunctions.net/computerHands',
  [string]$Branch = 'main',

  [switch]$KeepConfigOnUninstall,
  [switch]$NoBanner,
  [switch]$NonInteractive,
  [switch]$SkipCloudHealth,
  [switch]$KeepBackups,
  [int]$StartupProbeSeconds = 20
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Script:BooterVersion = 'home-center-computer-hands-booter.v2'
$Script:ContractExpected = 'home-center.computer-hands-contract.v1'
$Script:ApiExpected = 'home-center.computer-hands-api.v1'
$Script:FileLayerExpected = 'drive_sync'
$Script:StartedAt = Get-Date
$Script:RunId = 'booter-' + [Guid]::NewGuid().ToString('N')
$Script:InstallDir = Join-Path $env:LOCALAPPDATA 'HomeCenterHands'
$Script:ConfigPath = Join-Path $Script:InstallDir 'config.json'
$Script:WorkerPath = Join-Path $Script:InstallDir 'worker.ps1'
$Script:LogPath = Join-Path $Script:InstallDir 'worker.log'
$Script:ReceiptPath = Join-Path $Script:InstallDir 'last-booter-receipt.json'
$Script:TranscriptPath = Join-Path $Script:InstallDir 'booter-transcript.log'
$Script:TaskName = 'HomeCenterHands'
$Script:BackupRoot = Join-Path $Script:InstallDir 'backups'
$Script:CurrentBackup = Join-Path $Script:BackupRoot $Script:RunId
$Script:Ledger = [System.Collections.Generic.List[object]]::new()
$Script:Warnings = [System.Collections.Generic.List[string]]::new()
$Script:Claims = [ordered]@{
  requestedCapability = 'Home Center Computer Hands'
  requestedOwner = 'Home Center'
  fileLayer = $Script:FileLayerExpected
  cloudHealthObserved = $false
  bootstrapExchanged = $false
  workerDownloaded = $false
  workerSyntaxValid = $false
  scheduledTaskInstalled = $false
  taskStarted = $false
  localConfigProtected = $false
  workerHeartbeatObserved = $false
  endToEndHandsProven = $false
}

function NowIso { (Get-Date).ToString('o') }

function Add-Ledger {
  param(
    [string]$Phase,
    [string]$Status,
    [string]$Detail,
    $Evidence = $null
  )
  $entry = [ordered]@{
    at = NowIso
    phase = $Phase
    status = $Status
    detail = $Detail
    evidence = $Evidence
  }
  $Script:Ledger.Add([pscustomobject]$entry)
  $prefix = switch ($Status) {
    'ok' { '[+]' }
    'warn' { '[!]' }
    'skip' { '[-]' }
    'fail' { '[X]' }
    default { '[.]' }
  }
  Write-Host "$prefix $Phase :: $Detail"
}

function Add-Warning {
  param([string]$Text)
  $Script:Warnings.Add($Text)
  Add-Ledger -Phase 'warning' -Status 'warn' -Detail $Text
}

function Assert-True {
  param([bool]$Condition, [string]$Message, [string]$Phase = 'assertion')
  if (-not $Condition) {
    Add-Ledger -Phase $Phase -Status 'fail' -Detail $Message
    throw $Message
  }
}

function Sha256-File {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return '' }
  (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-JsonFile {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  try { Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json }
  catch { throw "Invalid JSON at $Path :: $($_.Exception.Message)" }
}

function Write-JsonAtomic {
  param([string]$Path, $Value)
  $directory = Split-Path -Parent $Path
  New-Item -ItemType Directory -Path $directory -Force | Out-Null
  $tmp = "$Path.$([Guid]::NewGuid().ToString('N')).tmp"
  try {
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -LiteralPath $tmp -Destination $Path -Force
  } finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
  }
}

function Invoke-Json {
  param(
    [ValidateSet('GET','POST')][string]$Method,
    [string]$Uri,
    $Body = $null,
    [hashtable]$Headers = @{},
    [int]$TimeoutSec = 20
  )
  $params = @{
    Method = $Method
    Uri = $Uri
    Headers = $Headers
    UseBasicParsing = $true
    TimeoutSec = $TimeoutSec
  }
  if ($null -ne $Body) {
    $params.ContentType = 'application/json'
    $params.Body = ($Body | ConvertTo-Json -Depth 12 -Compress)
  }
  Invoke-RestMethod @params
}

function Test-PowerShellFileSyntax {
  param([string]$Path)
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $Path), [ref]$tokens, [ref]$errors)
  if ($errors -and $errors.Count) {
    $text = ($errors | ForEach-Object { $_.Message }) -join '; '
    throw "PowerShell parser rejected $Path :: $text"
  }
  $true
}

function Protect-ConfigAcl {
  param([string]$Path)
  $acl = Get-Acl -LiteralPath $Path
  $acl.SetAccessRuleProtection($true, $false)
  foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRule($rule) }
  $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
  $ruleCurrent = New-Object Security.AccessControl.FileSystemAccessRule($currentIdentity, 'FullControl', 'Allow')
  $ruleSystem = New-Object Security.AccessControl.FileSystemAccessRule('SYSTEM', 'FullControl', 'Allow')
  $acl.AddAccessRule($ruleCurrent)
  $acl.AddAccessRule($ruleSystem)
  Set-Acl -LiteralPath $Path -AclObject $acl
  $Script:Claims.localConfigProtected = $true
}

function Backup-ExistingState {
  if (-not (Test-Path -LiteralPath $Script:InstallDir)) {
    Add-Ledger -Phase 'backup' -Status 'skip' -Detail 'No prior installation exists.'
    return
  }
  New-Item -ItemType Directory -Path $Script:CurrentBackup -Force | Out-Null
  foreach ($name in @('config.json','worker.ps1','last-booter-receipt.json')) {
    $source = Join-Path $Script:InstallDir $name
    if (Test-Path -LiteralPath $source) {
      Copy-Item -LiteralPath $source -Destination (Join-Path $Script:CurrentBackup $name) -Force
    }
  }
  try {
    $task = Get-ScheduledTask -TaskName $Script:TaskName -ErrorAction Stop
    $task | Export-Clixml -LiteralPath (Join-Path $Script:CurrentBackup 'scheduled-task.xml')
  } catch { }
  Add-Ledger -Phase 'backup' -Status 'ok' -Detail "Captured prior state." -Evidence @{ path = $Script:CurrentBackup }
}

function Restore-BackupBestEffort {
  if (-not (Test-Path -LiteralPath $Script:CurrentBackup)) { return }
  Add-Ledger -Phase 'rollback' -Status 'warn' -Detail 'Attempting best-effort rollback to pre-run local state.'
  try {
    foreach ($name in @('config.json','worker.ps1','last-booter-receipt.json')) {
      $source = Join-Path $Script:CurrentBackup $name
      $dest = Join-Path $Script:InstallDir $name
      if (Test-Path -LiteralPath $source) { Copy-Item -LiteralPath $source -Destination $dest -Force }
    }
    Add-Ledger -Phase 'rollback' -Status 'ok' -Detail 'Previous local files restored where backups existed.'
  } catch {
    Add-Warning "Rollback was incomplete: $($_.Exception.Message)"
  }
}

function Cloud-Health {
  $uri = "$($Origin.TrimEnd('/'))/computer-hands/v1/health"
  $health = Invoke-Json -Method GET -Uri $uri -TimeoutSec 20
  Assert-True ($health.ok -eq $true) 'Computer Hands health endpoint did not return ok=true.' 'cloud-health'
  Assert-True ([string]$health.service -eq 'computer-hands') 'Unexpected Computer Hands service identity.' 'cloud-health'
  Assert-True ([string]$health.apiVersion -eq $Script:ApiExpected) "API mismatch. Expected $Script:ApiExpected, got $($health.apiVersion)." 'cloud-health'
  Assert-True ([string]$health.contractVersion -eq $Script:ContractExpected) "Contract mismatch. Expected $Script:ContractExpected, got $($health.contractVersion)." 'cloud-health'
  Assert-True ([string]$health.fileLayer -eq $Script:FileLayerExpected) 'File-layer invariant failed. Drive sync must remain the file layer.' 'cloud-health'
  $caps = @($health.capabilities)
  foreach ($cap in @('system.status','screen.capture','window.list','window.focus','process.list','process.start','process.stop','input.type','input.key','input.mouse','clipboard.get','clipboard.set','shell.exec')) {
    Assert-True ($caps -contains $cap) "Cloud contract missing expected capability: $cap" 'cloud-health'
  }
  $Script:Claims.cloudHealthObserved = $true
  Add-Ledger -Phase 'cloud-health' -Status 'ok' -Detail 'Production Computer Hands contract is live and preserves Drive sync as file layer.' -Evidence @{ uri = $uri; apiVersion = $health.apiVersion; contractVersion = $health.contractVersion; capabilities = $caps }
  $health
}

function Exchange-Bootstrap {
  Assert-True (-not [string]::IsNullOrWhiteSpace($BootstrapCode)) 'BootstrapCode is required for Install/Repair.' 'bootstrap'
  $uri = "$($Origin.TrimEnd('/'))/computer-hands/v1/bootstrap"
  $registration = Invoke-Json -Method POST -Uri $uri -Body @{ bootstrapCode = $BootstrapCode; workerId = $WorkerId } -TimeoutSec 30
  Assert-True (-not [string]::IsNullOrWhiteSpace([string]$registration.token)) 'Home Center did not return a worker token.' 'bootstrap'
  Assert-True ([string]$registration.contractVersion -eq $Script:ContractExpected) 'Bootstrap returned the wrong Computer Hands contract version.' 'bootstrap'
  $Script:Claims.bootstrapExchanged = $true
  Add-Ledger -Phase 'bootstrap' -Status 'ok' -Detail 'One-use bootstrap exchanged for worker token.' -Evidence @{ workerId = $WorkerId; origin = $registration.origin; contractVersion = $registration.contractVersion; token = '[redacted]' }
  $registration
}

function Download-Worker {
  param([string]$TargetBranch)
  $url = "https://raw.githubusercontent.com/Valar05/home-center/$TargetBranch/computer-hands/worker.ps1"
  New-Item -ItemType Directory -Path $Script:InstallDir -Force | Out-Null
  $tmp = Join-Path $Script:InstallDir ('worker-' + [Guid]::NewGuid().ToString('N') + '.tmp.ps1')
  try {
    Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing -TimeoutSec 30
    Assert-True (Test-Path -LiteralPath $tmp) 'Worker download did not produce a file.' 'worker-download'
    Assert-True ((Get-Item -LiteralPath $tmp).Length -gt 1000) 'Worker payload is suspiciously small.' 'worker-download'
    [void](Test-PowerShellFileSyntax -Path $tmp)
    $Script:Claims.workerSyntaxValid = $true
    Move-Item -LiteralPath $tmp -Destination $Script:WorkerPath -Force
    $Script:Claims.workerDownloaded = $true
    Add-Ledger -Phase 'worker-download' -Status 'ok' -Detail 'Worker downloaded and parsed before installation.' -Evidence @{ url = $url; sha256 = Sha256-File $Script:WorkerPath; bytes = (Get-Item -LiteralPath $Script:WorkerPath).Length }
  } finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
  }
}

function Write-WorkerConfig {
  param($Registration)
  $config = [ordered]@{
    origin = [string]$Registration.origin
    workerId = $WorkerId
    token = [string]$Registration.token
    contractVersion = [string]$Registration.contractVersion
    installedAt = NowIso
    installedBy = $env:USERNAME
    booterVersion = $Script:BooterVersion
    runId = $Script:RunId
    workerSha256 = Sha256-File $Script:WorkerPath
    fileLayer = $Script:FileLayerExpected
  }
  Write-JsonAtomic -Path $Script:ConfigPath -Value $config
  Protect-ConfigAcl -Path $Script:ConfigPath
  Add-Ledger -Phase 'config' -Status 'ok' -Detail 'Worker config written atomically and ACL restricted.' -Evidence @{ path = $Script:ConfigPath; token = '[redacted]'; fileLayer = $Script:FileLayerExpected }
}

function Install-ScheduledTask {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
  $argument = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script:WorkerPath`" -ConfigPath `"$Script:ConfigPath`""
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argument
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Days 0)
  Register-ScheduledTask -TaskName $Script:TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Home Center owner-scoped Computer Hands outbound worker. Drive sync remains the file layer.' -Force | Out-Null
  $Script:Claims.scheduledTaskInstalled = $true
  Add-Ledger -Phase 'scheduled-task' -Status 'ok' -Detail 'Idempotent logon task installed.' -Evidence @{ taskName = $Script:TaskName; identity = $identity; executable = 'powershell.exe'; arguments = $argument }
}

function Start-WorkerTask {
  Start-ScheduledTask -TaskName $Script:TaskName
  $Script:Claims.taskStarted = $true
  Add-Ledger -Phase 'start' -Status 'ok' -Detail 'Scheduled worker start requested.'
}

function Local-Diagnostics {
  $diag = [ordered]@{
    os = [Environment]::OSVersion.VersionString
    powershell = $PSVersionTable.PSVersion.ToString()
    processArchitecture = [Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture.ToString()
    machine = $env:COMPUTERNAME
    user = $env:USERNAME
    installDirExists = Test-Path -LiteralPath $Script:InstallDir
    configExists = Test-Path -LiteralPath $Script:ConfigPath
    workerExists = Test-Path -LiteralPath $Script:WorkerPath
    workerSha256 = Sha256-File $Script:WorkerPath
    taskExists = $false
    taskState = ''
    lastTaskResult = $null
  }
  try {
    $task = Get-ScheduledTask -TaskName $Script:TaskName -ErrorAction Stop
    $info = Get-ScheduledTaskInfo -TaskName $Script:TaskName
    $diag.taskExists = $true
    $diag.taskState = [string]$task.State
    $diag.lastTaskResult = [int]$info.LastTaskResult
  } catch { }
  Add-Ledger -Phase 'local-diagnostics' -Status 'ok' -Detail 'Collected local installation state.' -Evidence $diag
  [pscustomobject]$diag
}

function Probe-WorkerStartup {
  param([int]$Seconds)
  $deadline = (Get-Date).AddSeconds([Math]::Max(3, $Seconds))
  $observedRunning = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $task = Get-ScheduledTask -TaskName $Script:TaskName -ErrorAction Stop
      $info = Get-ScheduledTaskInfo -TaskName $Script:TaskName
      if ([string]$task.State -eq 'Running' -or [int]$info.LastTaskResult -eq 267009) {
        $observedRunning = $true
        break
      }
    } catch { }
    Start-Sleep -Milliseconds 750
  }
  if ($observedRunning) {
    Add-Ledger -Phase 'startup-probe' -Status 'ok' -Detail 'Windows reports the worker task running.'
  } else {
    Add-Warning 'Windows did not report the worker task running during the startup probe window. This is local evidence only; inspect task history before assuming cloud failure.'
  }
  $observedRunning
}

function Remove-Hands {
  Add-Ledger -Phase 'uninstall' -Status 'ok' -Detail 'Beginning local kill-switch sequence.'
  $task = Get-ScheduledTask -TaskName $Script:TaskName -ErrorAction SilentlyContinue
  if ($task) {
    try { Stop-ScheduledTask -TaskName $Script:TaskName -ErrorAction SilentlyContinue } catch { }
    Unregister-ScheduledTask -TaskName $Script:TaskName -Confirm:$false
  }
  if ($KeepConfigOnUninstall) {
    if (Test-Path -LiteralPath $Script:InstallDir) {
      Get-ChildItem -LiteralPath $Script:InstallDir -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -eq $Script:ConfigPath -or $_.FullName -like "$Script:BackupRoot*" } |
        ForEach-Object { }
      Get-ChildItem -LiteralPath $Script:InstallDir -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -ne $Script:ConfigPath -and $_.FullName -notlike "$Script:BackupRoot*" } |
        Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
    }
  } else {
    Remove-Item -LiteralPath $Script:InstallDir -Force -Recurse -ErrorAction SilentlyContinue
  }
  $Script:Claims.scheduledTaskInstalled = $false
  $Script:Claims.taskStarted = $false
  Add-Ledger -Phase 'uninstall' -Status 'ok' -Detail 'Local Computer Hands worker removed. Drive-synced files were untouched.' -Evidence @{ keepConfig = [bool]$KeepConfigOnUninstall; fileLayer = $Script:FileLayerExpected }
}

function Self-Reflection {
  $known = [System.Collections.Generic.List[string]]::new()
  $inferred = [System.Collections.Generic.List[string]]::new()
  $refused = [System.Collections.Generic.List[string]]::new()

  if ($Script:Claims.cloudHealthObserved) { $known.Add('The production Computer Hands endpoint answered the expected API and contract health check during this run.') }
  if ($Script:Claims.bootstrapExchanged) { $known.Add('A one-use bootstrap credential was accepted and a worker credential was issued during this run.') }
  if ($Script:Claims.workerDownloaded -and $Script:Claims.workerSyntaxValid) { $known.Add('The installed worker payload was downloaded during this run and parsed successfully by this machine PowerShell parser.') }
  if ($Script:Claims.scheduledTaskInstalled) { $known.Add('The Windows scheduled task exists because this run installed or replaced it.') }
  if ($Script:Claims.localConfigProtected) { $known.Add('The local worker configuration ACL was restricted to the current Windows identity and SYSTEM.') }

  if ($Script:Claims.taskStarted) { $inferred.Add('The worker was asked to start. A running scheduled task is evidence of local execution, not proof that Home Center can yet control the machine.') }
  $inferred.Add('If the cloud deployment is healthy and the worker continues polling successfully, Home Center should be able to lease future Computer Hands tickets to this machine.')

  if (-not $Script:Claims.workerHeartbeatObserved) { $refused.Add('This booter does not claim an authenticated Home Center worker heartbeat unless one is observed through the authorized Home Center cloud state.') }
  if (-not $Script:Claims.endToEndHandsProven) { $refused.Add('This booter does not claim end-to-end hands are proven. That requires an owner-issued Home Center action and a returned cloud receipt from this worker.') }
  $refused.Add('This booter does not claim local files are Home Center artifacts. Drive sync remains the file layer.')
  $refused.Add('This booter does not treat a locally running process as proof of deployed cloud capability.')

  [ordered]@{
    known = @($known)
    inferred = @($inferred)
    refusedClaims = @($refused)
  }
}

function Build-Receipt {
  param([string]$Status, [string]$Failure = '')
  $finished = Get-Date
  [ordered]@{
    schemaVersion = 'home-center.computer-hands-booter-receipt.v2'
    booterVersion = $Script:BooterVersion
    runId = $Script:RunId
    mode = $Mode
    status = $Status
    failure = $Failure
    startedAt = $Script:StartedAt.ToString('o')
    finishedAt = $finished.ToString('o')
    durationMs = [int64]($finished - $Script:StartedAt).TotalMilliseconds
    workerId = $WorkerId
    origin = $Origin
    branch = $Branch
    taskName = $Script:TaskName
    installDir = $Script:InstallDir
    fileLayer = $Script:FileLayerExpected
    claims = $Script:Claims
    reflection = Self-Reflection
    warnings = @($Script:Warnings)
    ledger = @($Script:Ledger)
  }
}

function Write-Receipt {
  param($Receipt)
  if (-not (Test-Path -LiteralPath $Script:InstallDir)) {
    New-Item -ItemType Directory -Path $Script:InstallDir -Force | Out-Null
  }
  try {
    Write-JsonAtomic -Path $Script:ReceiptPath -Value $Receipt
    Add-Ledger -Phase 'receipt' -Status 'ok' -Detail 'Machine-readable local receipt written.' -Evidence @{ path = $Script:ReceiptPath }
  } catch {
    Add-Warning "Could not persist local receipt: $($_.Exception.Message)"
  }
  $Receipt | ConvertTo-Json -Depth 30
}

function Banner {
  if ($NoBanner) { return }
  Write-Host ''
  Write-Host '============================================================'
  Write-Host ' HOME CENTER // COMPUTER HANDS // BOOTER v2'
  Write-Host '============================================================'
  Write-Host ' Mission: give Home Center governed hands on this Windows box.'
  Write-Host ' File authority: Drive sync. Still. Deliberately.'
  Write-Host ' Philosophy: evidence before swagger; rollback before regret.'
  Write-Host ' This script will narrate what it knows, what it infers, and'
  Write-Host ' what it refuses to claim merely because a process is alive.'
  Write-Host '============================================================'
  Write-Host ''
}

function Preflight {
  Add-Ledger -Phase 'preflight' -Status 'ok' -Detail "Mode=$Mode WorkerId=$WorkerId Origin=$Origin Branch=$Branch"
  Assert-True ($env:OS -eq 'Windows_NT') 'Computer Hands booter requires Windows.' 'preflight'
  Assert-True ($PSVersionTable.PSVersion.Major -ge 5) 'PowerShell 5 or newer is required.' 'preflight'
  Assert-True (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) 'LOCALAPPDATA is unavailable.' 'preflight'
  Assert-True ([Uri]::IsWellFormedUriString($Origin, [UriKind]::Absolute)) 'Origin must be an absolute HTTPS URL.' 'preflight'
  Assert-True ($Origin.StartsWith('https://', [StringComparison]::OrdinalIgnoreCase)) 'Origin must use HTTPS.' 'preflight'
  Assert-True ($WorkerId -match '^[A-Za-z0-9_.:-]{6,160}$') 'WorkerId contains unsupported characters or is too short.' 'preflight'
  Add-Ledger -Phase 'preflight' -Status 'ok' -Detail 'Windows, PowerShell, identity, path, HTTPS origin, and worker ID checks passed.'
}

Banner

$transcriptStarted = $false
try {
  New-Item -ItemType Directory -Path $Script:InstallDir -Force | Out-Null
  try {
    Start-Transcript -LiteralPath $Script:TranscriptPath -Append | Out-Null
    $transcriptStarted = $true
  } catch {
    Add-Warning "Transcript could not start: $($_.Exception.Message)"
  }

  Preflight

  if ($Mode -eq 'Uninstall') {
    Backup-ExistingState
    Remove-Hands
    $receipt = Build-Receipt -Status 'uninstalled'
    Write-Receipt -Receipt $receipt
    exit 0
  }

  if (-not $SkipCloudHealth) {
    try { [void](Cloud-Health) }
    catch {
      Add-Ledger -Phase 'cloud-health' -Status 'fail' -Detail "Production Computer Hands is not proven healthy: $($_.Exception.Message)"
      if ($Mode -eq 'Diagnose') {
        Add-Warning 'Diagnose mode continues so local state can still be inspected.'
      } else {
        throw 'Cloud preflight failed. Refusing to install a local worker against an unproven Computer Hands deployment.'
      }
    }
  } else {
    Add-Warning 'Cloud health was explicitly skipped. This weakens evidence and does not prove deployed Computer Hands.'
  }

  $local = Local-Diagnostics

  if ($Mode -eq 'Diagnose') {
    $receipt = Build-Receipt -Status 'diagnosed'
    Write-Receipt -Receipt $receipt
    exit 0
  }

  Backup-ExistingState
  $registration = Exchange-Bootstrap
  Download-Worker -TargetBranch $Branch
  Write-WorkerConfig -Registration $registration
  Install-ScheduledTask
  Start-WorkerTask
  [void](Probe-WorkerStartup -Seconds $StartupProbeSeconds)
  [void](Local-Diagnostics)

  if (-not $KeepBackups -and (Test-Path -LiteralPath $Script:CurrentBackup)) {
    Remove-Item -LiteralPath $Script:CurrentBackup -Recurse -Force -ErrorAction SilentlyContinue
    Add-Ledger -Phase 'backup-cleanup' -Status 'ok' -Detail 'Per-run rollback backup removed after successful local installation.'
  }

  Add-Ledger -Phase 'completion' -Status 'ok' -Detail 'Local bootstrap completed. End-to-end hands remain intentionally unclaimed until Home Center receives a real worker receipt.'
  $receipt = Build-Receipt -Status 'local_bootstrap_complete'
  Write-Receipt -Receipt $receipt
  exit 0
}
catch {
  $failure = $_.Exception.Message
  Add-Ledger -Phase 'fatal' -Status 'fail' -Detail $failure
  if ($Mode -in @('Install','Repair')) {
    Restore-BackupBestEffort
  }
  $receipt = Build-Receipt -Status 'failed' -Failure $failure
  try { Write-Receipt -Receipt $receipt } catch { $receipt | ConvertTo-Json -Depth 30 }
  exit 1
}
finally {
  if ($transcriptStarted) {
    try { Stop-Transcript | Out-Null } catch { }
  }
}
