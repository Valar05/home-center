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
$modelFilePath = Join-Path $repoRoot '.continue\models\Modelfile.qwen2.5-coder-7b-8k'
$vladJarsPath = Join-Path $repoRoot 'tools\judgment_jars.py'
$jarReceiptPath = Join-Path $repoRoot 'tools\jar_receipt.py'
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

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "Required local command 'python' is not available on PATH. Judgment Jar use may not bypass Vlad's receipt outbox."
}
$pythonPath = $pythonCommand.Source

foreach ($required in @($configPath, $modelFilePath, $vladJarsPath, $jarReceiptPath)) {
    if (-not (Test-Path $required)) {
        throw "Required offline Continue/Judgment Jar component is missing: $required"
    }
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
$requiredBaseModels = @($baseModel, $autocompleteModel)
$missingBaseModels = @($requiredBaseModels | Where-Object { $_ -notin $installedModels })
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

$tempRoot = [System.IO.Path]::GetTempPath()
$runId = [guid]::NewGuid().ToString('N')
$jarContextPath = Join-Path $tempRoot "home-center-jars-$runId.md"
$jarUsagePath = Join-Path $tempRoot "home-center-jar-context-receipts-$runId.json"
$receiptArtifactDir = Join-Path $HOME '.local\state\home-center\vlad-swarm\judgment-jar-receipts\artifacts'
New-Item -ItemType Directory -Force -Path $receiptArtifactDir | Out-Null
$continueOutputPath = Join-Path $receiptArtifactDir "continue-output-$runId.log"

$jarContext = & $pythonPath $vladJarsPath --root $repoRoot --offline prompt 2> $jarUsagePath
if ($LASTEXITCODE -ne 0 -or -not $jarContext) {
    throw "Receipt-governed Judgment Jar context failed. See $jarUsagePath"
}
Set-Content -Path $jarContextPath -Value ($jarContext -join [Environment]::NewLine) -Encoding UTF8 -NoNewline

$registryJson = & $pythonPath $vladJarsPath --root $repoRoot --offline list
if ($LASTEXITCODE -ne 0 -or -not $registryJson) {
    throw "Could not resolve the receipted Judgment Jar registry."
}
$registry = ($registryJson -join [Environment]::NewLine) | ConvertFrom-Json
$activeJarIds = @(
    $registry.jars |
        Where-Object { $_.origin -eq 'repository-operational-core' -and $_.status -eq 'active' } |
        ForEach-Object { [string]$_.id }
)
if ($activeJarIds.Count -eq 0) {
    throw "No active repository Judgment Jars resolved for the offline Continue run."
}

$cnArgs = @('--config', $configPath, '--rule', $jarContextPath)
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

& $cnPath @cnArgs 2>&1 | Tee-Object -FilePath $continueOutputPath
$continueExitCode = $LASTEXITCODE
$outputStatus = if ($continueExitCode -eq 0) { 'completed' } else { 'failed' }

$receiptArgs = @(
    $jarReceiptPath,
    'record'
) + $activeJarIds + @(
    '--output-kind', 'execution_result',
    '--actor', 'Continue offline worker',
    '--intent', 'execute a bounded local coding task under the active Judgment Jars',
    '--surface', 'vlad',
    '--decision-action', "Continue exited with code $continueExitCode",
    '--summary', "Offline Continue created an execution_result with status $outputStatus",
    '--input-text', $Prompt,
    '--output-file', $continueOutputPath,
    '--output-status', $outputStatus,
    '--reference', $continueOutputPath,
    '--reference', $jarUsagePath
)
& $pythonPath @receiptArgs
$receiptExitCode = $LASTEXITCODE

if ($receiptExitCode -eq 0) {
    Remove-Item -Force -ErrorAction SilentlyContinue $jarContextPath, $jarUsagePath
} else {
    throw "Continue output remains at $continueOutputPath, but its typed Judgment Jar receipt capture failed with code $receiptExitCode."
}

if ($continueExitCode -ne 0) {
    throw "Continue CLI exited with code $continueExitCode after the failed result was receipted at $continueOutputPath."
}
