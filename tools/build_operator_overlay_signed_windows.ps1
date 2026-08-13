[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$ExpectedSourceSha = '',
    [string]$OutputDirectory = '',
    [string]$GeneratedSigningRef = 'origin/generated/operator-overlay-apk',
    [string]$GradleExecutable = '',
    [string]$AndroidSdk = '',
    [switch]$ExportKeystore
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$canonicalBuilder = Join-Path $PSScriptRoot 'build_operator_overlay_signed.ps1'
if (-not (Test-Path -LiteralPath $canonicalBuilder)) {
    throw "Canonical signed builder is missing: $canonicalBuilder"
}

$canonicalSource = [IO.File]::ReadAllText($canonicalBuilder)
$start = $canonicalSource.IndexOf('function Invoke-Checked {', [StringComparison]::Ordinal)
$end = $canonicalSource.IndexOf('function Get-Sha256 {', [StringComparison]::Ordinal)
if ($start -lt 0 -or $end -le $start) {
    throw 'Canonical signed builder Invoke-Checked boundaries are missing.'
}
if ($canonicalSource -notmatch [regex]::Escape('if ($apkCertificateSha -ne $signingCertificateSha)')) {
    throw 'Canonical signed builder no longer verifies APK/key certificate equality.'
}
if ($canonicalSource -notmatch [regex]::Escape('durableSigningKey = $true')) {
    throw 'Canonical signed builder no longer emits durable-signing evidence.'
}

$newline = if ($canonicalSource.Contains("`r`n")) { "`r`n" } else { "`n" }
$invokeChecked = @(
    'function Invoke-Checked {',
    '    param(',
    '        [Parameter(Mandatory = $true)][string]$FilePath,',
    '        [string[]]$Arguments = @(),',
    "        [string]`$WorkingDirectory = ''",
    '    )',
    '    $oldLocation = Get-Location',
    '    $savedErrorActionPreference = $ErrorActionPreference',
    '    try {',
    '        if ($WorkingDirectory) { Set-Location -LiteralPath $WorkingDirectory }',
    '        # Windows PowerShell 5.1 maps native stderr to the error stream. Git writes',
    '        # ordinary fetch progress there, so inspect the native exit code explicitly.',
    "        `$ErrorActionPreference = 'Continue'",
    '        & $FilePath @Arguments',
    '        $exitCode = $LASTEXITCODE',
    '        $ErrorActionPreference = $savedErrorActionPreference',
    '        if ($exitCode -ne 0) {',
    '            throw "Command failed ($exitCode): $FilePath $($Arguments -join '' '')"',
    '        }',
    '    } finally {',
    '        $ErrorActionPreference = $savedErrorActionPreference',
    '        Set-Location -LiteralPath $oldLocation',
    '    }',
    '}',
    ''
) -join $newline

$patchedSource = $canonicalSource.Substring(0, $start) + $invokeChecked + $canonicalSource.Substring($end)
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('home-center-overlay-windows-wrapper-' + [Guid]::NewGuid().ToString('N'))
$patchedBuilder = Join-Path $tempRoot 'build_operator_overlay_signed.ps1'
$utf8 = New-Object System.Text.UTF8Encoding($false)

try {
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    [IO.File]::WriteAllText($patchedBuilder, $patchedSource, $utf8)
    $tokens = $null
    $parseErrors = $null
    [Management.Automation.Language.Parser]::ParseFile(
        $patchedBuilder,
        [ref]$tokens,
        [ref]$parseErrors
    ) | Out-Null
    if ($parseErrors.Count -gt 0) {
        throw "Patched signed builder failed to parse: $($parseErrors.Message -join '; ')"
    }

    $parameters = @{
        RepositoryRoot = $RepositoryRoot
        ExpectedSourceSha = $ExpectedSourceSha
        OutputDirectory = $OutputDirectory
        GeneratedSigningRef = $GeneratedSigningRef
        GradleExecutable = $GradleExecutable
        AndroidSdk = $AndroidSdk
    }
    if ($ExportKeystore) { $parameters.ExportKeystore = $true }
    & $patchedBuilder @parameters
} finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
