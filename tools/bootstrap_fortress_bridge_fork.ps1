param(
    [string]$Owner = 'Valar05',
    [string]$Upstream = 'RikkaApps/Shizuku',
    [string]$ForkName = 'Shizuku',
    [string]$CheckoutRoot = "$HOME\src",
    [string]$WorkBranch = 'fortress-bridge',
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Step([string]$message) { Write-Host "[fortress-bridge] $message" }
function Require-Command([string]$name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { throw "Required command is unavailable: $name" }
}
function Invoke-Checked([scriptblock]$body, [string]$label) {
    & $body
    if ($LASTEXITCODE -ne 0) { throw "$label failed with exit code $LASTEXITCODE" }
}

Require-Command git
Require-Command gh

Step 'Verifying GitHub authentication'
Invoke-Checked { gh auth status } 'gh auth status'

$fork = "$Owner/$ForkName"
$forkExists = $true
gh repo view $fork --json nameWithOwner,isFork,parent 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { $forkExists = $false }

if (-not $forkExists) {
    Step "Creating genuine GitHub fork $fork from $Upstream"
    Invoke-Checked { gh repo fork $Upstream --org $Owner --fork-name $ForkName --clone=false --remote=false } 'gh repo fork'
} else {
    Step "Fork already exists: $fork"
}

$meta = gh repo view $fork --json nameWithOwner,isFork,parent | ConvertFrom-Json
if (-not $meta.isFork) { throw "$fork exists but GitHub does not identify it as a fork; refusing to launder a copy as the commissioned fork." }
if (-not $meta.parent -or $meta.parent.nameWithOwner -ne $Upstream) { throw "$fork parent is not $Upstream; refusing to continue." }

New-Item -ItemType Directory -Force -Path $CheckoutRoot | Out-Null
$checkout = Join-Path $CheckoutRoot 'fortress-bridge-shizuku'
if (-not (Test-Path (Join-Path $checkout '.git'))) {
    Step "Cloning $fork to $checkout"
    Invoke-Checked { git clone "https://github.com/$fork.git" $checkout } 'git clone fork'
}

Push-Location $checkout
try {
    $origin = (git remote get-url origin).Trim()
    if ($origin -notmatch [regex]::Escape("$Owner/$ForkName")) { throw "Unexpected origin: $origin" }

    if (-not (git remote | Where-Object { $_ -eq 'upstream' })) {
        git remote add upstream "https://github.com/$Upstream.git"
    }
    Invoke-Checked { git fetch origin } 'git fetch origin'
    Invoke-Checked { git fetch upstream } 'git fetch upstream'

    $branchExists = $false
    git show-ref --verify --quiet "refs/heads/$WorkBranch"
    if ($LASTEXITCODE -eq 0) { $branchExists = $true }
    if ($branchExists) {
        Invoke-Checked { git checkout $WorkBranch } 'git checkout work branch'
    } else {
        Invoke-Checked { git checkout -b $WorkBranch upstream/master } 'git create work branch'
    }

    Step 'Applying Fortress Bridge identity changes without rewriting Shizuku Binder/server machinery'

    $buildFile = 'manager/build.gradle'
    $build = Get-Content $buildFile -Raw
    $build = $build.Replace("namespace 'moe.shizuku.manager'", "namespace 'com.valar05.fortressbridge'")
    $build = $build.Replace('applicationId "moe.shizuku.privileged.api"', 'applicationId "com.valar05.fortressbridge"')
    $build = $build.Replace('outputFileName = "shizuku-v${variant.versionName}-${variant.name}.apk"', 'outputFileName = "fortress-bridge-v${variant.versionName}-${variant.name}.apk"')
    Set-Content -Path $buildFile -Value $build -NoNewline

    $manifestFile = 'manager/src/main/AndroidManifest.xml'
    $manifest = Get-Content $manifestFile -Raw
    $manifest = $manifest.Replace('moe.shizuku.manager.permission-group.API', 'com.valar05.fortressbridge.permission-group.API')
    $manifest = $manifest.Replace('moe.shizuku.manager.permission.MANAGER', 'com.valar05.fortressbridge.permission.MANAGER')
    $manifest = $manifest.Replace('moe.shizuku.manager.permission.API_V23', 'com.valar05.fortressbridge.permission.API_V23')
    $manifest = $manifest.Replace('moe.shizuku.manager.permission.API"', 'com.valar05.fortressbridge.permission.API"')
    Set-Content -Path $manifestFile -Value $manifest -NoNewline

    $manifestJava = 'manager/src/main/java/moe/shizuku/manager/Manifest.java'
    $manifestClass = Get-Content $manifestJava -Raw
    $manifestClass = $manifestClass.Replace('moe.shizuku.manager.permission.API_V23', 'com.valar05.fortressbridge.permission.API_V23')
    Set-Content -Path $manifestJava -Value $manifestClass -NoNewline

    Get-ChildItem 'manager/src/main/res' -Recurse -File -Filter '*.xml' | ForEach-Object {
        $text = Get-Content $_.FullName -Raw
        if ($text -match '>Shizuku<') {
            $updated = $text.Replace('>Shizuku<', '>Fortress Bridge<')
            if ($updated -ne $text) { Set-Content -Path $_.FullName -Value $updated -NoNewline }
        }
    }

    $brandDoc = 'FORTRESS_BRIDGE.md'
    @'
# Fortress Bridge

Fortress Bridge is Drew Clarke / Valar05's fork of RikkaApps/Shizuku.

It preserves upstream Shizuku Binder/server machinery and Apache-2.0 attribution while giving the manager a distinct Fortress identity and lifecycle contract.

## Lifecycle contract

- Unrooted Android privilege still requires an Android-authorized ADB/bootstrap path.
- Always-on Wireless debugging is acceptable and preferred when it forms the durable phone <-> THECAULDRON relationship.
- Android 13+ upstream boot recovery using `WRITE_SECURE_SETTINGS`, `adb_wifi_enabled`, `ADB_ENABLED`, `adb_allowed_connection_time=0`, mDNS TLS discovery, and the persisted ADB key is preserved as the baseline recovery organ.
- `Server is not running` must become explicit bridge state, not an unexplained client traceback.
- Fortress must distinguish installed / paired / server-running / shell-identity / client-callable / last-bootstrap / recovery-route / physical-action-required.

## Rebranding

The fork must not present itself as upstream Shizuku. App/package/permission/artwork changes are Fortress-owned while upstream attribution and license remain intact.
'@ | Set-Content -Path $brandDoc -NoNewline

    Invoke-Checked { git diff --check } 'git diff --check'

    if ($Build) {
        Step 'Building manager debug APK on THECAULDRON'
        Invoke-Checked { .\gradlew.bat :manager:assembleDebug --no-daemon } 'Gradle debug build'
    }

    $dirty = git status --porcelain
    if ($dirty) {
        git add manager/build.gradle manager/src/main/AndroidManifest.xml manager/src/main/java/moe/shizuku/manager/Manifest.java manager/src/main/res FORTRESS_BRIDGE.md
        Invoke-Checked { git commit -m 'Fortress Bridge: establish distinct manager identity' } 'git commit'
        Invoke-Checked { git push -u origin $WorkBranch } 'git push'
    } else {
        Step 'No identity diff to commit'
    }

    $head = (git rev-parse HEAD).Trim()
    $upstreamHead = (git rev-parse upstream/master).Trim()
    $receipt = [ordered]@{
        kind = 'fortress.bridge.bootstrap.receipt.v1'
        fork = $fork
        githubForkVerified = $true
        upstream = $Upstream
        upstreamHead = $upstreamHead
        branch = $WorkBranch
        head = $head
        checkout = $checkout
        buildRequested = [bool]$Build
        generatedAt = (Get-Date).ToUniversalTime().ToString('o')
    }
    $receipt | ConvertTo-Json -Depth 4
}
finally {
    Pop-Location
}
