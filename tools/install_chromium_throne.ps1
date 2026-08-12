param(
  [string]$Root = "$env:LOCALAPPDATA\HomeCenter\ChromiumThrone",
  [switch]$Launch
)

$ErrorActionPreference = 'Stop'
$PinnedExtensionCommit = 'eca3705f3e99dbdd5b735234444422f286e29f21'
$ExtensionDir = Join-Path $Root 'extension'
$BrowserRoot = Join-Path $Root 'chrome-for-testing'
$ProfileDir = Join-Path $Root 'profile'
$ReceiptPath = Join-Path $Root 'install-receipt.json'
$Files = @('manifest.json','service-worker.js','sidepanel.html','throne-panel.mjs','swarm-core.mjs')
$RawBase = "https://raw.githubusercontent.com/Valar05/home-center/$PinnedExtensionCommit/browser-porch/extension"

Write-Host '[Chromium Throne] Installing real desktop runtime'
New-Item -ItemType Directory -Force -Path $Root,$ExtensionDir,$BrowserRoot,$ProfileDir | Out-Null

foreach ($name in $Files) {
  $dest = Join-Path $ExtensionDir $name
  Invoke-WebRequest -UseBasicParsing -Uri "$RawBase/$name" -OutFile $dest
  if (!(Test-Path $dest) -or (Get-Item $dest).Length -lt 10) { throw "Failed to vendor extension file: $name" }
}

$manifest = Get-Content (Join-Path $ExtensionDir 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.name -ne 'Chromium Throne' -or [int]$manifest.manifest_version -ne 3 -or $manifest.version -ne '0.5.0') {
  throw 'Downloaded extension is not the expected Chromium Throne 0.5.0 MV3 package.'
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
  campaignContextBuiltIn = $true
  workerModel = 'ChatGPT chat-mode Instant'
  workerSlicePolicy = 'one bounded feature/proof slice at a time'
  threadChokePolicy = 'strict six-field handoff -> durable merge -> fresh worker'
  automaticSwarmBabysitting = $true
  maxSwarmSlices = 12
  swarmTerminalState = 'awaiting_venice_review'
  externalReviewer = 'Venice local CLI via Ollama'
  externalReviewReceiptField = 'externalReviewGateSatisfied'
  chatGptMayApproveSwarm = $false
  greatWarPrompts = $false
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

Write-Host "[Chromium Throne] READY"
Write-Host "[Chromium Throne] Desktop launcher: $desktopLauncher"
Write-Host "[Chromium Throne] Receipt: $ReceiptPath"
Write-Host '[Chromium Throne] ChatGPT workers cannot close a swarm. Final acceptance requires a Venice local-review PASS receipt.'
Write-Host '[Chromium Throne] First launch requires signing into ChatGPT once in this dedicated profile.'

if ($Launch) { Start-Process -FilePath $desktopLauncher }
