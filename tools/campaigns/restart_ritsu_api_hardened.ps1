# Controlled voice-service repair. User requested thorough hardening on 2026-10-22.
# Only fixed Ritsu API processes may be stopped. All credentials remain local.
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:USERPROFILE 'workspace\ritsu-faster-qwen3-tts'
$work = Join-Path $env:LOCALAPPDATA 'RitsuWarmTicketWorker'
$api = Join-Path $root 'ritsu_voice_api_warm_v1.py'
$python = Join-Path $root '.venv\Scripts\pythonw.exe'
$pythonConsole = Join-Path $root '.venv\Scripts\python.exe'
$pause = Join-Path $root 'RITSU_WARM_ASMR_MAINTENANCE'
$report = Join-Path $work 'hardened-restart-report.json'
$backup = Join-Path $work ('api-before-hardening-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.py')
$url = 'https://raw.githubusercontent.com/Valar05/home-center/5ded526665cc766d3090961bb38c164a45eaa80b/tools/campaigns/ritsu_voice_api_repertoire_v1.py'
function Record($phase,$detail) {
    [pscustomobject]@{phase=$phase;detail=$detail;backup=$backup;when=(Get-Date).ToString('o')} |
        ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath $report
}
function VoiceProcesses {
    @(Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and $_.CommandLine.Contains('ritsu_voice_api_warm_v1.py') -and
        $_.ExecutablePath -match 'pythonw\.exe$'
    })
}
$hadPause = Test-Path $pause
$replaced = $false
try {
    if(!(Test-Path $python) -or !(Test-Path $pythonConsole)){throw 'Canonical Python missing'}
    if(!(Test-Path $api)){throw 'Current Ritsu API source missing'}
    $catalog = Get-Content (Join-Path $root 'ritsu_voice_profiles.json') -Raw | ConvertFrom-Json
    foreach($name in @('normal','whisper','amused','happy','upset','somber')){
       if($catalog.profiles.$name.pitchSemitones -ne -1){throw "Pitch mismatch: $name"}
    }
    $current = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 19645 -State Listen -ErrorAction SilentlyContinue
    if(!$current){throw 'Original Ritsu API not serving localhost; refusing blind restart'}
    New-Item -ItemType File -Force -Path $pause | Out-Null
    Record 'paused' 'New ticket dispatch paused; checking replacement before stopping old API'
    $incoming = Join-Path $work 'api-replacement.new.py'
    Invoke-WebRequest -UseBasicParsing $url -OutFile $incoming
    & $pythonConsole -m py_compile $incoming
    if($LASTEXITCODE -ne 0){throw 'Replacement Python failed compilation'}
    $source = Get-Content $incoming -Raw
    if(!$source.Contains('formant=preserved') -or !$source.Contains("if model is None: state['model']='error'")){
        throw 'Replacement does not contain expected pitch and error-isolation fixes'
    }
    Copy-Item -LiteralPath $api -Destination $backup
    Record 'backed_up' 'Immutable original source retained; controlled restart beginning'
    $processes = @(VoiceProcesses)
    if($processes.Count -lt 1){throw 'No fixed Ritsu API processes identified'}
    foreach($proc in $processes){Stop-Process -Id $proc.ProcessId -Force}
    Start-Sleep -Seconds 5
    if(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 19645 -State Listen -ErrorAction SilentlyContinue){
        throw 'Voice listener remained occupied after stopping known API processes'
    }
    Copy-Item -LiteralPath $incoming -Destination $api -Force
    $replaced = $true
    $started = Start-Process -FilePath $python -ArgumentList ('"'+$api+'"') -WorkingDirectory $root -WindowStyle Hidden -PassThru
    Record 'loading' ('API restarted using canonical Python PID '+$started.Id)
    $headers = @{Authorization=('Bearer '+(Get-Content (Join-Path $root 'ritsu-api-token.txt') -Raw).Trim())}
    $ready = $false
    for($n=0;$n -lt 150;$n++){
        Start-Sleep -Seconds 2
        if($started.HasExited){throw 'Canonical API process exited during initialization'}
        try {
            $health=Invoke-RestMethod 'http://127.0.0.1:19645/v1/health' -Headers $headers -TimeoutSec 3
            if($health.model -eq 'loaded' -and !$health.error){$ready=$true;break}
            if($health.model -eq 'error'){throw ('API init error '+$health.error)}
        }catch{
            if($_.Exception.Message -like 'API init error*'){throw}
        }
    }
    if(!$ready){throw 'Canonical API did not reach loaded before deadline'}
    $owners=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 19645 -State Listen -ErrorAction SilentlyContinue)
    if($owners.Count -ne 1 -or $owners[0].OwningProcess -ne $started.Id){
        throw 'API TCP listener owned by unexpected process'
    }
    $voices=Invoke-RestMethod 'http://127.0.0.1:19645/v1/voices' -Headers $headers -TimeoutSec 6
    foreach($name in @('normal','whisper','amused','happy','upset','somber')){
        if($voices.profiles.$name.pitchSemitones -ne -1){throw ('Runtime profile mismatch '+$name)}
    }
    if(!$hadPause){Remove-Item -LiteralPath $pause -Force}
    Record 'ready' ('New canonical API loaded; owner PID '+$started.Id+'; six profiles at -1; maintenance restored')
}catch{
    $problem=$_.Exception.Message
    Record 'failed' $problem
    # Preserve the maintenance lock on error: never release stuck tickets into unknown audio.
    if(!(Test-Path $pause)){New-Item -ItemType File -Force -Path $pause | Out-Null}
    if($replaced -and (Test-Path $backup)){
        $newProcesses=@(VoiceProcesses)
        foreach($proc in $newProcesses){Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue}
        Copy-Item -LiteralPath $backup -Destination $api -Force
        Start-Process -FilePath $python -ArgumentList ('"'+$api+'"') -WorkingDirectory $root -WindowStyle Hidden
        Record 'rollback' ('Original API restored after: '+$problem)
    }
    throw
}
