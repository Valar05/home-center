param(
    [switch]$InstallAsDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceConfig = Join-Path $repoRoot '.continue\offline-config.yaml'
$modelFilePath = Join-Path $repoRoot '.continue\models\Modelfile.qwen2.5-coder-7b-8k'
$userContinueDir = Join-Path $HOME '.continue'
$userConfig = Join-Path $userContinueDir 'config.yaml'
$baseModel = 'qwen2.5-coder:7b'
$runtimeModel = 'home-center-qwen-coder:7b-8k'
$autocompleteModel = 'qwen2.5-coder:1.5b'

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Required local command 'ollama' is not available on PATH. This setup does not download dependencies."
}

$cnCommand = Get-Command cn.cmd -ErrorAction SilentlyContinue
if (-not $cnCommand) {
    throw "Required local Continue launcher 'cn.cmd' is not available on PATH. This setup does not download dependencies."
}
$cnPath = $cnCommand.Source

if (-not (Test-Path $sourceConfig)) {
    throw "Repository offline config is missing: $sourceConfig"
}
if (-not (Test-Path $modelFilePath)) {
    throw "Repository offline Qwen Modelfile is missing: $modelFilePath"
}

try {
    $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -Method Get -TimeoutSec 3
} catch {
    throw "Local Ollama is not reachable at 127.0.0.1:11434. $($_.Exception.Message)"
}

$installedModels = @($tags.models | ForEach-Object { $_.name })
$requiredBaseModels = @($baseModel, $autocompleteModel)
$missingModels = @($requiredBaseModels | Where-Object { $_ -notin $installedModels })
if ($missingModels.Count -gt 0) {
    throw "Required local model(s) missing: $($missingModels -join ', '). This setup will not download or replace them with cloud models."
}

if ($runtimeModel -notin $installedModels) {
    & ollama create $runtimeModel -f $modelFilePath
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create pinned local runtime model '$runtimeModel' from '$baseModel'."
    }
}

$showBody = @{model = $runtimeModel} | ConvertTo-Json
$runtimeDetails = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/show' -Method Post -ContentType 'application/json' -Body $showBody -TimeoutSec 5
if ([string]$runtimeDetails.parameters -notmatch '(?m)^num_ctx\s+8192\s*$') {
    throw "Pinned local runtime model '$runtimeModel' does not declare num_ctx 8192."
}

$cnVersion = (& $cnPath --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Continue CLI version probe exited with code $LASTEXITCODE."
}
Write-Host "Continue CLI: $cnVersion"
Write-Host "Continue launcher: $cnPath"
Write-Host "Ollama base models: $($requiredBaseModels -join ', ')"
Write-Host "Ollama runtime model: $runtimeModel (num_ctx 8192)"
Write-Host "Repo config: $sourceConfig"

if ($InstallAsDefault) {
    New-Item -ItemType Directory -Force -Path $userContinueDir | Out-Null
    if (Test-Path $userConfig) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $backup = "$userConfig.before-home-center-offline-$stamp.bak"
        Copy-Item $userConfig $backup
        Write-Host "Backed up existing Continue config: $backup"
    }
    Copy-Item $sourceConfig $userConfig -Force
    Write-Host "Installed local-only Continue config: $userConfig"
} else {
    Write-Host 'Default Continue config was not changed. Use tools/cn-offline.ps1 for the repo-pinned offline lane.'
}

Write-Host 'SETUP ready-for-acceptance'
