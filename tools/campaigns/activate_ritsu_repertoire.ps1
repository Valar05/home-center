# User authorized THECAULDRON voice cutover after ASMR ended, 2026-10-22.
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:USERPROFILE 'workspace\ritsu-faster-qwen3-tts'
$stage = Join-Path $env:LOCALAPPDATA 'RitsuWarmTicketWorker\staged-repertoire'
$workerRoot = Join-Path $env:LOCALAPPDATA 'RitsuWarmTicketWorker'
$report = Join-Path $workerRoot 'activation-report.json'
$pause = Join-Path $root 'RITSU_WARM_ASMR_MAINTENANCE'
$python = Join-Path $root '.venv\Scripts\pythonw.exe'
$pythonConsole = Join-Path $root '.venv\Scripts\python.exe'
$api = Join-Path $root 'ritsu_voice_api_warm_v1.py'
$sender = Join-Path $root 'ritsu_say.py'
$catalog = Join-Path $root 'ritsu_voice_profiles.json'
$workerFile = Join-Path $workerRoot 'worker.py'
$backup = Join-Path $workerRoot ('repertoire-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$originals = @($api,$sender,$catalog,$workerFile)
function Report($phase,$detail) {
  [pscustomobject]@{phase=$phase;detail=$detail;time=(Get-Date).ToString('o');backup=$backup} | ConvertTo-Json | Set-Content -Encoding UTF8 $report
}
function ProcessMatches($regex) {
  @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match $regex) })
}
try {
  Report 'preflight' 'Starting transactional activation'
  foreach($f in @($python,$pythonConsole,$api,$sender,$workerFile,
    (Join-Path $stage 'ritsu_voice_api_repertoire_v1.py'),
    (Join-Path $stage 'ritsu_say_repertoire_v1.py'),
    (Join-Path $stage 'ritsu_voice_profiles.json'),
    (Join-Path $stage 'ritsu_warm_ticket_worker.py'))) {
      if(!(Test-Path -LiteralPath $f -PathType Leaf)){throw "Missing required file: $f"}
  }
  $profiles = Get-Content (Join-Path $stage 'ritsu_voice_profiles.json') -Raw | ConvertFrom-Json
  foreach($n in @('normal','whisper','amused','happy','upset','somber')) {
    if($profiles.profiles.$n.pitchSemitones -ne -1){throw "Pitch setting not -1 for $n"}
    $ref = Join-Path (Join-Path $env:USERPROFILE 'workspace\ritsu-expresso-auditions') $profiles.profiles.$n.referenceFile
    if(!(Test-Path -LiteralPath $ref -PathType Leaf)){throw "Missing audition WAV: $n"}
  }
  & $pythonConsole -c 'import librosa,numpy,soundfile,faster_qwen3_tts'
  if($LASTEXITCODE -ne 0){throw 'Python dependencies unavailable'}
  New-Item -ItemType Directory -Force -Path $backup | Out-Null
  foreach($file in $originals) {
    if(Test-Path -LiteralPath $file){Copy-Item -LiteralPath $file -Destination (Join-Path $backup (Split-Path $file -Leaf)) -Force}
  }
  Report 'backed_up' 'Originals saved; stopping only explicitly identified Ritsu services'
  $oldApi = ProcessMatches 'ritsu_voice_api_warm_v1\.py'
  $oldWorker = ProcessMatches 'RitsuWarmTicketWorker\\worker\.py'
  foreach($p in @($oldWorker)+@($oldApi)) {
    if($p -and $p.ProcessId -ne $PID){Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop}
  }
  Start-Sleep -Seconds 4
  $listeners = @(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 19645 -State Listen -ErrorAction SilentlyContinue)
  if($listeners.Count -gt 0){throw 'Local Ritsu API listener still occupied; not replacing process'}
  Copy-Item (Join-Path $stage 'ritsu_voice_api_repertoire_v1.py') $api -Force
  Copy-Item (Join-Path $stage 'ritsu_say_repertoire_v1.py') $sender -Force
  Copy-Item (Join-Path $stage 'ritsu_voice_profiles.json') $catalog -Force
  Copy-Item (Join-Path $stage 'ritsu_warm_ticket_worker.py') $workerFile -Force
  foreach($f in @($api,$sender,$workerFile)){ & $pythonConsole -m py_compile $f; if($LASTEXITCODE -ne 0){throw "Compile failed: $f"} }
  Report 'installed' 'Repertoire files installed; starting API'
  Start-Process -FilePath $python -ArgumentList ('"' + $api + '"') -WorkingDirectory $root -WindowStyle Hidden
  $token = (Get-Content (Join-Path $root 'ritsu-api-token.txt') -Raw).Trim()
  $headers = @{Authorization=('Bearer '+$token)}
  $healthy = $false
  for($i=0;$i -lt 120;$i++){
    Start-Sleep -Seconds 2
    try {
      $h = Invoke-RestMethod -Uri 'http://127.0.0.1:19645/v1/health' -Headers $headers -TimeoutSec 3
      if($h.model -eq 'loaded' -and !$h.error){$healthy=$true;break}
      if($h.model -eq 'error'){throw ('Model API error: '+$h.error)}
    }catch { if($_.Exception.Message -match 'Model API error:'){throw} }
  }
  if(!$healthy){throw 'New Qwen API did not report loaded before timeout'}
  $voices = Invoke-RestMethod -Uri 'http://127.0.0.1:19645/v1/voices' -Headers $headers -TimeoutSec 5
  foreach($n in @('normal','whisper','amused','happy','upset','somber')){
    if($voices.profiles.$n.pitchSemitones -ne -1){throw "Local API pitch mismatch: $n"}
  }
  Report 'api_ready' 'Qwen API loaded; local six-profile endpoint matches cloud'
  if(Test-Path $pause){Remove-Item -LiteralPath $pause -Force}
  $workerPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
  Start-Process -FilePath $workerPython -ArgumentList ('"'+$workerFile+'"') -WindowStyle Hidden -WorkingDirectory $workerRoot -RedirectStandardOutput (Join-Path $workerRoot 'worker.stdout.log') -RedirectStandardError (Join-Path $workerRoot 'worker.stderr.log')
  Report 'activated' 'Local API and registered ticket worker started; maintenance cleared; awaiting phone HEARD'
}catch{
  $problem = $_.Exception.Message
  Report 'failure' $problem
  # Roll back from immutable backups if a copy or restart failed. Preserve maintenance.
  if(!(Test-Path $pause)){New-Item -ItemType File -Path $pause -Force | Out-Null}
  if(Test-Path $backup){
    foreach($f in $originals){
      $saved = Join-Path $backup (Split-Path $f -Leaf)
      if(Test-Path $saved){Copy-Item -LiteralPath $saved -Destination $f -Force}
    }
  }
  throw
}
