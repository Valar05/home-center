param(
  [Parameter(Mandatory=$true)]
  [string]$BootstrapCodeBase64
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($env:OS -ne 'Windows_NT') { throw 'This repair is for Windows.' }
if (-not [Environment]::UserInteractive) { throw 'Run from the normal interactive Windows account.' }

$Root = Join-Path $env:LOCALAPPDATA 'HomeCenter\ComputerHands'
$ConfigPath = Join-Path $Root 'config.json'
$TokenPath = Join-Path $Root 'worker-token.dpapi'
$LogPath = Join-Path $Root 'worker.log'
$TaskName = 'HomeCenterComputerHands'

if (-not (Test-Path -LiteralPath $ConfigPath)) { throw "Computer Hands config missing: $ConfigPath" }
$cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$origin = ([string]$cfg.origin).TrimEnd('/')
$workerId = [string]$cfg.workerId
if (-not $origin -or -not $workerId) { throw 'Computer Hands config is incomplete.' }

$bootstrapCode = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($BootstrapCodeBase64))
$registration = Invoke-RestMethod -Method Post -Uri ($origin + '/computer-hands/v1/bootstrap') -ContentType 'application/json' -Body (@{ bootstrapCode = $bootstrapCode; workerId = $workerId } | ConvertTo-Json -Compress) -TimeoutSec 30
if (-not $registration.token) { throw 'Computer Hands bootstrap did not return a worker token.' }

$secure = ConvertTo-SecureString ([string]$registration.token) -AsPlainText -Force
$protected = $secure | ConvertFrom-SecureString
Set-Content -LiteralPath $TokenPath -Value $protected -Encoding ASCII

# Prove the DPAPI payload can be decoded by this same interactive user before restarting.
$roundTrip = Get-Content -LiteralPath $TokenPath -Raw | ConvertTo-SecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($roundTrip)
try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
if (-not $plain -or $plain -ne [string]$registration.token) { throw 'DPAPI token round-trip verification failed.' }

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName
$logTail = @()
if (Test-Path -LiteralPath $LogPath) { $logTail = @(Get-Content -LiteralPath $LogPath -Tail 20) }

[ordered]@{
  ok = $true
  workerId = $workerId
  taskState = [string]$task.State
  lastTaskResult = $info.LastTaskResult
  tokenRoundTrip = $true
  logExists = (Test-Path -LiteralPath $LogPath)
  logTail = $logTail
  fileLayer = 'drive_sync'
} | ConvertTo-Json -Depth 6
