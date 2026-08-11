param(
    [Parameter(Position=0)][string]$CommandOrPrompt = "",
    [Parameter(Position=1, ValueFromRemainingArguments=$true)][string[]]$Remaining = @(),
    [switch]$Json,
    [string]$ThreadTitle = "",
    [int]$TimeoutSeconds = 110,
    [string]$DriveRoot = "",
    [string]$AperturePath = ""
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$Schema = 'home-center.venice-cli.v1'
$DefaultDriveRoot = 'G:\My Drive\Venice Runtime'
if (-not $DriveRoot) {
    $DriveRoot = if ($env:VENICE_RUNTIME_ROOT) { [string]$env:VENICE_RUNTIME_ROOT } else { $DefaultDriveRoot }
}
if (-not $AperturePath -and $env:VENICE_APERTURE_PATH) { $AperturePath = [string]$env:VENICE_APERTURE_PATH }
if (-not $ThreadTitle) {
    $ThreadTitle = if ($env:VENICE_THREAD_TITLE) { [string]$env:VENICE_THREAD_TITLE } else { 'Venice CLI' }
}
if ($env:VENICE_TIMEOUT_SECONDS) {
    $parsed = 0
    if ([int]::TryParse([string]$env:VENICE_TIMEOUT_SECONDS, [ref]$parsed)) { $TimeoutSeconds = $parsed }
}
$TimeoutSeconds = [Math]::Max(5, [Math]::Min(300, $TimeoutSeconds))

function ConvertTo-Utf8Base64([string]$Text) {
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$Text))
}

