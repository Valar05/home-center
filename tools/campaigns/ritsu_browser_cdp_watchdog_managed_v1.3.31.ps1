# Ritsu managed Chrome CDP watchdog v1.3.31.
# This is a dedicated profile, never an existing personal Chrome profile.
# Runs as the existing signed-in Windows user; no credential processing.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$version='1.3.31'
$base=Join-Path $env:USERPROFILE '.ritsu-control\watchdogs'
$throne=Join-Path $env:LOCALAPPDATA 'HomeCenter\ChromiumThrone'
$profile=Join-Path $throne 'profile'
$receipt=Join-Path $base 'Ritsu-Browser-Watchdog-LAST.json'
$mutex=$null
$mutexHeld=$false
$state=[ordered]@{version=$version; utc=[DateTime]::UtcNow.ToString('o'); status='STARTED'; reason=''; cdp_port=0; profile='DEDICATED_PERSISTENT'; chrome_pid=0; task='Ritsu Browser CDP Watchdog Managed'; interactive=$true}
function Probe-Cdp {
 try {
  $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri 'http://127.0.0.1:9236/json/version'
  if($r.StatusCode -ne 200){return $false}
  $j=$r.Content|ConvertFrom-Json
  return (([string]$j.Browser -match '^(Chrome|Chromium|HeadlessChrome)/') -and ([string]$j.webSocketDebuggerUrl -match '^ws://(127[.]0[.]0[.]1|localhost):9236/'))
 }catch{return $false}
}
function Get-OwnedChrome {
 # Only examine Chrome processes explicitly associated with this new profile.
 $target=[IO.Path]::GetFullPath($profile).TrimEnd('\')
 return @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue | Where-Object {
  $c=[string]$_.CommandLine
  $c -and $c.IndexOf($target,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and $c -match '(?i)--user-data-dir'
 })
}
function Find-ChromeExecutable {
 $paths=New-Object 'System.Collections.Generic.List[string]'
 if($env:ProgramFiles){$paths.Add((Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'))}
 ${pfx86}=[Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
 if(${pfx86}){$paths.Add((Join-Path ${pfx86} 'Google\Chrome\Application\chrome.exe'))}
 if($env:LOCALAPPDATA){$paths.Add((Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe'))}
 foreach($p in $paths){if(Test-Path -LiteralPath $p -PathType Leaf){return [IO.Path]::GetFullPath($p)}}
 return $null
}
try {
 [IO.Directory]::CreateDirectory($base)|Out-Null
 $mutex=New-Object Threading.Mutex($false,'Local\RitsuBrowserCDPWatchdogManaged')
 if(-not $mutex.WaitOne(0)){$state.status='SKIPPED';$state.reason='ANOTHER_WATCHDOG_RUNNING';return}
 $mutexHeld=$true
 # Avoid service/session-zero browser startup. Scheduler logon trigger handles the visible session.
 $session=[Diagnostics.Process]::GetCurrentProcess().SessionId
 if($session -eq 0){$state.status='WAITING';$state.reason='INTERACTIVE_LOGON_REQUIRED';$state.interactive=$false;return}
 if(-not $env:LOCALAPPDATA){$state.status='BLOCKED';$state.reason='LOCALAPPDATA_MISSING';return}
 $chrome=Find-ChromeExecutable
 if(-not $chrome){$state.status='BLOCKED';$state.reason='CHROME_INSTALL_NOT_FOUND';return}
 # We manage only this app-owned path. Never copy, discover, or mutate a personal browser profile.
 $profileRoot=[IO.Path]::GetFullPath($profile)
 if((Test-Path -LiteralPath (Join-Path $env:LOCALAPPDATA 'HomeCenter')) -and ((Get-Item -LiteralPath (Join-Path $env:LOCALAPPDATA 'HomeCenter') -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){$state.status='BLOCKED';$state.reason='HOMECENTER_ROOT_IS_REPARSE_POINT';return}
 $allowedRoot=[IO.Path]::GetFullPath($throne).TrimEnd('\')+'\'
 if(-not $profileRoot.StartsWith($allowedRoot,[StringComparison]::OrdinalIgnoreCase)){$state.status='BLOCKED';$state.reason='PROFILE_NOT_IN_APPROVED_ROOT';return}
 if(-not (Test-Path -LiteralPath $throne -PathType Container)){[IO.Directory]::CreateDirectory($throne)|Out-Null}
 if(-not (Test-Path -LiteralPath $profileRoot -PathType Container)){
  [IO.Directory]::CreateDirectory($profileRoot)|Out-Null
  $state.reason='NEW_DEDICATED_PROFILE_CREATED'
 }
 # A CDP listener on 9236 must belong to the Ritsu-owned Chrome instance; otherwise do not use it.
 $owned=@(Get-OwnedChrome)
 if(Probe-Cdp){
  if($owned.Count -lt 1){$state.status='BLOCKED';$state.reason='CDP_PORT_OWNED_BY_UNRELATED_CHROME';return}
  $state.status='CDP_READY';$state.cdp_port=9236;$state.reason='EXISTING_DEDICATED_BROWSER';return
 }
 if($owned.Count -gt 0){$state.status='BLOCKED';$state.reason='DEDICATED_BROWSER_RUNNING_WITHOUT_CDP_NO_TERMINATION';return}
 # If something else listens on 9236, do not launch a competing Chrome instance.
 $listener=@(Get-NetTCPConnection -State Listen -LocalPort 9236 -ErrorAction SilentlyContinue)
 if($listener.Count -gt 0){$state.status='BLOCKED';$state.reason='CDP_PORT_9236_OCCUPIED';return}
 # Chrome 136+ requires a non-default user-data-dir for debugging. This path is dedicated and persistent.
 $args='--remote-debugging-port=9236 --remote-debugging-address=127.0.0.1 --user-data-dir="'+$profileRoot+'" --no-first-run --no-default-browser-check https://chatgpt.com/'
 # The Playwright bridge requires this exact launcher in this exact app-owned directory.
 $launcher=Join-Path $throne 'launch-chromium-throne.cmd'
 if(@(Get-OwnedChrome).Count -gt 0 -and (Test-Path -LiteralPath $launcher -PathType Leaf)){$state.status='BLOCKED';$state.reason='LIVE_BROWSER_PROFILE_LAUNCHER_NOT_MODIFIED';return}
 $launcherText='@echo off'+[Environment]::NewLine+'start "" "'+$chrome+'" --remote-debugging-port=9236 --remote-debugging-address=127.0.0.1 --user-data-dir="'+$profileRoot+'" --no-first-run --no-default-browser-check https://chatgpt.com/'+[Environment]::NewLine
 $existingLauncher=''
 if(Test-Path -LiteralPath $launcher -PathType Leaf){$existingLauncher=[IO.File]::ReadAllText($launcher)}
 if($existingLauncher -ne $launcherText){
  if($existingLauncher){$backup=Join-Path $base ('launcher-before-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'.cmd');[IO.File]::WriteAllText($backup,$existingLauncher,[Text.Encoding]::UTF8)}
  [IO.File]::WriteAllText($launcher,$launcherText,(New-Object Text.UTF8Encoding($false)))
 }
 if(-not ([IO.File]::ReadAllText($launcher)).Contains('ChromiumThrone')){$state.status='BLOCKED';$state.reason='LAUNCHER_CONTRACT_NOT_MET';return}

 $process=Start-Process -FilePath $chrome -ArgumentList $args -PassThru -ErrorAction Stop
 $state.chrome_pid=$process.Id
 for($n=0;$n -lt 20;$n++){
  Start-Sleep -Seconds 2
  if(Probe-Cdp){
   if(@(Get-OwnedChrome).Count -lt 1){$state.status='BLOCKED';$state.reason='CDP_OWNER_NOT_VERIFIED';return}
   $state.status='CDP_READY';$state.cdp_port=9236;$state.reason='DEDICATED_BROWSER_STARTED_SIGN_IN_ONCE_IF_NEEDED';return
  }
 }
 $state.status='BLOCKED';$state.reason='CHROME_STARTED_CDP_NOT_VERIFIED'
}catch{
 $state.status='ERROR';$state.reason=$_.Exception.GetType().Name
 try { $state.error_line=[int]$_.InvocationInfo.ScriptLineNumber; $state.error_category=[string]$_.CategoryInfo.Category }catch{}
}finally{
 try{
  [IO.Directory]::CreateDirectory($base)|Out-Null
  $tmp=$receipt+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
  [IO.File]::WriteAllText($tmp,($state|ConvertTo-Json -Depth 4),(New-Object Text.UTF8Encoding($false)))
  Move-Item -LiteralPath $tmp -Destination $receipt -Force -ErrorAction Stop
 }catch{Write-Host 'RITSU_WATCHDOG_RECEIPT_WRITE_FAILED'}
 if($mutex){if($mutexHeld){try{$mutex.ReleaseMutex()}catch{}};$mutex.Dispose()}
}