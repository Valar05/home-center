[CmdletBinding()]
param(
    [ValidateSet('Run','Worker','Status','Stop','Doctor','Follow','DispatchInitial')]
    [string]$Action = 'Run'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Repo = 'Valar05/home-center'
$PrNumber = 351
$Branch = 'campaign/vanguard-overlay-resurrection'
$RequestMarker = '<!-- VANGUARD_THRONE_REQUEST -->'
$ReceiptMarker = '<!-- VANGUARD_THRONE_RECEIPT -->'
$RelayBase = 'http://127.0.0.1:9234/v1/throne'
$Root = if ($env:HOME_CENTER_VANGUARD_OVERLAY_THRONE_STATE) {
    $env:HOME_CENTER_VANGUARD_OVERLAY_THRONE_STATE
} else {
    Join-Path $env:LOCALAPPDATA 'HomeCenter\VanguardOverlayCampaign'
}
$CapabilityFile = if ($env:HOME_CENTER_CHROMIUM_THRONE_CAPABILITY_FILE) {
    $env:HOME_CENTER_CHROMIUM_THRONE_CAPABILITY_FILE
} else {
    Join-Path $env:LOCALAPPDATA 'HomeCenter\ChromiumThrone\relay-capability.txt'
}
$History = Join-Path $Root 'throne-history.jsonl'
$Latest = Join-Path $Root 'throne-latest.json'
$PidFile = Join-Path $Root 'throne-worker.pid'
$StopFile = Join-Path $Root 'STOP'
$FollowCursor = Join-Path $Root 'follow.cursor'
$ScriptPath = $MyInvocation.MyCommand.Path

New-Item -ItemType Directory -Force -Path $Root | Out-Null

function Get-NowMs {
    return [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
}

function Write-State {
    param(
        [Parameter(Mandatory=$true)][string]$Phase,
        [Parameter(Mandatory=$true)][string]$Status,
        [Parameter(Mandatory=$true)][string]$Detail,
        [hashtable]$Extra = @{}
    )
    $row = [ordered]@{
        schema = 'vanguard-overlay-throne-campaign-v1'
        campaign = 'VANGUARD // OVERLAY RESURRECTION'
        organ = 'Chromium Throne / THECAULDRON'
        phase = $Phase
        status = $Status
        detail = $Detail
        atMs = Get-NowMs
        repo = $Repo
        pr = $PrNumber
        branch = $Branch
        requested = $true
        freeTabTransportObserved = $false
        androidImplemented = $false
        phoneDeployed = $false
        accepted = $false
    }
    foreach ($key in $Extra.Keys) { $row[$key] = $Extra[$key] }
    $json = $row | ConvertTo-Json -Depth 30 -Compress
    Add-Content -LiteralPath $History -Value $json -Encoding UTF8
    $tmp = "$Latest.part"
    $row | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $tmp -Encoding UTF8
    Move-Item -Force -LiteralPath $tmp -Destination $Latest
    Write-Output $json
}

function Test-GhAuth {
    try {
        & gh auth status *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Invoke-GhJson {
    param([Parameter(Mandatory=$true)][string[]]$Arguments)
    $text = & gh api @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "gh api failed: $($text -join "`n")" }
    $raw = ($text -join "`n").Trim()
    if (-not $raw) { return $null }
    return $raw | ConvertFrom-Json -Depth 50
}

function Invoke-GhRaw {
    param([Parameter(Mandatory=$true)][string[]]$Arguments)
    $text = & gh api @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "gh api failed: $($text -join "`n")" }
    return ($text -join "`n")
}

function Get-BranchHead {
    $branch = Invoke-GhJson @("repos/$Repo/branches/$Branch")
    return [string]$branch.commit.sha
}

function Get-Comments {
    $rows = Invoke-GhJson @("repos/$Repo/issues/$PrNumber/comments?per_page=100")
    if ($null -eq $rows) { return @() }
    return @($rows)
}

function ConvertFrom-MarkerJson {
    param([string]$Body, [string]$Marker)
    if ([string]::IsNullOrWhiteSpace($Body) -or -not $Body.Contains($Marker)) { return $null }
    $tail = $Body.Substring($Body.IndexOf($Marker) + $Marker.Length).Trim()
    if ($tail.StartsWith('```json')) { $tail = $tail.Substring(7) }
    elseif ($tail.StartsWith('```')) { $tail = $tail.Substring(3) }
    $fence = $tail.IndexOf('```')
    if ($fence -ge 0) { $tail = $tail.Substring(0, $fence) }
    try { return ($tail.Trim() | ConvertFrom-Json -Depth 60) } catch { return $null }
}

function Add-RemoteComment {
    param([Parameter(Mandatory=$true)][string]$Body)
    $payload = Join-Path $Root ("comment-{0}.json" -f ([guid]::NewGuid().ToString('N')))
    try {
        @{body=$Body} | ConvertTo-Json -Depth 30 -Compress | Set-Content -LiteralPath $payload -Encoding UTF8
        return Invoke-GhJson @('--method','POST',"repos/$Repo/issues/$PrNumber/comments",'--input',$payload)
    } finally {
        Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $payload
    }
}

function Get-Mailbox {
    $requests = @{}
    $receipts = @{}
    foreach ($comment in (Get-Comments)) {
        $body = [string]$comment.body
        $request = ConvertFrom-MarkerJson -Body $body -Marker $RequestMarker
        if ($null -ne $request -and $request.commandId) {
            $requests[[string]$request.commandId] = [pscustomobject]@{ envelope=$request; comment=$comment }
        }
        $receipt = ConvertFrom-MarkerJson -Body $body -Marker $ReceiptMarker
        if ($null -ne $receipt -and $receipt.commandId) {
            $key = [string]$receipt.commandId
            if (-not $receipts.ContainsKey($key) -or [int64]$comment.id -gt [int64]$receipts[$key].comment.id) {
                $receipts[$key] = [pscustomobject]@{ envelope=$receipt; comment=$comment }
            }
        }
    }
    return [pscustomobject]@{ requests=$requests; receipts=$receipts }
}

function Get-Capability {
    if (-not (Test-Path -LiteralPath $CapabilityFile -PathType Leaf)) {
        throw "THRONE_CAPABILITY_FILE_MISSING: $CapabilityFile"
    }
    $cap = (Get-Content -LiteralPath $CapabilityFile -Raw).Trim()
    if ($cap.Length -lt 32) { throw 'THRONE_CAPABILITY_TOO_SHORT' }
    return $cap
}

function Invoke-Relay {
    param(
        [Parameter(Mandatory=$true)][ValidateSet('GET','POST')][string]$Method,
        [Parameter(Mandatory=$true)][string]$Path,
        [object]$Body = $null,
        [int]$TimeoutSec = 30
    )
    $cap = Get-Capability
    $headers = @{Authorization="Bearer $cap"}
    $uri = "$RelayBase/$Path"
    if ($Method -eq 'GET') {
        return Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -TimeoutSec $TimeoutSec
    }
    $json = if ($null -eq $Body) { '{}' } else { $Body | ConvertTo-Json -Depth 60 -Compress }
    return Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -ContentType 'application/json' -Body $json -TimeoutSec $TimeoutSec
}

function Get-RelayCommand {
    param([string]$CommandId)
    $status = Invoke-Relay -Method GET -Path 'status' -TimeoutSec 10
    foreach ($row in @($status.commands)) {
        if ([string]$row.commandId -eq $CommandId) { return $row }
    }
    return $null
}

function Post-Receipt {
    param(
        [Parameter(Mandatory=$true)][object]$Request,
        [Parameter(Mandatory=$true)][string]$State,
        [object]$Result = $null,
        [string]$Detail = ''
    )
    $head = ''
    try { $head = Get-BranchHead } catch {}
    $receipt = [ordered]@{
        schema = 'vanguard-throne-receipt-v1'
        campaign = 'VANGUARD // OVERLAY RESURRECTION'
        transport = 'THECAULDRON Chromium Throne local relay'
        commandId = [string]$Request.commandId
        stage = [string]$Request.stage
        state = $State
        detail = $Detail
        throneRelay = $RelayBase
        sourceHeadAtRequest = [string]$Request.sourceHeadAtRequest
        sourceHeadObserved = $head
        result = $Result
        atMs = Get-NowMs
        truthBoundary = if ($State -in @('completed','failed','cancelled')) {
            'This proves Chromium Throne relay terminal state and the remote branch head observed afterward. It does not prove Android build, phone deployment, physical microphone behavior, or Drew acceptance.'
        } else {
            'This proves only that THECAULDRON submitted or observed the command in Chromium Throne. It is not completion evidence.'
        }
    }
    $body = $ReceiptMarker + "`n```json`n" + ($receipt | ConvertTo-Json -Depth 60) + "`n```"
    [void](Add-RemoteComment -Body $body)
    return $receipt
}

function Get-CommissionRaw {
    return Invoke-GhRaw @('-H','Accept: application/vnd.github.raw+json',"repos/$Repo/contents/campaigns/vanguard-overlay-resurrection/WORKER_COMMISSION.md?ref=$Branch")
}

function Get-Sha256Text {
    param([string]$Text)
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return ([BitConverter]::ToString($hash)).Replace('-','').ToLowerInvariant()
}

function Ensure-InitialRequest {
    $commission = Get-CommissionRaw
    $digest = Get-Sha256Text $commission
    $head = Get-BranchHead
    $commandId = "vanguard-overlay-initial-throne-$($digest.Substring(0,8))-$($head.Substring(0,8))"
    $mailbox = Get-Mailbox
    if ($mailbox.requests.ContainsKey($commandId)) {
        Write-State -Phase 'initial-request' -Status 'already-present' -Detail 'Initial free-tab request already exists in the durable PR mailbox.' -Extra @{commandId=$commandId; sourceHead=$head}
        return $commandId
    }
    $command = [ordered]@{
        commandId = $commandId
        action = 'swarm.enqueue'
        source = 'vanguard-overlay-throne-desktop'
        createdAt = [DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
        jobs = @([ordered]@{
            jobId = "vanguard-overlay-initial-$($digest.Substring(0,10))"
            commission = $commission.Substring(0, [Math]::Min(31900, $commission.Length))
            context = 'VANGUARD // OVERLAY RESURRECTION. Initial free-tab implementation round. Read the remote campaign branch and both architecture receipts. Preserve the one-service/one-heartbeat design, bounded transient retention, Ritsu default, Adam exclusion, and evidence boundaries. Push the SAME campaign/vanguard-overlay-resurrection branch. Phone deployment belongs to the phone runner.'
        })
    }
    $envelope = [ordered]@{
        schema = 'vanguard-throne-request-v1'
        campaign = 'VANGUARD // OVERLAY RESURRECTION'
        transport = 'github-pr-mailbox'
        repo = $Repo
        pr = $PrNumber
        branch = $Branch
        stage = 'initial-source'
        attempt = 1
        commandId = $commandId
        sourceHeadAtRequest = $head
        commissionSha256 = $digest
        issues = @('Implement the commissioned resurrection against current branch source; this is the initial free-tab round.')
        command = $command
        requestedAtMs = Get-NowMs
        truthBoundary = 'This durable request is not proof that Chromium Throne accepted or executed it.'
    }
    $body = $RequestMarker + "`n```json`n" + ($envelope | ConvertTo-Json -Depth 60) + "`n```"
    $comment = Add-RemoteComment -Body $body
    Write-State -Phase 'initial-request' -Status 'posted' -Detail 'Initial implementation request persisted in PR #351 mailbox.' -Extra @{commandId=$commandId; commentUrl=[string]$comment.html_url; sourceHead=$head}
    return $commandId
}

function Process-Request {
    param([Parameter(Mandatory=$true)][object]$Request)
    $commandId = [string]$Request.commandId
    if (-not $Request.command) {
        [void](Post-Receipt -Request $Request -State 'failed' -Detail 'MAILBOX_COMMAND_PAYLOAD_MISSING')
        return
    }

    # POST is idempotent by commandId in the real relay. This deliberately repairs
    # relay restarts or desktop-runner crashes without creating a second logical job.
    try {
        $submitted = Invoke-Relay -Method POST -Path 'command' -Body $Request.command -TimeoutSec 20
        [void](Post-Receipt -Request $Request -State ([string]$submitted.state) -Result $submitted -Detail 'Command submitted/idempotently re-observed at the real local Chromium Throne relay.')
        Write-State -Phase 'throne-dispatch' -Status 'submitted' -Detail 'Durable mailbox request reached the real Chromium Throne localhost relay.' -Extra @{commandId=$commandId; stage=[string]$Request.stage; freeTabTransportObserved=$true}
    } catch {
        Write-State -Phase 'throne-dispatch' -Status 'retrying' -Detail $_.Exception.Message -Extra @{commandId=$commandId; stage=[string]$Request.stage}
        return
    }

    $deadline = [DateTimeOffset]::UtcNow.AddMinutes(45)
    while ([DateTimeOffset]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath $StopFile)) {
        try {
            $row = Get-RelayCommand -CommandId $commandId
            if ($null -eq $row) {
                Start-Sleep -Seconds 3
                continue
            }
            $state = [string]$row.state
            if ($state -in @('completed','failed','cancelled')) {
                [void](Post-Receipt -Request $Request -State $state -Result $row.result -Detail 'Chromium Throne relay reached a terminal command state.')
                Write-State -Phase 'throne-worker' -Status $state -Detail 'Free-tab command reached terminal relay state and receipt was persisted remotely.' -Extra @{commandId=$commandId; stage=[string]$Request.stage; freeTabTransportObserved=$true}
                return
            }
        } catch {
            Write-State -Phase 'throne-worker' -Status 'poll-retry' -Detail $_.Exception.Message -Extra @{commandId=$commandId}
        }
        Start-Sleep -Seconds 5
    }
    if (Test-Path -LiteralPath $StopFile) {
        try { [void](Invoke-Relay -Method POST -Path 'cancel' -Body @{commandId=$commandId} -TimeoutSec 10) } catch {}
        [void](Post-Receipt -Request $Request -State 'cancelled' -Detail 'Desktop campaign STOP requested while command was active.')
        return
    }
    [void](Post-Receipt -Request $Request -State 'failed' -Detail 'THRONE_COMMAND_TERMINAL_TIMEOUT_45_MIN')
}

function Worker-Loop {
    Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $StopFile
    Set-Content -LiteralPath $PidFile -Value $PID -Encoding ASCII
    Write-State -Phase 'worker' -Status 'running' -Detail 'THECAULDRON runner is watching the durable PR mailbox and actuating only the real local Chromium Throne relay.' -Extra @{pid=$PID}
    $backoff = 2
    while (-not (Test-Path -LiteralPath $StopFile)) {
        try {
            if (-not (Test-GhAuth)) { throw 'GH_AUTH_UNAVAILABLE' }
            [void](Get-Capability)
            [void](Invoke-Relay -Method GET -Path 'status' -TimeoutSec 8)
            $mailbox = Get-Mailbox
            $didWork = $false
            foreach ($entry in $mailbox.requests.GetEnumerator() | Sort-Object { [string]$_.Key }) {
                $request = $entry.Value.envelope
                $commandId = [string]$request.commandId
                $receipt = if ($mailbox.receipts.ContainsKey($commandId)) { $mailbox.receipts[$commandId].envelope } else { $null }
                if ($null -ne $receipt -and [string]$receipt.state -in @('completed','failed','cancelled')) { continue }
                Process-Request -Request $request
                $didWork = $true
                break
            }
            $backoff = 2
            if (-not $didWork) {
                Write-State -Phase 'worker' -Status 'watching' -Detail 'No unanswered Vanguard mailbox request; Chromium Throne runner remains armed.'
                Start-Sleep -Seconds 10
            }
        } catch {
            Write-State -Phase 'worker' -Status 'retrying' -Detail $_.Exception.Message -Extra @{backoffSeconds=$backoff}
            Start-Sleep -Seconds $backoff
            $backoff = [Math]::Min(60, $backoff * 2)
        }
    }
    Write-State -Phase 'worker' -Status 'stopped' -Detail 'THECAULDRON mailbox runner stopped by explicit campaign STOP.'
    Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $PidFile
}

function Get-WorkerAlive {
    if (-not (Test-Path -LiteralPath $PidFile -PathType Leaf)) { return $false }
    try {
        $workerPid = [int](Get-Content -LiteralPath $PidFile -Raw).Trim()
        $proc = Get-Process -Id $workerPid -ErrorAction Stop
        return ($null -ne $proc)
    } catch { return $false }
}

function Start-Worker {
    if (Get-WorkerAlive) {
        Write-State -Phase 'launcher' -Status 'already-running' -Detail 'THECAULDRON campaign worker is already alive; no duplicate runner started.'
        return
    }
    Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $StopFile
    $exe = (Get-Process -Id $PID).Path
    $args = @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"{0}"' -f $ScriptPath),'-Action','Worker')
    $process = Start-Process -FilePath $exe -ArgumentList $args -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath $PidFile -Value $process.Id -Encoding ASCII
    Write-State -Phase 'launcher' -Status 'running' -Detail 'THECAULDRON campaign worker launched out-of-band; this shell is free.' -Extra @{pid=$process.Id; controls=@('Run','Status','Follow','Stop','Doctor')}
}

function Show-Doctor {
    $checks = @()
    $checks += [ordered]@{check='gh-auth'; ok=(Test-GhAuth); detail='Required for durable GitHub mailbox/branch readback.'}
    $capOk = $false
    $capDetail = $CapabilityFile
    try { $capOk = ((Get-Capability).Length -ge 32) } catch { $capDetail = $_.Exception.Message }
    $checks += [ordered]@{check='throne-capability'; ok=$capOk; detail=$capDetail}
    $relayOk = $false
    $relayDetail = ''
    try {
        $status = Invoke-Relay -Method GET -Path 'status' -TimeoutSec 8
        $relayOk = ($status.ok -eq $true)
        $relayDetail = ($status | ConvertTo-Json -Depth 12 -Compress)
    } catch { $relayDetail = $_.Exception.Message }
    $checks += [ordered]@{check='throne-relay'; ok=$relayOk; detail=$relayDetail}
    $result = [ordered]@{
        schema='vanguard-overlay-throne-doctor-v1'
        ok=($checks | Where-Object { -not $_.ok }).Count -eq 0
        organ='Chromium Throne / THECAULDRON'
        evidenceSource='local relay + local capability + authenticated GitHub mailbox'
        observedAt=[DateTimeOffset]::UtcNow.ToString('o')
        workerAlive=(Get-WorkerAlive)
        checks=$checks
        proves='Only whether this desktop body can actuate the commissioned free-tab lane and persist remote mailbox evidence.'
        doesNotProve='Android implementation, phone deployment, microphone activity, or acceptance.'
    }
    $result | ConvertTo-Json -Depth 30
}

function Show-Status {
    $latestValue = $null
    if (Test-Path -LiteralPath $Latest -PathType Leaf) {
        try { $latestValue = Get-Content -LiteralPath $Latest -Raw | ConvertFrom-Json -Depth 30 } catch {}
    }
    [ordered]@{
        schema='vanguard-overlay-throne-status-v1'
        workerAlive=(Get-WorkerAlive)
        workerPid=if (Test-Path -LiteralPath $PidFile) { (Get-Content -LiteralPath $PidFile -Raw).Trim() } else { $null }
        latest=$latestValue
        stateRoot=$Root
        history=$History
        stopFile=$StopFile
        truthBoundary='Desktop runner status proves only this runner/local Throne transport state. Phone runtime state is separate.'
    } | ConvertTo-Json -Depth 30
}

function Stop-Campaign {
    Set-Content -LiteralPath $StopFile -Value (Get-NowMs) -Encoding ASCII
    if (Get-WorkerAlive) {
        $workerPid = [int](Get-Content -LiteralPath $PidFile -Raw).Trim()
        try { Stop-Process -Id $workerPid -Force -ErrorAction Stop } catch {}
    }
    Write-State -Phase 'stop' -Status 'stopped' -Detail 'Desktop campaign stop intent persisted; runner process terminated. Any already-leased Throne command will be cancelled by relay timeout or explicit cancel on worker path.'
}

function Follow-History {
    if (-not (Test-Path -LiteralPath $History)) { New-Item -ItemType File -Path $History | Out-Null }
    try { Get-Content -LiteralPath $History -Wait -Tail 20 } catch [System.Management.Automation.PipelineStoppedException] {}
}

switch ($Action) {
    'Run' {
        if (-not (Test-GhAuth)) { throw 'GH_AUTH_UNAVAILABLE: authenticate GitHub on THECAULDRON before running the free-tab campaign.' }
        [void](Ensure-InitialRequest)
        Start-Worker
        Show-Status
    }
    'Worker' { Worker-Loop }
    'Status' { Show-Status }
    'Stop' { Stop-Campaign }
    'Doctor' { Show-Doctor }
    'Follow' { Follow-History }
    'DispatchInitial' { [void](Ensure-InitialRequest) }
}
