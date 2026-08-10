param(
  [string]$RepoPath = 'C:\Users\dclar\workspace\home-center',
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not (Test-Path -LiteralPath (Join-Path $RepoPath '.git'))) { throw "Home Center repo missing: $RepoPath" }

& git -C $RepoPath fetch --quiet origin main | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'git fetch origin main failed.' }
$sourceCommit = (& git -C $RepoPath rev-parse origin/main).Trim()

function Materialize-OriginScript([string]$Path, [string]$Name) {
  $text = (& git -C $RepoPath show ('origin/main:' + $Path)) -join "`n"
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($text)) { throw "Could not read $Path from origin/main." }
  $target = Join-Path $env:TEMP $Name
  [IO.File]::WriteAllText($target, $text, [Text.UTF8Encoding]::new($false))
  return $target
}

function Quote-ProcessArg([string]$Value) {
  if ($null -eq $Value) { return '""' }
  return '"' + ($Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
}

function Invoke-CapturedPowerShell([string]$ScriptPath, [hashtable]$NamedArguments = @{}) {
  $parts = @(
    '-NoLogo',
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', (Quote-ProcessArg $ScriptPath)
  )
  foreach ($name in $NamedArguments.Keys) {
    $parts += ('-' + $name)
    $parts += (Quote-ProcessArg ([string]$NamedArguments[$name]))
  }

  $psi = New-Object Diagnostics.ProcessStartInfo
  $psi.FileName = 'powershell.exe'
  $psi.Arguments = ($parts -join ' ')
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true

  $process = New-Object Diagnostics.Process
  $process.StartInfo = $psi
  [void]$process.Start()
  $stdoutTask = $process.StandardOutput.ReadToEndAsync()
  $stderrTask = $process.StandardError.ReadToEndAsync()
  $process.WaitForExit()
  $stdout = $stdoutTask.Result.Trim()
  $stderr = $stderrTask.Result.Trim()

  return [pscustomobject]@{
    ExitCode = $process.ExitCode
    Stdout = $stdout
    Stderr = $stderr
  }
}

$repairPath = Materialize-OriginScript 'computer-hands/windows/repair.ps1' 'hc-repair-v33.ps1'
$repairProcess = Invoke-CapturedPowerShell $repairPath @{ RepoPath = $RepoPath }
$repairExit = $repairProcess.ExitCode
if ($repairExit -ne 0) {
  throw "Computer Hands repair failed (exit $repairExit):`nSTDOUT:`n$($repairProcess.Stdout)`nSTDERR:`n$($repairProcess.Stderr)"
}
try { $repair = $repairProcess.Stdout | ConvertFrom-Json } catch {
  $repair = [pscustomobject]@{ raw = $repairProcess.Stdout; stderr = $repairProcess.Stderr }
}

$installPath = Materialize-OriginScript 'staging/venice-phase1/install-shadow-v2.ps1' 'venice-install-shadow-v2.ps1'
$phaseProcess = Invoke-CapturedPowerShell $installPath @{ RepoPath = $RepoPath; RuntimeRoot = $RuntimeRoot }
$phaseExit = $phaseProcess.ExitCode
try { $phase = $phaseProcess.Stdout | ConvertFrom-Json } catch {
  $phase = [pscustomobject]@{ raw = $phaseProcess.Stdout; stderr = $phaseProcess.Stderr; exitCode = $phaseExit }
}

$result = [ordered]@{
  ok = ($repairExit -eq 0 -and $phaseExit -eq 0)
  sourceCommit = $sourceCommit
  handsRepair = $repair
  handsRepairStderr = $repairProcess.Stderr
  phase1 = $phase
  phase1Stderr = $phaseProcess.Stderr
  phase1ExitCode = $phaseExit
  workstationRestartPerformed = $false
  next = if ($phaseExit -eq 0) { 'Remote acceptance: verify Hands/watchdog, inspect shadow receipts, then restart only Venice Workstation when approved by evidence.' } else { 'Hands should be recovered. Phase 1 integration stopped safely; inspect phase1 output for source drift or test failure before retrying.' }
}
$result | ConvertTo-Json -Depth 12
if ($phaseExit -ne 0) { exit $phaseExit }
