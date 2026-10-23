# Ritsu Pocket: replace only the verified legacy sentence-splitting sender.
# No voice model, worker, relay, phone receiver, cloud config or token changes.
# The replacement is one complete agent-authored input -> one Pocket job -> WAV.
# Fail-closed over the existing /v1/speak 450-character max.
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$SourceCommit = 'e12eab25ad6fb679ff52d78a2295f408750af2fb'
$ExpectedOldSender = '2922EFE848AAD961C96282EB491E4090FCE9DD0891E67CD01FBE1D357AA24B3D'
$ExpectedWorker = 'C72A0AC06CB5806D7A4F07A9FD8DE1966979B72CC09EA8E9109C0F157EF43166'
$ExpectedPocket = 'FA679DF591572219AAD33EF958221F2E3A68B2AA7D93AFCCED295968DB5C3B08'
$Root = Join-Path $env:USERPROFILE 'workspace\ritsu-faster-qwen3-tts'
$Sender = Join-Path $Root 'ritsu_say.py'
$Worker = Join-Path $env:LOCALAPPDATA 'RitsuWarmTicketWorker\worker.py'
$Pocket = Join-Path $env:USERPROFILE 'Documents\Codex\Venice\PocketTTS\ritsu_pocket_repertoire_server_v2.py'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$TokenFile = Join-Path $Root 'ritsu-api-token.txt'
$BackupRoot = Join-Path $env:LOCALAPPDATA 'RitsuWarmTicketWorker\sender-backups'
$Stage = Join-Path $Root ('.ritsu-no-split-' + [guid]::NewGuid().ToString('N'))
$OldHash = ''
$NewHash = ''
$Backup = ''
$Phase = 'preflight'
try {
    foreach($file in @($Sender,$Worker,$Pocket,$Python,$TokenFile)){
        if(-not (Test-Path -LiteralPath $file -PathType Leaf)){throw "MISSING_DEPENDENCY"}
    }
    $OldHash = (Get-FileHash -LiteralPath $Sender -Algorithm SHA256).Hash
    $WorkerHash = (Get-FileHash -LiteralPath $Worker -Algorithm SHA256).Hash
    $PocketHash = (Get-FileHash -LiteralPath $Pocket -Algorithm SHA256).Hash
    if($OldHash -ne $ExpectedOldSender){throw 'LIVE_SENDER_DIVERGED_RECONCILE'}
    if($WorkerHash -ne $ExpectedWorker){throw 'LIVE_WORKER_DIVERGED_RECONCILE'}
    if($PocketHash -ne $ExpectedPocket){throw 'LIVE_POCKET_DIVERGED_RECONCILE'}
    $token = (Get-Content -LiteralPath $TokenFile -Raw).Trim()
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:10205/v1/health' -Headers @{Authorization="Bearer $token"} -TimeoutSec 6
    $token = $null
    if($health.model -ne 'loaded' -or [int]$health.queue -ne 0) {throw 'POCKET_NOT_IDLE'}
    $liveSender = @(Get-CimInstance Win32_Process |
        Where-Object {$_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match 'ritsu_say\.py'})
    if($liveSender.Count -gt 0){throw 'SENDER_CURRENTLY_RUNNING'}
    $Phase='fetch-pinned-candidate'
    New-Item -ItemType Directory -Path $Stage -ErrorAction Stop | Out-Null
    $base='https://raw.githubusercontent.com/Valar05/home-center/'+$SourceCommit+'/tools/campaigns/ritsu_pocket_v2_deployed/'
    foreach($file in @('ritsu_say.py','test_ritsu_whole_text.py')){
        Invoke-WebRequest -Uri ($base+$file) -OutFile (Join-Path $Stage $file) -TimeoutSec 20 -UseBasicParsing
    }
    $candidate=Join-Path $Stage 'ritsu_say.py'
    $test=Join-Path $Stage 'test_ritsu_whole_text.py'
    $source=Get-Content -LiteralPath $candidate -Raw
    if($source -notmatch 'MAX_TEXT_CHARS\s*=\s*450' -or
       $source -notmatch 'deliver_whole' -or
       $source -match 'sentence_chunks|def chunks\(|re\.split\('){
       throw 'NO_SPLIT_CONTRACT_MISMATCH'
    }
    $Phase='validate-unit-test'
    & $Python -B $test 2>&1 | ForEach-Object { Write-Output "TEST|$_" }
    if($LASTEXITCODE -ne 0){throw 'WHOLE_TEXT_TEST_FAILED'}
    $NewHash=(Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash
    Write-Output "PREFLIGHT|old_sha=$OldHash|candidate_sha=$NewHash|pocket_queue=0|one_input_one_WAV=TRUE"
    if($DryRun) {Write-Output 'RITSU_SENDER_DRY_RUN_PASS=1';exit 0}
    $Phase='recheck-live'
    if((Get-FileHash -LiteralPath $Sender -Algorithm SHA256).Hash -ne $OldHash) {
        throw 'SENDER_CHANGED_DURING_PREFLIGHT'
    }
    $liveSender = @(Get-CimInstance Win32_Process |
        Where-Object {$_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match 'ritsu_say\.py'})
    if($liveSender.Count -gt 0){throw 'SENDER_STARTED_DURING_PREFLIGHT'}
    $Phase='atomic-install'
    New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
    $Backup=Join-Path $BackupRoot ("ritsu_say."+(Get-Date -Format 'yyyyMMddTHHmmss')+".pre-no-split.py")
    $sameDirStage = Join-Path $Root ('.ritsu_say.candidate.'+[guid]::NewGuid().ToString('N')+'.py')
    Copy-Item -LiteralPath $candidate -Destination $sameDirStage
    [System.IO.File]::Replace($sameDirStage,$Sender,$Backup)
    $readback=(Get-FileHash -LiteralPath $Sender -Algorithm SHA256).Hash
    if($readback -ne $NewHash){throw 'CUTOVER_READBACK_HASH_MISMATCH'}
    if((Get-FileHash -LiteralPath $Backup -Algorithm SHA256).Hash -ne $OldHash){
        throw 'CUTOVER_BACKUP_HASH_MISMATCH'
    }
    Write-Output 'RITSU_NO_SPLIT_SENDER_INSTALLED=1'
    Write-Output "LIVE_SHA256=$readback"
    Write-Output "BACKUP=$Backup"
    Write-Output 'AGENT_AUTHORED_TEXT_LIMIT=450'
    Write-Output 'SENDER_SIDE_SENTENCE_SPLITTING=OFF'
    Write-Output 'WORKER_RESTARTED=NO'
    Write-Output 'POCKET_RESTARTED=NO'
    Write-Output 'RELAY_RESTARTED=NO'
    Write-Output 'PHONE_RECEIVER_MODIFIED=NO'
    Write-Output 'HEARD=unverified'
} catch {
    Write-Output ('RITSU_NO_SPLIT_SENDER_CUTOVER_FAILED=1|phase='+$Phase+'|error='+$_.Exception.Message)
    if($Phase -eq 'atomic-install' -and $Backup -and (Test-Path -LiteralPath $Backup)) {
        try {
            $restore=Join-Path $Root ('.ritsu_say.restore.'+[guid]::NewGuid().ToString('N')+'.py')
            Copy-Item -LiteralPath $Backup -Destination $restore
            [System.IO.File]::Replace($restore,$Sender,$null)
            Write-Output ('ROLLBACK_HASH='+(Get-FileHash -LiteralPath $Sender -Algorithm SHA256).Hash)
        }catch{Write-Output ('ROLLBACK_FAILED|'+$_.Exception.Message)}
    }
    exit 2
}finally{
    if(Test-Path -LiteralPath $Stage){Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue}
}
