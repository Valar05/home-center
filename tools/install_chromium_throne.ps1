param(
  [string]$InstallDir = "$env:LOCALAPPDATA\HomeCenter\ChromiumThrone",
  [switch]$Launch
)

$ErrorActionPreference = 'Stop'
$PinnedCommit = 'e592c9ac8309cf1527813167306c91595578f7af'
$Base = "https://raw.githubusercontent.com/Valar05/home-center/$PinnedCommit/browser-porch/extension"
$Files = @('manifest.json','service-worker.js','sidepanel.html','sidepanel.js')

Write-Host "[Chromium Throne] Installing pinned extension $PinnedCommit"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

foreach ($name in $Files) {
  $dest = Join-Path $InstallDir $name
  Invoke-WebRequest -UseBasicParsing -Uri "$Base/$name" -OutFile $dest
  if (!(Test-Path $dest) -or (Get-Item $dest).Length -lt 10) {
    throw "Failed to vendor $name"
  }
}

$manifest = Get-Content (Join-Path $InstallDir 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.name -ne 'Chromium Throne' -or $manifest.manifest_version -ne 3) {
  throw 'Downloaded extension manifest is not Chromium Throne MV3'
}

$browserCandidates = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
)
$Browser = $browserCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (!$Browser) { throw 'Chrome or Edge was not found.' }

$ProfileDir = Join-Path $env:LOCALAPPDATA 'HomeCenter\ChromiumThroneProfile'
New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$launcher = Join-Path $InstallDir 'launch-chromium-throne.cmd'
$quotedBrowser = '"' + $Browser + '"'
$quotedExt = '"' + $InstallDir + '"'
$quotedProfile = '"' + $ProfileDir + '"'
$cmd = "@echo off`r`nstart \"Chromium Throne\" $quotedBrowser --user-data-dir=$quotedProfile --load-extension=$quotedExt --no-first-run --no-default-browser-check https://chatgpt.com/`r`n"
Set-Content -Path $launcher -Value $cmd -Encoding ASCII

$desktop = [Environment]::GetFolderPath('Desktop')
$desktopLauncher = Join-Path $desktop 'Chromium Throne.cmd'
Copy-Item $launcher $desktopLauncher -Force

$receipt = [ordered]@{
  installedAt = (Get-Date).ToString('o')
  pinnedCommit = $PinnedCommit
  installDir = $InstallDir
  browser = $Browser
  profileDir = $ProfileDir
  launcher = $desktopLauncher
  manifestVersion = $manifest.manifest_version
  extensionName = $manifest.name
  extensionVersion = $manifest.version
}
$receipt | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $InstallDir 'install-receipt.json') -Encoding UTF8

Write-Host "[Chromium Throne] Installed: $InstallDir"
Write-Host "[Chromium Throne] Launcher: $desktopLauncher"
Write-Host "[Chromium Throne] First launch may require signing into ChatGPT once in the dedicated Chromium Throne profile."

if ($Launch) {
  Start-Process -FilePath $desktopLauncher
}
