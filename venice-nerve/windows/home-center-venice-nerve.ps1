param(
    [string]$ConfigPath = "$env:LOCALAPPDATA\HomeCenter\VeniceNerve\config.json",
    [string]$BootstrapCode = "",
    [string]$Origin = "https://us-central1-home-center-dclar.cloudfunctions.net/veniceNerve",
    [string]$WorkerId = "windows-venice-nerve-01",
    [string]$AperturePath = "",
    [string]$DriveRoot = "G:\My Drive\Venice Runtime",
    [switch]$Once
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
Add-Type -AssemblyName System.Security
$WorkerVersion = '1.0.2'

function ConvertTo-Utf8Base64([string]$Text) {
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$Text))
}
function Get-Sha256File([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Protect-Token([string]$Token) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Token)
    $protected = [Security.Cryptography.ProtectedData]::Protect($bytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
    return [Convert]::ToBase64String($protected)
}
function Unprotect-Token([string]$ProtectedToken) {
    $bytes = [Convert]::FromBase64String($ProtectedToken)
    $plain = [Security.Cryptography.ProtectedData]::Unprotect($bytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
    return [Text.Encoding]::UTF8.GetString($plain)
}
function Save-Config([hashtable]$Config) {
    $dir = Split-Path -Parent $ConfigPath
    [IO.Directory]::CreateDirectory($dir) | Out-Null
    $tmp = "$ConfigPath.tmp"
    $json = $Config | ConvertTo-Json -Depth 10
    [IO.File]::WriteAllText($tmp, $json, (New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $tmp -Destination $ConfigPath -Force
}
function Load-Config {
    if (-not (Test-Path -LiteralPath $ConfigPath)) { return $null }
    return Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
}
function Quote-ProcessArg([string]$Value) {
    return '"' + ([string]$Value).Replace('"', '\"') + '"'
}
function Resolve-Aperture([object]$Config) {
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($AperturePath) { $candidates.Add($AperturePath) }
    if ($Config -and $Config.PSObject.Properties['aperturePath'] -and $Config.aperturePath) { $candidates.Add([string]$Config.aperturePath) }
    $candidates.Add((Join-Path $DriveRoot 'venice-aperture.ps1'))
    $candidates.Add((Join-Path $DriveRoot 'tools\venice-aperture.ps1'))
    $candidates.Add((Join-Path $DriveRoot 'work\venice-aperture.ps1'))
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    if (Test-Path -LiteralPath $DriveRoot) {
        $found = Get-ChildItem -LiteralPath $DriveRoot -Filter 'venice-aperture.ps1' -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    throw "Drive-synced venice-aperture.ps1 was not found under $DriveRoot."
}
function Read-Utf8JsonFile([string]$Path) {
    $utf8 = New-Object Text.UTF8Encoding($false)
    $raw = [IO.File]::ReadAllText($Path, $utf8)
    return ($raw | ConvertFrom-Json)
}
function Find-DurableApertureRecord {
    param(
        [string]$PromptSha256,
        [DateTimeOffset]$StartedAt
    )
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
            Select-Object -First 40
        foreach ($item in $recent) { $paths.Add($item.FullName) }
    }

    $seen = @{}
    foreach ($path in $paths) {
        if ($seen.ContainsKey($path)) { continue }
        $seen[$path] = $true
        try {
            $candidate = Read-Utf8JsonFile $path
            $inputSha = [string]$candidate.input.sha256
            $speechText = [string]$candidate.speech.text
            $speechSource = [string]$candidate.speech.source
            if ($candidate.ok -and $inputSha -eq $PromptSha256 -and $speechText -and $speechSource -eq 'local-venice') {
                return [ordered]@{record=$candidate; path=$path}
            }
        } catch {
            continue
        }
    }
    return $null
}
function Invoke-JsonRequest {
    param(
        [ValidateSet('GET','POST')][string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [string]$Token = "",
        [string]$CurrentOrigin = $Origin,
        [string]$CurrentWorkerId = $WorkerId
    )
    $uri = $CurrentOrigin.TrimEnd('/') + '/venice-nerve/v1/' + $Path.TrimStart('/')
    $headers = @{}
    if ($Token) {
        $headers.Authorization = "Bearer $Token"
        $headers['X-Home-Center-Worker'] = $CurrentWorkerId
        $headers['X-Home-Center-Worker-Version'] = $WorkerVersion
    }
    $params = @{Method=$Method; Uri=$uri; Headers=$headers; TimeoutSec=45; ErrorAction='Stop'}
    if ($null -ne $Body) {
        $params.ContentType = 'application/json'
        $params.Body = ($Body | ConvertTo-Json -Depth 30 -Compress)
    }
    return Invoke-RestMethod @params
}
function Invoke-ApertureTurn {
    param([object]$Turn, [string]$ResolvedAperture)
    $started = [DateTimeOffset]::UtcNow
    $base64 = ConvertTo-Utf8Base64 ([string]$Turn.prompt)
    $promptSha = [string]$Turn.promptSha256
    $timeout = [Math]::Max(5, [Math]::Min(110, [int]$Turn.timeoutSeconds))
    $title = if ($Turn.threadTitle) { [string]$Turn.threadTitle } else { 'ChatGPT Aperture' }

    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = 'powershell.exe'
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.Arguments = @(
        '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', (Quote-ProcessArg $ResolvedAperture),
        '-MessageBase64', $base64,
        '-ThreadTitle', (Quote-ProcessArg $title),
        '-TimeoutSeconds', [string]$timeout,
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
        return [ordered]@{ok=$false; error='venice_aperture_failed'; detail=($stderr.Trim() + ' ' + $stdout.Trim()).Trim(); diagnostics=@{elapsedMs=$elapsed; apertureScriptSha256=(Get-Sha256File $ResolvedAperture)}}
    }

    $record = $null
    $durableRecordPath = ''
    $stdoutParseError = ''
    try {
        $record = $stdout.Trim() | ConvertFrom-Json
    } catch {
        $stdoutParseError = $_.Exception.Message
    }

    if ($null -eq $record) {
        $recovered = Find-DurableApertureRecord -PromptSha256 $promptSha -StartedAt $started
        if ($null -eq $recovered) {
            return [ordered]@{ok=$false; error='venice_aperture_invalid_json'; detail=$stdoutParseError; diagnostics=@{elapsedMs=$elapsed; apertureScriptSha256=(Get-Sha256File $ResolvedAperture)}}
        }
        $record = $recovered.record
        $durableRecordPath = [string]$recovered.path
    }

    if (-not $record.ok -or -not $record.speech -or $null -eq $record.speech.text) {
        return [ordered]@{ok=$false; error='venice_aperture_no_speech'; detail='The proven aperture did not return successful local Venice speech.'; diagnostics=@{elapsedMs=$elapsed; apertureScriptSha256=(Get-Sha256File $ResolvedAperture)}}
    }
    if ([string]$record.input.sha256 -ne $promptSha) {
        return [ordered]@{ok=$false; error='venice_aperture_prompt_mismatch'; detail='Recovered aperture record did not match the leased prompt SHA-256.'; diagnostics=@{elapsedMs=$elapsed; apertureScriptSha256=(Get-Sha256File $ResolvedAperture)}}
    }

    $speech = [string]$record.speech.text
    $speechSha = [string]$record.speech.sha256
    $conversation = $record.diagnostics.conversation
    $durability = $record.diagnostics.durability
    $workstation = $record.diagnostics.workstation
    if (-not $durableRecordPath) { $durableRecordPath = [string]$durability.turnPath }
    return [ordered]@{
        ok = $true
        speech = [ordered]@{text=$speech; sha256=$speechSha}
        actions = @()
        observations = @()
        diagnostics = [ordered]@{
            workstationThreadId = [string]$conversation.threadId
            workstationJobId = [string]$conversation.jobId
            durableTurnRecord = $durableRecordPath
            apertureScriptSha256 = Get-Sha256File $ResolvedAperture
            workstationVersion = [string]$workstation.version
            elapsedMs = $elapsed
        }
    }
}

if ($BootstrapCode) {
    $registration = Invoke-JsonRequest -Method POST -Path 'bootstrap' -Body @{bootstrapCode=$BootstrapCode; workerId=$WorkerId} -CurrentOrigin $Origin -CurrentWorkerId $WorkerId
    if (-not $registration.token) { throw 'Venice Nerve bootstrap did not return a worker token.' }
    $resolved = Resolve-Aperture $null
    Save-Config @{
        origin = [string]$registration.origin
        workerId = [string]$registration.workerId
        tokenProtected = Protect-Token ([string]$registration.token)
        expiresAtMs = [int64]$registration.expiresAtMs
        aperturePath = $resolved
        driveRoot = $DriveRoot
        workerVersion = $WorkerVersion
    }
}

$config = Load-Config
if (-not $config) { throw "Venice Nerve is not configured. Supply -BootstrapCode once. Config: $ConfigPath" }
$currentOrigin = [string]$config.origin
$currentWorkerId = [string]$config.workerId
$token = Unprotect-Token ([string]$config.tokenProtected)
if ($config.PSObject.Properties['driveRoot'] -and $config.driveRoot) { $DriveRoot = [string]$config.driveRoot }
$resolvedAperture = Resolve-Aperture $config

while ($true) {
    try {
        $lease = Invoke-JsonRequest -Method POST -Path 'lease' -Body @{} -Token $token -CurrentOrigin $currentOrigin -CurrentWorkerId $currentWorkerId
        if ($lease.turn) {
            $turn = $lease.turn
            $turnId = [string]$turn.turnId
            [void](Invoke-JsonRequest -Method POST -Path ("turns/$turnId/heartbeat") -Body @{phase='calling_local_venice'} -Token $token -CurrentOrigin $currentOrigin -CurrentWorkerId $currentWorkerId)
            $result = Invoke-ApertureTurn -Turn $turn -ResolvedAperture $resolvedAperture
            [void](Invoke-JsonRequest -Method POST -Path ("turns/$turnId/complete") -Body @{result=$result} -Token $token -CurrentOrigin $currentOrigin -CurrentWorkerId $currentWorkerId)
            if ($Once) { break }
            continue
        }
        if ($Once) { break }
        $seconds = [Math]::Max(1, [Math]::Min(10, [int]$lease.pollAfterSeconds))
        Start-Sleep -Seconds $seconds
    } catch {
        if ($Once) { throw }
        Write-Warning ("Venice Nerve poll failed: " + $_.Exception.Message)
        Start-Sleep -Seconds 3
    }
}
