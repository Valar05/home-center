$ErrorActionPreference='Stop'
function Report([string]$line){
  Write-Output $line
  if($env:RITSU_RECOVERY_RECEIPT_PATH){[IO.File]::AppendAllText($env:RITSU_RECOVERY_RECEIPT_PATH,$line+"`n",[Text.Encoding]::UTF8)}
}
$phase='PRECHECK';$changed=$false;$stopped=$false;$old='';$target='';$exe='';$nodeArgs='';$listenIp='';$listenPort=0;$oldPid=0
function StopSafe([string]$why){Report ('RITSU_WINDOWS_BLOCKED='+$why);exit 5}
try {
  if(-not $env:RITSU_RECOVERY_PACKET_DIR){StopSafe 'REMOTE_PACKET_DIR_UNSET'}
  $dir=$env:RITSU_RECOVERY_PACKET_DIR
  Report 'WINDOWS_PHASE=PRECHECK'
  $helper=Join-Path $dir 'ritsu_browser_recover_v133.mjs'
  $catalog=Join-Path $dir 'ritsu_browser_catalog_v135.mjs'
  $catalogFunctions=Join-Path $dir 'server_catalog_functions.js'
  $catalogRoutes=Join-Path $dir 'server_catalog_routes.js'
  $insertion=Join-Path $dir 'server_recovery_patch.js'
  if(-not ([IO.File]::Exists($helper) -and [IO.File]::Exists($insertion) -and [IO.File]::Exists($catalog) -and [IO.File]::Exists($catalogFunctions) -and [IO.File]::Exists($catalogRoutes))){StopSafe 'PACKET_PART_MISSING'}
  $running=@(Get-CimInstance Win32_Process -Filter "Name='node.exe'"|Where-Object{$_.CommandLine -match 'ritsu-local-server[\\/]server\.mjs'})
  if($running.Count -ne 1){StopSafe ('ACTIVE_RITSU_SERVER_COUNT_'+$running.Count)}
  $p=$running[0];$oldPid=[int]$p.ProcessId;$exe=[string]$p.ExecutablePath
  if(-not [IO.File]::Exists($exe)){StopSafe 'NODE_EXE_UNAVAILABLE'}
  $roots=@((Join-Path $env:USERPROFILE 'AppData\Local\RitsuControlBridge\release-016'),(Join-Path $env:USERPROFILE 'workspace\home-center'))
  $matches=@($roots|ForEach-Object{Join-Path $_ 'tools\ritsu-local-server\server.mjs'}|Where-Object{[IO.File]::Exists($_) -and $p.CommandLine.Contains($_)})
  if($matches.Count -ne 1){StopSafe ('RUNNING_SOURCE_PATH_NOT_UNIQUELY_VERIFIED_COUNT_'+$matches.Count)}
  $target=$matches[0]
  $cmd=([string]$p.CommandLine).Trim()
  $regex='^\s*"?'+[regex]::Escape($exe)+'"?\s+"?'+[regex]::Escape($target)+'"?\s*$'
  if($cmd -notmatch $regex){StopSafe 'NONSTANDARD_NODE_START_RECIPE'}
  $ports=@(Get-NetTCPConnection -OwningProcess $oldPid -State Listen -ErrorAction Stop|Where-Object{$_.LocalPort -in @(19646,19647)})
  if($ports.Count -ne 1){StopSafe 'ACTIVE_RITSU_PORT_NOT_UNIQUE'}
  $listenPort=[int]$ports[0].LocalPort;$listenIp=[string]$ports[0].LocalAddress
  if(($listenPort -eq 19647 -and $listenIp -ne '127.0.0.1') -or ($listenPort -eq 19646 -and $listenIp -notmatch '^100\.')){StopSafe 'ACTIVE_LISTENER_ADDRESS_MISMATCH'}
  $old=[IO.File]::ReadAllText($target,[Text.Encoding]::UTF8)
  $add=[IO.File]::ReadAllText($insertion,[Text.Encoding]::UTF8)
  $key='// Ritsu v1.3.3 server insertion; loaded into existing authenticated server.mjs.'
  $anchor='  const server=http.createServer(async(req,res)=>{'
  $route="      if(req.method==='GET'&&url.pathname==='/v1/ritsu/status')"
  if($old.Contains($key)){
    if(-not $old.Contains("url.pathname==='/v1/ritsu/recover'")){StopSafe 'INCOMPLETE_PREVIOUS_BACKEND_PATCH'}
    $new=$old; Report 'SERVER_PATCH=ALREADY_PRESENT'
  }else{
    if($old.Split(@($anchor),[StringSplitOptions]::None).Count -ne 2 -or $old.Split(@($route),[StringSplitOptions]::None).Count -ne 2){StopSafe 'UNRECOGNIZED_SERVER_SOURCE_ANCHORS'}
    $inEndpoint=@'
      if(req.method==='GET'&&url.pathname==='/v1/ritsu/recover'){
        const id=url.searchParams.get('turnId')||'',tab=url.searchParams.get('tabId')||'';
        const digest=url.searchParams.get('promptSha256')||'';
        if(!turnPattern.test(id)||!tabPattern.test(tab)||!/^[0-9a-f]{64}$/.test(digest))
          return send(400,{error:'invalid_recovery_identity'});
        const result=await recoverOriginalTurn(id,tab,digest);
        return send(200,result);
      }
'@
    $new=$old.Replace($anchor,$add+"`n"+$anchor).Replace($route,$inEndpoint+"`n"+$route)
    if($new -ceq $old){StopSafe 'NO_SOURCE_CHANGE'}
  }
  # Integrate new endpoints whether v1.3.3 recovery was previously installed or not.
  $catalogMark='// RITSU_V135_CATALOG_FUNCTIONS:'
  $catalogRouteMark='// RITSU_V135_CATALOG_ROUTES:'
  if(-not $new.Contains($catalogMark)){
    $fn=[IO.File]::ReadAllText($catalogFunctions,[Text.Encoding]::UTF8)
    $rt=[IO.File]::ReadAllText($catalogRoutes,[Text.Encoding]::UTF8)
    if($new.Split(@($anchor),[StringSplitOptions]::None).Count -ne 2 -or $new.Split(@($route),[StringSplitOptions]::None).Count -ne 2){StopSafe 'CATALOG_BACKEND_ANCHOR_DRIFT'}
    $new=$new.Replace($anchor,$fn+"`n"+$anchor).Replace($route,$rt+"`n"+$route)
  }elseif(-not $new.Contains($catalogRouteMark)){StopSafe 'INCOMPLETE_CATALOG_PATCH'}
  $catalogDest=Join-Path (Split-Path -Parent $target) '..\campaigns\ritsu_browser_catalog_v135.mjs'
  $catalogDest=[IO.Path]::GetFullPath($catalogDest)
  if([IO.File]::Exists($catalogDest)){
    if([IO.File]::ReadAllText($catalogDest,[Text.Encoding]::UTF8) -cne [IO.File]::ReadAllText($catalog,[Text.Encoding]::UTF8)){StopSafe 'CATALOG_HELPER_VERSION_COLLISION'}
  }
  $bridgeHelper=Join-Path (Split-Path -Parent $target) '..\campaigns\ritsu_browser_recover_v133.mjs'
  $bridgeHelper=[IO.Path]::GetFullPath($bridgeHelper)
  if([IO.File]::Exists($bridgeHelper)){
    if([IO.File]::ReadAllText($bridgeHelper,[Text.Encoding]::UTF8) -cne [IO.File]::ReadAllText($helper,[Text.Encoding]::UTF8)){StopSafe 'VERSIONED_HELPER_COLLISION'}
  }
  $stage=Join-Path (Split-Path -Parent $target) ('.ritsu-staged-recovery-'+[guid]::NewGuid().ToString('N')+'.mjs')
  [IO.File]::WriteAllText($stage,$new,(New-Object Text.UTF8Encoding($false)))
  try {
    & $exe --check $stage 2>&1 | Out-Null
    if($LASTEXITCODE -ne 0){StopSafe 'SERVER_NODE_SYNTAX_FAIL'}
    & $exe --check $catalog 2>&1 | Out-Null
    if($LASTEXITCODE -ne 0){StopSafe 'CATALOG_HELPER_NODE_SYNTAX_FAIL'}
    & $exe --check $helper 2>&1 | Out-Null
    if($LASTEXITCODE -ne 0){StopSafe 'HELPER_NODE_SYNTAX_FAIL'}
    $dirBackup=Join-Path $env:USERPROFILE '.ritsu-control\patch-backups';[IO.Directory]::CreateDirectory($dirBackup)|Out-Null
    $digest=([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($old)))).Replace('-','').ToLowerInvariant()
    $backup=Join-Path $dirBackup ('server-before-uncertain-recovery-'+$digest.Substring(0,16)+'.mjs')
    if(-not [IO.File]::Exists($backup)){[IO.File]::WriteAllText($backup,$old,(New-Object Text.UTF8Encoding($false)))}
    $phase='PREPARED';Report 'WINDOWS_PHASE=PREPARED'
    if([IO.File]::ReadAllText($target,[Text.Encoding]::UTF8) -cne $old){StopSafe 'ACTIVE_SOURCE_CHANGED_DURING_PREFLIGHT'}
    if(-not [IO.File]::Exists($bridgeHelper)){
      [IO.File]::Copy($helper,$bridgeHelper,$false)
      if([IO.File]::ReadAllText($bridgeHelper,[Text.Encoding]::UTF8) -cne [IO.File]::ReadAllText($helper,[Text.Encoding]::UTF8)){StopSafe 'HELPER_COPY_READBACK_FAILED'}
    }
    if(-not [IO.File]::Exists($catalogDest)){
      [IO.File]::Copy($catalog,$catalogDest,$false)
      if([IO.File]::ReadAllText($catalogDest,[Text.Encoding]::UTF8) -cne [IO.File]::ReadAllText($catalog,[Text.Encoding]::UTF8)){StopSafe 'CATALOG_HELPER_COPY_MISMATCH'}
    }
    if($new -cne $old){[IO.File]::Replace($stage,$target,$null);$changed=$true}
    if([IO.File]::ReadAllText($target,[Text.Encoding]::UTF8) -cne $new){StopSafe 'SERVER_PATCH_READBACK_FAILED'}
  } finally {if([IO.File]::Exists($stage)){Remove-Item -LiteralPath $stage -Force}}
  $phase='RESTART_VERIFIED_NODE';Report 'WINDOWS_PHASE=RESTART_VERIFIED_NODE'
  Stop-Process -Id $oldPid -ErrorAction Stop;$stopped=$true
  Start-Sleep -Milliseconds 650
  if($listenPort -eq 19647){$env:RITSU_TAILSCALE_SERVE='1'}
  $newProc=Start-Process -FilePath $exe -ArgumentList @('"'+$target+'"') -WorkingDirectory (Split-Path -Parent $target) -PassThru -WindowStyle Hidden
  $live=$false
  for($i=0;$i -lt 35;$i++){
    Start-Sleep -Milliseconds 350
    if($newProc.HasExited){break}
    try{$l=@(Get-NetTCPConnection -OwningProcess $newProc.Id -State Listen -ErrorAction Stop|Where-Object{$_.LocalPort -eq $listenPort -and $_.LocalAddress -eq $listenIp});if($l.Count -gt 0){$live=$true;break}}catch{}
  }
  if(-not $live){throw 'PATCHED_LISTENER_NOT_VERIFIED'}
  $phase='VERIFY_AUTHENTICATED_ROUTE';Report 'WINDOWS_PHASE=VERIFY_AUTHENTICATED_ROUTE'
  $base=Join-Path $env:USERPROFILE '.ritsu-control\local-link'
  $token=[IO.File]::ReadAllText((Join-Path $base 'device-token')).Trim()
  $url='http://'+$listenIp+':'+$listenPort+'/v1/ritsu/recover?turnId=00000000-0000-0000-0000-000000000000&tabId=main&promptSha256='+('0'*64)
  $response=Invoke-RestMethod -Uri $url -Headers @{Authorization='Bearer '+$token} -TimeoutSec 12
  if($response.ok -ne $true -or $response.state -ne 'no_server_receipt'){throw 'AUTHENTICATED_RECOVERY_ROUTE_NOT_VERIFIED'}
  # Authenticated catalog presence: 200 verified, or 503 with precise browser-unavailable reason.
  # A 404 means the app will inevitably raise IllegalStateException.
  try{
    $r=Invoke-WebRequest -Uri ('http://'+$listenIp+':'+$listenPort+'/v1/ritsu/catalog?probe=1') -Headers @{Authorization='Bearer '+$token} -UseBasicParsing -TimeoutSec 12
    $catalogCode=[int]$r.StatusCode
  }catch{
    $catalogCode=if($_.Exception.Response){[int]$_.Exception.Response.StatusCode}else{0}
  }
  if($catalogCode -ne 200){throw ('CATALOG_ROUTE_UNVERIFIED_HTTP_'+$catalogCode)}
  Report ('CATALOG_ROUTE_HTTP='+$catalogCode)
  try{
    $r=Invoke-WebRequest -Uri ('http://'+$listenIp+':'+$listenPort+'/v1/ritsu/bind') -Method POST -ContentType 'application/json' -Body '{}' -Headers @{Authorization='Bearer '+$token} -UseBasicParsing -TimeoutSec 12
    $bindCode=[int]$r.StatusCode
  }catch{
    $bindCode=if($_.Exception.Response){[int]$_.Exception.Response.StatusCode}else{0}
  }
  if($bindCode -ne 400){throw ('BIND_ROUTE_UNVERIFIED_HTTP_'+$bindCode)}
  Report 'BIND_ROUTE_INVALID_INPUT=GUARDED_400'
  Report 'RITSU_WINDOWS_PATCH=PASS'
  Report 'SERVER_RESTART=LIVE'
  Report 'READ_ONLY_RECOVERY_ROUTE=AUTHENTICATED_TEST_PASS'
  Report 'PROMPT_RESUBMITTED=NO'
  Report 'JOURNAL_REWRITTEN=NO'
  exit 0
}catch{
  Report ('WINDOWS_FAILURE_PHASE='+$phase)
  Report ('WINDOWS_FAILURE_CLASS='+$_.Exception.GetType().Name)
  if($changed -and -not $stopped -and $old){
    try{
      $restore0=Join-Path (Split-Path -Parent $target) ('.ritsu-rollback-'+[guid]::NewGuid().ToString('N')+'.mjs')
      [IO.File]::WriteAllText($restore0,$old,(New-Object Text.UTF8Encoding($false)))
      [IO.File]::Replace($restore0,$target,$null)
      Report 'WINDOWS_SOURCE_ROLLBACK=RESTORED_WITHOUT_STOP'
    }catch{Report 'WINDOWS_SOURCE_ROLLBACK=UNVERIFIED'}
  }
  if($stopped){
    try{
      if($null -ne $newProc -and -not $newProc.HasExited){Stop-Process -Id $newProc.Id -ErrorAction SilentlyContinue}
      if($changed -and $old){
        $restore=Join-Path (Split-Path -Parent $target) ('.ritsu-rollback-'+[guid]::NewGuid().ToString('N')+'.mjs')
        [IO.File]::WriteAllText($restore,$old,(New-Object Text.UTF8Encoding($false)))
        [IO.File]::Replace($restore,$target,$null)
      }
      if($listenPort -eq 19647){$env:RITSU_TAILSCALE_SERVE='1'}
      $again=Start-Process -FilePath $exe -ArgumentList @('"'+$target+'"') -WorkingDirectory (Split-Path -Parent $target) -PassThru -WindowStyle Hidden
      Start-Sleep -Seconds 2
      $list=@(Get-NetTCPConnection -OwningProcess $again.Id -State Listen -ErrorAction SilentlyContinue|Where-Object{$_.LocalPort -eq $listenPort})
      Report ('WINDOWS_ROLLBACK_LISTENER='+ $(if($list.Count){'RESTORED'}else{'NOT_VERIFIED'}))
    }catch{Report 'WINDOWS_ROLLBACK_LISTENER=ERROR'}
  }
  exit 7
}
