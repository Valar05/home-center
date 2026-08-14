#Requires -Version 5.1
<#
Fortress Online — THECAULDRON continuous creation megabootstrap.

One idempotent entrypoint. It installs/repairs Computer Hands and Browser Nerve,
vendors a dedicated visible Chromium Throne, installs a loopback-only durable
command spool, keeps the machine awake without forcing the display on, and
seeds the first bounded Pro-reasoning creation wave.

This script does not scrape cookies, rotate accounts, use API-token compute,
run a hidden headless farm, or grant remote arbitrary shell authority to Atom.
The phone may submit only validated Chromium Throne command packets.
#>
[CmdletBinding()]
param(
  [ValidateSet('Ensure','Repair','Status','Stop')]
  [string]$Mode = 'Ensure',
  [string]$RepoPath = '',
  [string]$Ref = 'main',
  [string]$ComputerHandsBootstrapCode = '',
  [switch]$NoLaunch,
  [switch]$SkipOpenSsh
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$env:GIT_LFS_SKIP_SMUDGE = '1'

$Version = '2026.08.13.1'
$Repository = 'Valar05/home-center'
$Owner = 'Drew Clarke'
$WorkerUser = "$env:USERDOMAIN\$env:USERNAME"
$Local = [Environment]::GetFolderPath('LocalApplicationData')
$FortressRoot = Join-Path $Local 'HomeCenter\Fortress'
$RuntimeRoot = Join-Path $FortressRoot 'runtime'
$StateRoot = Join-Path $FortressRoot 'state'
$SpoolRoot = Join-Path $FortressRoot 'spool'
$PendingRoot = Join-Path $SpoolRoot 'pending'
$CompletedRoot = Join-Path $SpoolRoot 'completed'
$FailedRoot = Join-Path $SpoolRoot 'failed'
$LogPath = Join-Path $StateRoot 'fortress-desktop.log'
$LatestReceipt = Join-Path $StateRoot 'latest.json'
$HistoryPath = Join-Path $StateRoot 'history.jsonl'
$ThroneRoot = Join-Path $Local 'HomeCenter\ChromiumThrone'
$ExtensionDir = Join-Path $ThroneRoot 'extension'
$ThroneProfile = Join-Path $ThroneRoot 'profile'
$RelayCapabilityPath = Join-Path $ThroneRoot 'relay-capability.txt'
$RuntimeConfigPath = Join-Path $ThroneRoot 'runtime-config.json'
$RelayEventLog = Join-Path $ThroneRoot 'relay-events.jsonl'
$ThroneClient = Join-Path $ThroneRoot 'throne-client.mjs'
$RelayRunner = Join-Path $ThroneRoot 'throne-relay-runner.mjs'
$ThroneCommandScript = Join-Path $FortressRoot 'fortress-throne.ps1'
$SupervisorScript = Join-Path $FortressRoot 'fortress-supervisor.ps1'
$StatusScript = Join-Path $FortressRoot 'fortress-status.ps1'
$UserThroneWrapper = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'fortress-throne.cmd'
$TaskRelay = 'HomeCenterChromiumThroneRelay'
$TaskSupervisor = 'HomeCenterFortressContinuousCreation'
$TaskHands = 'HomeCenterComputerHands'
$TaskBrowser = 'HomeCenterBrowserNerve'
$ExtensionId = 'lccnchjcenaomhnjjaomabpajagenkaf'
$RelayBase = 'http://127.0.0.1:9234/v1/throne'
$Mutex = $null
$Scars = New-Object System.Collections.Generic.List[string]

New-Item -ItemType Directory -Force -Path `
  $FortressRoot,$StateRoot,$SpoolRoot,$PendingRoot,$CompletedRoot,$FailedRoot,$ThroneRoot,$ExtensionDir,$ThroneProfile | Out-Null

function Write-Log {
  param([string]$Message)
  $line = '{0} {1}' -f (Get-Date).ToString('o'), $Message
  Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
  Write-Host $line
}

function Write-Receipt {
  param(
    [string]$Phase,
    [string]$Status,
    [string]$Detail,
    [hashtable]$Extra = @{}
  )
  $obj = [ordered]@{
    schema = 'fortress.desktop.megabootstrap.receipt.v1'
    version = $Version
    owner = $Owner
    phase = $Phase
    status = $Status
    detail = $Detail
    at = (Get-Date).ToUniversalTime().ToString('o')
    machine = $env:COMPUTERNAME
    user = $WorkerUser
  }
  foreach ($key in $Extra.Keys) { $obj[$key] = $Extra[$key] }
  $json = $obj | ConvertTo-Json -Depth 12
  $tmp = "$LatestReceipt.tmp"
  [IO.File]::WriteAllText($tmp, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
  Move-Item -LiteralPath $tmp -Destination $LatestReceipt -Force
  Add-Content -LiteralPath $HistoryPath -Value (($obj | ConvertTo-Json -Compress -Depth 12)) -Encoding UTF8
  return $obj
}

function Add-Scar {
  param([string]$Scar)
  if (-not [string]::IsNullOrWhiteSpace($Scar)) {
    $Scars.Add($Scar)
    Write-Log "SCAR $Scar"
  }
}

function Enter-Lock {
  $script:Mutex = New-Object Threading.Mutex($false, 'Local\HomeCenterFortressMegabootstrap')
  if (-not $script:Mutex.WaitOne(0)) {
    if (Test-Path -LiteralPath $LatestReceipt) { Get-Content -LiteralPath $LatestReceipt -Raw }
    else { '{"status":"already_running"}' }
    exit 0
  }
}

function Exit-Lock {
  if ($script:Mutex) {
    try { $script:Mutex.ReleaseMutex() | Out-Null } catch {}
    $script:Mutex.Dispose()
  }
}

function Invoke-External {
  param(
    [Parameter(Mandatory=$true)][string]$File,
    [string[]]$Arguments = @(),
    [string]$WorkingDirectory = ''
  )
  Write-Log ("EXEC {0} {1}" -f $File, ($Arguments -join ' '))
  if ($WorkingDirectory) { Push-Location $WorkingDirectory }
  try {
    $output = & $File @Arguments 2>&1 | Out-String
    $code = $LASTEXITCODE
  } finally {
    if ($WorkingDirectory) { Pop-Location }
  }
  if ($code -ne 0) { throw "Command failed ($code): $File $($Arguments -join ' ')`n$output" }
  return $output.Trim()
}

