param(
 [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]{1,64}$')][string]$Episode,
 [Parameter(Mandatory=$true)][ValidateRange(45,536870912)][long]$Size,
 [Parameter(Mandatory=$true)][ValidatePattern('^[A-F0-9]{64}$')][string]$Digest,
 [Parameter(Mandatory=$true)][ValidateSet('pixel-10-pro-xl-1')][string]$Device,
 [Parameter(Mandatory=$true)][ValidateSet('100.93.128.108')][string]$PeerIP,
 [switch]$Resend
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
# FileShare.None protects against two independent Cauldron operators.
$guard=[IO.File]::Open(($ledger+'.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try{
 if((Test-Path -LiteralPath $ledger) -and !$Resend){
  $old=Get-Content -LiteralPath $ledger -Raw|ConvertFrom-Json
  if($old.phase -ne 'taildrop_sent_not_verified'){throw 'Prior Taildrop outcome ambiguous; check phone before explicit drop --resend'}
  $joined=$old|ConvertTo-Json -Compress
 }else{
  $record=@{phase='taildrop_dispatch_uncertain';episodeId="$Episode";device="$Device";bytes=$Size;wavSha256="$Digest";fileName="$Episode.wav";updatedUtc=[DateTime]::UtcNow.ToString('o')}
  $record|ConvertTo-Json -Compress|Set-Content -LiteralPath $ledger -Encoding UTF8
  $output=& $exe file cp $p "${PeerIP}:"
  if($LASTEXITCODE -ne 0){throw 'Taildrop CLI send failed; check phone before explicit retry'}
  $record.phase='taildrop_sent_not_verified'
  $record.updatedUtc=[DateTime]::UtcNow.ToString('o')
  $joined=$record|ConvertTo-Json -Compress
  $joined|Set-Content -LiteralPath $ledger -Encoding UTF8
 }
}finally{$guard.Dispose()}
$bytes=[Text.Encoding]::UTF8.GetBytes($joined)
$encoded=[Convert]::ToBase64String($bytes)
$hash=([BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes))).Replace('-','')
# ConsoleHost can wrap at the remote PTY width. Use numbered 16-character frames.
[Console]::WriteLine(('JSTART:'+ $encoded.Length))
for($i=0;$i -lt $encoded.Length;$i+=16){[Console]::WriteLine(('J:{0:D5}:{1}' -f ($i/16),$encoded.Substring($i,[Math]::Min(16,$encoded.Length-$i))))}
for($i=0;$i -lt 64;$i+=16){[Console]::WriteLine(('H:{0}:{1}' -f ($i/16),$hash.Substring($i,16)))}
Write-Output 'RITSU_ASMR_REMOTE_OK=1'
