param(
  [string]$SourceDirectory = '',
  [switch]$NoStartup,
  [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Chromium Throne Windows installer requires Windows.' }
if (-not [Environment]::UserInteractive) { throw 'Run Chromium Throne once from the normal signed-in Windows account.' }

if ([string]::IsNullOrWhiteSpace($SourceDirectory)) {
  $SourceDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
} else {
  $SourceDirectory = [IO.Path]::GetFullPath($SourceDirectory)
}
if (-not (Test-Path -LiteralPath (Join-Path $SourceDirectory 'package.json') -PathType Leaf)) { throw "Chromium Throne package.json not found under $SourceDirectory" }
if (-not (Test-Path -LiteralPath (Join-Path $SourceDirectory 'src\throne.mjs') -PathType Leaf)) { throw "Chromium Throne daemon not found under $SourceDirectory" }

$Root = Join-Path $env:LOCALAPPDATA 'HomeCenter\ChromiumThrone'
$App = Join-Path $Root 'app'
$State = Join-Path $Root 'state'
$Log = Join-Path $Root 'daemon.log'
$TaskName = 'HomeCenterChromiumThrone'
$Dashboard = 'http://127.0.0.1:17373/'
New-Item -ItemType Directory -Force -Path $Root,$App,$State | Out-Null

Write-Host "Installing Chromium Throne from $SourceDirectory"
if (Test-Path -LiteralPath $App) {
  Get-ChildItem -LiteralPath $App -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $SourceDirectory 'package.json') -Destination (Join-Path $App 'package.json') -Force
Copy-Item -LiteralPath (Join-Path $SourceDirectory 'src') -Destination (Join-Path $App 'src') -Recurse -Force

$node = (Get-Command node.exe -ErrorAction Stop).Source
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
Push-Location $App
try {
  & $npm install --omit=dev --no-audit --no-fund | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "npm install failed with exit code $LASTEXITCODE" }
  & $npm run check | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "Chromium Throne self-check failed with exit code $LASTEXITCODE" }
} finally { Pop-Location }

$Launcher = Join-Path $Root 'start-throne.ps1'
$escapedApp = $App.Replace("'", "''")
$escapedState = $State.Replace("'", "''")
$escapedNode = $node.Replace("'", "''")
$escapedLog = $Log.Replace("'", "''")
@"
`$ErrorActionPreference = 'Stop'
`$env:CHROMIUM_THRONE_HOME = '$escapedState'
Set-Location -LiteralPath '$escapedApp'
& '$escapedNode' 'src\throne.mjs' *>> '$escapedLog'
"@ | Set-Content -LiteralPath $Launcher -Encoding UTF8

$ps = (Get-Command powershell.exe -ErrorAction Stop).Source
if (-not $NoStartup) {
  $args = "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`""
  $action = New-ScheduledTaskAction -Execute $ps -Argument $args
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
}

$Desktop = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop 'Chromium Throne.url'
@"
[InternetShortcut]
URL=$Dashboard
IconFile=$env:SystemRoot\System32\shell32.dll
IconIndex=13
"@ | Set-Content -LiteralPath $ShortcutPath -Encoding ASCII

if (-not $NoLaunch) {
  Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*ChromiumThrone*throne.mjs*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Process -FilePath $ps -ArgumentList @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',$Launcher) -WindowStyle Hidden
  $deadline = (Get-Date).AddSeconds(20)
  $healthy = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $health = Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:17373/health' -TimeoutSec 2
      if ($health.ok -and $health.contract -eq 'home-center.chromium-throne.v1') { $healthy = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 400
  }
  if (-not $healthy) { throw "Chromium Throne installed but health check failed. Inspect $Log" }
  Start-Process $Dashboard
}

[ordered]@{
  ok=$true
  contract='home-center.chromium-throne.v1'
  app=$App
  state=$State
  launcher=$Launcher
  dashboard=$Dashboard
  desktopShortcut=$ShortcutPath
  startupTask=if($NoStartup){$null}else{$TaskName}
  sourceDirectory=$SourceDirectory
  next='Use the dashboard. Click Open ChatGPT profile once and sign in if needed, then commission a repository task.'
} | ConvertTo-Json -Depth 5
