param(
    [switch]$RequireInternetDown = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$configPath = Join-Path $repoRoot '.continue\offline-config.yaml'
$launcherPath = Join-Path $repoRoot 'tools\cn-offline.ps1'
$rulesPath = Join-Path $repoRoot '.continue\rules'

function Pass([string]$message) { Write-Host "PASS  $message" }
function Fail([string]$message) { throw "FAIL  $message" }

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { Fail 'ollama is not on PATH' }
Pass 'ollama command exists'

if (-not (Get-Command cn -ErrorAction SilentlyContinue)) { Fail 'cn is not on PATH' }
Pass 'Continue CLI command cn exists'

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

$jarFiles = @(Get-ChildItem -Path $rulesPath -Filter '*judgement-jar*.md' -File)
if ($jarFiles.Count -lt 4) { Fail "expected at least four judgement jars; found $($jarFiles.Count)" }
Pass "$($jarFiles.Count) judgement jars are present"

try {
    $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -Method Get -TimeoutSec 3
} catch {
    Fail "local Ollama is not reachable: $($_.Exception.Message)"
}
Pass 'local Ollama API is reachable'

$installedModels = @($tags.models | ForEach-Object { $_.name })
foreach ($requiredModel in @('qwen2.5-coder:7b', 'qwen2.5-coder:1.5b')) {
    if ($requiredModel -notin $installedModels) { Fail "required local model is missing: $requiredModel" }
    Pass "local model installed: $requiredModel"
}

if ($RequireInternetDown) {
    $internetReachable = Test-NetConnection -ComputerName '1.1.1.1' -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($internetReachable) { Fail 'internet is still reachable; air-gap acceptance was requested' }
    Pass 'internet reachability check failed as required for air-gap acceptance'
}

$probe = & $launcherPath --readonly -p 'Reply with exactly OFFLINE_CONTINUE_OK and nothing else.' 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail "Continue local inference probe exited $LASTEXITCODE. Output: $($probe -join [Environment]::NewLine)"
}

$probeText = ($probe -join [Environment]::NewLine).Trim()
if ($probeText -notmatch 'OFFLINE_CONTINUE_OK') {
    Fail "Continue did not return the acceptance token. Output: $probeText"
}
Pass 'Continue produced a response through the local Qwen configuration'

Write-Host 'RESULT green'
