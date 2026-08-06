[CmdletBinding()]
param(
  [string]$Root = "$env:LOCALAPPDATA\HelmCenter\cauldron-voice-farm",
  [switch]$SkipKokoro,
  [switch]$SkipChatterbox
)
$ErrorActionPreference = "Stop"
$Root = [IO.Path]::GetFullPath($Root)
$ExpectedParent = [IO.Path]::GetFullPath("$env:LOCALAPPDATA\HelmCenter")
if (-not $Root.StartsWith($ExpectedParent, [StringComparison]::OrdinalIgnoreCase)) { throw "REFUSED_ROOT_OUTSIDE_HELM_CENTER" }
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "PY_LAUNCHER_MISSING" }
& py -3.11 -c "import sys; assert sys.version_info[:2] == (3, 11)"
if ($LASTEXITCODE -ne 0) { throw "PYTHON_3_11_REQUIRED" }

function Invoke-Checked([string]$File, [string[]]$Arguments) {
  & $File @Arguments
  if ($LASTEXITCODE -ne 0) { throw "COMMAND_FAILED: $File" }
}
foreach ($Directory in @("envs", "models\kokoro", "cache\huggingface", "outputs", "receipts", "state")) {
  New-Item -ItemType Directory -Force -Path (Join-Path $Root $Directory) | Out-Null
}
$Receipt = [ordered]@{ schemaVersion = "home-center.cauldron-voice-install-receipt.v1"; host = $env:COMPUTERNAME; root = $Root; installedAtUtc = [DateTime]::UtcNow.ToString("o"); environments = @(); modelFiles = @() }

if (-not $SkipKokoro) {
  $EnvPath = Join-Path $Root "envs\kokoro"
  if (-not (Test-Path "$EnvPath\Scripts\python.exe")) { Invoke-Checked py @("-3.11", "-m", "venv", $EnvPath) }
  $Python = "$EnvPath\Scripts\python.exe"
  Invoke-Checked $Python @("-m", "pip", "install", "--upgrade", "pip")
  Invoke-Checked $Python @("-m", "pip", "install", "kokoro-onnx", "soundfile", "numpy")
  $Receipt.environments += @{ name = "kokoro"; freeze = ((& $Python -m pip freeze) -join "`n") }
  $Downloads = @(
    @{Name="kokoro-v1.0.onnx"; Url="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"},
    @{Name="voices-v1.0.bin"; Url="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"}
  )
  foreach ($Download in $Downloads) {
    $Path = Join-Path $Root "models\kokoro\$($Download.Name)"
    if (-not (Test-Path $Path)) { Invoke-WebRequest -Uri $Download.Url -OutFile $Path }
    $Receipt.modelFiles += @{ name=$Download.Name; source=$Download.Url; bytes=(Get-Item $Path).Length; sha256=(Get-FileHash -Algorithm SHA256 $Path).Hash.ToLowerInvariant() }
  }
}
if (-not $SkipChatterbox) {
  $EnvPath = Join-Path $Root "envs\chatterbox"
  if (-not (Test-Path "$EnvPath\Scripts\python.exe")) { Invoke-Checked py @("-3.11", "-m", "venv", $EnvPath) }
  $Python = "$EnvPath\Scripts\python.exe"
  Invoke-Checked $Python @("-m", "pip", "install", "--upgrade", "pip")
  Invoke-Checked $Python @("-m", "pip", "install", "chatterbox-tts", "soundfile", "numpy")
  $Receipt.environments += @{ name = "chatterbox"; freeze = ((& $Python -m pip freeze) -join "`n") }
}
$Receipt | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $Root "install-receipt.json")
$Receipt | ConvertTo-Json -Depth 8
