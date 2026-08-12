param(
  [string]$Endpoint = $(if ($env:VENICE_RADIO_ENDPOINT) { $env:VENICE_RADIO_ENDPOINT } else { 'https://us-central1-home-center-dclar.cloudfunctions.net/veniceRadioApi' }),
  [string]$StationId = $(if ($env:VENICE_RADIO_STATION) { $env:VENICE_RADIO_STATION } else { 'venice-asmr-primary' }),
  [string]$VoiceSeed = $env:VENICE_VOICE_SEED_WAV,
  [string]$StateDir = $(Join-Path $env:LOCALAPPDATA 'HomeCenter\venice-radio'),
  [int]$SegmentMs = 4000,
  [int]$RetentionSegments = 30,
  [int]$CacheSegments = 75,
  [int]$MaxSegments = 0
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
New-Item -ItemType Directory -Force $StateDir | Out-Null
$cache = Join-Path $StateDir 'cache'
New-Item -ItemType Directory -Force $cache | Out-Null
$log = Join-Path $StateDir 'radio.log'
$stateFile = Join-Path $StateDir 'state.json'
$stopFile = Join-Path $StateDir 'STOP'
$script:AccessToken = ''

function Log([string]$message) {
  $line = "$(Get-Date -Format o) $message"
  Add-Content -Path $log -Value $line
  Write-Output $line
}

function Get-AccessToken {
  if ($script:AccessToken) { return $script:AccessToken }
  if ($env:VENICE_RADIO_ACCESS_TOKEN) { $script:AccessToken = $env:VENICE_RADIO_ACCESS_TOKEN; return $script:AccessToken }
  $gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
  if (-not $gcloud) { throw 'gcloud unavailable and VENICE_RADIO_ACCESS_TOKEN not set' }
  $token = (& gcloud auth print-access-token 2>$null | Select-Object -First 1).Trim()
  if (-not $token) { throw 'gcloud did not return an access token' }
  $script:AccessToken = $token
  return $script:AccessToken
}

function Invoke-Radio([hashtable]$body) {
  $token = Get-AccessToken
  $headers = @{ Authorization = "Bearer $token" }
  return Invoke-RestMethod -Uri $Endpoint -Method Post -Headers $headers -ContentType 'application/json' -Body ($body | ConvertTo-Json -Depth 8 -Compress)
}

function Write-State($object) {
  $tmp = "$stateFile.tmp"
  $object | ConvertTo-Json -Depth 8 | Set-Content -Path $tmp
  Move-Item -Force $tmp $stateFile
}

function Trim-Cache {
  $files = @(Get-ChildItem $cache -File -Filter 'segment-*.wav' | Sort-Object LastWriteTime -Descending)
  if ($files.Count -gt $CacheSegments) {
    $files | Select-Object -Skip $CacheSegments | Remove-Item -Force -ErrorAction SilentlyContinue
  }
}

$ffmpeg = (Get-Command ffmpeg -ErrorAction Stop).Source
if ($VoiceSeed -and -not (Test-Path $VoiceSeed)) { Log "voice seed missing: $VoiceSeed"; $VoiceSeed = '' }
if (Test-Path $stopFile) { Remove-Item $stopFile -Force }

$begin = Invoke-Radio @{ action='radio.station.publish_begin'; stationId=$StationId; reset=$false; retentionSegments=$RetentionSegments; segmentDurationTargetMs=$SegmentMs }
$generation = [int]$begin.generation
$sequence = [int]$begin.headSequence
$publishedCount = 0
Log "station=$StationId generation=$generation head=$sequence endpoint=$Endpoint"

while (-not (Test-Path $stopFile)) {
  $started = Get-Date
  $sequence += 1
  $wav = Join-Path $cache ('segment-{0:D10}.wav' -f $sequence)
  $mode = $sequence % 12
  $freq = 118 + (($sequence * 37) % 173)
  $tapDelay = 450 + (($sequence * 233) % 2600)
  $pink = 0.009 + (($sequence % 5) * 0.0015)
  $voiceTurn = [bool]($VoiceSeed -and ($mode -eq 0 -or $mode -eq 7))

  if ($voiceTurn) {
    & $ffmpeg -hide_banner -loglevel error -y `
      -f lavfi -i "anoisesrc=color=pink:amplitude=$pink:duration=4:sample_rate=24000" `
      -i $VoiceSeed `
      -filter_complex "[0:a]lowpass=f=2600,highpass=f=80[a0];[1:a]atrim=0:4,volume=0.72,highpass=f=100,lowpass=f=7200[a1];[a0][a1]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.86" `
      -t 4 -ar 24000 -ac 1 -c:a pcm_s16le $wav
  } else {
    & $ffmpeg -hide_banner -loglevel error -y `
      -f lavfi -i "anoisesrc=color=pink:amplitude=$pink:duration=4:sample_rate=24000" `
      -f lavfi -i "sine=frequency=$freq:duration=0.055:sample_rate=24000" `
      -filter_complex "[0:a]lowpass=f=3200,highpass=f=55[a0];[1:a]volume=0.035,adelay=${tapDelay}|${tapDelay},aecho=0.7:0.22:55:0.12[a1];[a0][a1]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.80" `
      -t 4 -ar 24000 -ac 1 -c:a pcm_s16le $wav
  }
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path $wav)) { throw "ffmpeg failed for sequence $sequence" }

  $bytes = [IO.File]::ReadAllBytes($wav)
  $sha = (Get-FileHash $wav -Algorithm SHA256).Hash.ToLower()
  $result = Invoke-Radio @{
    action='radio.station.publish_segment'; stationId=$StationId; generation=$generation; sequence=$sequence;
    contentType='audio/wav'; durationMs=$SegmentMs; sha256=$sha; audioBase64=[Convert]::ToBase64String($bytes)
  }
  if (-not $result.ok) { throw "publish failed for sequence $sequence" }

  $snapshot = [ordered]@{
    status='publishing'; stationId=$StationId; generation=$generation; sequence=$sequence; sha256=$sha;
    byteCount=$bytes.Length; mode=$(if ($voiceTurn) {'voice_bed'} else {'texture'}); frequencyHz=$freq;
    tapDelayMs=$tapDelay; cacheDir=$cache; updatedAt=(Get-Date).ToUniversalTime().ToString('o')
  }
  Write-State $snapshot
  Log "published seq=$sequence mode=$($snapshot.mode) sha=$sha bytes=$($bytes.Length)"
  Trim-Cache
  $publishedCount += 1
  if ($MaxSegments -gt 0 -and $publishedCount -ge $MaxSegments) { Log "max-segments reached count=$publishedCount"; break }

  $elapsed = ((Get-Date) - $started).TotalMilliseconds
  $sleepMs = [Math]::Max(250, $SegmentMs - [int]$elapsed)
  Start-Sleep -Milliseconds $sleepMs
}

if (Test-Path $stopFile) {
  Invoke-Radio @{ action='radio.station.stop'; stationId=$StationId } | Out-Null
  Log 'station stopped by STOP file'
}