function Resolve-Repository {
  if ($RepoPath -and (Test-Path -LiteralPath (Join-Path $RepoPath '.git'))) {
    return [IO.Path]::GetFullPath($RepoPath)
  }

  $scriptParent = Split-Path -Parent $PSCommandPath
  $scriptCandidate = Split-Path -Parent $scriptParent
  $candidates = @(
    $scriptCandidate,
    (Join-Path ([Environment]::GetFolderPath('UserProfile')) 'home-center'),
    (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'GitHub\home-center'),
    (Join-Path ([Environment]::GetFolderPath('UserProfile')) 'source\repos\home-center'),
    (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'GodotProjects\home-center')
  ) | Select-Object -Unique

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath (Join-Path $candidate '.git'))) {
      return [IO.Path]::GetFullPath($candidate)
    }
  }

  $gh = Get-Command gh.exe -ErrorAction SilentlyContinue
  if (-not $gh) { $gh = Get-Command gh -ErrorAction SilentlyContinue }
  if ($gh) {
    $clone = Join-Path $FortressRoot 'source'
    if (-not (Test-Path -LiteralPath (Join-Path $clone '.git'))) {
      Invoke-External -File $gh.Source -Arguments @('repo','clone',$Repository,$clone)
    }
    if (Test-Path -LiteralPath (Join-Path $clone '.git')) { return $clone }
  }

  throw 'Authenticated home-center clone was not found. Pass -RepoPath or authenticate gh once.'
}

function Sync-IsolatedRuntime {
  param([string]$SourceRepo)
  $git = (Get-Command git.exe -ErrorAction Stop).Source
  Invoke-External -File $git -Arguments @('-C',$SourceRepo,'fetch','origin',$Ref) | Out-Null

  $runtimeGit = Join-Path $RuntimeRoot '.git'
  if (Test-Path -LiteralPath $runtimeGit) {
    Invoke-External -File $git -Arguments @('-C',$RuntimeRoot,'reset','--hard',"origin/$Ref") | Out-Null
    Invoke-External -File $git -Arguments @('-C',$RuntimeRoot,'clean','-fd') | Out-Null
  } else {
    if (Test-Path -LiteralPath $RuntimeRoot) {
      Remove-Item -LiteralPath $RuntimeRoot -Recurse -Force
    }
    Invoke-External -File $git -Arguments @('-C',$SourceRepo,'worktree','prune') | Out-Null
    Invoke-External -File $git -Arguments @('-C',$SourceRepo,'worktree','add','--detach',$RuntimeRoot,"origin/$Ref") | Out-Null
  }
  return (Invoke-External -File $git -Arguments @('-C',$RuntimeRoot,'rev-parse','HEAD')).Trim()
}

