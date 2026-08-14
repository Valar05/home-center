param(
  [string]$Root = "$env:LOCALAPPDATA\HomeCenter\ChromiumThrone",
  [switch]$Launch
)

$ErrorActionPreference = 'Stop'
# Pinned to the reviewed extension commit containing the 0.7.0 single-Pro
# Fortress evolution body. This pin covers every vendored extension file below.
$PinnedExtensionCommit = '3f4567d767a57fe532858c9f96576af8d973b8b4'
$ExtensionDir = Join-Path $Root 'extension'
$BrowserRoot = Join-Path $Root 'chrome-for-testing'
$ProfileDir = Join-Path $Root 'profile'
$ReceiptPath = Join-Path $Root 'install-receipt.json'
$Files = @(
  'manifest.json',
  'service-worker.js',
  'sidepanel.html',
  'throne-panel.mjs',
  'swarm-core.mjs',
  'relay-config.mjs',
  'throne_context.test.mjs',
  'swarm-core.test.mjs',
  'swarm-policy.md',
  'babysitting-policy.md'
)
$RawBase = "https://raw.githubusercontent.com/Valar05/home-center/$PinnedExtensionCommit/browser-porch/extension"

Write-Host '[Chromium Throne] Installing single-Pro Fortress evolution runtime'
New-Item -ItemType Directory -Force -Path $Root,$ExtensionDir,$BrowserRoot,$ProfileDir | Out-Null

foreach ($name in $Files) {
  $dest = Join-Path $ExtensionDir $name
  Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/$name" -OutFile $dest
  if (!(Test-Path $dest) -or (Get-Item $dest).Length -lt 10) { throw "Failed to vendor extension file: $name" }
}

$manifest = Get-Content (Join-Path $ExtensionDir 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.name -ne 'Chromium Throne' -or [int]$manifest.manifest_version -ne 3 -or $manifest.version -ne '0.7.0') { throw 'Downloaded extension is not the expected Chromium Throne 0.7.0 MV3 package.' }
if (-not ($manifest.permissions -contains 'tabs')) { throw 'Chromium Throne requires tabs authority for explicit recovery rotation and persistent worker identity.' }
if (-not ($manifest.permissions -contains 'alarms')) { throw 'Chromium Throne requires alarms for relay polling/recovery.' }

$coreText = Get-Content (Join-Path $ExtensionDir 'swarm-core.mjs') -Raw
$panelText = Get-Content (Join-Path $ExtensionDir 'throne-panel.mjs') -Raw
$workerText = Get-Content (Join-Path $ExtensionDir 'service-worker.js') -Raw
$relayText = Get-Content (Join-Path $ExtensionDir 'relay-config.mjs') -Raw

if ($coreText -notmatch 'MAX_PARALLEL_WORKERS\s*=\s*1') { throw 'Single persistent Pro worker bound is missing.' }
if ($coreText -notmatch "WORKER_REASONING_MODE\s*=\s*'Pro reasoning'") { throw 'Pro reasoning doctrine is missing.' }
if ($coreText -notmatch 'singlePersistentProWorker:\s*true') { throw 'Persistent Pro worker doctrine is missing.' }
if ($coreText -notmatch 'phoneSovereign:\s*true' -or $coreText -notmatch 'phoneControlFromProWorker:\s*false') { throw 'Phone sovereignty boundary is missing.' }
if ($coreText -notmatch 'harrowayConsultationRequired:\s*true') { throw 'Harroway consultation requirement is missing.' }
if ($coreText -notmatch 'sheRawMotivationRequired:\s*true') { throw 'She-Raw motivational pressure requirement is missing.' }
if ($coreText -notmatch 'narratedContinuationForbidden:\s*true') { throw 'Narrated-continuation guard is missing.' }
if ($coreText -notmatch "VENICE_REVIEW_MODE\s*=\s*'judgment_jar_emulation'") { throw 'Stable Judgment-Jar Venice reviewer wire ID is missing.' }
if ($coreText -notmatch "veniceReviewSemantics:\s*'primary-judgment-jar'") { throw 'Primary Judgment-Jar Venice semantics are missing.' }
if ($coreText -notmatch 'planVeniceContinuation' -or $coreText -notmatch 'parseVeniceDirective') { throw 'Venice continuation core is missing.' }
if ($coreText -notmatch "explicitRecovery = source === 'explicit-recovery'") { throw 'Fresh worker rotation is not restricted to explicit recovery.' }

