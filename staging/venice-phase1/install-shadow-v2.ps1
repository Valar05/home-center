param(
  [string]$RepoPath = 'C:\Users\dclar\workspace\home-center',
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$transportPath = 'staging/venice-phase1/durable-core-shadow-v2.zip.b64'
$patchPath = 'staging/venice-phase1/apply-durable-shadow.ps1'
$expectedZip = 'f30f62e26c74251801a9b32c5e19cfbe6656f8c8943241481325721b49cc53ef'
$expected = [ordered]@{
  'src\durable-core\schema.mjs' = 'aaf214ab269b6de403315cd44fffa973ac56208f215ba51db25853acc1e12d2f'
  'src\durable-core\legacy-migration.mjs' = 'd842a80338dc1a909d801d88d03699e446f46fb563fd5eb336207be80cda7676'
  'src\durable-core\shadow-observer.mjs' = 'cec46ba4c17b867f04e649ea626e81e076e3e61ba3408de1ee9867c4991159f9'
  'test\durable-core-schema.test.mjs' = '22b681abd764e2de58ce306148f32687d3a000c2ea18af75d6068fd4b549b68b'
  'test\durable-core-shadow.test.mjs' = '805083ef7323d278b10d04976dceb101149225ef46586b681b7527fe24f50d9b'
  'test\durable-core-shadow-integration.test.mjs' = '34cb58c4f7af89558dee7b4e43a5c33702518d45337086116ae01222dec20d8a'
}

if (-not (Test-Path -LiteralPath (Join-Path $RepoPath '.git'))) { throw "Home Center repo missing: $RepoPath" }
if (-not (Test-Path -LiteralPath $RuntimeRoot)) { throw "Venice Runtime missing: $RuntimeRoot" }

& git -C $RepoPath fetch --quiet origin main | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'git fetch origin main failed.' }
$sourceCommit = (& git -C $RepoPath rev-parse origin/main).Trim()
$b64 = ((& git -C $RepoPath show ('origin/main:' + $transportPath)) -join '')
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($b64)) { throw 'Could not read Phase 1 transport from origin/main.' }
$zip = Join-Path $env:TEMP 'venice-phase1-shadow-v2.zip'
[IO.File]::WriteAllBytes($zip, [Convert]::FromBase64String($b64))
$zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($zipHash -ne $expectedZip) { throw "Phase 1 transport hash mismatch: $zipHash" }

$stage = Join-Path $env:TEMP 'venice-phase1-shadow-v2'
Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -LiteralPath $zip -DestinationPath $stage -Force

foreach ($rel in $expected.Keys) {
  $source = Join-Path $stage $rel
  $actual = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actual -ne $expected[$rel]) { throw "Payload hash mismatch: $rel $actual" }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$installed = @()
foreach ($rel in $expected.Keys) {
  $source = Join-Path $stage $rel
  $destination = Join-Path $RuntimeRoot $rel
  $directory = Split-Path -Parent $destination
  [IO.Directory]::CreateDirectory($directory) | Out-Null
  if (Test-Path -LiteralPath $destination) {
    $existingHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($existingHash -ne $expected[$rel]) {
      Copy-Item -LiteralPath $destination -Destination "$destination.pre-phase1-$stamp" -Force
    }
  }
  $tmp = "$destination.new"
  Copy-Item -LiteralPath $source -Destination $tmp -Force
  $copiedHash = (Get-FileHash -LiteralPath $tmp -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($copiedHash -ne $expected[$rel]) { throw "Staged copy hash mismatch: $rel $copiedHash" }
  Move-Item -LiteralPath $tmp -Destination $destination -Force
  $installed += [pscustomobject]@{ path=$rel; sha256=$copiedHash }
}

$schema = Join-Path $RuntimeRoot 'src\durable-core\schema.mjs'
$legacy = Join-Path $RuntimeRoot 'src\durable-core\legacy-migration.mjs'
$shadow = Join-Path $RuntimeRoot 'src\durable-core\shadow-observer.mjs'
foreach ($module in @($schema,$legacy,$shadow)) {
  & node --check $module
  if ($LASTEXITCODE -ne 0) { throw "Node syntax check failed: $module" }
}
$tests = @(
  (Join-Path $RuntimeRoot 'test\durable-core-schema.test.mjs'),
  (Join-Path $RuntimeRoot 'test\durable-core-shadow.test.mjs'),
  (Join-Path $RuntimeRoot 'test\durable-core-shadow-integration.test.mjs')
)
$testOutput = (& node --test @tests 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) { throw "Phase 1 focused tests failed`n$testOutput" }

$patchTemp = Join-Path $env:TEMP 'venice-apply-durable-shadow.ps1'
$patchText = (& git -C $RepoPath show ('origin/main:' + $patchPath)) -join "`n"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($patchText)) { throw 'Could not read shadow integration patch from origin/main.' }
[IO.File]::WriteAllText($patchTemp, $patchText, [Text.UTF8Encoding]::new($false))
$patchStdout = Join-Path $env:TEMP 'venice-shadow-patch.stdout.txt'
$patchStderr = Join-Path $env:TEMP 'venice-shadow-patch.stderr.txt'
Remove-Item -LiteralPath $patchStdout,$patchStderr -Force -ErrorAction SilentlyContinue
$patchProcess = Start-Process powershell.exe -ArgumentList @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$patchTemp,'-RuntimeRoot',$RuntimeRoot) -Wait -PassThru -NoNewWindow -RedirectStandardOutput $patchStdout -RedirectStandardError $patchStderr
$patchExit = $patchProcess.ExitCode
$patchOutput = if (Test-Path -LiteralPath $patchStdout) { Get-Content -LiteralPath $patchStdout -Raw } else { '' }
$patchErrorOutput = if (Test-Path -LiteralPath $patchStderr) { Get-Content -LiteralPath $patchStderr -Raw } else { '' }
if ($patchExit -ne 0) {
  [pscustomobject]@{
    ok = $false
    phase1CoreInstalled = $true
    focusedTestsPassed = $true
    shadowRunnerIntegrated = $false
    shadowPatchError = (($patchOutput + "`n" + $patchErrorOutput).Trim())
    sourceCommit = $sourceCommit
    zipSha256 = $zipHash
    installed = $installed
    tests = ($testOutput -split "`r?`n" | Where-Object { $_ -match '^# (tests|pass|fail) ' })
    restartPerformed = $false
  } | ConvertTo-Json -Depth 7
  exit 2
}

[pscustomobject]@{
  ok = $true
  phase1CoreInstalled = $true
  focusedTestsPassed = $true
  shadowRunnerIntegrated = $true
  sourceCommit = $sourceCommit
  zipSha256 = $zipHash
  installed = $installed
  tests = ($testOutput -split "`r?`n" | Where-Object { $_ -match '^# (tests|pass|fail) ' })
  shadowPatch = $patchOutput.Trim()
  restartPerformed = $false
} | ConvertTo-Json -Depth 8
