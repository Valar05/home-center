param([ValidateSet('doctor','deploy','status','stop')][string]$Mode='doctor')
$ErrorActionPreference='Stop'
$repo=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$server=Join-Path $repo 'tools\ritsu-local-server\server.mjs'
$test=Join-Path $repo 'tools\ritsu-local-server\server.test.mjs'
$bridge=Join-Path $repo 'tools\campaigns\ritsu_control_playwright_bridge.mjs'
$state=Join-Path $env:LOCALAPPDATA 'RitsuControlBridge\LocalLink'
New-Item -ItemType Directory -Force -Path $state|Out-Null
$pidFile=Join-Path $state 'server.pid'
function owned {if(!(Test-Path $pidFile)){return $false};$n=[int](Get-Content $pidFile -Raw).Trim();$p=Get-CimInstance Win32_Process -Filter "ProcessId=$n" -ErrorAction SilentlyContinue;return ($null -ne $p -and $p.CommandLine -like '*ritsu-local-server*server.mjs*')}
if($Mode -eq 'status'){if(owned){'RITSU_RUNNING=1'}else{'RITSU_RUNNING=0'};exit 0}
if($Mode -eq 'stop'){if(owned){$n=[int](Get-Content $pidFile -Raw).Trim();Stop-Process -Id $n};'RITSU_STOPPED=1';exit 0}
& node --check $server
if($LASTEXITCODE -ne 0){throw 'server_syntax_failed'}
& node --check $bridge
if($LASTEXITCODE -ne 0){throw 'bridge_syntax_failed'}
& node --test $test
if($LASTEXITCODE -ne 0){throw 'protocol_tests_failed'}
$ip=(& 'C:\Program Files\Tailscale\tailscale.exe' ip -4).Trim()
if($ip -notmatch '^100\.'){throw 'tailscale_unavailable'}
if($Mode -eq 'doctor'){'RITSU_DOCTOR_PASS='+$ip;exit 0}
if(owned){'RITSU_ALREADY_RUNNING=1';exit 0}
$p=Start-Process node.exe -ArgumentList @($server) -WorkingDirectory $repo -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $state 'stdout.log') -RedirectStandardError (Join-Path $state 'stderr.log')
[IO.File]::WriteAllText($pidFile,[string]$p.Id)
Start-Sleep -Seconds 2
if(!(owned)){throw 'server_failed_to_start'}
'RITSU_LOCAL_DEPLOYED='+$ip