if ($panelText -notmatch "type:\s*'throne\.swarm\.run'") { throw 'Side panel is not a client of the existing service-worker runtime.' }
if ($panelText -notmatch 'one visible authenticated ChatGPT Pro worker') { throw 'Single-Pro Fortress evolution campaign seed is missing.' }
if ($panelText -notmatch 'creative insults are load-bearing motivational pressure') { throw 'She-Raw load-bearing motivation is missing from campaign seed.' }
if ($panelText -notmatch "newWorker\.checked \? 'explicit-recovery' : 'manual'") { throw 'Panel fresh-worker rotation is not explicit recovery only.' }

if ($workerText -notmatch 'single persistent ChatGPT Pro-reasoning worker') { throw 'Worker boot envelope does not bind a persistent Pro worker.' }
if ($workerText -notmatch 'thronePersistentWorkerTabId' -or $workerText -notmatch 'resolvePersistentWorker') { throw 'Persistent ChatGPT tab identity is missing.' }
if ($workerText -notmatch 'continuation\.job\.workerTabId = job\.workerTabId' -or $workerText -notmatch 'venice\.job\.workerTabId = job\.workerTabId') { throw 'Continuation is not pinned to the persistent conversation.' }
if ($workerText -notmatch 'The phone is sovereign' -or $workerText -notmatch 'do not own an unlock loop or continuously puppet the phone') { throw 'Pro worker phone-control boundary is missing.' }
if ($workerText -notmatch 'Harroway/operator consultation') { throw 'Harroway worker consultation is missing.' }
if ($workerText -notmatch 'She-Raw creative insults are load-bearing motivational pressure') { throw 'She-Raw worker pressure is missing.' }
if ($workerText -notmatch 'Narrating the next action is not continuation') { throw 'Narrated-continuation execution guard is missing.' }
if ($workerText -notmatch "don't talk to me mean execute") { throw 'Operator-imperative continuation is missing.' }
if ($workerText -notmatch 'Venice Judgment Jars are mandatory and PRIMARY') { throw 'Worker boot envelope does not require primary Judgment-Jar Venice.' }
if ($workerText -notmatch 'CONTINUE_REQUIRED forbids stopping') { throw 'Worker boot envelope does not preserve Venice continuation.' }
if ($workerText -notmatch 'venice_continue_required' -or $workerText -notmatch 'venice_review_missing' -or $workerText -notmatch 'venice_stop_allowed') { throw 'Service worker does not mechanically enforce Venice continuation/stop states.' }
if ($workerText -notmatch 'continuationPending' -or $workerText -notmatch "type: 'swarm_run_checkpoint'") { throw 'Evolution checkpoint risks masquerading as mission completion.' }
if ($workerText -match "type: 'swarm_run_complete'") { throw 'Stale terminal swarm-wave receipt remains.' }
if ($workerText -match 'disposable execution threads' -or $workerText -match 'one bounded bite') { throw 'Stale disposable-worker doctrine remains.' }
if ($workerText -match 'chat-mode Instant execution worker' -or $workerText -match 'WORKER MODEL: ChatGPT chat-mode Instant') { throw 'Stale Instant worker doctrine is present.' }
if ($workerText -match "reviewer:\s*'venice-local'") { throw 'Stale local-Venice terminal dependency is present.' }
if ($workerText -notmatch 'reviewerMode:\s*WORKER_DOCTRINE\.veniceReviewMode') { throw 'Worker receipts are not using the canonical Venice reviewer mode.' }

if ($relayText -notmatch 'enabled:\s*false' -or $relayText -notmatch "capability:\s*''") { throw 'Committed relay template must remain disabled and secret-free.' }

$nodeTestState = 'not_run_node_missing'
$node = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $node) { $node = Get-Command node -ErrorAction SilentlyContinue }
if ($node) {
  Write-Host '[Chromium Throne] Running extension contract tests'
  Push-Location $ExtensionDir
  try {
    & $node.Source --test throne_context.test.mjs swarm-core.test.mjs
    if ($LASTEXITCODE -ne 0) { throw "Chromium Throne contract tests failed with exit $LASTEXITCODE" }
    $nodeTestState = 'passed'
  } finally { Pop-Location }
}

