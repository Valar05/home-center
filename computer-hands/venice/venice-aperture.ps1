param(
    [string]$MessageText,
    [string]$MessageBase64,
    [string]$ThreadTitle = "ChatGPT Aperture",
    [int]$TimeoutSeconds = 95,
    [string]$DriveRoot = "G:\My Drive\Venice Runtime"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$ScriptVersion = "1.0.0"
$RuntimeRoot = Split-Path -Parent $PSScriptRoot
$ServerStatePath = Join-Path $RuntimeRoot "work\workstation\server.json"

function Get-Utf8Sha256([string]$Text) {
    $bytes = [Text.Encoding]::UTF8.GetBytes([string]$Text)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Invoke-VeniceApi {
    param(
        [ValidateSet("GET","POST","PATCH")][string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [int]$TimeoutSec = 20
    )
    $params = @{
        Method = $Method
        Uri = "$script:BaseUrl$Path"
        Headers = $script:Headers
        TimeoutSec = $TimeoutSec
        ErrorAction = "Stop"
    }
    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 20 -Compress)
    }
    return Invoke-RestMethod @params
}

function Get-GpuSnapshot {
    try {
        $smi = Get-Command nvidia-smi.exe -ErrorAction Stop
        $raw = @(& $smi.Source "--query-gpu=name,memory.used,memory.free,memory.total,utilization.gpu,temperature.gpu" "--format=csv,noheader,nounits" 2>$null)
        if (-not $raw -or $raw.Count -eq 0) { return $null }
        $parts = @(([string]$raw[0]).Split(",") | ForEach-Object { $_.Trim() })
        if ($parts.Count -lt 6) { return @{ raw = [string]$raw[0] } }
        return [ordered]@{
            name = $parts[0]
            usedMB = [int]$parts[1]
            freeMB = [int]$parts[2]
            totalMB = [int]$parts[3]
            utilizationPct = [int]$parts[4]
            temperatureC = [int]$parts[5]
        }
    } catch {
        return [ordered]@{ error = $_.Exception.Message }
    }
}

function Get-OllamaSnapshot {
    try {
        $ps = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:11434/api/ps" -TimeoutSec 5 -ErrorAction Stop
        return [ordered]@{
            alive = $true
            models = @($ps.models | ForEach-Object {
                [ordered]@{
                    name = $_.name
                    model = $_.model
                    sizeVram = $_.size_vram
                    expiresAt = $_.expires_at
                }
            })
        }
    } catch {
        return [ordered]@{ alive = $false; error = $_.Exception.Message; models = @() }
    }
}

if ($MessageBase64) {
    try {
        $MessageText = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($MessageBase64))
    } catch {
        throw "MessageBase64 was not valid UTF-8 Base64: $($_.Exception.Message)"
    }
}
if ($null -eq $MessageText -or $MessageText.Length -eq 0) {
    throw "MessageText or MessageBase64 is required."
}
if (-not (Test-Path -LiteralPath $ServerStatePath)) {
    throw "Venice Workstation server state was not found: $ServerStatePath"
}

$startedAt = [DateTimeOffset]::UtcNow
$stopwatch = [Diagnostics.Stopwatch]::StartNew()
$server = Get-Content -LiteralPath $ServerStatePath -Raw | ConvertFrom-Json
$serverUri = [Uri]$server.url
$token = $null
foreach ($pair in @($serverUri.Query.TrimStart("?").Split("&"))) {
    if (-not $pair) { continue }
    $kv = $pair.Split("=", 2)
    if ($kv[0] -eq "token") {
        $token = [Uri]::UnescapeDataString($kv[1])
        break
    }
}
if (-not $token) { throw "Venice Workstation state URL did not contain a bearer token." }
$script:BaseUrl = "{0}://{1}:{2}" -f $serverUri.Scheme, $serverUri.Host, $serverUri.Port
$script:Headers = @{ Authorization = "Bearer $token" }

$diagnosticErrors = New-Object System.Collections.Generic.List[object]
$gpuBefore = Get-GpuSnapshot
$ollamaBefore = Get-OllamaSnapshot

