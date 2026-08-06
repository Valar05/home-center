[CmdletBinding()]
param(
  [string]$Root="$env:LOCALAPPDATA\HelmCenter\cauldron-voice-farm",
  [string]$ReferenceAudio="",
  [string]$ConsentRecord="",
  [switch]$IncludeNano,
  [switch]$IncludeTurbo
)
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Canaries = (Get-Content "$ScriptRoot\canaries.v1.json" -Raw | ConvertFrom-Json).canaries
$env:HF_HOME = Join-Path $Root "cache\huggingface"
$Runner = "$ScriptRoot\cauldron_voice_preflight.py"
$OutputDir = Join-Path $Root "outputs"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
function Invoke-Render([string]$Python, [string[]]$Arguments) { & $Python $Runner @Arguments; if ($LASTEXITCODE -ne 0) { throw "RENDER_FAILED" } }

foreach ($Canary in $Canaries | Where-Object { -not $_.requiresReference }) {
  Invoke-Render "$Root\envs\kokoro\Scripts\python.exe" @("--engine","kokoro","--request-id","cauldron-kokoro-$($Canary.id)-v1","--text",$Canary.text,"--output","$OutputDir\kokoro-$($Canary.id).wav","--root",$Root,"--model-dir","$Root\models\kokoro")
}
if ($IncludeNano -or $IncludeTurbo) {
  if (-not $ReferenceAudio -or -not $ConsentRecord) { throw "CONSENTED_REFERENCE_REQUIRED" }
  $Text = ($Canaries | Where-Object { $_.requiresReference } | Select-Object -First 1).text
  if ($IncludeNano) { Invoke-Render "$Root\envs\chatterbox\Scripts\python.exe" @("--engine","chatterbox-nano","--request-id","cauldron-chatterbox-nano-character-v1","--text",$Text,"--output","$OutputDir\chatterbox-nano-character.wav","--root",$Root,"--reference",$ReferenceAudio,"--consent",$ConsentRecord,"--device","cpu") }
  if ($IncludeTurbo) { Invoke-Render "$Root\envs\chatterbox\Scripts\python.exe" @("--engine","chatterbox-turbo","--request-id","cauldron-chatterbox-turbo-character-v1","--text",$Text,"--output","$OutputDir\chatterbox-turbo-character.wav","--root",$Root,"--reference",$ReferenceAudio,"--consent",$ConsentRecord,"--device","cuda") }
}
& "$ScriptRoot\control.ps1" status -Root $Root
