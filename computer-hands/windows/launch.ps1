param([string]$ConfigPath)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $ConfigPath
$startup = Join-Path $root 'startup.log'
function S([string]$m) {
  Add-Content -LiteralPath $startup -Value ("{0} {1}" -f (Get-Date -Format o), $m) -Encoding UTF8
}
try {
  S "launcher_start pid=$PID user=$([Environment]::UserName) interactive=$([Environment]::UserInteractive)"
  $worker = Join-Path $root 'home-center-hands.ps1'
  if (-not (Test-Path -LiteralPath $worker)) { throw "Worker missing: $worker" }
  & $worker -ConfigPath $ConfigPath
  S "worker_returned exit=$LASTEXITCODE"
} catch {
  S ("startup_failure " + $_.Exception.ToString())
  throw
}