try {
    $bootstrap = Invoke-VeniceApi -Method GET -Path "/api/bootstrap" -TimeoutSec 10
} catch {
    throw "Venice Workstation bootstrap failed: $($_.Exception.Message)"
}

$threadEnvelope = Invoke-VeniceApi -Method POST -Path "/api/mobile/thread" -Body @{
    title = $ThreadTitle
    model = "gpt-5.6-terra"
    instructions = "Direct conversation with Drew through the ChatGPT aperture. Venice's natural Social-mode reply is the voice. Do not narrate the transport."
} -TimeoutSec 15

$project = $threadEnvelope.project
$thread = $threadEnvelope.thread
if (-not $thread.id) { throw "Venice Workstation did not return a thread id." }

try {
    $thread = Invoke-VeniceApi -Method PATCH -Path ("/api/threads/{0}" -f $thread.id) -Body @{ mode = "social" } -TimeoutSec 10
} catch {
    $diagnosticErrors.Add([ordered]@{ stage = "thread_mode"; error = $_.Exception.Message })
}

$before = Invoke-VeniceApi -Method GET -Path ("/api/threads/{0}/context" -f $thread.id) -TimeoutSec 15
$beforeAssistantIds = New-Object "System.Collections.Generic.HashSet[string]"
foreach ($m in @($before.messages)) {
    if ($m.role -eq "assistant" -and $m.id) { [void]$beforeAssistantIds.Add([string]$m.id) }
}

$promptTrimmed = $MessageText.Trim()
$run = Invoke-VeniceApi -Method POST -Path ("/api/threads/{0}/run" -f $thread.id) -Body @{
    prompt = $MessageText
    mode = "social"
    streamSocial = $true
} -TimeoutSec 20

$jobId = [string]$run.job.id
if (-not $jobId) { throw "Venice Workstation did not return a job id." }

$deadline = [DateTimeOffset]::UtcNow.AddSeconds([Math]::Max(5, [Math]::Min(110, $TimeoutSeconds)))
$context = $null
$job = $null
do {
    Start-Sleep -Milliseconds 250
    $context = Invoke-VeniceApi -Method GET -Path ("/api/threads/{0}/context" -f $thread.id) -TimeoutSec 15
    $job = @($context.jobs | Where-Object { $_.id -eq $jobId } | Select-Object -First 1)[0]
    if ($job -and @("completed","failed","cancelled","waiting_approval") -contains [string]$job.status) { break }
} while ([DateTimeOffset]::UtcNow -lt $deadline)

if (-not $job) {
    throw "Venice job $jobId disappeared from thread context."
}

$newAssistant = $null
foreach ($m in @($context.messages)) {
    if ($m.role -eq "assistant" -and $m.id -and -not $beforeAssistantIds.Contains([string]$m.id)) {
        $newAssistant = $m
    }
}

$events = @()
try {
    $eventEnvelope = Invoke-VeniceApi -Method GET -Path ("/api/jobs/{0}/events?after=0" -f $jobId) -TimeoutSec 10
    $events = @($eventEnvelope.events)
} catch {
    $diagnosticErrors.Add([ordered]@{ stage = "job_events"; error = $_.Exception.Message })
}

$replyText = $null
if ($newAssistant -and $null -ne $newAssistant.content) {
    $replyText = [string]$newAssistant.content
} elseif ($job.result) {
    foreach ($candidate in @("text","output","reply","content","message")) {
        $prop = $job.result.PSObject.Properties[$candidate]
        if ($prop -and $null -ne $prop.Value -and [string]$prop.Value) {
            $replyText = [string]$prop.Value
            break
        }
    }
}

$gpuAfter = Get-GpuSnapshot
$ollamaAfter = Get-OllamaSnapshot
$stopwatch.Stop()
$finishedAt = [DateTimeOffset]::UtcNow

$ok = ([string]$job.status -eq "completed" -and $null -ne $replyText)
$replyHash = if ($null -ne $replyText) { Get-Utf8Sha256 $replyText } else { $null }

