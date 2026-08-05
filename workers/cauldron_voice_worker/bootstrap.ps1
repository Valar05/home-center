$ErrorActionPreference = "Stop"

$InstallRoot = Join-Path $env:LOCALAPPDATA "Ferravine\VoiceWorker\v1"
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Models = Join-Path $InstallRoot "models"
$Venv = Join-Path $InstallRoot ".venv"

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

Write-Host "Cauldron fixed-voice pilot installed at $InstallRoot"
Write-Host "No service or scheduled task was created. Configure the Helm Center token, run worker.py --verify, then execute the audible canary before enabling persistence."
