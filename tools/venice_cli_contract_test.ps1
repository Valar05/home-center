$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$cli = Join-Path $PSScriptRoot 'venice_cli.ps1'
$installer = Join-Path $PSScriptRoot 'install_venice_cli.ps1'
foreach ($path in @($cli, $installer)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "missing required Venice CLI file: $path" }
    $tokens = $null
    $errors = $null
    [void][Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw ("PowerShell parse errors in {0}: {1}" -f $path, (($errors | ForEach-Object { $_.Message }) -join '; ')) }
}

$text = Get-Content -LiteralPath $cli -Raw
$installText = Get-Content -LiteralPath $installer -Raw

$required = @(
    'venice-aperture.ps1',
    'VENICE_IDENTITY_PROFILE.md',
    '.env.venice',
    'function Test-VeniceRecord',
    "speech.source -ne 'local-venice'",
    'exact Venice speech SHA-256 mismatch',
    'aperture result failed identity/byte verification and no matching durable Nerve Silk record was found',
    'Find-DurableApertureRecord -PromptSha256 $promptSha',
    'work\\nerve-silk\\latest.json',
    '127.0.0.1',
    '47261',
    'transformedByCli = $false',
    "cloudFallback = $false",
    '[Console]::Error.WriteLine($errorEnvelope)',
    "exit 2",
    "exit 3",
    "exit 5"
)
foreach ($needle in $required) {
    if (-not $text.Contains($needle)) { throw "Venice CLI lost required invariant: $needle" }
}

if ($text -match 'OPENAI_API_KEY|ANTHROPIC_API_KEY|VENICE_API_KEY|api\.openai\.com|api\.anthropic\.com') {
    throw 'Venice CLI must not contain cloud model credentials or fallback endpoints.'
}
if ($text -match 'computer_hands|shell\.exec|browser\.click|SendKeys|Set-Clipboard|Get-Clipboard') {
    throw 'Venice speech CLI must not import body transport or UI-driving behavior.'
}
if (-not $installText.Contains("'venice.cmd'")) { throw 'installer must create the first-class venice command' }
if (-not $installText.Contains("'venice.ps1'")) { throw 'installer must install the canonical CLI script' }

Write-Output '{"ok":true,"contract":"home-center.venice-cli.v1","canonicalLocalSpeech":true,"durableRecovery":true,"cloudFallback":false,"bodySeparated":true}'