$record = [ordered]@{
    schema = "venice-nerve-silk.turn.v1"
    scriptVersion = $ScriptVersion
    ok = $ok
    input = [ordered]@{
        source = "chatgpt-aperture"
        text = $MessageText
        sha256 = Get-Utf8Sha256 $MessageText
    }
    speech = [ordered]@{
        source = "local-venice"
        text = $replyText
        transformedByOrchestrator = $false
        sha256 = $replyHash
    }
    diagnostics = [ordered]@{
        transport = "Home Center Computer Hands -> shell.exec -> Venice Workstation loopback"
        request = [ordered]@{
            startedAt = $startedAt.ToString("o")
            finishedAt = $finishedAt.ToString("o")
            elapsedMs = [int64]$stopwatch.ElapsedMilliseconds
            promptSha256 = Get-Utf8Sha256 $MessageText
            promptCharacters = $MessageText.Length
            serverTrimWouldChangePrompt = ($MessageText -ne $promptTrimmed)
        }
        workstation = [ordered]@{
            version = $server.version
            pid = $server.pid
            host = $server.host
            port = $server.port
            startedAt = $server.startedAt
            latestEventSequence = $bootstrap.latestEventSequence
            routing = $bootstrap.routing
            senses = $bootstrap.senses
        }
        conversation = [ordered]@{
            projectId = $project.id
            threadId = $thread.id
            threadMode = $thread.mode
            threadTitle = $thread.title
            jobId = $jobId
            jobStatus = $job.status
            jobProgress = $job.progress
            jobResult = $job.result
            jobError = $job.error
            assistantMessageId = if ($newAssistant) { $newAssistant.id } else { $null }
            assistantCreatedAt = if ($newAssistant) { $newAssistant.createdAt } else { $null }
            assistantMetadata = if ($newAssistant) { $newAssistant.metadata } else { $null }
            toolEvents = $events
        }
        resources = [ordered]@{
            gpuBefore = $gpuBefore
            gpuAfter = $gpuAfter
            ollamaBefore = $ollamaBefore
            ollamaAfter = $ollamaAfter
        }
        errors = @($diagnosticErrors)
    }
}

$durability = [ordered]@{
    driveRoot = $DriveRoot
    cloudDriveWritten = $false
    turnPath = $null
    latestPath = $null
    ledgerPath = $null
    error = $null
}
try {
    if (-not (Test-Path -LiteralPath $DriveRoot)) { throw "Drive root is unavailable: $DriveRoot" }
    $logRoot = Join-Path $DriveRoot "work\nerve-silk"
    $turnRoot = Join-Path $logRoot "turns"
    [IO.Directory]::CreateDirectory($turnRoot) | Out-Null
    $stamp = [DateTimeOffset]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
    $durability.turnPath = Join-Path $turnRoot ("turn-{0}-{1}.json" -f $stamp, $jobId)
    $durability.latestPath = Join-Path $logRoot "latest.json"
    $durability.ledgerPath = Join-Path $logRoot "turns.jsonl"
    $durability.cloudDriveWritten = $true
} catch {
    $durability.error = $_.Exception.Message
}
$record.diagnostics["durability"] = $durability

$finalPretty = $record | ConvertTo-Json -Depth 30
$finalJson = $record | ConvertTo-Json -Depth 30 -Compress

if ($durability.cloudDriveWritten) {
    try {
        $utf8 = New-Object Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($durability.turnPath, $finalPretty, $utf8)
        [IO.File]::WriteAllText($durability.latestPath, $finalPretty, $utf8)
        [IO.File]::AppendAllText($durability.ledgerPath, $finalJson + [Environment]::NewLine, $utf8)
    } catch {
        $durability.cloudDriveWritten = $false
        $durability.error = $_.Exception.Message
        $record.diagnostics["durability"] = $durability
        $finalJson = $record | ConvertTo-Json -Depth 30 -Compress
    }
}

Write-Output $finalJson
if (-not $ok) { exit 2 }
