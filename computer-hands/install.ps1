param(
  [Parameter(Mandatory=$true)][string]$BootstrapCode,
  [string]$WorkerId = 'windows-hands-01',
  [string]$Origin = 'https://us-central1-home-center-dclar.cloudfunctions.net/computerHands',
  [string]$Branch = 'main'
)

$ErrorActionPreference = 'Stop'
$InstallDir = Join-Path $env:LOCALAPPDATA 'HomeCenterHands'
$ConfigPath = Join-Path $InstallDir 'config.json'
$WorkerPath = Join-Path $InstallDir 'worker.ps1'
$LogPath = Join-Path $InstallDir 'worker.log'
$TaskName = 'HomeCenterHands'
$WorkerUrl = "https://raw.githubusercontent.com/Valar05/home-center/$Branch/computer-hands/worker.ps1"

Write-Host 'Home Center Computer Hands bootstrap'
Write-Host 'File layer: Drive sync (unchanged)'

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$bootstrapUri = "$($Origin.TrimEnd('/'))/computer-hands/v1/bootstrap"
$exchangeBody = @{ bootstrapCode = $BootstrapCode; workerId = $WorkerId } | ConvertTo-Json -Compress
$registration = Invoke-RestMethod -Method Post -Uri $bootstrapUri -ContentType 'application/json' -Body $exchangeBody -UseBasicParsing
if (-not $registration.token) { throw 'Home Center did not return a Computer Hands worker token.' }

Invoke-WebRequest -Uri $WorkerUrl -OutFile $WorkerPath -UseBasicParsing
if (-not (Test-Path -LiteralPath $WorkerPath)) { throw 'Worker download failed.' }

$config = @{ origin = [string]$registration.origin; workerId = $WorkerId; token = [string]$registration.token; contractVersion = [string]$registration.contractVersion; installedAt = (Get-Date).ToString('o'); fileLayer = 'drive_sync' }
$config | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

# Lock the token/config to the current Windows user plus SYSTEM.
$acl = Get-Acl -LiteralPath $ConfigPath
$acl.SetAccessRuleProtection($true, $false)
$acl.Access | ForEach-Object { [void]$acl.RemoveAccessRule($_) }
$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$ruleCurrent = New-Object Security.AccessControl.FileSystemAccessRule($currentIdentity, 'FullControl', 'Allow')
$ruleSystem = New-Object Security.AccessControl.FileSystemAccessRule('SYSTEM', 'FullControl', 'Allow')
$acl.AddAccessRule($ruleCurrent)
$acl.AddAccessRule($ruleSystem)
Set-Acl -LiteralPath $ConfigPath -AclObject $acl

$escapedWorker = $WorkerPath.Replace("'", "''")
$escapedConfig = $ConfigPath.Replace("'", "''")
$argument = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WorkerPath`" -ConfigPath `"$ConfigPath`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argument
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentIdentity
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Days 0)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Home Center owner-scoped Computer Hands outbound worker. Drive sync remains the file layer.' -Force | Out-Null

Get-Process powershell -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Id -ne $PID } | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName
$result = [ordered]@{
  ok = $true
  taskName = $TaskName
  taskState = [string]$task.State
  lastTaskResult = [int]$info.LastTaskResult
  workerId = $WorkerId
  origin = [string]$registration.origin
  contractVersion = [string]$registration.contractVersion
  configPath = $ConfigPath
  workerPath = $WorkerPath
  fileLayer = 'drive_sync'
}
$result | ConvertTo-Json -Depth 5
