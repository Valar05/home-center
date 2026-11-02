# Ritsu Tailscale Serve transition; no admin, no Windows Firewall changes.
# Existing Tailscale Serve ports remain untouched. Modes doctor/apply/status/rollback.
param([ValidateSet('doctor','apply','status','rollback')][string]$Mode='doctor')
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$src=Join-Path $root 'tools\ritsu-local-server\server.mjs'
$state=Join-Path $env:LOCALAPPDATA 'RitsuControlBridge\LocalLink'
$pidFile=Join-Path $state 'serve-backend.pid'
$receiptFile=Join-Path $state 'tailscale-serve-receipt.json'
$tail='C:\Program Files\Tailscale\tailscale.exe'
[IO.Directory]::CreateDirectory($state)|Out-Null
function MyServer {
 if(!(Test-Path $pidFile)){return $null}
 $number=[int](Get-Content $pidFile -Raw).Trim()
 $p=Get-CimInstance Win32_Process -Filter "ProcessId=$number" -ErrorAction SilentlyContinue
 if($p -and $p.CommandLine -like '*ritsu-local-server*server.mjs*'){return $p}
 return $null
}
function ServeStatus {
 $value=(& $tail serve status 2>&1 | Out-String)
 if($LASTEXITCODE -ne 0){throw 'tailscale_serve_status_unavailable'}
 return $value
}
function OwnRoute($v) {return ([bool]($v -match '(?m):19646\b') -and [bool]($v -match '(?m)tcp://127\.0\.0\.1:19647'))}
function HasRoute($v){return [bool]($v -match '(?m):19646\b')}
function Save($stage,$detail){
 $status=ServeStatus
 $sha=(& git -C $root rev-parse HEAD).Trim()
 $obj=[ordered]@{campaign='ritsu-tailnet-serve-v1';stage=$stage;detail=$detail;mode=$Mode;sourceSha=$sha;backendPid=$(if(MyServer){(MyServer).ProcessId}else{0});servicePort=19646;localBackend='127.0.0.1:19647';serveRouteVerified=[bool](OwnRoute $status);atUTC=(Get-Date).ToUniversalTime().ToString('o')}
 $tmp=$receiptFile+'.tmp'
 [IO.File]::WriteAllText($tmp,($obj|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
 Move-Item -Force $tmp $receiptFile
 $obj|ConvertTo-Json -Compress
}
if(!(Test-Path $tail)){throw 'tailscale_cli_not_installed_on_windows'}
if(!(Test-Path $src)){throw 'pinned_server_source_missing'}
if($Mode -eq 'status'){Save 'observed' 'read_only';exit 0}
$current=ServeStatus
if($Mode -eq 'rollback'){
 if((HasRoute $current) -and -not (OwnRoute $current)){throw 'refuse_to_remove_unowned_serve_route'}
 if(OwnRoute $current){
  & $tail serve --tcp=19646 off
  if($LASTEXITCODE -ne 0){throw 'tailscale_route_rollback_failed'}
 }
 $mine=MyServer
 if($mine){Stop-Process -Id $mine.ProcessId -ErrorAction Stop}
 Save 'rolled_back' 'only_Ritsu_serve_route_and_owned_backend'
 exit 0
}
if((HasRoute $current) -and -not (OwnRoute $current)){throw 'port_19646_already_owned_by_other_serve_route'}
& node --check $src
if($LASTEXITCODE -ne 0){throw 'node_syntax_invalid'}
$tests=Join-Path $root 'tools\ritsu-local-server\server.test.mjs'
& node --test $tests
if($LASTEXITCODE -ne 0){throw 'protocol_tests_failed'}
if($Mode -eq 'doctor'){
 if(OwnRoute $current){Save 'doctor_pass' 'managed_route_already_exists'}
 else{Save 'doctor_pass' 'safe_to_configure_single_TCP_serve_route'}
 exit 0
}
if(!(MyServer)){
 $empty=Join-Path $state 'stdin.empty'
 if(!(Test-Path $empty)){[IO.File]::WriteAllText($empty,'')}
 $env:RITSU_TAILSCALE_SERVE='1'
 $p=Start-Process node.exe -ArgumentList @($src) -WorkingDirectory $root -PassThru -WindowStyle Hidden -RedirectStandardInput $empty -RedirectStandardOutput (Join-Path $state 'serve-stdout.log') -RedirectStandardError (Join-Path $state 'serve-stderr.log')
 [IO.File]::WriteAllText($pidFile,[string]$p.Id)
}
Start-Sleep -Seconds 2
if(!(MyServer)){throw 'loopback_backend_not_running'}
$health=0
try{Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:19647/v1/ritsu/status' -TimeoutSec 5|Out-Null}
catch{if($_.Exception.Response){$health=[int]$_.Exception.Response.StatusCode}}
if($health -ne 401){throw 'loopback_server_bearer_auth_preflight_failed'}
if(-not (OwnRoute (ServeStatus))){
 & $tail serve --bg --tcp=19646 tcp://127.0.0.1:19647
 if($LASTEXITCODE -ne 0){throw 'tailscale_serve_configuration_failed'}
}
if(-not (OwnRoute (ServeStatus))){throw 'tailscale_serve_readback_failed'}
Save 'deployed' 'existing_routes_preserved_phone_retries_probe_without_cli'
