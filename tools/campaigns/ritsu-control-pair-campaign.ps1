#requires -Version 5.1
<#
Ritsu Control pairing CAMPAIGN (THECAULDRON Windows PowerShell 5.1).
Stable modes: Plan, Apply, Resume, Worker, Status, Receipts, Follow, Stop, Canary.
Does not change 19646, install an APK, or assert the phone is paired.
A separate, local masked GUI displays the existing phone-only credential.
#>
[CmdletBinding()]
param(
 [ValidateSet('Plan','Apply','Resume','Worker','Status','Receipts','Follow','Stop','Canary')]
 [string]$Mode='Plan',
 [string]$Revision='',
 [string]$RunId='',
 [string]$TokenFile='',
 [string]$TailnetHost='100.68.37.106',
 [switch]$TestWorker
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$base=Join-Path $env:LOCALAPPDATA 'HomeCenter\RitsuControlPairCampaign'
$latest=Join-Path $base 'latest.json'
$history=Join-Path $base 'history.jsonl'
$owner=Join-Path $base 'owner.json'
$stopFile=Join-Path $base 'stop.json'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$helper=Join-Path $PSScriptRoot 'ritsu-control-pair.ps1'
$script:reason='unspecified_failure'
$script:phase='preflight'
$script:rid=$RunId

function Need([bool]$ok,[string]$errorCode) {
 if(-not $ok){$script:reason=$errorCode;throw 'PAIR_CAMPAIGN_GATE'}
}
function Ensure-Base{[void](New-Item -ItemType Directory -Path $base -Force)}
function Read-Json([string]$name){
 if(-not(Test-Path -LiteralPath $name -PathType Leaf)){return $null}
 return (Get-Content -LiteralPath $name -Raw | ConvertFrom-Json)
}
function Store-Json([string]$name,$value){
 Ensure-Base
 $tmp=$name+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
 try{
  [IO.File]::WriteAllText($tmp,(ConvertTo-Json -InputObject $value -Compress -Depth 6),[Text.Encoding]::UTF8)
  Move-Item -LiteralPath $tmp -Destination $name -Force
 }finally{if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force}}
}
function Receipt([string]$phase,[string]$state,[string]$detail){
 Ensure-Base
 $row=[ordered]@{schema=1;campaign='ritsu-control-pair';runId=$script:rid;
   atUtc=[DateTime]::UtcNow.ToString('o');revision=$Revision;phase=$phase;state=$state;
   detail=$detail;phonePairedVerified=$false;secretInReceipt=$false}
 $line=ConvertTo-Json -InputObject $row -Compress
 [IO.File]::AppendAllText($history,$line+[Environment]::NewLine,[Text.Encoding]::UTF8)
 Store-Json $latest $row
}
function Emit([string]$message){
 $safe='RITSU_PAIR '+$message
 Write-Output $safe
 if(Get-Command termux-clipboard-set -ErrorAction SilentlyContinue){
  try{$safe | termux-clipboard-set}catch{Write-Output 'RITSU_PAIR CLIPBOARD_UNAVAILABLE'}
 }elseif(Get-Command Set-Clipboard -ErrorAction SilentlyContinue){
  try{Set-Clipboard -Value $safe}catch{Write-Output 'RITSU_PAIR CLIPBOARD_UNAVAILABLE'}
 }else{Write-Output 'RITSU_PAIR CLIPBOARD_UNAVAILABLE'}
}
function Pinned {
 Need ($Revision -cmatch '^[a-f0-9]{40}$') 'exact_git_revision_required'
 Need (Test-Path -LiteralPath $helper -PathType Leaf) 'local_pairing_ui_helper_missing'
 $head=(& git -C $root rev-parse HEAD 2>$null)
 Need ($LASTEXITCODE -eq 0 -and [string]$head -ceq $Revision) 'pinned_checkout_mismatch'
 $dirty=@(& git -C $root status --porcelain --untracked-files=no 2>$null)
 Need ($LASTEXITCODE -eq 0 -and $dirty.Count -eq 0) 'tracked_checkout_modified'
}
function Is-OwnedAlive($p){
 if($null -eq $p -or -not $p.pid){return $false}
 try{
  $proc=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$p.pid) -ErrorAction Stop
  if($null -eq $proc){return $false}
  $line=[string]$proc.CommandLine
  return ($line.Contains('ritsu-control-pair-campaign.ps1') -and
    $line.Contains('-Mode Worker') -and $line.Contains([string]$p.runId))
 }catch{return $false}
}
function Token-Location{
 if($TokenFile){return $TokenFile}
 if($env:HOME_CENTER_RITSU_PHONE_CAPABILITY_FILE){return $env:HOME_CENTER_RITSU_PHONE_CAPABILITY_FILE}
 $known=Join-Path $env:LOCALAPPDATA 'HomeCenter\RitsuE2E\phone-capability.txt'
 if(Test-Path -LiteralPath $known -PathType Leaf){return $known}
 return ''
}
function Status{
 $s=Read-Json $latest
 $p=Read-Json $owner
 $state=if($s){$s.state}else{'not_started'}
 $phase=if($s){$s.phase}else{'none'}
 $rid=if($s){$s.runId}else{'none'}
 $age=if($s){[math]::Max(0,[math]::Round(([DateTime]::UtcNow-[DateTime]::Parse([string]$s.atUtc)).TotalSeconds))}else{-1}
 Emit ('state='+$state+' phase='+$phase+' runId='+$rid+
  ' workerAlive='+(Is-OwnedAlive $p)+' lastActionAgeSec='+$age+
  ' stopLatch='+(Test-Path $stopFile)+
  ' phonePaired=UNVERIFIED receipts='+$history)
}
function Start-Run([bool]$resume){
 Pinned
 Ensure-Base
 $prev=Read-Json $owner
 if(Is-OwnedAlive $prev){Status;return}
 if(Test-Path -LiteralPath $stopFile){
   Need $resume 'run_resume_required_after_stop'
   Remove-Item -LiteralPath $stopFile -Force
 }
 $script:rid='pair-'+([guid]::NewGuid().ToString('N').Substring(0,16))
 $job=[ordered]@{runId=$script:rid;revision=$Revision;host=$TailnetHost;
   tokenFile=Token-Location;createdUtc=[DateTime]::UtcNow.ToString('o')}
 Store-Json (Join-Path $base ('job-'+$script:rid+'.json')) $job
 Receipt 'queued' 'queued' 'operator_commission_persisted_before_spawn'
 $params='-NoProfile -STA -ExecutionPolicy Bypass -File "'+$PSCommandPath+'" -Mode Worker -Revision '+$Revision+' -RunId '+$script:rid
 $child=Start-Process -FilePath 'powershell.exe' -ArgumentList $params -WindowStyle Hidden -PassThru
 Need ($null -ne $child -and $child.Id -gt 0) 'detached_worker_spawn_failed'
 Store-Json $owner ([ordered]@{runId=$script:rid;pid=$child.Id;revision=$Revision})
 Emit ('QUEUED runId='+$script:rid+' pid='+$child.Id+
  ' controls=Status,Receipts,Follow,Stop,Resume. This returns immediately.')
}
function Worker{
 Pinned
 Need ($RunId -match '^pair-[a-f0-9]{16}$') 'invalid_run_id'
 $job=Read-Json (Join-Path $base ('job-'+$RunId+'.json'))
 Need ($null -ne $job -and $job.runId -ceq $RunId -and $job.revision -ceq $Revision) 'job_not_committed'
 Need (-not(Test-Path -LiteralPath $stopFile)) 'owner_stopped'
 $script:rid=$RunId
 $script:phase='gateway_preflight'
 Receipt $script:phase 'running' 'isolated_worker_started'
 if($TestWorker){
  while(-not(Test-Path -LiteralPath $stopFile)){Start-Sleep -Milliseconds 400}
  return
 }
 $file=[string]$job.tokenFile
 if(-not [string]::IsNullOrWhiteSpace($file)){
  Need (Test-Path -LiteralPath $file -PathType Leaf) 'phone_token_file_missing'
 }
 $script:phase='owner_pairing'
 Receipt $script:phase 'awaiting_owner' 'choose_existing_token_file_if_needed_then_check_private_gateway'
 # Existing helper checks the token against the existing Tailscale listener.
 # The helper never prints or copies the credential. Its GUI is local to Windows.
 & $helper -Mode Show -TokenFile $file -TailnetHost ([string]$job.host) | Out-Null
 Receipt 'device_verification' 'awaiting_device_verification' 'local_dialog_closed_phone_connection_not_observed'
}
function Stop-Run{
 $p=Read-Json $owner
 if($p){$script:rid=[string]$p.runId}
 Store-Json $stopFile ([ordered]@{runId=$script:rid;atUtc=[DateTime]::UtcNow.ToString('o')})
 if(Is-OwnedAlive $p){
  $id=[int]$p.pid
  try{Stop-Process -Id $id -ErrorAction Stop}catch{}
  for($i=0;$i -lt 8 -and (Is-OwnedAlive $p);$i++){Start-Sleep -Milliseconds 250}
  if(Is-OwnedAlive $p){& taskkill.exe /PID $id /T /F | Out-Null}
  Need (-not(Is-OwnedAlive $p)) 'worker_process_tree_survived_stop'
 }
 Receipt 'stop' 'stopped' 'owned_worker_stopped_no_unowned_process_touched'
 Emit ('STOPPED runId='+$script:rid+' resume_with=Resume')
}
function Canary{
 Pinned
 Ensure-Base
 Need (-not(Is-OwnedAlive (Read-Json $owner))) 'existing_worker_active'
 if(Test-Path $stopFile){Remove-Item $stopFile -Force}
 $script:rid='pair-'+([guid]::NewGuid().ToString('N').Substring(0,16))
 Store-Json (Join-Path $base ('job-'+$script:rid+'.json')) ([ordered]@{
  runId=$script:rid;revision=$Revision;host=$TailnetHost;tokenFile='';createdUtc=[DateTime]::UtcNow.ToString('o')})
 Receipt 'canary' 'queued' 'no_token_no_browser_no_phone'
 $params='-NoProfile -STA -ExecutionPolicy Bypass -File "'+$PSCommandPath+'" -Mode Worker -Revision '+$Revision+' -RunId '+$script:rid+' -TestWorker'
 $child=Start-Process -FilePath 'powershell.exe' -ArgumentList $params -WindowStyle Hidden -PassThru
 Store-Json $owner ([ordered]@{runId=$script:rid;pid=$child.Id;revision=$Revision})
 $alive=$false
 for($i=0;$i -lt 15;$i++){
  if(Is-OwnedAlive (Read-Json $owner)){$alive=$true;break}
  Start-Sleep -Milliseconds 300
 }
 Need $alive 'canary_worker_not_detached'
 Stop-Run
 Need (-not(Is-OwnedAlive (Read-Json $owner))) 'canary_worker_not_stopped'
 if(Test-Path -LiteralPath $stopFile){Remove-Item -LiteralPath $stopFile -Force}
 Receipt 'canary' 'canary_passed' 'detached_process_survived_launcher_then_stopped_out_of_band'
 Emit ('CANARY_PASS runId='+$script:rid+' phoneUntouched=true independentStop=true')
}
try{
 switch($Mode){
  'Plan'{
   Emit ('PLAN source='+$PSCommandPath+' endpoint=http://'+$TailnetHost+':19646')
   Emit 'CONTRACT existing_token_only; authenticated_private_health; local_masked_dialog; no_gateway_restart; no_phone_mutation'
   Emit ('STATE='+$base+' MODES=Plan,Apply,Resume,Status,Receipts,Follow,Stop,Canary')
  }
  'Status'{Status}
  'Receipts'{if(Test-Path $history){Get-Content -LiteralPath $history -Tail 20}else{Emit 'NO_RECEIPTS'}}
  'Follow'{
    Emit ('FOLLOW '+$history+' Ctrl-C_detaches_only')
    if(Test-Path $history){Get-Content -LiteralPath $history -Tail 20 -Wait}else{Emit 'NO_RECEIPTS'}
  }
  'Apply'{Start-Run $false}
  'Resume'{Start-Run $true}
  'Worker'{Worker}
  'Stop'{Stop-Run}
  'Canary'{Canary}
 }
}catch{
 if(@('Apply','Resume','Worker','Stop','Canary') -contains $Mode){
  Receipt $script:phase 'blocked' $script:reason
 }
 Emit ('BLOCKED code='+$script:reason+' phase='+$script:phase+' pairing_not_claimed')
 exit 1
}
