param(
    [Parameter(Mandatory=$true)][string]$BootstrapCode,
    [string]$Origin = "https://us-central1-home-center-dclar.cloudfunctions.net/veniceNerve",
    [string]$WorkerId = "windows-venice-nerve-01",
    [string]$DriveRoot = "G:\My Drive\Venice Runtime",
    [string]$SourcePath = (Join-Path $PSScriptRoot 'home-center-venice-nerve.ps1'),
    [string]$TaskName = 'HomeCenter Venice Nerve'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) { throw "Worker source not found: $SourcePath" }
$installRoot = Join-Path $env:LOCALAPPDATA 'HomeCenter\VeniceNerve'
[IO.Directory]::CreateDirectory($installRoot) | Out-Null
$workerPath = Join-Path $installRoot 'home-center-venice-nerve.ps1'
$configPath = Join-Path $installRoot 'config.json'
Copy-Item -LiteralPath $SourcePath -Destination $workerPath -Force

# Exchange the short-lived bootstrap in the current user's security context.
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $workerPath -ConfigPath $configPath -BootstrapCode $BootstrapCode -Origin $Origin -WorkerId $WorkerId -DriveRoot $DriveRoot -Once
if ($LASTEXITCODE -ne 0) { throw "Venice Nerve bootstrap failed with exit code $LASTEXITCODE." }
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) { throw 'Venice Nerve config was not written.' }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ("-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"{0}`" -ConfigPath `"{1}`"" -f $workerPath, $configPath)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

$task = Get-ScheduledTask -TaskName $TaskName
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$result = [ordered]@{
    ok = $true
    installed = $true
    taskName = $TaskName
    taskState = [string]$task.State
    workerId = [string]$config.workerId
    workerPath = $workerPath
    workerSha256 = (Get-FileHash -LiteralPath $workerPath -Algorithm SHA256).Hash.ToLowerInvariant()
    configPath = $configPath
    tokenStoredWithDpapi = $true
    fileLayer = 'drive_sync'
    bodyWorkerShared = $false
}
$result | ConvertTo-Json -Depth 8 -Compress
