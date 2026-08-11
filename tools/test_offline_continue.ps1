param(
    [switch]$RequireInternetDown = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$configPath = Join-Path $repoRoot '.continue\offline-config.yaml'
$launcherPath = Join-Path $repoRoot 'tools\cn-offline.ps1'
$rulesPath = Join-Path $repoRoot '.continue\rules'
$receiptDir = Join-Path $repoRoot 'generated\engineering_memory'

$evidence = [ordered]@{
    schema = 'home-center.offline-continue-acceptance.v1'
    startedAt = (Get-Date).ToString('o')
    requireInternetDown = [bool]$RequireInternetDown
    result = 'red'
    checks = @()
}

function Pass([string]$message) {
    Write-Host "PASS  $message"
    $script:evidence.checks += [ordered]@{ status = 'pass'; message = $message }
}

function Fail([string]$message) {
    $script:evidence.checks += [ordered]@{ status = 'fail'; message = $message }
    throw "FAIL  $message"
}

try {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { Fail 'ollama is not on PATH' }
    Pass 'ollama command exists'

    $cnCommand = Get-Command cn.cmd -ErrorAction SilentlyContinue
    if (-not $cnCommand) { Fail 'Continue launcher cn.cmd is not on PATH' }
    $cnPath = $cnCommand.Source
    $evidence.continueLauncher = $cnPath
    Pass "Continue launcher exists: $cnPath"

    $cnVersion = (& $cnPath --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { Fail "Continue version probe exited with code $LASTEXITCODE" }
    $evidence.continueVersion = $cnVersion
    Pass "Continue CLI version recorded: $cnVersion"

    if (-not (Test-Path $configPath)) { Fail "offline config missing: $configPath" }
    Pass 'offline config exists'

    if (-not (Test-Path $launcherPath)) { Fail "offline launcher missing: $launcherPath" }
    Pass 'offline launcher exists'

    $configText = Get-Content -Raw $configPath
    if ($configText -notmatch 'provider:\s*ollama') { Fail 'offline config does not declare Ollama' }
    if ($configText -match 'provider:\s*(openai|anthropic|gemini|openrouter|groq|mistral|azure|bedrock)') {
        Fail 'offline config contains a cloud model provider'
    }
    if ($configText -match 'apiBase:\s*https?://(?!127\.0\.0\.1|localhost)') {
        Fail 'offline config contains a non-local model endpoint'
    }
    Pass 'offline config has no declared cloud model provider or non-local model endpoint'

    $jarFiles = @(Get-ChildItem -Path $rulesPath -Filter '*judgement-jar*.md' -File | Sort-Object Name)
    if ($jarFiles.Count -lt 6) { Fail "expected at least six judgement jars; found $($jarFiles.Count)" }
    $evidence.judgementJars = @($jarFiles | ForEach-Object { $_.Name })
    Pass "$($jarFiles.Count) judgement jars are present"

    try {
        $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -Method Get -TimeoutSec 3
    } catch {
        Fail "local Ollama is not reachable: $($_.Exception.Message)"
    }
    Pass 'local Ollama API is reachable'

    $installedModels = @($tags.models | ForEach-Object { $_.name })
    $requiredModels = @('qwen2.5-coder:7b', 'qwen2.5-coder:1.5b')
    $evidence.requiredModels = $requiredModels
    foreach ($requiredModel in $requiredModels) {
        if ($requiredModel -notin $installedModels) { Fail "required local model is missing: $requiredModel" }
        Pass "local model installed: $requiredModel"
    }

    if ($RequireInternetDown) {
        if (Get-Command Get-NetConnectionProfile -ErrorAction SilentlyContinue) {
            $internetProfiles = @(Get-NetConnectionProfile -ErrorAction SilentlyContinue | Where-Object { $_.IPv4Connectivity -eq 'Internet' -or $_.IPv6Connectivity -eq 'Internet' })
            if ($internetProfiles.Count -gt 0) { Fail 'Windows still reports an Internet-connected network profile' }
            Pass 'Windows reports no Internet-connected network profile'
        }

        $internetReachable = Test-NetConnection -ComputerName '1.1.1.1' -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($internetReachable) { Fail 'public internet is still reachable; offline acceptance was requested' }
        Pass 'public reachability probe failed as required for offline acceptance'
    }

    $probe = & $launcherPath -Readonly -Prompt 'Reply with exactly OFFLINE_CONTINUE_OK and nothing else.' 2>&1
    $probeText = ($probe -join [Environment]::NewLine).Trim()
    $evidence.inferenceProbe = $probeText
    if ($probeText -notmatch 'OFFLINE_CONTINUE_OK') {
        Fail "Continue did not return the acceptance token. Output: $probeText"
    }
    Pass 'Continue produced a response through the local Qwen configuration'

    $fixtureRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("home-center-offline-continue-" + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $fixtureRoot | Out-Null
    try {
        Set-Content -Path (Join-Path $fixtureRoot 'fixture.txt') -Value 'alpha' -NoNewline
        Push-Location $fixtureRoot
        try {
            $editOutput = & $launcherPath -Allow @('read_file', 'edit_existing_file') -Exclude @('run_terminal_command', 'create_new_file') -Prompt 'Edit fixture.txt so its entire contents are exactly beta. Do not create or modify any other file.' 2>&1
        } finally {
            Pop-Location
        }

        $evidence.editProbeOutput = ($editOutput -join [Environment]::NewLine).Trim()
        $fixtureFiles = @(Get-ChildItem -Path $fixtureRoot -File)
        if ($fixtureFiles.Count -ne 1 -or $fixtureFiles[0].Name -ne 'fixture.txt') {
            Fail 'bounded edit probe created an unexpected file'
        }

        $fixtureText = Get-Content -Raw (Join-Path $fixtureRoot 'fixture.txt')
        if ($fixtureText -ne 'beta') {
            Fail "bounded edit probe produced unexpected fixture contents: '$fixtureText'"
        }
        Pass 'Continue performed and constrained a real local file edit through the local Qwen configuration'
    } finally {
        if (Test-Path $fixtureRoot) { Remove-Item -Recurse -Force $fixtureRoot }
    }

    $evidence.result = 'green'
    Write-Host 'RESULT green'
} catch {
    $message = $_.Exception.Message
    if (-not ($evidence.checks | Where-Object { $_.status -eq 'fail' -and $_.message -eq $message })) {
        $evidence.checks += [ordered]@{ status = 'fail'; message = $message }
    }
    $evidence.failure = [ordered]@{
        message = $message
        type = $_.Exception.GetType().FullName
    }
    Write-Error $message
} finally {
    $evidence.finishedAt = (Get-Date).ToString('o')
    New-Item -ItemType Directory -Force -Path $receiptDir | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $receiptPath = Join-Path $receiptDir "offline-continue-acceptance-$stamp.json"
    $evidence | ConvertTo-Json -Depth 8 | Set-Content -Path $receiptPath -Encoding UTF8
    Write-Host "RECEIPT $receiptPath"
}

if ($evidence.result -ne 'green') {
    exit 1
}
