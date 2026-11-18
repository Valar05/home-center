param(
 [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]{1,64}$')][string]$Episode,
 [Parameter(Mandatory=$true)][ValidateRange(45,536870912)][long]$Size,
 [Parameter(Mandatory=$true)][ValidatePattern('^[A-F0-9]{64}$')][string]$Digest,
 [Parameter(Mandatory=$true)][ValidateSet('pixel-10-pro-xl-1')][string]$Device,
 [Parameter(Mandatory=$true)][ValidateSet('100.93.128.108')][string]$PeerIP,
 [switch]$Resend,
 [switch]$Worker
)

$ErrorActionPreference='Stop'
$p=Join-Path $env:LOCALAPPDATA "RitsuASMR\runs\$Episode\${Episode}.wav"
if(!(Test-Path -LiteralPath $p)){throw 'Rendered WAV missing'}
if((Get-Item -LiteralPath $p).Length -ne $Size -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ne "$Digest"){throw 'Rendered WAV identity mismatch'}
$cli=Get-Command tailscale.exe -ErrorAction SilentlyContinue
if($cli){$exe=$cli.Source}else{$exe=Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'}
if(!(Test-Path -LiteralPath $exe)){throw 'Tailscale CLI unavailable'}
$raw=& $exe status --json
if($LASTEXITCODE -ne 0){throw 'Tailscale status failed'}
$ts=($raw -join [Environment]::NewLine)|ConvertFrom-Json
if($ts.BackendState -ne 'Running'){throw 'Tailscale is not running'}
$peers=@($ts.Peer.PSObject.Properties.Value|Where-Object {
 $_.ID -ceq 'nC5TZJzU3e11CNTRL' -and
 $_.OS -ieq 'android' -and
 (([string]$_.DNSName -split '\.')[0] -ieq $Device) -and
 $_.TailscaleIPs -contains $PeerIP
})
if($peers.Count -ne 1){throw 'Expected exact Pixel name and tailnet IP not found; refusing to send'}
$peer=$peers[0]
if(!$peer.Online){throw 'Expected Pixel is offline'}
$ledger=Join-Path (Split-Path -Parent $p) "taildrop-$Digest-$PeerIP.json"
$taskName="RitsuASMR-Taildrop-$Episode"
$log=$ledger+'.log'
if(!$Worker){
 $t=Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue
 if($t){
  $a=@($t.Actions)
  if($a.Count -ne 1 -or $a[0].Arguments -notmatch '[\\/]RitsuASMR[\\/]code[\\/][A-Fa-f0-9]{64}[\\/]ritsu_asmr_taildrop[.]ps1"' -or $a[0].Arguments -notmatch (' -Episode '+[regex]::Escape($Episode)+' ') -or $a[0].Arguments -notmatch ' -Worker(?: |$)'){throw 'TAIL_DROP_TASK_IDENTITY_MISMATCH'}
  if([string]$t.State -in @('Running','Queued')){throw 'TAIL_DROP_TASK_ALREADY_ACTIVE; use drop-status'}
 }
 $g=[IO.File]::Open(($ledger+'.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 $launch=$false
 try{
  $old=$null
  if(Test-Path -LiteralPath $ledger){$old=Get-Content -LiteralPath $ledger -Raw|ConvertFrom-Json}
  if($old -and !$Resend){
   if($old.phase -eq 'taildrop_sent_not_verified'){$joined=$old|ConvertTo-Json -Compress}
   else{throw 'Prior Taildrop outcome ambiguous; check phone before explicit drop --resend'}
  }else{
   if($old){Copy-Item -LiteralPath $ledger -Destination ($ledger+'.'+[guid]::NewGuid().ToString('N')+'.history')}
   $record=@{phase='taildrop_scheduled';episodeId=$Episode;device=$Device;bytes=$Size;wavSha256=$Digest;fileName="$Episode.wav";updatedUtc=[DateTime]::UtcNow.ToString('o');taskName=$taskName}
   $arg='-NoLogo -NoProfile -NonInteractive -File "'+$PSCommandPath+'" -Episode '+$Episode+' -Size '+$Size+' -Digest '+$Digest+' -Device '+$Device+' -PeerIP '+$PeerIP+' -Worker'
   $action=New-ScheduledTaskAction -Execute (Join-Path $PSHOME 'powershell.exe') -Argument $arg
   $principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
   $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
   Register-ScheduledTask -TaskName $taskName -TaskPath '\' -Action $action -Principal $principal -Settings $settings -Force|Out-Null
   $joined=$record|ConvertTo-Json -Compress
   $joined|Set-Content -LiteralPath $ledger -Encoding UTF8
   $launch=$true
  }
 }finally{$g.Dispose()}
 if($launch){Start-ScheduledTask -TaskName $taskName -TaskPath '\'}
}else{
 $guard=[IO.File]::Open(($ledger+'.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 try{
  $record=Get-Content -LiteralPath $ledger -Raw|ConvertFrom-Json
  if($record.phase -ne 'taildrop_scheduled' -or $record.wavSha256 -ne $Digest -or $record.device -ne $Device -or $record.bytes -ne $Size -or $record.episodeId -ne $Episode){throw 'TAIL_DROP_COMMISSION_MISMATCH'}
  $record.phase='taildrop_dispatch_uncertain';$record.updatedUtc=[DateTime]::UtcNow.ToString('o')
  $record|ConvertTo-Json -Compress|Set-Content -LiteralPath $ledger -Encoding UTF8
  Add-Content -LiteralPath $log -Value ([DateTime]::UtcNow.ToString('o')+' SEND_STARTED')
  try{
   & $exe file cp $p ($PeerIP+':') 2>&1 | ForEach-Object {Add-Content -LiteralPath $log -Value ([string]$_)}
   $rc=$LASTEXITCODE
   $record|Add-Member -NotePropertyName exitCode -NotePropertyValue $rc -Force
   if($rc -ne 0){throw "Taildrop CLI exit $rc"}
   $record.phase='taildrop_sent_not_verified'
  }catch{
   $record.phase='taildrop_failed'
   $record|Add-Member -NotePropertyName lastError -NotePropertyValue ($_.Exception.Message) -Force
  }finally{
   $record.updatedUtc=[DateTime]::UtcNow.ToString('o')
   $record|ConvertTo-Json -Compress|Set-Content -LiteralPath $ledger -Encoding UTF8
   Add-Content -LiteralPath $log -Value ($record.updatedUtc+' '+$record.phase)
  }
  if($record.phase -ne 'taildrop_sent_not_verified'){exit 2}
  exit 0
 }finally{$guard.Dispose()}
}
$bytes=[Text.Encoding]::UTF8.GetBytes($joined)
$encoded=[Convert]::ToBase64String($bytes)
$hash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
# ConsoleHost can wrap at the remote PTY width. Use numbered 16-character frames.
[Console]::WriteLine(('JSTART:'+ $encoded.Length))
for($i=0;$i -lt $encoded.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$encoded.Substring($i,[Math]::Min(16,$encoded.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$hash.Substring($i,16)))}
Write-Output 'RITSU_ASMR_REMOTE_OK=1'