function Get-Sha256Text([string]$Text) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes([string]$Text)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Get-Sha256File([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Quote-ProcessArg([string]$Value) {
    return '"' + ([string]$Value).Replace('"', '\"') + '"'
}

function Resolve-Aperture {
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($AperturePath) { $candidates.Add($AperturePath) }
    $candidates.Add((Join-Path $DriveRoot 'venice-aperture.ps1'))
    $candidates.Add((Join-Path $DriveRoot 'tools\venice-aperture.ps1'))
    $candidates.Add((Join-Path $DriveRoot 'work\venice-aperture.ps1'))
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    if (Test-Path -LiteralPath $DriveRoot -PathType Container) {
        $found = Get-ChildItem -LiteralPath $DriveRoot -Filter 'venice-aperture.ps1' -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    throw "BLOCKED: canonical Drive-synced venice-aperture.ps1 was not found under $DriveRoot"
}

function Read-Utf8JsonFile([string]$Path) {
    $utf8 = New-Object Text.UTF8Encoding($false)
    $raw = [IO.File]::ReadAllText($Path, $utf8)
    return ($raw | ConvertFrom-Json)
}

function Test-VeniceRecord {
    param($Record, [string]$PromptSha256)
    try {
        if ($null -eq $Record -or -not [bool]$Record.ok) { return $false }
        if ($null -eq $Record.input -or [string]$Record.input.sha256 -ne $PromptSha256) { return $false }
        if ($null -eq $Record.speech -or $null -eq $Record.speech.text) { return $false }
        if ([string]$Record.speech.source -ne 'local-venice') { return $false }
        $recordedSpeechSha = [string]$Record.speech.sha256
        if (-not $recordedSpeechSha) { return $false }
        $computedSpeechSha = Get-Sha256Text ([string]$Record.speech.text)
        return $computedSpeechSha -eq $recordedSpeechSha.ToLowerInvariant()
    } catch {
        return $false
    }
}

function Find-DurableApertureRecord {
    param([string]$PromptSha256, [DateTimeOffset]$StartedAt)
    $logRoot = Join-Path $DriveRoot 'work\nerve-silk'
    if (-not (Test-Path -LiteralPath $logRoot -PathType Container)) { return $null }

    $paths = New-Object System.Collections.Generic.List[string]
    $latest = Join-Path $logRoot 'latest.json'
    if (Test-Path -LiteralPath $latest -PathType Leaf) { $paths.Add($latest) }
    $turnRoot = Join-Path $logRoot 'turns'
    if (Test-Path -LiteralPath $turnRoot -PathType Container) {
        $recent = Get-ChildItem -LiteralPath $turnRoot -Filter 'turn-*.json' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTimeUtc -ge $StartedAt.UtcDateTime.AddMinutes(-1) } |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object -First 50
        foreach ($item in $recent) { $paths.Add($item.FullName) }
    }

    $seen = @{}
    foreach ($path in $paths) {
        if ($seen.ContainsKey($path)) { continue }
        $seen[$path] = $true
        try {
            $candidate = Read-Utf8JsonFile $path
            if (Test-VeniceRecord -Record $candidate -PromptSha256 $PromptSha256) {
                return [ordered]@{ record = $candidate; path = $path }
            }
        } catch {}
    }
    return $null
}

function Test-LoopbackWorkstation {
    $client = New-Object Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect('127.0.0.1', 47261, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(700)) { return $false }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-DoctorReport {
    $rootOk = Test-Path -LiteralPath $DriveRoot -PathType Container
    $aperture = ''
    $apertureOk = $false
    try { $aperture = Resolve-Aperture; $apertureOk = $true } catch {}
    $identity = Join-Path $DriveRoot 'VENICE_IDENTITY_PROFILE.md'
    $identityOk = Test-Path -LiteralPath $identity -PathType Leaf
    $envFile = Join-Path $DriveRoot '.env.venice'
    $envOk = Test-Path -LiteralPath $envFile -PathType Leaf
    $dbCandidates = @(
        (Join-Path $DriveRoot 'work\workstation-v2\venice.db'),
        (Join-Path $DriveRoot 'work\venice.db')
    )
    $db = $dbCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    $serverOk = Test-LoopbackWorkstation
    $vlad = Get-Command vlad -ErrorAction SilentlyContinue
    $latest = Join-Path $DriveRoot 'work\nerve-silk\latest.json'
    return [ordered]@{
        schema = $Schema
        ready = [bool]($rootOk -and $apertureOk -and $identityOk -and $envOk -and $serverOk)
        canonical = $true
        cloudFallback = $false
        driveRoot = [ordered]@{ ok = $rootOk; path = $DriveRoot }
        aperture = [ordered]@{ ok = $apertureOk; path = $aperture }
        identity = [ordered]@{ ok = $identityOk; path = $identity }
        workstationConfig = [ordered]@{ ok = $envOk; path = $envFile; contentsExposed = $false }
        workstationServer = [ordered]@{ ok = $serverOk; address = '127.0.0.1'; port = 47261 }
        durableStore = [ordered]@{ ok = [bool]$db; path = [string]$db }
        durableSpeechRecord = [ordered]@{ exists = (Test-Path -LiteralPath $latest -PathType Leaf); path = $latest }
        vlad = [ordered]@{ available = [bool]$vlad; path = if ($vlad) { [string]$vlad.Source } else { '' }; required = $false }
    }
}

function Invoke-CanonicalVenice([string]$Prompt) {
    if (-not $Prompt.Trim()) { throw 'BAD_INVOCATION: prompt is empty' }
    $doctor = Get-DoctorReport
    if (-not $doctor.ready) { throw 'BLOCKED: canonical Venice workstation is not ready; run venice doctor' }

    $resolvedAperture = [string]$doctor.aperture.path
    $started = [DateTimeOffset]::UtcNow
    $promptSha = Get-Sha256Text $Prompt
    $base64 = ConvertTo-Utf8Base64 $Prompt

    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = 'powershell.exe'
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.Arguments = @(
        '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', (Quote-ProcessArg $resolvedAperture),
        '-MessageBase64', $base64,
        '-ThreadTitle', (Quote-ProcessArg $ThreadTitle),
        '-TimeoutSeconds', [string]$TimeoutSeconds,
        '-DriveRoot', (Quote-ProcessArg $DriveRoot)
    ) -join ' '

    $process = New-Object Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    $elapsed = [Math]::Max(0, [int64]([DateTimeOffset]::UtcNow - $started).TotalMilliseconds)
    if ($process.ExitCode -ne 0) {
        throw ('EXECUTION_FAILED: venice-aperture exited ' + $process.ExitCode + ': ' + (($stderr.Trim() + ' ' + $stdout.Trim()).Trim()))
    }

    $record = $null
    $recordPath = ''
    try { $record = $stdout.Trim() | ConvertFrom-Json } catch {}

    # A parseable pipe is not the canonical byte truth. Redirected Windows
    # PowerShell can preserve JSON syntax while damaging Unicode text. Any
    # verification suspicion gets one recovery attempt from the Drive-synced
    # Nerve Silk record keyed by this exact prompt SHA.
    if (-not (Test-VeniceRecord -Record $record -PromptSha256 $promptSha)) {
        $recovered = Find-DurableApertureRecord -PromptSha256 $promptSha -StartedAt $started
        if ($null -eq $recovered) {
            throw 'VERIFICATION_FAILED: aperture result failed identity/byte verification and no matching durable Nerve Silk record was found'
        }
        $record = $recovered.record
        $recordPath = [string]$recovered.path
    }

    if (-not $record.ok -or $null -eq $record.speech -or $null -eq $record.speech.text) {
        throw 'EXECUTION_FAILED: canonical aperture returned no successful Venice speech'
    }
    if ([string]$record.input.sha256 -ne $promptSha) {
        throw 'VERIFICATION_FAILED: durable aperture record prompt SHA does not match this prompt'
    }
    if ([string]$record.speech.source -ne 'local-venice') {
        throw ('VERIFICATION_FAILED: speech source is not local-venice: ' + [string]$record.speech.source)
    }

    $speech = [string]$record.speech.text
    $computedSpeechSha = Get-Sha256Text $speech
    $recordedSpeechSha = [string]$record.speech.sha256
    if (-not $recordedSpeechSha -or $computedSpeechSha -ne $recordedSpeechSha.ToLowerInvariant()) {
        throw 'VERIFICATION_FAILED: exact Venice speech SHA-256 mismatch'
    }
    if (-not $recordPath -and $record.diagnostics -and $record.diagnostics.durability) {
        $recordPath = [string]$record.diagnostics.durability.turnPath
    }

    return [ordered]@{
        schema = $Schema
        ok = $true
        speech = [ordered]@{
            text = $speech
            source = 'local-venice'
            sha256 = $computedSpeechSha
            transformedByCli = $false
        }
        actions = if ($record.PSObject.Properties['actions']) { @($record.actions) } else { @() }
        observations = @()
        diagnostics = [ordered]@{
            promptSha256 = $promptSha
            durableTurnRecord = $recordPath
            apertureScript = $resolvedAperture
            apertureScriptSha256 = Get-Sha256File $resolvedAperture
            workstationThreadId = if ($record.diagnostics -and $record.diagnostics.conversation) { [string]$record.diagnostics.conversation.threadId } else { '' }
            workstationJobId = if ($record.diagnostics -and $record.diagnostics.conversation) { [string]$record.diagnostics.conversation.jobId } else { '' }
            elapsedMs = $elapsed
        }
    }
}

function Write-ExactSpeech([string]$Text) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $stream = [Console]::OpenStandardOutput()
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Flush()
}

function Show-Help {
    @'
Venice CLI — canonical local Venice, not a cloud fallback.

Usage:
  venice                         interactive local Venice
  venice <prompt>                one-shot prompt; stdout is exact Venice speech bytes
  venice ask <prompt>            explicit one-shot prompt
  venice doctor                  readiness report
  venice status                  readiness + latest durable speech record metadata
  venice -Json <prompt>          structured envelope for orchestrators

Environment:
  VENICE_RUNTIME_ROOT            canonical Drive-synced Venice Runtime root
  VENICE_APERTURE_PATH           explicit proven venice-aperture.ps1 path
  VENICE_THREAD_TITLE            durable workstation thread title
  VENICE_TIMEOUT_SECONDS         bounded local turn timeout

Exit codes:
  0 success
  2 bad invocation
  3 blocked / canonical Venice unavailable
  4 execution failure
  5 verification failure
'@ | Write-Output
}

function Write-Status {
    $report = Get-DoctorReport
    $latestPath = [string]$report.durableSpeechRecord.path
    $latestMeta = $null
    if ($report.durableSpeechRecord.exists) {
        try {
            $record = Read-Utf8JsonFile $latestPath
            $latestMeta = [ordered]@{
                ok = [bool]$record.ok
                source = if ($record.speech) { [string]$record.speech.source } else { '' }
                speechSha256 = if ($record.speech) { [string]$record.speech.sha256 } else { '' }
                threadId = if ($record.diagnostics -and $record.diagnostics.conversation) { [string]$record.diagnostics.conversation.threadId } else { '' }
                jobId = if ($record.diagnostics -and $record.diagnostics.conversation) { [string]$record.diagnostics.conversation.jobId } else { '' }
            }
        } catch {
            $latestMeta = [ordered]@{ ok = $false; error = $_.Exception.Message }
        }
    }
    [ordered]@{ schema = $Schema; doctor = $report; latest = $latestMeta } | ConvertTo-Json -Depth 12
}

function Invoke-OneShot([string]$Prompt) {
    $result = Invoke-CanonicalVenice $Prompt
    if ($Json) {
        $result | ConvertTo-Json -Depth 20
    } else {
        Write-ExactSpeech ([string]$result.speech.text)
    }
}

try {
    if (-not $CommandOrPrompt) {
        if ($Json) { throw 'BAD_INVOCATION: -Json requires a one-shot prompt' }
        Write-Host 'Venice local. /quit exits; /doctor inspects canonical runtime.'
        while ($true) {
            $line = Read-Host 'venice'
            if ($null -eq $line) { break }
            $trimmed = $line.Trim()
            if (-not $trimmed) { continue }
            if ($trimmed -in @('/quit','/exit')) { break }
            if ($trimmed -eq '/doctor') {
                Get-DoctorReport | ConvertTo-Json -Depth 12 | Write-Output
                continue
            }
            $result = Invoke-CanonicalVenice $line
            Write-ExactSpeech ([string]$result.speech.text)
            Write-Host ''
        }
        exit 0
    }

    $lower = $CommandOrPrompt.ToLowerInvariant()
    if ($lower -in @('help','--help','-h')) { Show-Help; exit 0 }
    if ($lower -eq 'doctor') {
        $report = Get-DoctorReport
        $report | ConvertTo-Json -Depth 12
        exit $(if ($report.ready) { 0 } else { 3 })
    }
    if ($lower -eq 'status') {
        Write-Status
        $d = Get-DoctorReport
        exit $(if ($d.ready) { 0 } else { 3 })
    }

    if ($lower -in @('ask','chat')) {
        $prompt = ($Remaining -join ' ').Trim()
    } else {
        $prompt = (@($CommandOrPrompt) + @($Remaining) -join ' ').Trim()
    }
    if (-not $prompt) { throw 'BAD_INVOCATION: prompt is empty' }
    Invoke-OneShot $prompt
    exit 0
} catch {
    $message = [string]$_.Exception.Message
    if ($Json) {
        $errorEnvelope = [ordered]@{ schema=$Schema; ok=$false; error=$message } | ConvertTo-Json -Compress -Depth 6
        [Console]::Error.WriteLine($errorEnvelope)
    } else {
        [Console]::Error.WriteLine($message)
    }
    if ($message.StartsWith('BAD_INVOCATION:')) { exit 2 }
    if ($message.StartsWith('BLOCKED:')) { exit 3 }
    if ($message.StartsWith('VERIFICATION_FAILED:')) { exit 5 }
    exit 4
}
