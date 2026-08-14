[CmdletBinding()]
param(
    [string]$HomeCenterDir = (Join-Path $env:LOCALAPPDATA 'HomeCenter'),
    [string]$TaskName = 'Fortress Swarm Continuity Lights',
    [switch]$Open
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$utf8 = [System.Text.UTF8Encoding]::new($false)
$templatePath = Join-Path $HomeCenterDir 'swarm-failover-lights.template.html'
$outputPath = Join-Path $HomeCenterDir 'swarm-failover-lights.html'
$statePath = Join-Path $HomeCenterDir 'swarm-failover-runtime.json'
$receiptPath = Join-Path $HomeCenterDir 'swarm-failover-scheduler-receipts.jsonl'

New-Item -ItemType Directory -Force -Path $HomeCenterDir | Out-Null

function Write-ReceiptLine {
    param([Parameter(Mandatory)][System.Collections.IDictionary]$Receipt)
    $line = $Receipt | ConvertTo-Json -Depth 8 -Compress
    [System.IO.File]::AppendAllText($receiptPath, $line + [Environment]::NewLine, $utf8)
    return $line
}

try {
    if (-not (Test-Path -LiteralPath $templatePath)) {
        throw "Template missing: $templatePath"
    }

    $priorSequence = 0
    if (Test-Path -LiteralPath $statePath) {
        try {
            $prior = [System.IO.File]::ReadAllText($statePath, $utf8) | ConvertFrom-Json
            if ($null -ne $prior.sequence) {
                $priorSequence = [int]$prior.sequence
            }
        }
        catch {
            $priorSequence = 0
        }
    }

    $sequence = $priorSequence + 1
    $pulseUtc = (Get-Date).ToUniversalTime().ToString('o')
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    $taskState = if ($null -ne $task) { 'SCHEDULED' } else { 'DIRECT_RUN' }

    $template = [System.IO.File]::ReadAllText($templatePath, $utf8)
    $rendered = $template.Replace('__PULSE_UTC__', $pulseUtc)
    $rendered = $rendered.Replace('__PULSE_SEQUENCE__', [string]$sequence)
    $rendered = $rendered.Replace('__TASK_STATE__', $taskState)

    if ($rendered -match '__PULSE_|__TASK_STATE__') {
        throw 'Unresolved scheduler placeholders remain in rendered HTML.'
    }

    $temporaryPath = $outputPath + '.tmp'
    [System.IO.File]::WriteAllText($temporaryPath, $rendered, $utf8)
    Move-Item -LiteralPath $temporaryPath -Destination $outputPath -Force

    $htmlSha256 = (Get-FileHash -LiteralPath $outputPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $htmlBytes = (Get-Item -LiteralPath $outputPath).Length

    $runtime = [ordered]@{
        schema = 'fortress.swarm-failover-runtime.v1'
        sequence = $sequence
        pulseUtc = $pulseUtc
        taskName = $TaskName
        taskState = $taskState
        htmlPath = $outputPath
        htmlSha256 = $htmlSha256
        htmlBytes = $htmlBytes
        phoneState = 'dead_and_charging'
        continuityState = 'surviving_bodies_active'
        countdown = $false
    }
    [System.IO.File]::WriteAllText($statePath, ($runtime | ConvertTo-Json -Depth 8), $utf8)

    $receipt = [ordered]@{
        schema = 'fortress.scheduler-receipt.v1'
        ok = $true
        sequence = $sequence
        pulseUtc = $pulseUtc
        taskName = $TaskName
        taskState = $taskState
        htmlPath = $outputPath
        htmlSha256 = $htmlSha256
        htmlBytes = $htmlBytes
        phoneState = 'dead_and_charging'
        continuityState = 'surviving_bodies_active'
    }
    $line = Write-ReceiptLine -Receipt $receipt

    if ($Open) {
        $chromeCandidates = @(@(
            (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
            (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe')
        ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) })
        if ($chromeCandidates.Count -gt 0) {
            $url = 'file:///' + (($outputPath -replace '\\', '/') -replace ' ', '%20')
            Start-Process -FilePath $chromeCandidates[0] -ArgumentList @('--new-window', $url) | Out-Null
        }
        else {
            Start-Process -FilePath $outputPath | Out-Null
        }
    }

    Write-Output $line
    exit 0
}
catch {
    $failure = [ordered]@{
        schema = 'fortress.scheduler-receipt.v1'
        ok = $false
        pulseUtc = (Get-Date).ToUniversalTime().ToString('o')
        taskName = $TaskName
        error = $_.Exception.Message
        phoneState = 'dead_and_charging'
        continuityState = 'surviving_bodies_active_with_scheduler_wound'
    }
    $line = Write-ReceiptLine -Receipt $failure
    Write-Output $line
    exit 1
}
