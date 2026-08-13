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

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = ''
    )
    $old = Get-Location
    try {
        if ($WorkingDirectory) { Set-Location -LiteralPath $WorkingDirectory }
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed ($LASTEXITCODE): $FilePath $($Arguments -join ' ')"
        }
    } finally {
        Set-Location -LiteralPath $old
    }
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-CertificateSha256 {
    param([Parameter(Mandatory = $true)][string]$Keystore)
    $output = & keytool -list -v -keystore $Keystore -storepass android -alias androiddebugkey 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "Unable to inspect signing key: $output" }
    $match = [regex]::Match($output, 'SHA256:\s*([0-9A-F:]{95})', [Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $match.Success) { throw 'Signing certificate SHA-256 was not found.' }
    return $match.Groups[1].Value.Replace(':', '').ToLowerInvariant()
}

function Find-Gradle {
    param([string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path -LiteralPath $Explicit)) { throw "Gradle not found: $Explicit" }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    if ($env:HC_GRADLE -and (Test-Path -LiteralPath $env:HC_GRADLE)) {
        return (Resolve-Path -LiteralPath $env:HC_GRADLE).Path
    }
    $known = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.cache/home-center/gradle-8.9/gradle-8.9/bin/gradle.bat'
    if (Test-Path -LiteralPath $known) { return (Resolve-Path -LiteralPath $known).Path }
    $command = Get-Command gradle -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw 'Gradle is unavailable. Supply -GradleExecutable or HC_GRADLE.'
}

function Find-ApkSigner {
    param([Parameter(Mandatory = $true)][string]$SdkRoot)
    $buildTools = Join-Path $SdkRoot 'build-tools'
    if (-not (Test-Path -LiteralPath $buildTools)) { throw "Android build-tools missing: $buildTools" }
    $candidates = @(Get-ChildItem -LiteralPath $buildTools -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @('apksigner', 'apksigner.bat') })
    if (-not $candidates) { throw 'apksigner is unavailable.' }
    return ($candidates | Sort-Object FullName | Select-Object -Last 1).FullName
}