$versions = Invoke-RestMethod -Uri 'https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json'
$stable = $versions.channels.Stable
$download = $stable.downloads.chrome | Where-Object { $_.platform -eq 'win64' } | Select-Object -First 1
if (!$download.url) { throw 'Chrome for Testing win64 download was not found in the official manifest.' }
$BrowserVersionDir = Join-Path $BrowserRoot $stable.version
$BrowserExe = Join-Path $BrowserVersionDir 'chrome-win64\chrome.exe'
if (!(Test-Path $BrowserExe)) {
  $zip = Join-Path $Root "chrome-for-testing-$($stable.version)-win64.zip"
  Write-Host "[Chromium Throne] Vendoring Chrome for Testing $($stable.version)"
  Invoke-WebRequest -UseBasicParsing -Uri $download.url -OutFile $zip
  if (!(Test-Path $zip) -or (Get-Item $zip).Length -lt 1000000) { throw 'Chrome for Testing download is incomplete.' }
  New-Item -ItemType Directory -Force -Path $BrowserVersionDir | Out-Null
  Expand-Archive -Path $zip -DestinationPath $BrowserVersionDir -Force
  Remove-Item $zip -Force
}
if (!(Test-Path $BrowserExe)) { throw "Chrome for Testing executable missing after extraction: $BrowserExe" }

$launcher = Join-Path $Root 'launch-chromium-throne.cmd'
$cmd = @"
@echo off
start "Chromium Throne" "$BrowserExe" --user-data-dir="$ProfileDir" --load-extension="$ExtensionDir" --no-first-run --no-default-browser-check "https://chatgpt.com/"
"@
Set-Content -Path $launcher -Value $cmd -Encoding ASCII
$desktop = [Environment]::GetFolderPath('Desktop')
$desktopLauncher = Join-Path $desktop 'Chromium Throne.cmd'
Copy-Item $launcher $desktopLauncher -Force

$receipt = [ordered]@{
  installedAt = (Get-Date).ToString('o')
  extensionCommit = $PinnedExtensionCommit
  extensionDir = $ExtensionDir
  extensionName = $manifest.name
  extensionVersion = $manifest.version
  manifestVersion = $manifest.manifest_version
  sourceContractChecks = 'passed'
  nodeContractTests = $nodeTestState
  workerModel = 'ChatGPT Pro reasoning'
  workerModelDefault = 'Pro reasoning'
  instantDefault = $false
  persistentProWorker = $true
  phoneSovereign = $true
  proWorkerOwnsPhoneUnlockLoop = $false
  harrowayConsultationRequired = $true
  sheRawMotivationRequired = $true
  narratedContinuationForbidden = $true
  explicitWorkerRotationOnly = $true
  operatorSurface = 'Home Center / Adam overlay + notifications; Chromium Throne is Pro reasoning organ'
  workerSlicePolicy = 'persistent conversation advances one evidence-backed evolution slice at a time'
  parallelWorkerPool = $false
  maxParallelWorkers = 1
  maxSwarmSlicesPerWave = 12
  boundedWaveIsTerminal = $false
  preDispatchAssistantBaseline = $true
  persistentWorkerTabIdentity = $true
  veniceReviewMode = 'judgment_jar_emulation'
  veniceReviewSemantics = 'primary-judgment-jar'
  veniceJudgmentJarPrimary = $true
  localVeniceRequired = $false
  stopAllowedRequiredForNormalStop = $true
  continueRequiredAutomaticallyContinues = $true
  responseBoundaryNeverStopsMission = $true
  vladReviewRequired = $true
  tetsuyaFinalReleaseRequired = $true
  chatGptMaySelfAcceptCampaign = $false
  requiredRealEvolutionGenerations = 2
  browser = 'Chrome for Testing'
  browserVersion = $stable.version
  browserExe = $BrowserExe
  browserDownload = $download.url
  profileDir = $ProfileDir
  desktopLauncher = $desktopLauncher
  initialUrl = 'https://chatgpt.com/'
  initialTabs = 1
  extensionLoadMode = '--load-extension'
  bootPhrase = 'PORTCULLIS LOCKED'
}
$receipt | ConvertTo-Json -Depth 6 | Set-Content $ReceiptPath -Encoding UTF8

Write-Host '[Chromium Throne] READY FOR RUNTIME CANARY'
Write-Host "[Chromium Throne] Desktop launcher: $desktopLauncher"
Write-Host "[Chromium Throne] Receipt: $ReceiptPath"
Write-Host '[Chromium Throne] Installed source is not runtime acceptance. Two real interface-evolution generations with device receipts are still required.'
Write-Host '[Chromium Throne] First launch may require signing into ChatGPT once in this dedicated profile.'

if ($Launch) { Start-Process -FilePath $desktopLauncher }
