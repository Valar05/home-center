param([ValidateSet('install','test','status')][string]$Stage='install')
$ErrorActionPreference='Stop'
$Root=Join-Path $env:USERPROFILE 'workspace\ritsu-audio-lab'
$Python=Join-Path $Root '.venv\Scripts\python.exe'
$Receipt=Join-Path $Root 'clap-receipt.json'
New-Item -ItemType Directory -Force -Path $Root | Out-Null
function Run([string]$Executable,[string[]]$Arguments) {
  & $Executable @Arguments
  if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Executable $($Arguments -join ' ')" }
}
if ($Stage -eq 'install') {
  if (-not (Test-Path $Python)) { Run 'py' @('-3.10','-m','venv',(Join-Path $Root '.venv')) }
  Run $Python @('-m','pip','install','--disable-pip-version-check','--upgrade','pip')
  Run $Python @('-m','pip','install','--disable-pip-version-check','torch','torchaudio','torchvision','--index-url','https://download.pytorch.org/whl/cu124')
  Run $Python @('-m','pip','install','--disable-pip-version-check','laion-clap','soundfile')
}
if (-not (Test-Path $Python)) { throw 'Environment missing: run install first' }
$Probe=Join-Path $PSScriptRoot 'probe.py'
Run $Python @($Probe,$Stage,$Receipt)
Write-Host "RITSU_AUDIO_LAB_$($Stage.ToUpper())_PASS"