$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$sourceSha = (& git -C $repo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or -not $sourceSha) { throw 'Repository HEAD is unavailable.' }
if ($ExpectedSourceSha -and $sourceSha -ne $ExpectedSourceSha) {
    throw "Source SHA mismatch. expected=$ExpectedSourceSha actual=$sourceSha"
}
$trackedStatus = @(& git -C $repo status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect repository state.' }
if ($trackedStatus.Count -gt 0) { throw "Tracked working tree is dirty: $($trackedStatus -join '; ')" }

Invoke-Checked git @('-C', $repo, 'fetch', 'origin', 'generated/operator-overlay-apk', '--no-tags')
$keySpec = "$GeneratedSigningRef`:operator-overlay-debug.keystore"
Invoke-Checked git @('-C', $repo, 'cat-file', '-e', $keySpec)

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('home-center-overlay-signing-' + [Guid]::NewGuid().ToString('N'))
$tarPath = Join-Path $tempRoot 'signing.tar'
$signingKey = Join-Path $tempRoot 'operator-overlay-debug.keystore'
$home = [Environment]::GetFolderPath('UserProfile')
if (-not $home) { $home = $HOME }
$androidHome = Join-Path $home '.android'
$debugKey = Join-Path $androidHome 'debug.keystore'
$debugBackup = Join-Path $tempRoot 'original-debug.keystore'
$hadDebugKey = Test-Path -LiteralPath $debugKey
$projectRoot = Join-Path $repo 'android/operator-overlay'
$localProperties = Join-Path $projectRoot 'local.properties'
$localPropertiesBackup = Join-Path $tempRoot 'local.properties.original'
$hadLocalProperties = Test-Path -LiteralPath $localProperties
$utf8 = New-Object System.Text.UTF8Encoding($false)

try {
    New-Item -ItemType Directory -Force -Path $tempRoot, $androidHome | Out-Null
    Invoke-Checked git @('-C', $repo, 'archive', '--format=tar', "--output=$tarPath", $GeneratedSigningRef, 'operator-overlay-debug.keystore')
    Invoke-Checked tar @('-xf', $tarPath, '-C', $tempRoot)
    if (-not (Test-Path -LiteralPath $signingKey)) { throw 'Durable signing key extraction failed.' }
    $signingKeySha = Get-Sha256 $signingKey
    $signingCertificateSha = Get-CertificateSha256 $signingKey

    if ($hadDebugKey) { Copy-Item -LiteralPath $debugKey -Destination $debugBackup -Force }
    Copy-Item -LiteralPath $signingKey -Destination $debugKey -Force

    if (-not $AndroidSdk) {
        if ($env:ANDROID_SDK_ROOT) { $AndroidSdk = $env:ANDROID_SDK_ROOT }
        elseif ($env:ANDROID_HOME) { $AndroidSdk = $env:ANDROID_HOME }
    }
    if (-not $AndroidSdk -or -not (Test-Path -LiteralPath $AndroidSdk)) {
        throw 'Android SDK is unavailable. Supply -AndroidSdk or ANDROID_SDK_ROOT.'
    }
    $AndroidSdk = (Resolve-Path -LiteralPath $AndroidSdk).Path
    $env:ANDROID_SDK_ROOT = $AndroidSdk
    $env:ANDROID_HOME = $AndroidSdk

    if ($hadLocalProperties) { Copy-Item -LiteralPath $localProperties -Destination $localPropertiesBackup -Force }
    $escapedSdk = $AndroidSdk.Replace('\', '\\')
    [IO.File]::WriteAllText($localProperties, "sdk.dir=$escapedSdk`n", $utf8)

    $gradle = Find-Gradle $GradleExecutable
    Invoke-Checked $gradle @(':app:testDebugUnitTest', ':app:assembleDebug', '--no-daemon', '--console=plain') $projectRoot

    $builtApk = Join-Path $projectRoot 'app/build/outputs/apk/debug/app-debug.apk'
    if (-not (Test-Path -LiteralPath $builtApk)) { throw 'Built overlay APK is missing.' }
    if (-not $OutputDirectory) { $OutputDirectory = Join-Path $repo 'build/operator-overlay' }
    New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
    $outputApk = Join-Path $OutputDirectory 'operator-overlay-debug.apk'
    Copy-Item -LiteralPath $builtApk -Destination $outputApk -Force

    $apksigner = Find-ApkSigner $AndroidSdk
    $signerOutput = & $apksigner verify --print-certs $outputApk 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "APK signer verification failed: $signerOutput" }
    $signerMatch = [regex]::Match($signerOutput, 'certificate SHA-256 digest:\s*([0-9a-f]{64})', [Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $signerMatch.Success) { throw 'APK certificate SHA-256 was not found.' }
    $apkCertificateSha = $signerMatch.Groups[1].Value.ToLowerInvariant()
    if ($apkCertificateSha -ne $signingCertificateSha) {
        throw "APK signer mismatch. key=$signingCertificateSha apk=$apkCertificateSha"
    }

    if ($ExportKeystore) {
        Copy-Item -LiteralPath $signingKey -Destination (Join-Path $OutputDirectory 'operator-overlay-debug.keystore') -Force
    }

    $gradleText = Get-Content -LiteralPath (Join-Path $projectRoot 'app/build.gradle') -Raw
    $versionNameMatch = [regex]::Match($gradleText, "versionName\s+'([^']+)'")
    $versionCodeMatch = [regex]::Match($gradleText, 'versionCode\s+(\d+)')
    if (-not $versionNameMatch.Success -or -not $versionCodeMatch.Success) { throw 'Overlay version metadata is missing.' }

    $receipt = [ordered]@{
        schemaVersion = 'home-center.operator-overlay-build.v2'
        package = 'com.homecenter.operatoroverlay'
        versionName = $versionNameMatch.Groups[1].Value
        versionCode = [int]$versionCodeMatch.Groups[1].Value
        sourceCommit = $sourceSha
        artifact = 'operator-overlay-debug.apk'
        sha256 = Get-Sha256 $outputApk
        byteCount = (Get-Item -LiteralPath $outputApk).Length
        signingCertificateSha256 = $apkCertificateSha
        signingKeySha256 = $signingKeySha
        signingSourceRef = $GeneratedSigningRef
        durableSigningKey = $true
        testTasks = @(':app:testDebugUnitTest', ':app:assembleDebug')
        installed = $false
        deploymentEvidence = $false
        phoneTouched = $false
        screenInteractionUsed = $false
        createdAtUtc = [DateTime]::UtcNow.ToString('o')
    }
    $receiptPath = Join-Path $OutputDirectory 'operator-overlay-receipt.json'
    [IO.File]::WriteAllText($receiptPath, (($receipt | ConvertTo-Json -Depth 8) + "`n"), $utf8)
    $receipt | ConvertTo-Json -Depth 8 -Compress
} finally {
    if ($hadDebugKey -and (Test-Path -LiteralPath $debugBackup)) {
        Copy-Item -LiteralPath $debugBackup -Destination $debugKey -Force
    } elseif (-not $hadDebugKey) {
        Remove-Item -LiteralPath $debugKey -Force -ErrorAction SilentlyContinue
    }
    if ($hadLocalProperties -and (Test-Path -LiteralPath $localPropertiesBackup)) {
        Copy-Item -LiteralPath $localPropertiesBackup -Destination $localProperties -Force
    } elseif (-not $hadLocalProperties) {
        Remove-Item -LiteralPath $localProperties -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
