# Canonical Windows Pocket TTS relay sender. Text arrives on STDIN, never argv.
# Existing sender law: exact phone Tailscale relay /enqueue at port 19643.
# Do not use Phone Hands, Android shell, Chrome TTS or any fallback.
$ErrorActionPreference='Stop'
$root=$env:HOME_CENTER_RITSU_CANONICAL_RELAY_ROOT
if([string]::IsNullOrWhiteSpace($root) -or !(Test-Path -LiteralPath $root)){throw 'canonical_relay_root_required'}
$tokenPath=Join-Path $root 'relay-token.txt'
if(!(Test-Path -LiteralPath $tokenPath)){throw 'canonical_relay_secret_missing'}
$data=[Console]::In.ReadToEnd()|ConvertFrom-Json
$text=[string]$data.text
if([string]::IsNullOrWhiteSpace($text) -or $text.Length -gt 600){throw 'bounded_voice_chunk_required'}
$ip=(& 'C:\Program Files\Tailscale\tailscale.exe' ip -4|Select-Object -First 1).Trim()
if($ip -notmatch '^100\.(\d+)\.(\d+)\.(\d+)$'){throw 'canonical_tailnet_not_available'}
$token=[IO.File]::ReadAllText($tokenPath).Trim()
$payload=@{text=$text;character='ritsu'}|ConvertTo-Json -Compress
$reply=Invoke-RestMethod -Uri ('http://'+$ip+':19643/enqueue') -Method Post -Headers @{Authorization=('Bearer '+$token)} -ContentType 'application/json' -Body $payload -TimeoutSec 45
$clip=''
foreach($key in @('clipId','clip_id','id','audioId','audio_id')){
  if($reply.PSObject.Properties[$key]){$clip=[string]$reply.$key;break}
}
if($clip -notmatch '^[A-Za-z0-9_.:-]{8,100}$'){throw 'canonical_relay_missing_verified_clip_id'}
Write-Output (@{ok=$true;relayId=$clip;boundary='enqueued_not_heard'}|ConvertTo-Json -Compress)
