param(
  [string]$RepoPath = 'C:\Users\dclar\workspace\home-center',
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not (Test-Path -LiteralPath (Join-Path $RepoPath '.git'))) { throw "Home Center repo missing: $RepoPath" }

& git -C $RepoPath fetch origin main | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'git fetch origin main failed.' }
$sourceCommit = (& git -C $RepoPath rev-parse origin/main).Trim()

function Materialize-OriginScript([string]$Path, [string]$Name) {
  $text = (& git -C $RepoPath show ('origin/main:' + $Path)) -join "`n"
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($text)) { throw "Could not read $Path from origin/main." }
  $target = Join-Path $env:TEMP $Name
  [IO.File]::WriteAllText($target, $text, [Text.UTF8Encoding]::new($false))
  return $target
}

$repairPath = Materialize-OriginScript 'computer-hands/windows/repair.ps1' 'hc-repair-v33.ps1'
$repairRaw = (& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $repairPath -RepoPath $RepoPath 2>&1 | Out-String).Trim()
$repairExit = $LASTEXITCODE
if ($repairExit -ne 0) { throw "Computer Hands repair failed:`n$repairRaw" }
try { $repair = $repairRaw | ConvertFrom-Json } catch { $repair = [pscustomobject]@{ raw = $repairRaw } }

$installPath = Materialize-OriginScript 'staging/venice-phase1/install-shadow-v2.ps1' 'venice-install-shadow-v2.ps1'
$phaseRaw = (& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $installPath -RepoPath $RepoPath -RuntimeRoot $RuntimeRoot 2>&1 | Out-String).Trim()
$phaseExit = $LASTEXITCODE
try { $phase = $phaseRaw | ConvertFrom-Json } catch { $phase = [pscustomobject]@{ raw = $phaseRaw; exitCode = $phaseExit } }

$result = [ordered]@{
  ok = ($repairExit -eq 0 -and $phaseExit -eq 0)
  sourceCommit = $sourceCommit
  handsRepair = $repair
  phase1 = $phase
  phase1ExitCode = $phaseExit
  workstationRestartPerformed = $false
  next = if ($phaseExit -eq 0) { 'Remote acceptance: verify Hands/watchdog, inspect shadow receipts, then restart only Venice Workstation when approved by evidence.' } else { 'Hands should be recovered. Phase 1 integration stopped safely; inspect phase1 output for source drift or test failure before retrying.' }
}
$result | ConvertTo-Json -Depth 12
if ($phaseExit -ne 0) { exit $phaseExit }