function Test-IsAdministrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-OpenSsh {
  if ($SkipOpenSsh) { return @{state='skipped'; callable=$false} }
  $service = Get-Service -Name sshd -ErrorAction SilentlyContinue
  if (-not $service -and (Test-IsAdministrator)) {
    Write-Log 'Installing Windows OpenSSH Server capability'
    $capability = Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0'
    if ($capability.State -notin @('Installed','InstallPending')) {
      Add-Scar "openssh_install_state=$($capability.State)"
    }
    $service = Get-Service -Name sshd -ErrorAction SilentlyContinue
  }
  if (-not $service) {
    Add-Scar 'openssh_server_missing_requires_one_elevated_run'
    return @{state='missing'; callable=$false}
  }

  try {
    Set-Service -Name sshd -StartupType Automatic
    if ((Get-Service -Name sshd).Status -ne 'Running') { Start-Service -Name sshd }
  } catch {
    Add-Scar ('openssh_service_repair_failed:' + $_.Exception.Message)
  }

  if (Test-IsAdministrator) {
    try {
      $defaultRule = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
      if ($defaultRule) { Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' | Out-Null }
      if (-not (Get-NetFirewallRule -Name 'HomeCenter-SSHD-In-TCP' -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name 'HomeCenter-SSHD-In-TCP' -DisplayName 'Home Center SSH (LAN + Tailscale only)' `
          -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 `
          -Profile Private -RemoteAddress @('LocalSubnet','100.64.0.0/10') | Out-Null
      } else {
        Set-NetFirewallRule -Name 'HomeCenter-SSHD-In-TCP' -Enabled True -Profile Private -Action Allow | Out-Null
        Set-NetFirewallAddressFilter -AssociatedNetFirewallRule (Get-NetFirewallRule -Name 'HomeCenter-SSHD-In-TCP') `
          -RemoteAddress @('LocalSubnet','100.64.0.0/10') | Out-Null
      }
    } catch {
      Add-Scar ('openssh_firewall_lock_failed:' + $_.Exception.Message)
    }
  }

  $fresh = Get-Service -Name sshd
  return @{state=[string]$fresh.Status; callable=($fresh.Status -eq 'Running')}
}

function Ensure-ComputerHands {
  param([string]$SourceRepo)
  $root = Join-Path $Local 'HomeCenter\ComputerHands'
  $config = Join-Path $root 'config.json'
  $token = Join-Path $root 'worker-token.dpapi'
  $repair = Join-Path $RuntimeRoot 'computer-hands\windows\repair.ps1'
  $install = Join-Path $RuntimeRoot 'computer-hands\windows\install.ps1'
  if ((Test-Path -LiteralPath $config) -and (Test-Path -LiteralPath $token)) {
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $repair -RepoPath $SourceRepo | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Computer Hands repair failed: $LASTEXITCODE" }
    return 'repaired_existing_identity'
  }
  if ([string]::IsNullOrWhiteSpace($ComputerHandsBootstrapCode)) {
    throw 'Computer Hands is not registered. Supply -ComputerHandsBootstrapCode for this one operator-only pairing.'
  }
  & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $install -BootstrapCode $ComputerHandsBootstrapCode -Ref $Ref | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "Computer Hands install failed: $LASTEXITCODE" }
  return 'installed_new_identity'
}

function Ensure-BrowserNerve {
  $root = Join-Path $Local 'HomeCenter\BrowserNerve'
  $token = Join-Path $root 'worker-token.dpapi'
  $hadToken = Test-Path -LiteralPath $token
  $installer = Join-Path $RuntimeRoot 'browser-nerve\windows\install.ps1'
  $source = Join-Path $RuntimeRoot 'browser-nerve\windows'
  $args = @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$installer,'-SourceDirectory',$source,'-Ref',$Ref)
  if (-not $hadToken) { $args += '-PairWithComputerHands' }
  & powershell.exe @args | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "Browser Nerve install/repair failed: $LASTEXITCODE" }
  return $(if ($hadToken) { 'online_identity_preserved' } else { 'paired_to_computer_hands' })
}

function New-RelayCapability {
  if (Test-Path -LiteralPath $RelayCapabilityPath) {
    $existing = (Get-Content -LiteralPath $RelayCapabilityPath -Raw).Trim()
    if ($existing.Length -ge 32) { return $existing }
  }
  $bytes = New-Object byte[] 48
  $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  $capability = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
  [IO.File]::WriteAllText($RelayCapabilityPath, $capability + [Environment]::NewLine, [Text.Encoding]::ASCII)
  return $capability
}

function Resolve-BrowserExe {
  $receipt = Join-Path $ThroneRoot 'install-receipt.json'
  if (Test-Path -LiteralPath $receipt) {
    try {
      $value = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
      if ($value.browserExe -and (Test-Path -LiteralPath ([string]$value.browserExe))) {
        return [string]$value.browserExe
      }
    } catch {}
  }
  $found = Get-ChildItem -LiteralPath (Join-Path $ThroneRoot 'chrome-for-testing') -Filter chrome.exe -Recurse -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($found) { return $found.FullName }
  return ''
}

function Ensure-ChromiumThrone {
  $installer = Join-Path $RuntimeRoot 'tools\install_chromium_throne.ps1'
  $browserExe = Resolve-BrowserExe
  if (-not $browserExe) {
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $installer -Root $ThroneRoot | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Chromium Throne base installer failed: $LASTEXITCODE" }
    $browserExe = Resolve-BrowserExe
  }
  if (-not $browserExe) { throw 'Chrome for Testing executable is still missing.' }

  $sourceExtension = Join-Path $RuntimeRoot 'browser-porch\extension'
  if (-not (Test-Path -LiteralPath (Join-Path $sourceExtension 'manifest.json'))) {
    throw "Current Chromium Throne extension source is missing: $sourceExtension"
  }
  New-Item -ItemType Directory -Force -Path $ExtensionDir | Out-Null
  Copy-Item -Path (Join-Path $sourceExtension '*') -Destination $ExtensionDir -Recurse -Force

  $manifest = Get-Content -LiteralPath (Join-Path $ExtensionDir 'manifest.json') -Raw | ConvertFrom-Json
  if ($manifest.name -ne 'Chromium Throne' -or [int]$manifest.manifest_version -ne 3) {
    throw 'Installed extension manifest is not Chromium Throne MV3.'
  }
  if (-not ($manifest.permissions -contains 'tabs') -or -not ($manifest.permissions -contains 'alarms')) {
    throw 'Installed extension lacks tabs/alarms authority required for bounded visible workers.'
  }

  $node = (Get-Command node.exe -ErrorAction SilentlyContinue)
  if (-not $node) { $node = Get-Command node -ErrorAction Stop }
  Push-Location $ExtensionDir
  try {
    & $node.Source --test throne_context.test.mjs swarm-core.test.mjs | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Chromium Throne contract tests failed: $LASTEXITCODE" }
  } finally { Pop-Location }

  foreach ($name in @('relay.mjs','contract.mjs','throne-relay-runner.mjs','throne-client.mjs')) {
    $source = Join-Path (Join-Path $RuntimeRoot 'browser-porch') $name
    if (-not (Test-Path -LiteralPath $source)) { throw "Chromium Throne relay source missing: $name" }
    Copy-Item -LiteralPath $source -Destination (Join-Path $ThroneRoot $name) -Force
  }

  $capability = New-RelayCapability
  $escapedCapability = $capability.Replace("'","")
  $relayConfig = @"
export const THRONE_RELAY = Object.freeze({
  enabled: true,
  baseUrl: '$RelayBase',
  capability: '$escapedCapability',
  pollSeconds: 5,
});
"@
  [IO.File]::WriteAllText((Join-Path $ExtensionDir 'relay-config.mjs'), $relayConfig, [Text.UTF8Encoding]::new($false))

  $launcher = Join-Path $ThroneRoot 'launch-chromium-throne.cmd'
  $launcherText = @"
@echo off
start "Chromium Throne" "$browserExe" --user-data-dir="$ThroneProfile" --load-extension="$ExtensionDir" --no-first-run --no-default-browser-check "chrome-extension://$ExtensionId/wake.html"
"@
  Set-Content -LiteralPath $launcher -Value $launcherText -Encoding ASCII

  $runtime = [ordered]@{
    schema = 'fortress.chromium-throne.runtime.v1'
    root = $ThroneRoot
    relayBase = $RelayBase
    relayPort = 9234
    browserExe = $browserExe
    profileDir = $ThroneProfile
    extensionDir = $ExtensionDir
    extensionId = $ExtensionId
    workerModelDefault = 'ChatGPT Pro reasoning'
    instantDefault = $false
    visibleWorkers = $true
    maxParallelWorkers = 8
    installedRevision = (Invoke-External -File (Get-Command git.exe).Source -Arguments @('-C',$RuntimeRoot,'rev-parse','HEAD')).Trim()
  }
  [IO.File]::WriteAllText($RuntimeConfigPath, (($runtime | ConvertTo-Json -Depth 8) + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
  return $runtime
}

function Install-ThroneCommandWrapper {
  $scriptText = @'
[CmdletBinding()]
param(
  [string]$CommandB64 = '',
  [string]$CommandFile = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Local = [Environment]::GetFolderPath('LocalApplicationData')
$FortressRoot = Join-Path $Local 'HomeCenter\Fortress'
$ThroneRoot = Join-Path $Local 'HomeCenter\ChromiumThrone'
$PendingRoot = Join-Path $FortressRoot 'spool\pending'
$CompletedRoot = Join-Path $FortressRoot 'spool\completed'
$Client = Join-Path $ThroneRoot 'throne-client.mjs'
$Node = (Get-Command node.exe -ErrorAction SilentlyContinue)
if (-not $Node) { $Node = Get-Command node -ErrorAction Stop }
New-Item -ItemType Directory -Force -Path $PendingRoot,$CompletedRoot | Out-Null

function Decode-B64Url([string]$Value) {
  $value = $Value.Replace('-','+').Replace('_','/')
  switch ($value.Length % 4) {
    0 {}
    2 { $value += '==' }
    3 { $value += '=' }
    default { throw 'Invalid base64url command packet.' }
  }
  return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($value))
}
function Encode-B64Url([string]$Value) {
  return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Value)).TrimEnd('=').Replace('+','-').Replace('/','_')
}
if ($CommandFile) {
  $raw = Get-Content -LiteralPath $CommandFile -Raw
  $CommandB64 = Encode-B64Url $raw
} elseif ($CommandB64) {
  $raw = Decode-B64Url $CommandB64
} else {
  throw 'CommandB64 or CommandFile is required.'
}
$command = $raw | ConvertFrom-Json
$commandId = [string]$command.commandId
$action = [string]$command.action
if ($commandId -notmatch '^[A-Za-z0-9_.:-]{6,180}$') { throw 'Invalid commandId.' }
if ($action -notin @('swarm.enqueue','swarm.stop','swarm.resume','swarm.status')) { throw 'Unsupported throne action.' }
$jobs = @($command.jobs)
if ($action -eq 'swarm.enqueue') {
  if ($jobs.Count -lt 1 -or $jobs.Count -gt 12) { throw 'swarm.enqueue requires 1-12 jobs.' }
  foreach ($job in $jobs) {
    if ([string]::IsNullOrWhiteSpace([string]$job.commission) -or ([string]$job.commission).Length -gt 32000) {
      throw 'Invalid job commission.'
    }
  }
}
$path = Join-Path $PendingRoot ($commandId + '.json')
$completed = Join-Path $CompletedRoot ($commandId + '.json')
if (Test-Path -LiteralPath $completed) {
  @{ok=$true;commandId=$commandId;state='completed';idempotent=$true;path=$completed}|ConvertTo-Json -Compress
  exit 0
}
if (-not (Test-Path -LiteralPath $path)) {
  $tmp = "$path.tmp"
  [IO.File]::WriteAllText($tmp, ($command | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))
  Move-Item -LiteralPath $tmp -Destination $path -Force
}
$output = & $Node.Source $Client --root $ThroneRoot --command-b64 $CommandB64 2>&1 | Out-String
$code = $LASTEXITCODE
$parsed = $null
try { $parsed = ($output.Trim().Split([Environment]::NewLine)[-1] | ConvertFrom-Json) } catch {}
$receipt = [ordered]@{
  ok = ($code -eq 0)
  commandId = $commandId
  action = $action
  state = $(if ($code -eq 0) {'spooled_and_relay_accepted'} else {'spooled_relay_unavailable'})
  path = $path
  relay = $parsed
  detail = $(if ($code -eq 0) {''} else {$output.Trim()})
}
$receipt | ConvertTo-Json -Depth 10 -Compress
if ($code -ne 0) { exit $code }
'@
  [IO.File]::WriteAllText($ThroneCommandScript, $scriptText, [Text.UTF8Encoding]::new($false))

  $cmd = @"
@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\HomeCenter\Fortress\fortress-throne.ps1" -CommandB64 "%~1"
"@
  Set-Content -LiteralPath $UserThroneWrapper -Value $cmd -Encoding ASCII
}

function Install-Supervisor {
  $scriptText = @'
[CmdletBinding()]
param([switch]$Once)
$ErrorActionPreference = 'Continue'
Set-StrictMode -Version Latest
$Local = [Environment]::GetFolderPath('LocalApplicationData')
$Root = Join-Path $Local 'HomeCenter\Fortress'
$State = Join-Path $Root 'state'
$Pending = Join-Path $Root 'spool\pending'
$Completed = Join-Path $Root 'spool\completed'
$Failed = Join-Path $Root 'spool\failed'
$Throne = Join-Path $Local 'HomeCenter\ChromiumThrone'
$RuntimeConfig = Join-Path $Throne 'runtime-config.json'
$CapabilityPath = Join-Path $Throne 'relay-capability.txt'
$Latest = Join-Path $State 'supervisor.json'
$History = Join-Path $State 'supervisor.jsonl'
$RelayTask = 'HomeCenterChromiumThroneRelay'
$HandsTask = 'HomeCenterComputerHands'
$BrowserTask = 'HomeCenterBrowserNerve'
$CommandScript = Join-Path $Root 'fortress-throne.ps1'
New-Item -ItemType Directory -Force -Path $State,$Pending,$Completed,$Failed | Out-Null

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class FortressPower {
  [DllImport("kernel32.dll", SetLastError = true)]
  public static extern uint SetThreadExecutionState(uint esFlags);
}
"@ -ErrorAction SilentlyContinue
[FortressPower]::SetThreadExecutionState(0x80000001) | Out-Null

function Task-State([string]$Name) {
  try {
    $task = Get-ScheduledTask -TaskName $Name -ErrorAction Stop
    if ([string]$task.State -ne 'Running') { Start-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue }
    return [string](Get-ScheduledTask -TaskName $Name).State
  } catch { return 'missing' }
}
function Encode-B64Url([string]$Value) {
  return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Value)).TrimEnd('=').Replace('+','-').Replace('/','_')
}
function Relay-Status {
  try {
    $cap = (Get-Content -LiteralPath $CapabilityPath -Raw).Trim()
    return Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:9234/v1/throne/status' -Headers @{Authorization="Bearer $cap"} -TimeoutSec 4
  } catch { return $null }
}
function Ensure-Browser($config) {
  $needle = [string]$config.profileDir
  $running = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue |
    Where-Object { [string]$_.CommandLine -like "*$needle*" })
  if ($running.Count -eq 0) {
    $launcher = Join-Path $Throne 'launch-chromium-throne.cmd'
    if (Test-Path -LiteralPath $launcher) {
      Start-Process -FilePath $launcher
      Start-Sleep -Seconds 2
    }
  }
  return @((Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue |
    Where-Object { [string]$_.CommandLine -like "*$needle*" })).Count
}
function Replay-Spool($relay) {
  $commands = @{}
  if ($relay -and $relay.commands) {
    foreach ($row in @($relay.commands)) { $commands[[string]$row.commandId] = $row }
  }
  foreach ($file in Get-ChildItem -LiteralPath $Pending -Filter '*.json' -File -ErrorAction SilentlyContinue | Sort-Object CreationTime) {
    try {
      $raw = Get-Content -LiteralPath $file.FullName -Raw
      $cmd = $raw | ConvertFrom-Json
      $id = [string]$cmd.commandId
      $row = $commands[$id]
      if ($row -and [string]$row.state -in @('completed','failed','cancelled')) {
        $targetRoot = if ([string]$row.state -eq 'completed') { $Completed } else { $Failed }
        Move-Item -LiteralPath $file.FullName -Destination (Join-Path $targetRoot $file.Name) -Force
        continue
      }
      if (-not $row) {
        $encoded = Encode-B64Url $raw
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $CommandScript -CommandB64 $encoded | Out-Null
      }
    } catch {
      Add-Content -LiteralPath (Join-Path $State 'spool-errors.log') -Value ((Get-Date).ToString('o') + ' ' + $_.Exception.ToString()) -Encoding UTF8
    }
  }
}
function Write-State($config,$relay,$browserCount,$taskStates) {
  $obj = [ordered]@{
    schema = 'fortress.desktop.supervisor.v1'
    at = (Get-Date).ToUniversalTime().ToString('o')
    machine = $env:COMPUTERNAME
    workerModelDefault = 'ChatGPT Pro reasoning'
    instantDefault = $false
    continuousCreation = $true
    tasks = $taskStates
    relay = $relay
    visibleBrowserProcessCount = $browserCount
    pendingCommands = @(Get-ChildItem -LiteralPath $Pending -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
    completedCommands = @(Get-ChildItem -LiteralPath $Completed -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
    failedCommands = @(Get-ChildItem -LiteralPath $Failed -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
    runtime = $config
  }
  $tmp = "$Latest.tmp"
  [IO.File]::WriteAllText($tmp, (($obj | ConvertTo-Json -Depth 16) + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
  Move-Item -LiteralPath $tmp -Destination $Latest -Force
  Add-Content -LiteralPath $History -Value ($obj | ConvertTo-Json -Compress -Depth 16) -Encoding UTF8
}
do {
  $config = Get-Content -LiteralPath $RuntimeConfig -Raw | ConvertFrom-Json
  $taskStates = [ordered]@{
    computerHands = Task-State $HandsTask
    browserNerve = Task-State $BrowserTask
    throneRelay = Task-State $RelayTask
  }
  Start-Sleep -Milliseconds 500
  $relay = Relay-Status
  if (-not $relay) {
    Start-ScheduledTask -TaskName $RelayTask -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    $relay = Relay-Status
  }
  $browserCount = Ensure-Browser $config
  Replay-Spool $relay
  Write-State $config $relay $browserCount $taskStates
  if (-not $Once) { Start-Sleep -Seconds 15 }
} while (-not $Once)
'@
  [IO.File]::WriteAllText($SupervisorScript, $scriptText, [Text.UTF8Encoding]::new($false))

  $statusText = @'
$path = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'HomeCenter\Fortress\state\supervisor.json'
if (Test-Path -LiteralPath $path) { Get-Content -LiteralPath $path -Raw }
else { '{"schema":"fortress.desktop.supervisor.v1","status":"never_run"}' }
'@
  [IO.File]::WriteAllText($StatusScript, $statusText, [Text.UTF8Encoding]::new($false))
}

function Register-LongRunningTask {
  param(
    [string]$Name,
    [string]$Execute,
    [string]$Arguments,
    [string]$WorkingDirectory = ''
  )
  $actionArgs = @{Execute=$Execute;Argument=$Arguments}
  if ($WorkingDirectory) { $actionArgs.WorkingDirectory = $WorkingDirectory }
  $action = New-ScheduledTaskAction @actionArgs
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User $WorkerUser
  $principal = New-ScheduledTaskPrincipal -UserId $WorkerUser -LogonType Interactive -RunLevel Limited
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1)
  Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
  Start-ScheduledTask -TaskName $Name
}

function Register-FortressTasks {
  $node = (Get-Command node.exe -ErrorAction SilentlyContinue)
  if (-not $node) { $node = Get-Command node -ErrorAction Stop }
  $relayArgs = "`"$RelayRunner`""
  Register-LongRunningTask -Name $TaskRelay -Execute $node.Source -Arguments $relayArgs -WorkingDirectory $ThroneRoot

  $supervisorArgs = "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$SupervisorScript`""
  Register-LongRunningTask -Name $TaskSupervisor -Execute (Get-Command powershell.exe).Source -Arguments $supervisorArgs -WorkingDirectory $FortressRoot
  Start-Sleep -Seconds 2
}

function Lock-LocalRuntime {
  try {
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true, $false)
    $inherit = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
    $prop = [Security.AccessControl.PropagationFlags]::None
    $allow = [Security.AccessControl.AccessControlType]::Allow
    foreach ($identity in @($WorkerUser,'NT AUTHORITY\SYSTEM','BUILTIN\Administrators')) {
      $rule = New-Object Security.AccessControl.FileSystemAccessRule($identity,'FullControl',$inherit,$prop,$allow)
      $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $FortressRoot -AclObject $acl
    Set-Acl -LiteralPath $ThroneRoot -AclObject $acl
    return 'current_user_system_administrators_only'
  } catch {
    Add-Scar ('acl_lock_failed:' + $_.Exception.Message)
    return 'lock_failed'
  }
}

function New-GenesisCommand {
  $common = @'
PORTCULLIS LOCKED.
Use ChatGPT Pro reasoning, never Instant by default. Work in one bounded slice. Research authoritative connected state before mutation. Apply the relevant Judgment Jars and a separate Venice plan review. Persist code/docs/receipts through Home Center or GitHub; local ChatGPT scratch is not completion proof. Create an isolated branch/PR for repository writes; do not write directly to main. Distinguish requested, intended, implemented, tested, deployed, callable, delivered, and accepted states. Every model-assisted step must leave behind tests, a deterministic recipe, structured state, or tooling that reduces future inference. CONTINUE_REQUIRED forbids stopping; return a strict six-field handoff when more remains.
'@
  $jobs = @(
    [ordered]@{
      jobId='genesis-desire-ledger'
      commission=$common + @'

CURRENT SLICE — AUTHORITATIVE DESIRE ARCHAEOLOGY
Mine only authorized durable sources available through Home Center, GitHub, Drive, Atom/Vlad receipts, owner-authorized intake, and visible ChatGPT history. Build or repair a canonical desire ledger that preserves Drew's exact outcomes, ownership, tool/lane, exclusions, evidence standard, delivery surface, priority, dependencies, and truth state. Reconcile duplicates without erasing nuance. Make the ledger executable: each open desire must have the smallest useful next slice and acceptance evidence. Deliver the ledger durably and seed the next non-conflicting jobs. Do not merely write a wishlist.
'@
      context='Genesis lane: inventory and prioritization. Avoid changing product code except the durable ledger/intake mechanism itself.'
    },
    [ordered]@{
      jobId='genesis-overlay-command-surface'
      commission=$common + @'

CURRENT SLICE — PHONE COMMAND SURFACE
Inspect the actual primary-phone overlay, Atom, Home Center, and current receipts. Make the overlay a tiny draggable/collapsible pinprick when inactive and a complete usable command surface when active. The Home Center status and restart control is a priority; every visible button must either work end-to-end or be removed/disabled with an honest state. Preserve touch-through when inactive. Produce primary-phone receipts, not desktop or repository substitutes.
'@
      context='Independent phone/overlay branch. Coordinate with existing overlay work; do not rewrite working architecture.'
    },
    [ordered]@{
      jobId='genesis-throne-acceptance'
      commission=$common + @'

CURRENT SLICE — CHROMIUM THRONE ACCEPTANCE
Exercise this installed Chromium Throne on THECAULDRON as the visible ChatGPT Pro worker organ. Verify bounded parallel tabs, per-worker identity, prompt submission, checkpoint capture, choke rotation, relay recovery, and receipts. Fix the smallest real defect that prevents unattended continuation. The desktop and phone must agree on command/job/receipt state. Do not self-certify from source inspection.
'@
      context='Independent orchestration acceptance branch. This worker is allowed to improve its own durable control loop.'
    },
    [ordered]@{
      jobId='genesis-armory-ledger'
      commission=$common + @'

CURRENT SLICE — ARMORY LEDGER
Reorient with the existing Armory Ledger/Inventory implementation and actual Home Center surface. Make food/snack synthesis, supplements, medication-adjacent context, vape supplies/tank preservation, inventory counts, hunger signals, and receipts one durable accessible ledger instead of scattered chat memories. Preserve uncertainty and do not invent quantities. Deliver one immediately usable phone slice with end-to-end evidence.
'@
      context='Independent Armory branch. Health interpretation is out of scope; this is durable user-authored inventory/intake recording.'
    },
    [ordered]@{
      jobId='genesis-intake-continuity'
      commission=$common + @'

CURRENT SLICE — HUMAN INTAKE CONTINUITY
Audit Eve/June/Caroline intake and unanswered-question handling. Build the deterministic unread/unanswered/undelivered/acknowledged state machine the user commissioned, exposed in Atom/overlay with persistent notification and optional PocketTTS readback. Spoken output never counts as read without explicit acknowledgement. Fix one highest-severity live gap and preserve relationship context without hallucinating messages.
'@
      context='Independent intake branch. Use authoritative Gmail/Home Center/Drive sources only.'
    },
    [ordered]@{
      jobId='genesis-pockettts-minimal'
      commission=$common + @'

CURRENT SLICE — OWN THE VOICE
Determine whether PocketTTS is already forked under Drew's authority. If not, establish the proper fork/repository lane. Isolate one approved voice and reduce inference/runtime dependencies to the bare minimum practical local path. Parallelize rendering only where measured. Produce a callable local utility with a deterministic test phrase and resource receipt; do not burn paid speech credits.
'@
      context='Independent voice branch. Preserve upstream licensing and provenance.'
    },
    [ordered]@{
      jobId='genesis-inference-decay'
      commission=$common + @'

CURRENT SLICE — NATURAL SELECTION OF WORKERS
Instrument one complete Fortress workflow and identify every inference call. Replace the highest-frequency knowable decision with deterministic code/config/tests. Preserve a fallback ladder: deterministic recipe, bounded local inference, ChatGPT Pro only for genuinely unresolved creation. Record before/after token dependence and promote the learned recipe only after regression evidence.
'@
      context='Independent infrastructure branch. No aspirational claims; measure the real path.'
    },
    [ordered]@{
      jobId='genesis-accessibility'
      commission=$common + @'

CURRENT SLICE — ACCESSIBILITY IS FIRST CLASS
Audit the current Atom/overlay/receipt flow for screen-reader, low-vision, motor, and no-visual-confirmation use, prioritizing Drew's blind spouse's practical use. Fix one high-impact barrier in a bounded branch and add an acceptance test or deterministic checklist. Do not treat speech alone as delivery, and do not bury status in color or unlabeled controls.
'@
      context='Independent accessibility branch; coordinate with overlay work by touching a separate component or test surface.'
    }
  )
  return [ordered]@{
    commandId = 'fortress-continuous-creation-genesis-v1'
    action = 'swarm.enqueue'
    jobs = $jobs
  }
}

function Encode-B64Url([string]$Value) {
  return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Value)).TrimEnd('=').Replace('+','-').Replace('/','_')
}

function Seed-Genesis {
  $command = New-GenesisCommand
  $raw = $command | ConvertTo-Json -Depth 20
  $encoded = Encode-B64Url $raw
  & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $ThroneCommandScript -CommandB64 $encoded | Out-Host
  if ($LASTEXITCODE -ne 0) {
    Add-Scar "genesis_spooled_but_relay_unavailable_exit=$LASTEXITCODE"
  }
}

function Get-TaskState([string]$Name) {
  try { return [string](Get-ScheduledTask -TaskName $Name -ErrorAction Stop).State }
  catch { return 'missing' }
}

function Show-Status {
  $supervisor = Join-Path $StateRoot 'supervisor.json'
  $result = [ordered]@{
    schema = 'fortress.desktop.status.v1'
    latestBootstrap = $(if (Test-Path -LiteralPath $LatestReceipt) { Get-Content -LiteralPath $LatestReceipt -Raw | ConvertFrom-Json } else { $null })
    supervisor = $(if (Test-Path -LiteralPath $supervisor) { Get-Content -LiteralPath $supervisor -Raw | ConvertFrom-Json } else { $null })
    tasks = [ordered]@{
      computerHands = Get-TaskState $TaskHands
      browserNerve = Get-TaskState $TaskBrowser
      throneRelay = Get-TaskState $TaskRelay
      continuousCreation = Get-TaskState $TaskSupervisor
    }
    pending = @(Get-ChildItem -LiteralPath $PendingRoot -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
    completed = @(Get-ChildItem -LiteralPath $CompletedRoot -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
    failed = @(Get-ChildItem -LiteralPath $FailedRoot -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
    wrapper = $UserThroneWrapper
  }
  $result | ConvertTo-Json -Depth 18
}

function Stop-Explicit {
  foreach ($task in @($TaskSupervisor,$TaskRelay)) {
    Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
  }
  Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue |
    Where-Object { [string]$_.CommandLine -like "*$ThroneProfile*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Write-Receipt -Phase 'continuous-creation' -Status 'stopped' -Detail 'Stopped by explicit operator command.' | ConvertTo-Json -Depth 8
}

function Ensure-All {
  Enter-Lock
  try {
    Write-Receipt -Phase 'bootstrap' -Status 'running' -Detail 'Beginning THECAULDRON continuous creation bootstrap.' | Out-Null
    if ($env:OS -ne 'Windows_NT') { throw 'Desktop megabootstrap requires Windows.' }
    if (-not [Environment]::UserInteractive) { throw 'Run once from the normal signed-in Windows account.' }

    $source = Resolve-Repository
    Write-Log "Using repository $source"
    $revision = Sync-IsolatedRuntime -SourceRepo $source
    Write-Log "Isolated runtime revision $revision"

    $hands = Ensure-ComputerHands -SourceRepo $source
    $browserNerve = Ensure-BrowserNerve
    $throne = Ensure-ChromiumThrone
    Install-ThroneCommandWrapper
    Install-Supervisor
    $ssh = Ensure-OpenSsh
    $lockState = Lock-LocalRuntime
    Register-FortressTasks

    if (-not $NoLaunch) {
      Start-Process -FilePath (Join-Path $ThroneRoot 'launch-chromium-throne.cmd')
    }
    Seed-Genesis

    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $SupervisorScript -Once | Out-Null
    $receipt = Write-Receipt -Phase 'bootstrap' -Status 'healthy' `
      -Detail 'Desktop body, loopback relay, visible Pro worker pool, durable spool, and continuous campaign are installed.' `
      -Extra @{
        repository=$source
        runtimeRevision=$revision
        computerHands=$hands
        browserNerve=$browserNerve
        chromiumThrone=$throne
        ssh=$ssh
        acl=$lockState
        scars=@($Scars)
        genesisCommand='fortress-continuous-creation-genesis-v1'
        workerModelDefault='ChatGPT Pro reasoning'
        instantDefault=$false
        maxParallelWorkers=8
        phoneSubmissionSurface=$UserThroneWrapper
      }
    $receipt | ConvertTo-Json -Depth 18
    Show-Status
  } catch {
    $failure = $_.Exception.ToString()
    Write-Receipt -Phase 'bootstrap' -Status 'blocked' -Detail $failure -Extra @{scars=@($Scars)} | ConvertTo-Json -Depth 12
    throw
  } finally {
    Exit-Lock
  }
}

switch ($Mode) {
  'Ensure' { Ensure-All }
  'Repair' { Ensure-All }
  'Status' { Show-Status }
  'Stop' { Stop-Explicit }
}
