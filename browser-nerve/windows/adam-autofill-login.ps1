param(
  [Parameter(Mandatory=$true)][string]$InputJsonBase64,
  [string]$NodePath = "node.exe"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

try {
  $jsonBytes = [Convert]::FromBase64String($InputJsonBase64)
  $json = [Text.Encoding]::UTF8.GetString($jsonBytes)
  $null = $json | ConvertFrom-Json
} catch {
  throw 'InputJsonBase64 must contain valid UTF-8 JSON.'
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$executor = Join-Path $root 'adam-autofill-login.mjs'
if (-not (Test-Path -LiteralPath $executor)) { throw "Adam autofill executor missing: $executor" }

$temp = Join-Path $env:TEMP ("adam-login-{0}.json" -f ([Guid]::NewGuid().ToString('N')))
try {
  [IO.File]::WriteAllText($temp, $json, [Text.UTF8Encoding]::new($false))
  $psi = New-Object Diagnostics.ProcessStartInfo
  $psi.FileName = $NodePath
  $psi.Arguments = "`"$executor`" `"$temp`""
  $psi.WorkingDirectory = $root
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true
  $p = New-Object Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()
  $stdoutTask = $p.StandardOutput.ReadToEndAsync()
  $stderrTask = $p.StandardError.ReadToEndAsync()
  if (-not $p.WaitForExit(90000)) {
    try { $p.Kill() } catch {}
    throw 'Adam autofill login exceeded 90 seconds.'
  }
  $stdout = $stdoutTask.Result.Trim()
  $stderr = $stderrTask.Result.Trim()
  if ($stderr) { [Console]::Error.WriteLine($stderr.Substring(0,[Math]::Min(2000,$stderr.Length))) }
  if (-not $stdout) { throw "Adam autofill login returned no receipt (exit $($p.ExitCode))." }
  $lines = @($stdout -split "`r?`n" | Where-Object { $_.Trim() })
  $receipt = $lines[-1] | ConvertFrom-Json
  if ($receipt.secretsReturned -ne $false -or $receipt.valuesReturned -ne $false) { throw 'Credential executor violated redaction contract.' }
  $receipt | ConvertTo-Json -Depth 12 -Compress
  if ($receipt.ok -ne $true) { exit 2 }
  exit 0
} finally {
  Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
}
