param(
    [switch]$InstallAsDefault
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceConfig = Join-Path $repoRoot '.continue\offline-config.yaml'
$userContinueDir = Join-Path $HOME '.continue'
$userConfig = Join-Path $userContinueDir 'config.yaml'

foreach ($commandName in @('ollama', 'cn')) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required local command '$commandName' is not available on PATH. This setup does not download dependencies."
    }
}

if (-not (Test-Path $sourceConfig)) {
    throw "Repository offline config is missing: $sourceConfig"
}

try {
    $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -Method Get -TimeoutSec 3
} catch {
    throw "Local Ollama is not reachable at 127.0.0.1:11434. $($_.Exception.Message)"
}

$installedModels = @($tags.models | ForEach-Object { $_.name })
$requiredModels = @('qwen2.5-coder:7b', 'qwen2.5-coder:1.5b')
$missingModels = @($requiredModels | Where-Object { $_ -notin $installedModels })
if ($missingModels.Count -gt 0) {
    throw "Required local model(s) missing: $($missingModels -join ', '). This setup will not download or replace them with cloud models."
}

$cnVersion = (& cn --version 2>&1 | Out-String).Trim()
Write-Host "Continue CLI: $cnVersion"
Write-Host "Ollama models: $($requiredModels -join ', ')"
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
