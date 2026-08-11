param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ContinueArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$configPath = Join-Path $repoRoot '.continue\offline-config.yaml'
$rulesPath = Join-Path $repoRoot '.continue\rules'

foreach ($commandName in @('ollama', 'cn')) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required local command '$commandName' is not available on PATH."
    }
}

if (-not (Test-Path $configPath)) {
    throw "Offline Continue config is missing: $configPath"
}

try {
    $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -Method Get -TimeoutSec 3
} catch {
    throw "Local Ollama is not reachable at 127.0.0.1:11434. Start the installed Ollama service; no cloud fallback will be used. $($_.Exception.Message)"
}

$installedModels = @($tags.models | ForEach-Object { $_.name })
$requiredModels = @('qwen2.5-coder:7b', 'qwen2.5-coder:1.5b')
$missingModels = @($requiredModels | Where-Object { $_ -notin $installedModels })
if ($missingModels.Count -gt 0) {
    throw "Required local Ollama model(s) are not installed: $($missingModels -join ', '). This launcher will not download or substitute a cloud model."
}

$cnArgs = @('--config', $configPath)
Get-ChildItem -Path $rulesPath -Filter '*judgement-jar*.md' -File |
    Sort-Object Name |
    ForEach-Object {
        $cnArgs += @('--rule', $_.FullName)
    }

if ($ContinueArgs) {
    $cnArgs += $ContinueArgs
}

& cn @cnArgs
$continueExitCode = $LASTEXITCODE
if ($continueExitCode -ne 0) {
    throw "Continue CLI exited with code $continueExitCode."
}
