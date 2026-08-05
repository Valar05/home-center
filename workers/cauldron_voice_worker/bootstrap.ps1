param(
    [Parameter(Mandatory = $true)]
    [string]$BootstrapCode,
    [string]$Origin = "https://us-central1-home-center-dclar.cloudfunctions.net/localVoiceFarm",
    [string]$WorkerId = "cauldron-voice-01"
)

$ErrorActionPreference = "Stop"

$InstallRoot = Join-Path $env:LOCALAPPDATA "Ferravine\VoiceWorker\v1"
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Models = Join-Path $InstallRoot "models"
$Venv = Join-Path $InstallRoot ".venv"
$TokenFile = Join-Path $InstallRoot ".worker-token"
$OriginFile = Join-Path $InstallRoot ".worker-origin"
$RunOnce = Join-Path $InstallRoot "run-once.ps1"

New-Item -ItemType Directory -Force -Path $InstallRoot, $Models | Out-Null
Copy-Item (Join-Path $SourceRoot "worker.py") $InstallRoot -Force
Copy-Item (Join-Path $SourceRoot "model-manifest.json") $InstallRoot -Force
Copy-Item (Join-Path $SourceRoot "requirements.txt") $InstallRoot -Force

py -3.12 -m venv $Venv
& (Join-Path $Venv "Scripts\python.exe") -m pip install --disable-pip-version-check -r (Join-Path $InstallRoot "requirements.txt")

$Manifest = Get-Content (Join-Path $InstallRoot "model-manifest.json") -Raw | ConvertFrom-Json
foreach ($File in $Manifest.model.files) {
    $Target = Join-Path $Models $File.name
    if (-not (Test-Path $Target)) {
        Invoke-WebRequest -UseBasicParsing -Uri $File.url -OutFile $Target
    }
    $Actual = (Get-FileHash -Algorithm SHA256 $Target).Hash.ToLowerInvariant()
    if ($Actual -ne $File.sha256) {
        Remove-Item $Target -Force
        throw "Model hash mismatch: $($File.name)"
    }
}

$BootstrapUri = $Origin.TrimEnd("/") + "/local-voice-farm/v1/bootstrap"
$Payload = @{ bootstrapCode = $BootstrapCode; workerId = $WorkerId } | ConvertTo-Json -Compress
$Registration = Invoke-RestMethod -Method Post -Uri $BootstrapUri -ContentType "application/json" -Body $Payload
if ($Registration.status -ne "registered" -or -not $Registration.token) {
    throw "Helm Center worker bootstrap did not return a registered token."
}

[IO.File]::WriteAllText($TokenFile, [string]$Registration.token)
[IO.File]::WriteAllText($OriginFile, $Origin.TrimEnd("/"))
icacls $TokenFile /inheritance:r /grant:r "${env:USERNAME}:(R,W)" | Out-Null
icacls $OriginFile /inheritance:r /grant:r "${env:USERNAME}:(R)" | Out-Null

$Runner = @'
$ErrorActionPreference = "Stop"
$InstallRoot = Join-Path $env:LOCALAPPDATA "Ferravine\VoiceWorker\v1"
$env:HOME_CENTER_LOCAL_VOICE_ORIGIN = (Get-Content (Join-Path $InstallRoot ".worker-origin") -Raw).Trim()
& (Join-Path $InstallRoot ".venv\Scripts\python.exe") (Join-Path $InstallRoot "worker.py") --once
'@
[IO.File]::WriteAllText($RunOnce, $Runner)

& (Join-Path $Venv "Scripts\python.exe") (Join-Path $InstallRoot "worker.py") --verify

Write-Host "THECAULDRON fixed-voice worker installed and registered at $InstallRoot"
Write-Host "No service, scheduled task, inbound listener, cloud fallback, or cloning was enabled."
Write-Host "After Helm Center creates the canary ticket, run: & '$RunOnce'"
