# Native Windows firewall campaign for Ritsu Local Link.
# Fully reversible, pinned phone-only Tailscale scope, no package dependencies.
param([ValidateSet('doctor','apply','status','rollback')][string]$Mode='doctor')
$ErrorActionPreference='Stop'
$RuleName='Ritsu-LocalLink-Phone-Tailscale-19646'
$LocalIP='100.68.37.106'
$PhoneIP='100.117.17.119'
$Port=19646
$Dir=Join-Path $env:LOCALAPPDATA 'RitsuControlBridge\LocalLink'
$ReceiptPath=Join-Path $Dir 'firewall-campaign-receipt.json'
[IO.Directory]::CreateDirectory($Dir)|Out-Null
function Rule {Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue}
function Listener {
  $found=Get-NetTCPConnection -LocalAddress $LocalIP -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if(-not $found){return $false}
  $owner=Get-Process -Id $found.OwningProcess -ErrorAction SilentlyContinue
  return ($null -ne $owner -and $owner.ProcessName -eq 'node')
}
function Verified {
  $r=Rule
  if(-not $r){return $false}
  if($r.Direction -ne 'Inbound' -or $r.Action -ne 'Allow' -or $r.Enabled -ne 'True'){return $false}
  $p=$r|Get-NetFirewallPortFilter
  $a=$r|Get-NetFirewallAddressFilter
  return (($p.Protocol -eq 'TCP' -or $p.Protocol -eq 6) -and [string]$p.LocalPort -eq [string]$Port -and [string]$a.LocalAddress -eq $LocalIP -and [string]$a.RemoteAddress -eq $PhoneIP)
}
function SaveReceipt($stage,$reason){
  $object=[ordered]@{campaign='ritsu-tailnet-port-19646-v1';stage=$stage;reason=$reason;mode=$Mode;localIP=$LocalIP;remoteIP=$PhoneIP;port=$Port;rule=$RuleName;listenerVerified=[bool](Listener);ruleVerified=[bool](Verified);atUTC=(Get-Date).ToUniversalTime().ToString('o')}
  $temp=$ReceiptPath+'.tmp'
  [IO.File]::WriteAllText($temp,($object|ConvertTo-Json -Depth 3),[Text.UTF8Encoding]::new($false))
  Move-Item -Force $temp $ReceiptPath
  $object|ConvertTo-Json -Compress
}
if($Mode -eq 'status'){SaveReceipt 'observed' 'read_only';exit 0}
if($Mode -eq 'doctor'){
  if(-not (Listener)){SaveReceipt 'blocked' 'Ritsu Node listener absent';exit 2}
  if((Rule) -and -not (Verified)){SaveReceipt 'blocked' 'existing_named_rule_conflicts';exit 3}
  SaveReceipt 'doctor_pass' 'safe_to_apply_phone_scoped_rule';exit 0
}
if($Mode -eq 'rollback'){
  if(Rule){
    if(-not (Verified)){SaveReceipt 'blocked' 'rule_identity_mismatch';exit 4}
    Remove-NetFirewallRule -Name $RuleName -ErrorAction Stop
  }
  SaveReceipt 'rolled_back' 'campaign_owned_rule_only';exit 0
}
if(-not (Listener)){SaveReceipt 'blocked' 'refused_open_without_listener';exit 5}
if(Rule){
  if(-not (Verified)){SaveReceipt 'blocked' 'refused_rule_overwrite';exit 6}
  SaveReceipt 'already_applied' 'exact_rule_unchanged';exit 0
}
New-NetFirewallRule -Name $RuleName -DisplayName 'Ritsu Local Link (owner phone only)' -Direction Inbound -Action Allow -Enabled True -Profile Any -Protocol TCP -LocalPort $Port -LocalAddress $LocalIP -RemoteAddress $PhoneIP -Description 'Only the pinned owner phone Tailscale IPv4 may enter the local Ritsu SSE service.'|Out-Null
if(-not (Verified)){SaveReceipt 'blocked' 'created_rule_failed_readback';exit 7}
SaveReceipt 'applied' 'single_phone_direct_tailscale_tcp_only'
