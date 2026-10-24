#requires -Version 5.1
<#
Ritsu end-to-end campaign. Author and review in Git BEFORE final execution.
Plan/Status/Receipts/Stop are not builds or installs.
Apply requires a pinned Git SHA and one isolated Windows scheduled task.
#>
param(
 [ValidateSet('Plan','Apply','Status','Receipts','Stop')][string]$Mode='Plan',
 [string]$Revision='',
 [string]$SourceRepo='C:\Users\dclar\workspace\home-center-ritsu-e2e'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Name='ritsu-chat-voice-e2e'
$Task='HomeCenter-RitsuE2E-PhoneGateway'
$Base=Join-Path $env:LOCALAPPDATA 'HomeCenter\RitsuE2E'
$Root=Join-Path $Base 'campaign'
$Latest=Join-Path $Root 'latest.json'
$History=Join-Path $Root 'history.jsonl'
$Stage='preflight'
$RunId=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+([guid]::NewGuid().ToString('N').Substring(0,8))
function Say($s){Write-Output ('RITSU_CAMPAIGN '+$s)}
function State {if(Test-Path $Latest){return (Get-Content $Latest -Raw|ConvertFrom-Json)}return $null}
function Receipt($stage,$status,$detail,$sha='') {
 New-Item -ItemType Directory -Path $Root -Force|Out-Null
 $rec=[ordered]@{schema=1;campaign=$Name;runId=$RunId;atUtc=[DateTime]::UtcNow.ToString('o');revision=$sha;stage=$stage;status=$status;detail=$detail}
 [IO.File]::AppendAllText($History,($rec|ConvertTo-Json -Compress)+[Environment]::NewLine)
 $tmp=$Latest+'.'+([guid]::NewGuid().ToString('N'))+'.tmp'
 try {[IO.File]::WriteAllText($tmp,($rec|ConvertTo-Json -Depth 5));Move-Item $tmp $Latest -Force}
 finally {if(Test-Path $tmp){Remove-Item $tmp -Force}}
 Say ('stage='+$stage+' state='+$status+' sha='+$sha+' detail='+$detail)
}
function Need($p){if(-not(Test-Path -LiteralPath $p)){throw ('missing_required_file '+$p)}}
function Listen($port){return @((Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)).Count -gt 0}
function TaskObject {return (Get-ScheduledTask -TaskName $Task -ErrorAction SilentlyContinue)}
function Owned {
 $t=TaskObject
 if(-not $t){return $false}
 $a=$t.Actions|Select-Object -First 1
 return ($a.Execute -match 'powershell' -and $a.Arguments -like ('*'+(Join-Path $Root 'launch.ps1')+'*'))
}
function Git([string[]]$arguments){
 $result=& git -C $SourceRepo @arguments 2>&1
 if($LASTEXITCODE -ne 0){throw ('git_step_failed '+$arguments[0])}
 return $result
}
function Tailnet {
 $bin='C:\Program Files\Tailscale\tailscale.exe'
 Need $bin
 $ip=(& $bin ip -4|Select-Object -First 1)
 if($LASTEXITCODE -ne 0 -or -not $ip){throw 'tailnet_unavailable'}
 $ip=$ip.Trim();$n=$ip.Split('.')
 if($n.Length -ne 4 -or $n[0] -ne '100' -or ([int]$n[1]) -lt 64 -or ([int]$n[1]) -gt 127){throw 'invalid_tailnet_ip'}
 return $ip
}
try {
 switch($Mode){
 'Plan' {
  Say ('Git-first, one final Apply at exact SHA '+$Revision)
  Say ('Text ingress 19646; canonical audio 19643 and Serve 19645 untouched')
  Say ('Isolated only: '+$Base)
  Say ('Previous state '+(State|ConvertTo-Json -Compress))
  break
 }
 'Status' {
  Say ('Last receipt '+(State|ConvertTo-Json -Compress))
  Say ('Task '+(TaskObject|Select-Object TaskName,State|ConvertTo-Json -Compress))
  Say ('Ingress19646='+(Listen 19646)+' canonicalAudio19643='+(Listen 19643))
  break
 }
 'Receipts' {if(Test-Path $History){Get-Content $History -Tail 40}else{Say 'No receipts'};break}
 'Stop' {
  if(-not(Owned)){throw 'no_owned_gateway_task'}
  Stop-ScheduledTask -TaskName $Task -ErrorAction Stop
  Receipt 'gateway' 'stopped' 'explicit_stop'
  break
 }
 'Apply' {
  if($Revision -cnotmatch '^[0-9a-f]{40}$'){throw 'exact_40_character_git_sha_required'}
  Need (Join-Path $SourceRepo '.git')
  foreach($file in @('relay-capability.txt','phone-capability.txt','extension\manifest.json')){Need (Join-Path $Base $file)}
  $voice='C:\Users\dclar\Documents\Codex\Venice\PocketTTS\embodiment_campaign'
  Need (Join-Path $voice 'relay-token.txt')
  if(-not(Listen 19643) -or -not(Listen 9235)){throw 'canonical_19643_or_isolated_9235_offline'}
  if((Listen 19646) -and -not(Owned)){throw 'existing_19646_listener_unowned'}
  $ip=Tailnet
  $Stage='git'
  Receipt $Stage 'started' 'fetch_exact_sha_into_isolated_checkout' $Revision
  $env:GIT_LFS_SKIP_SMUDGE='1'
  Git @('fetch','origin',$Revision)|Out-Null
  $resolved=Git @('rev-parse','--verify',($Revision+'^{commit}'))
  if(($resolved|Select-Object -Last 1).Trim() -cne $Revision){throw 'git_revision_readback_failed'}
  $fromGit=(& git -C $SourceRepo show ($Revision+':tools/campaigns/ritsu-e2e-campaign.ps1')) -join [Environment]::NewLine
  if($LASTEXITCODE -ne 0){throw 'pinned_script_missing'}
  $here=[IO.File]::ReadAllText($PSCommandPath)
  $normal={param($v) $v.Replace([Environment]::NewLine,([char]10).ToString()).TrimEnd([char]13,[char]10)}
  if((& $normal $here) -cne (& $normal $fromGit)){throw 'running_script_not_from_pinned_commit'}
  $work=Join-Path $Root ('source-'+$Revision.Substring(0,12))
  if(-not(Test-Path $work)){Git @('-c','filter.lfs.smudge=','-c','filter.lfs.required=false','worktree','add','--detach',$work,$Revision)|Out-Null}
  $head=(& git -C $work rev-parse HEAD)
  if($LASTEXITCODE -ne 0 -or $head.Trim() -cne $Revision -or (& git -C $work status --porcelain)){throw 'isolated_checkout_mismatch_or_dirty'}
  $contract=Join-Path $work 'tools\campaigns\ritsu-e2e-contract.json'
  Need $contract
  if((Get-Content $contract -Raw|ConvertFrom-Json).campaignId -cne $Name){throw 'wrong_campaign_contract'}
  Receipt $Stage 'verified' 'exact_git_sha_and_disposable_worktree' $Revision
  $Stage='tests'
  $tests=@('ritsu-chat-relay.test.mjs','ritsu-android-gateway.test.mjs','ritsu-voice-return.test.mjs')|ForEach-Object{Join-Path $work ('browser-porch\'+$_)}
  foreach($f in $tests){Need $f}
  & node --test @($tests)|Out-Null
  if($LASTEXITCODE -ne 0){throw 'node_gateway_browser_voice_tests_failed'}
  Receipt $Stage 'verified' 'browser_gateway_voice_tests_passed' $Revision
  $Stage='extension'
  $backup=Join-Path $Root ('extension-backup-'+$Revision.Substring(0,12))
  New-Item -ItemType Directory -Path $backup -Force|Out-Null
  foreach($file in @('service-worker.js','sidepanel.html','throne-panel.mjs')){
   $src=Join-Path $work ('browser-porch\extension\'+$file)
   $dst=Join-Path $Base ('extension\'+$file)
   Need $src;Need $dst
   $hash=(Get-FileHash $src -Algorithm SHA256).Hash
   if((Get-FileHash $dst -Algorithm SHA256).Hash -ne $hash){
    if(-not(Test-Path (Join-Path $backup $file))){Copy-Item $dst (Join-Path $backup $file)}
    Copy-Item $src $dst -Force
    if((Get-FileHash $dst -Algorithm SHA256).Hash -ne $hash){throw ('extension_hash_failed '+$file)}
   }
  }
  Receipt $Stage 'verified' 'three_files_hash_verified;Chrome_reload_needed_if_active' $Revision
  $Stage='gateway'
  if((TaskObject) -and -not(Owned)){throw 'task_name_collision'}
  $old=State
  if((Listen 19646) -and $old -and $old.revision -and $old.revision -cne $Revision){throw 'older_gateway_requires_explicit_stop'}
  $launch=Join-Path $Root 'launch.ps1'
  $entry=Join-Path $work 'browser-porch\ritsu-android-gateway-runner.mjs'
  Need $entry
  $lines=@(
   '$ErrorActionPreference="Stop"',
   ('$root='+"'"+$Base.Replace("'","''")+"'"),
   '$env:HOME_CENTER_RITSU_PHONE_CAPABILITY_FILE=Join-Path $root "phone-capability.txt"',
   '$env:HOME_CENTER_CHROMIUM_THRONE_CAPABILITY=[IO.File]::ReadAllText((Join-Path $root "relay-capability.txt")).Trim()',
   '$env:HOME_CENTER_RITSU_NAMESPACE="ritsu-phone-campaign-20261023-v01"',
   '$env:HOME_CENTER_RITSU_CONTROL_SESSION="ritsu-phone-control-20261023-v01"',
   '$env:HOME_CENTER_RITSU_DIALOGUE_SESSION="ritsu-phone-dialogue-20261023-v01"',
   '$env:HOME_CENTER_RITSU_STATE_DIR=Join-Path $root "coordinator-state"',
   '$env:HOME_CENTER_RITSU_RELAY_URL="http://127.0.0.1:9235/v1/throne"',
   '$env:HOME_CENTER_RITSU_PHONE_PORT="19646"',
   ('$env:HOME_CENTER_RITSU_TAILNET_IPV4='+"'"+$ip+"'"),
   ('$env:HOME_CENTER_RITSU_CANONICAL_RELAY_ROOT='+"'"+$voice+"'"),
   ('& node '+"'"+$entry.Replace("'","''")+"'"+' *> '+"'"+(Join-Path $Root 'gateway.log').Replace("'","''")+"'")
  )
  [IO.File]::WriteAllLines($launch,$lines,[Text.Encoding]::UTF8)
  if(-not(TaskObject)){
   $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$launch+'"')
   $trigger=New-ScheduledTaskTrigger -Once -At ((Get-Date).AddHours(12))
   $settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Days 1)
   $principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
   Register-ScheduledTask -TaskName $Task -Action $action -Trigger $trigger -Settings $settings -Principal $principal -ErrorAction Stop|Out-Null
  }
  if(-not(Owned)){throw 'scheduled_task_readback_failed'}
  if(-not(Listen 19646)){Start-ScheduledTask -TaskName $Task -ErrorAction Stop}
  Receipt $Stage 'started' 'isolated_scheduler_started_no_shell_stdio' $Revision
  $Stage='health'
  $ready=$false
  for($n=0;$n -lt 12;$n++){
   $l=Get-NetTCPConnection -State Listen -LocalPort 19646 -ErrorAction SilentlyContinue|Select-Object -First 1
   if($l -and $l.LocalAddress -eq $ip){$ready=$true;break}
   Start-Sleep -Seconds 2
  }
  if(-not $ready){throw 'tailnet_listener_19646_not_confirmed'}
  $url='http://'+$ip+':19646/v1/ritsu/health'
  $token=[IO.File]::ReadAllText((Join-Path $Base 'phone-capability.txt')).Trim()
  $good=Invoke-WebRequest -UseBasicParsing -Uri $url -Headers @{Authorization=('Bearer '+$token)} -TimeoutSec 6
  if([int]$good.StatusCode -ne 200){throw 'authenticated_health_not_200'}
  $rejected=$false
  try{Invoke-WebRequest -UseBasicParsing -Uri $url -Headers @{Authorization='Bearer deliberately-invalid'} -TimeoutSec 6|Out-Null}
  catch{if($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 401){$rejected=$true}else{throw}}
  if(-not $rejected){throw 'bad_token_not_rejected'}
  Receipt $Stage 'transport_verified' '19646_200_valid_401_invalid;phone_chat_and_heard_not_verified' $Revision
  break
 }
 }
}catch{
 $safe=$_.Exception.Message -replace 'Bearer\s+\S+','Bearer_[redacted]'
 if($safe.Length -gt 200){$safe=$safe.Substring(0,200)}
 try{Receipt $Stage 'blocked' $safe $Revision}catch{Say ('error='+$safe)}
 throw
}
