param(
    [Parameter(Mandatory = $true)][string]$BootstrapCode,
    [Parameter(Mandatory = $true)][string[]]$Models,
    [string]$Origin = "https://us-central1-home-center-dclar.cloudfunctions.net/venusCauldronRelay",
    [string]$WorkerId = "cauldron-llm-01",
    [switch]$Start
)

$ErrorActionPreference = "Stop"
$InstallRoot = Join-Path $env:LOCALAPPDATA "Fortress\VenusCauldronRelay\v1"
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = (Get-Command py -ErrorAction Stop).Source
$TaskName = "Fortress Venus Cauldron Relay"

if (-not $Origin.StartsWith("https://")) { throw "Origin must use HTTPS." }
if ($Models.Count -lt 1) { throw "At least one explicit Ollama model is required." }
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Copy-Item (Join-Path $SourceRoot "worker.py") $InstallRoot -Force
Copy-Item (Join-Path $SourceRoot "run.ps1") $InstallRoot -Force
Copy-Item (Join-Path $SourceRoot "uninstall.ps1") $InstallRoot -Force

$Payload = @{ bootstrapCode = $BootstrapCode; workerId = $WorkerId } | ConvertTo-Json -Compress
$Registration = Invoke-RestMethod -Method Post -Uri ($Origin.TrimEnd("/") + "/worker/v1/bootstrap") -ContentType "application/json" -Body $Payload
if ($Registration.status -ne "registered" -or -not $Registration.token) { throw "Helm Center bootstrap did not return a registered worker token." }
$Requested = @($Models | Sort-Object -Unique)
$Granted = @($Registration.models | Sort-Object -Unique)
if ((Compare-Object $Requested $Granted).Count -ne 0) { throw "Bootstrap model grant differs from the requested local allowlist." }

[IO.File]::WriteAllText((Join-Path $InstallRoot ".worker-token"), [string]$Registration.token)
[IO.File]::WriteAllText((Join-Path $InstallRoot ".worker-origin"), $Origin.TrimEnd("/"))
[IO.File]::WriteAllText((Join-Path $InstallRoot ".worker-models"), ($Requested -join ","))
foreach ($Name in ".worker-token", ".worker-origin", ".worker-models") {
    icacls (Join-Path $InstallRoot $Name) /inheritance:r /grant:r "${env:USERNAME}:(R,W)" | Out-Null
}

& $Python -3.12 (Join-Path $InstallRoot "worker.py") --verify
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $InstallRoot 'run.ps1')`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Outbound-only VenusOS relay to loopback Ollama." -Force | Out-Null
if ($Start) { Start-ScheduledTask -TaskName $TaskName }
Write-Host "Installed $TaskName at $InstallRoot. Ollama remains loopback-only."

