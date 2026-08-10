param(
  [string]$BootstrapCode = '',
  [string]$WorkerId = 'windows-browser-nerve-01',
  [string]$Origin = 'https://us-central1-home-center-dclar.cloudfunctions.net/browserNerve',
  [string]$Repository = 'Valar05/home-center',
  [string]$Ref = 'main',
  [string]$SourceDirectory = '',
  [switch]$ForceRefreshToken
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'This installer is for Windows.' }
if (-not [Environment]::UserInteractive) { throw 'Run this once from the normal signed-in Windows account.' }

$Root = Join-Path $env:LOCALAPPDATA 'HomeCenter\BrowserNerve'
$WorkerPath = Join-Path $Root 'home-center-browser-nerve.ps1'
$ExecutorPath = Join-Path $Root 'browser-action.mjs'
$ConfigPath = Join-Path $Root 'config.json'
$TokenPath = Join-Path $Root 'worker-token.dpapi'
$LogPath = Join-Path $Root 'worker.log'
$ProgressPath = Join-Path $Root 'progress.json'
$BrowserProfile = Join-Path $Root 'chrome-profile'
$TaskName = 'HomeCenterBrowserNerve'
$Origin = $Origin.TrimEnd('/')
New-Item -ItemType Directory -Force -Path $Root,$BrowserProfile | Out-Null

if ([string]::IsNullOrWhiteSpace($SourceDirectory)) {
  $escapedRef = [Uri]::EscapeDataString($Ref)
  $base = "https://raw.githubusercontent.com/$Repository/$escapedRef/browser-nerve/windows"
  Write-Host "Home Center Browser Nerve: installing from $Repository@$Ref"
  Invoke-WebRequest -UseBasicParsing -Uri "$base/home-center-browser-nerve.ps1" -OutFile "$WorkerPath.download"
  Invoke-WebRequest -UseBasicParsing -Uri "$base/browser-action.mjs" -OutFile "$ExecutorPath.download"
} else {
  $SourceDirectory = [IO.Path]::GetFullPath($SourceDirectory)
  $sourceWorker = Join-Path $SourceDirectory 'home-center-browser-nerve.ps1'
  $sourceExecutor = Join-Path $SourceDirectory 'browser-action.mjs'
  if (-not (Test-Path -LiteralPath $sourceWorker -PathType Leaf)) { throw "Pre-staged Browser Nerve worker is missing: $sourceWorker" }
  if (-not (Test-Path -LiteralPath $sourceExecutor -PathType Leaf)) { throw "Pre-staged Browser Nerve executor is missing: $sourceExecutor" }
  Write-Host "Home Center Browser Nerve: installing from authenticated pre-staged source $SourceDirectory ($Repository@$Ref)"
  Copy-Item -LiteralPath $sourceWorker -Destination "$WorkerPath.download" -Force
  Copy-Item -LiteralPath $sourceExecutor -Destination "$ExecutorPath.download" -Force
}
if ((Get-Item "$WorkerPath.download").Length -lt 4000 -or (Get-Item "$ExecutorPath.download").Length -lt 6000) { throw 'Browser Nerve source files are unexpectedly small; refusing installation.' }
Move-Item -Force "$WorkerPath.download" $WorkerPath
Move-Item -Force "$ExecutorPath.download" $ExecutorPath

$health = Invoke-RestMethod -Method Get -Uri "$Origin/browser-nerve/v1/health" -TimeoutSec 30
if (-not $health.ok -or $health.contractVersion -ne 'home-center.browser-nerve-contract.v1') { throw 'Browser Nerve cloud health contract mismatch.' }

$node = (Get-Command node.exe -ErrorAction Stop).Source
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$packagePath = Join-Path $Root 'package.json'
@'
{
  "name": "home-center-browser-nerve-worker",
  "private": true,
  "type": "module",
  "dependencies": {"puppeteer-core": "24.16.0"}
}
'@ | Set-Content -LiteralPath $packagePath -Encoding UTF8
Push-Location $Root
try { & $npm install --omit=dev --no-audit --no-fund --ignore-scripts | Out-Host; if ($LASTEXITCODE -ne 0) { throw "npm install failed with exit code $LASTEXITCODE" } }
finally { Pop-Location }

$needsToken = $ForceRefreshToken -or -not (Test-Path -LiteralPath $TokenPath)
if ($needsToken) {
  if ([string]::IsNullOrWhiteSpace($BootstrapCode)) { throw 'BootstrapCode is required for first install or -ForceRefreshToken.' }
  $registration = Invoke-RestMethod -Method Post -Uri "$Origin/browser-nerve/v1/bootstrap" -ContentType 'application/json' -Body (@{bootstrapCode=$BootstrapCode;workerId=$WorkerId}|ConvertTo-Json -Compress) -TimeoutSec 30
  if (-not $registration.token) { throw 'Browser Nerve bootstrap did not return a worker token.' }
  $secure = ConvertTo-SecureString ([string]$registration.token) -AsPlainText -Force
  $secure | ConvertFrom-SecureString | Set-Content -LiteralPath $TokenPath -Encoding ASCII
} else { Write-Host 'Existing DPAPI worker token retained.' }

$config = [ordered]@{
  schemaVersion='home-center.browser-nerve-windows-config.v1';origin=$Origin;workerId=$WorkerId;tokenPath=$TokenPath;
  executorPath=$ExecutorPath;nodePath=$node;logPath=$LogPath;progressPath=$ProgressPath;browserProfile=$BrowserProfile;debugPort=9223;
  selectorPolicy='aria_role_name_then_testid_id_css_then_text';repository=$Repository;ref=$Ref;installedAt=(Get-Date).ToUniversalTime().ToString('o')
}
$config | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

$ps = (Get-Command powershell.exe -ErrorAction Stop).Source
$arg = "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WorkerPath`" -ConfigPath `"$ConfigPath`""
$action = New-ScheduledTaskAction -Execute $ps -Argument $arg
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2
$task = Get-ScheduledTask -TaskName $TaskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

[ordered]@{
  ok=$true;task=$TaskName;taskState=[string]$task.State;lastTaskResult=$taskInfo.LastTaskResult;workerId=$WorkerId;origin=$Origin;
  workerPath=$WorkerPath;executorPath=$ExecutorPath;browserProfile=$BrowserProfile;debugPort=9223;tokenProtectedBy='Windows DPAPI current user';
  selectorPolicy='aria_role_name_then_testid_id_css_then_text';sourceDirectory=if($SourceDirectory){$SourceDirectory}else{$null};next='Verify browser_nerve.worker.status through Home Center, then run browser.navigate and browser.observe acceptance.'
} | ConvertTo-Json -Depth 6
