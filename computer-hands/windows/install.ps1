param(
  [string]$BootstrapCode = '',
  [string]$WorkerId = 'windows-hands-01',
  [string]$Origin = 'https://us-central1-home-center-dclar.cloudfunctions.net/computerHands',
  [string]$Repository = 'Valar05/home-center',
  [string]$Ref = 'main',
  [switch]$ForceRefreshToken
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($env:OS -ne 'Windows_NT') { throw 'This installer is for Windows.' }
if (-not [Environment]::UserInteractive) { throw 'Run this once from your normal interactive Windows account.' }

$Root = Join-Path $env:LOCALAPPDATA 'HomeCenter\ComputerHands'
$WorkerPath = Join-Path $Root 'home-center-hands.ps1'
$ConfigPath = Join-Path $Root 'config.json'
$TokenPath = Join-Path $Root 'worker-token.dpapi'
$LogPath = Join-Path $Root 'worker.log'
$TaskName = 'HomeCenterComputerHands'
$Origin = $Origin.TrimEnd('/')

New-Item -ItemType Directory -Force -Path $Root | Out-Null

$escapedRef = [Uri]::EscapeDataString($Ref)
$workerUrl = "https://raw.githubusercontent.com/$Repository/$escapedRef/computer-hands/windows/home-center-hands.ps1"
Write-Host "Home Center Computer Hands: installing from $Repository@$Ref"
Invoke-WebRequest -UseBasicParsing -Uri $workerUrl -OutFile "$WorkerPath.download"
if ((Get-Item "$WorkerPath.download").Length -lt 4000) { throw 'Downloaded worker is unexpectedly small; refusing installation.' }
Move-Item -Force "$WorkerPath.download" $WorkerPath

$health = Invoke-RestMethod -Method Get -Uri "$Origin/computer-hands/v1/health" -TimeoutSec 30
if (-not $health.ok -or $health.fileLayer -ne 'drive_sync') { throw 'Computer Hands cloud health did not confirm drive_sync file ownership.' }

$needsToken = $ForceRefreshToken -or -not (Test-Path -LiteralPath $TokenPath)
if ($needsToken) {
  if ([string]::IsNullOrWhiteSpace($BootstrapCode)) { throw 'BootstrapCode is required for first install or -ForceRefreshToken.' }
  $registration = Invoke-RestMethod -Method Post -Uri "$Origin/computer-hands/v1/bootstrap" -ContentType 'application/json' -Body (@{ bootstrapCode = $BootstrapCode; workerId = $WorkerId } | ConvertTo-Json -Compress) -TimeoutSec 30
  if (-not $registration.token) { throw 'Computer Hands bootstrap did not return a worker token.' }
  $secure = ConvertTo-SecureString ([string]$registration.token) -AsPlainText -Force
  $secure | ConvertFrom-SecureString | Set-Content -LiteralPath $TokenPath -Encoding ASCII
} else {
  Write-Host 'Existing DPAPI worker token retained.'
}

$config = [ordered]@{
  schemaVersion = 'home-center.computer-hands-windows-config.v1'
  origin = $Origin
  workerId = $WorkerId
  tokenPath = $TokenPath
  logPath = $LogPath
  fileLayer = 'drive_sync'
  installedAt = (Get-Date).ToUniversalTime().ToString('o')
  repository = $Repository
  ref = $Ref
}
$config | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

$ps = (Get-Command powershell.exe -ErrorAction Stop).Source
$arg = "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WorkerPath`" -ConfigPath `"$ConfigPath`""
$action = New-ScheduledTaskAction -Execute $ps -Argument $arg
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2
$task = Get-ScheduledTask -TaskName $TaskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

[ordered]@{
  ok = $true
  task = $TaskName
  taskState = [string]$task.State
  lastTaskResult = $taskInfo.LastTaskResult
  workerId = $WorkerId
  origin = $Origin
  workerPath = $WorkerPath
  configPath = $ConfigPath
  tokenProtectedBy = 'Windows DPAPI current user'
  fileLayer = 'drive_sync'
  next = 'Verify computer_hands.worker.status through Home Center MCP.'
} | ConvertTo-Json -Depth 5
