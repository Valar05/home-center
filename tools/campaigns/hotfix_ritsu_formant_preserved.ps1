$ErrorActionPreference='Stop'
$root=Join-Path $env:USERPROFILE 'workspace\ritsu-faster-qwen3-tts'
$workerRoot=Join-Path $env:LOCALAPPDATA 'RitsuWarmTicketWorker'
$pause=Join-Path $root 'RITSU_WARM_ASMR_MAINTENANCE'
$stage=Join-Path $workerRoot 'staged-repertoire\ritsu_voice_api_repertoire_v1.py'
$active=Join-Path $root 'ritsu_voice_api_warm_v1.py'
$python=Join-Path $root '.venv\Scripts\python.exe'
$pythonw=Join-Path $root '.venv\Scripts\pythonw.exe'
$report=Join-Path $workerRoot 'formant-hotfix-report.json'
$backup=Join-Path $workerRoot ('formant-hotfix-backup-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.py')
function State($phase,$detail){
 [pscustomobject]@{phase=$phase;detail=$detail;backup=$backup;at=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content -Encoding UTF8 -LiteralPath $report
}
try {
 if(!(Test-Path $pause)){throw 'Ticket maintenance marker must be present before cutover'}
 if(!(Test-Path $stage)){throw 'Staged formant-preserving API missing'}
 if(!(Test-Path $active)){throw 'Active API missing'}
 & $python -m py_compile $stage
 if($LASTEXITCODE -ne 0){throw 'Candidate syntax invalid'}
 $candidate=Get-Content -Raw -LiteralPath $stage
 if($candidate -notmatch 'rubberband=pitch=' -or $candidate -notmatch 'formant=preserved' -or $candidate -match 'librosa.effects.pitch_shift\('){throw 'Candidate is not formant-preserving'}
 Copy-Item -LiteralPath $active -Destination $backup -Force
 State 'backed_up' 'Stopped voice ticket generation, prior active Python script backed up'
 $procs=@(Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -and $_.CommandLine -match 'ritsu_voice_api_warm_v1\.py'})
 foreach($p in $procs){Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop}
 Start-Sleep -Seconds 3
 $listeners=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 19645 -State Listen -ErrorAction SilentlyContinue)
 if($listeners.Count -gt 0){throw 'Voice service still bound to port 19645'}
 Copy-Item -LiteralPath $stage -Destination $active -Force
 State 'installed' 'New formant-preserving API file installed'
 Start-Process -FilePath $pythonw -ArgumentList ('"'+$active+'"') -WorkingDirectory $root -WindowStyle Hidden
 State 'started' 'New API launched; checking health'
 $token=(Get-Content -LiteralPath (Join-Path $root 'ritsu-api-token.txt') -Raw).Trim()
 $headers=@{Authorization=('Bearer '+$token)}
 for($i=0;$i -lt 180;$i++){
  Start-Sleep -Seconds 2
  try {
   $h=Invoke-RestMethod 'http://127.0.0.1:19645/v1/health' -Headers $headers -TimeoutSec 3
   if($h.model -eq 'loaded' -and !$h.error){
    $v=Invoke-RestMethod 'http://127.0.0.1:19645/v1/voices' -Headers $headers -TimeoutSec 3
    foreach($n in @('normal','whisper','amused','happy','upset','somber')){if($v.profiles.$n.pitchSemitones -ne -1){throw ('Incorrect pitch for '+$n)}}
    State 'ready_paused' 'API model loaded, all six profiles -1; ticket maintenance remains on pending audible quality test'
    exit 0
   }
   if($h.model -eq 'error'){throw ('API_MODEL_ERROR '+$h.error)}
  }catch{if($_.Exception.Message -match 'API_MODEL_ERROR|Incorrect pitch'){throw}}
 }
 throw 'Timeout waiting for new API model'
}catch{
 State 'failure' $_.Exception.Message
 if(Test-Path $backup){
  $running=@(Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -and $_.CommandLine -match 'ritsu_voice_api_warm_v1\.py'})
  foreach($p in $running){Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue}
  Copy-Item -LiteralPath $backup -Destination $active -Force
  Start-Process -FilePath $pythonw -ArgumentList ('"'+$active+'"') -WorkingDirectory $root -WindowStyle Hidden
 }
 throw
}
