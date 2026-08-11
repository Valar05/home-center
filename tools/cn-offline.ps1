param(
    [string]$Prompt = '',
    [switch]$Readonly,
    [string[]]$Allow = @(),
    [string[]]$Exclude = @(),
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$configPath = Join-Path $repoRoot '.continue\offline-config.yaml'
$rulesPath = Join-Path $repoRoot '.continue\rules'
$modelFilePath = Join-Path $repoRoot '.continue\models\Modelfile.qwen2.5-coder-7b-8k'
$baseModel = 'qwen2.5-coder:7b'
$runtimeModel = 'home-center-qwen-coder:7b-8k'
$autocompleteModel = 'qwen2.5-coder:1.5b'

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Required local command 'ollama' is not available on PATH."
}

$cnCommand = Get-Command cn.cmd -ErrorAction SilentlyContinue
if (-not $cnCommand) {
    throw "Required local Continue launcher 'cn.cmd' is not available on PATH. The PowerShell npm shim cn.ps1 is intentionally not used because it exits its caller."
}
$cnPath = $cnCommand.Source

if (-not (Test-Path $configPath)) {
    throw "Offline Continue config is missing: $configPath"
}
if (-not (Test-Path $modelFilePath)) {
    throw "Offline Qwen Modelfile is missing: $modelFilePath"
}

function Get-LocalOllamaTags {
    try {
        return Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -Method Get -TimeoutSec 3
    } catch {
        throw "Local Ollama is not reachable at 127.0.0.1:11434. Start the installed Ollama service; no cloud fallback will be used. $($_.Exception.Message)"
    }
}

$tags = Get-LocalOllamaTags
$installedModels = @($tags.models | ForEach-Object { $_.name })
$missingBaseModels = @($baseModel, $autocompleteModel | Where-Object { $_ -notin $installedModels })
if ($missingBaseModels.Count -gt 0) {
    throw "Required local Ollama base model(s) are not installed: $($missingBaseModels -join ', '). This launcher will not download or substitute a cloud model."
}

if ($runtimeModel -notin $installedModels) {
    & ollama create $runtimeModel -f $modelFilePath
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the pinned local Ollama runtime model '$runtimeModel' from already-installed '$baseModel'."
    }
    $tags = Get-LocalOllamaTags
    $installedModels = @($tags.models | ForEach-Object { $_.name })
    if ($runtimeModel -notin $installedModels) {
        throw "Pinned local Ollama runtime model '$runtimeModel' was not present after local creation."
    }
}

$showBody = @{model = $runtimeModel} | ConvertTo-Json
$runtimeDetails = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/show' -Method Post -ContentType 'application/json' -Body $showBody -TimeoutSec 5
if ([string]$runtimeDetails.parameters -notmatch '(?m)^num_ctx\s+8192\s*$') {
    throw "Pinned local Ollama runtime model '$runtimeModel' does not declare num_ctx 8192."
}

$cnArgs = @('--config', $configPath)
Get-ChildItem -Path $rulesPath -Filter '*judgement-jar*.md' -File |
    Sort-Object Name |
    ForEach-Object {
        $cnArgs += @('--rule', $_.FullName)
    }

if ($Readonly) {
    $cnArgs += '--readonly'
}
foreach ($toolName in $Allow) {
    if ($toolName) { $cnArgs += @('--allow', $toolName) }
}
foreach ($toolName in $Exclude) {
    if ($toolName) { $cnArgs += @('--exclude', $toolName) }
}
if ($Prompt) {
    $cnArgs += @('-p', $Prompt)
}
if ($ExtraArgs) {
    $cnArgs += $ExtraArgs
}

& $cnPath @cnArgs
$continueExitCode = $LASTEXITCODE
if ($continueExitCode -ne 0) {
    throw "Continue CLI exited with code $continueExitCode."
}
