[CmdletBinding()]
param(
    [string]$ExpectedPr317 = 'df17c17fb9fa7fa8019abc5ce78d212d9b51ef53',
    [string]$ExpectedPr318 = '14f01ca85534353d042cb2141f484ec13fac59bb',
    [string]$ArtifactDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runId = 'desktop-p0-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
if (-not $ArtifactDirectory) {
    $base = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { [IO.Path]::GetTempPath() }
    $ArtifactDirectory = Join-Path $base "HomeCenter\desktop-p0-offload\$runId"
}
New-Item -ItemType Directory -Force -Path $ArtifactDirectory | Out-Null

$wtRoot = Join-Path ([IO.Path]::GetTempPath()) $runId
$wt317 = Join-Path $wtRoot 'pr317'
$wt318 = Join-Path $wtRoot 'pr318'
New-Item -ItemType Directory -Force -Path $wtRoot | Out-Null

$steps = New-Object System.Collections.Generic.List[object]
$artifacts = New-Object System.Collections.Generic.List[object]
$overall = $true

function Add-Step {
    param([string]$Id, [scriptblock]$Body)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $value = & $Body
        $sw.Stop()
        $script:steps.Add([ordered]@{id=$Id; ok=$true; elapsedMs=$sw.ElapsedMilliseconds; result=$value})
        return $value
    } catch {
        $sw.Stop()
        $script:overall = $false
        $script:steps.Add([ordered]@{id=$Id; ok=$false; elapsedMs=$sw.ElapsedMilliseconds; error=$_.Exception.Message})
        return $null
    }
}

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory='')
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

function Add-Artifact {
    param([string]$Kind, [string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { throw "Artifact missing: $Path" }
    $item = Get-Item -LiteralPath $Path
    $sha = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    $script:artifacts.Add([ordered]@{kind=$Kind; path=$item.FullName; byteCount=$item.Length; sha256=$sha})
    return $sha
}

$python = (Get-Command python -ErrorAction SilentlyContinue)
$node = (Get-Command node -ErrorAction SilentlyContinue)
$ffmpeg = (Get-Command ffmpeg -ErrorAction SilentlyContinue)

Add-Step 'desktop_identity' {
    [ordered]@{
        computerName = $env:COMPUTERNAME
        userName = [Environment]::UserName
        os = [Environment]::OSVersion.VersionString
        powershell = $PSVersionTable.PSVersion.ToString()
        repo = $repo
        phoneTouched = $false
    }
} | Out-Null

Add-Step 'toolchain' {
    if (-not $python) { throw 'python is unavailable on desktop' }
    if (-not $node) { throw 'node is unavailable on desktop' }
    if (-not $ffmpeg) { throw 'ffmpeg is unavailable on desktop' }
    [ordered]@{python=$python.Source; node=$node.Source; ffmpeg=$ffmpeg.Source}
} | Out-Null

Add-Step 'fetch_exact_heads' {
    Invoke-Checked git @('-C',$repo,'fetch','--no-tags','origin','fortress/pocket-tts-nightcore','fortress/night-core-beard','generated/operator-overlay-apk')
    $actual317 = (& git -C $repo rev-parse 'origin/fortress/pocket-tts-nightcore').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve PR317 remote head' }
    $actual318 = (& git -C $repo rev-parse 'origin/fortress/night-core-beard').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve PR318 remote head' }
    if ($actual317 -ne $ExpectedPr317) { throw "PR317 moved: expected=$ExpectedPr317 actual=$actual317" }
    if ($actual318 -ne $ExpectedPr318) { throw "PR318 moved: expected=$ExpectedPr318 actual=$actual318" }
    [ordered]@{pr317=$actual317; pr318=$actual318}
} | Out-Null

Add-Step 'prepare_worktrees' {
    & git -C $repo worktree remove --force $wt317 2>$null
    & git -C $repo worktree remove --force $wt318 2>$null
    & git -C $repo worktree prune
    Remove-Item -LiteralPath $wt317,$wt318 -Recurse -Force -ErrorAction SilentlyContinue
    Invoke-Checked git @('-C',$repo,'worktree','add','--detach',$wt317,$ExpectedPr317)
    Invoke-Checked git @('-C',$repo,'worktree','add','--detach',$wt318,$ExpectedPr318)
    [ordered]@{pr317=$wt317; pr318=$wt318}
} | Out-Null

Add-Step 'pr318_source_contracts' {
    if (-not (Test-Path -LiteralPath $wt318)) { throw 'PR318 worktree unavailable' }
    foreach ($test in @('tools/test_adam_overlay_contract.py','tools/test_night_core_contract.py','tools/test_adam_auto_router_contract.py')) {
        Invoke-Checked $python.Source @($test) $wt318
    }
    'PASS'
} | Out-Null

Add-Step 'pr318_signed_overlay_build' {
    if (-not (Test-Path -LiteralPath $wt318)) { throw 'PR318 worktree unavailable' }
    $out = Join-Path $ArtifactDirectory 'pr318-overlay'
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    $build = Join-Path $wt318 'tools/build_operator_overlay_signed.ps1'
    if (-not (Test-Path -LiteralPath $build)) { throw 'signed overlay build script missing' }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $build -RepositoryRoot $wt318 -ExpectedSourceSha $ExpectedPr318 -OutputDirectory $out
    if ($LASTEXITCODE -ne 0) { throw "signed overlay build failed rc=$LASTEXITCODE" }
    $apk = Join-Path $out 'operator-overlay-debug.apk'
    $receipt = Join-Path $out 'operator-overlay-receipt.json'
    Add-Artifact 'pr318-overlay-apk' $apk | Out-Null
    Add-Artifact 'pr318-overlay-build-receipt' $receipt | Out-Null
    Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
} | Out-Null

Add-Step 'pr317_performance_contract' {
    if (-not (Test-Path -LiteralPath $wt317)) { throw 'PR317 worktree unavailable' }
    Invoke-Checked $node.Source @('tools/pocket_tts_performance_contract_test.mjs') $wt317
    Invoke-Checked $python.Source @('-m','py_compile','tools/fortress_status_read.py') $wt317
    'PASS'
} | Out-Null

Add-Step 'pr317_desktop_ffmpeg_dryrun' {
    if (-not (Test-Path -LiteralPath $wt317)) { throw 'PR317 worktree unavailable' }
    $dry = Join-Path $ArtifactDirectory 'pr317-ffmpeg-dryrun'
    New-Item -ItemType Directory -Force -Path $dry | Out-Null
    $py = Join-Path $dry 'dryrun.py'
    $script = @'
import hashlib, importlib.util, json, os, pathlib, struct, sys, wave
repo=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
os.environ['FORTRESS_HOME_CENTER']=str(repo)
os.environ['FORTRESS_POCKET_TTS_PERFORMANCE_CONFIG']=str(repo/'config/fortress-pocket-tts-performance.json')
path=repo/'tools/fortress_status_read.py'
spec=importlib.util.spec_from_file_location('fortress_status_read_desktop',path)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
src=out/'synthetic.wav'
rate=16000; frames=rate//4
with wave.open(str(src),'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(b'\x00\x00'*frames)
results={}
for i,name in enumerate(('orandroid67','she-ra')):
    _,persona=mod.load_performance(name)
    processed,receipt=mod.postprocess(src,persona,i)
    raw=processed.read_bytes()
    results[name]={'processing':receipt,'sha256':hashlib.sha256(raw).hexdigest(),'byteCount':len(raw)}
(out/'desktop-ffmpeg-dryrun.json').write_text(json.dumps({'schema':'fortress.pocket-tts.desktop-prep.v1','phoneTouched':False,'results':results},indent=2,sort_keys=True)+'\n',encoding='utf-8')
'@
    Set-Content -LiteralPath $py -Value $script -Encoding UTF8
    Invoke-Checked $python.Source @($py,$wt317,$dry)
    $receipt = Join-Path $dry 'desktop-ffmpeg-dryrun.json'
    Add-Artifact 'pr317-ffmpeg-dryrun-receipt' $receipt | Out-Null
    Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
} | Out-Null

Add-Step 'pr317_phone_payload_package' {
    if (-not (Test-Path -LiteralPath $wt317)) { throw 'PR317 worktree unavailable' }
    $staging = Join-Path $ArtifactDirectory 'pr317-payload'
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path (Join-Path $staging 'tools'),(Join-Path $staging 'config'),(Join-Path $staging 'docs/evidence/nightcore-design') | Out-Null
    Copy-Item -LiteralPath (Join-Path $wt317 'tools/fortress_status_read.py') -Destination (Join-Path $staging 'tools/fortress_status_read.py')
    Copy-Item -LiteralPath (Join-Path $wt317 'tools/fortress_pocket_tts_phone_canary.sh') -Destination (Join-Path $staging 'tools/fortress_pocket_tts_phone_canary.sh')
    Copy-Item -LiteralPath (Join-Path $wt317 'tools/pocket_tts_performance_contract_test.mjs') -Destination (Join-Path $staging 'tools/pocket_tts_performance_contract_test.mjs')
    Copy-Item -LiteralPath (Join-Path $wt317 'config/fortress-pocket-tts-performance.json') -Destination (Join-Path $staging 'config/fortress-pocket-tts-performance.json')
    Copy-Item -LiteralPath (Join-Path $wt317 'docs/evidence/nightcore-design/hunger-hyperbolic-profile-20260814.json') -Destination (Join-Path $staging 'docs/evidence/nightcore-design/hunger-hyperbolic-profile-20260814.json')
    $manifest = [ordered]@{
        schema='fortress.pocket-tts.desktop-payload.v1'
        sourceCommit=$ExpectedPr317
        providerLock='pocket-home-center'
        engineLock='pocket-tts-phone'
        playbackLock='com.dclar.homecenter/.PocketTtsPlaybackActivity'
        phoneTouched=$false
        physicalPlaybackPending=$true
        createdAtUtc=[DateTime]::UtcNow.ToString('o')
    }
    $manifestPath = Join-Path $staging 'manifest.json'
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    $zip = Join-Path $ArtifactDirectory 'pr317-pocket-tts-phone-payload.zip'
    Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
    Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zip -CompressionLevel Optimal
    Add-Artifact 'pr317-pocket-tts-phone-payload' $zip | Out-Null
    Add-Artifact 'pr317-pocket-tts-payload-manifest' $manifestPath | Out-Null
    $manifest
} | Out-Null

$receipt = [ordered]@{
    schema = 'fortress.desktop-p0-offload.v1'
    commandId = $runId
    ok = $overall
    targetHost = 'windows-hands-01/THECAULDRON'
    repository = 'Valar05/home-center'
    source = [ordered]@{pr317=$ExpectedPr317; pr318=$ExpectedPr318}
    phoneTouched = $false
    heavyWorkLocation = 'desktop'
    physicalAndroidAcceptancePending = $true
    homeCenterReturnReceiptPending = $true
    steps = $steps
    artifacts = $artifacts
    nextIrreduciblePhoneWork = @(
        'Home Center relay/device-queue liveness proof',
        'PR318 signer-safe install + overlay/runtime observation',
        'PR317 Pocket TTS generation/playback + MediaSession completion evidence'
    )
    createdAtUtc = [DateTime]::UtcNow.ToString('o')
}
$receiptPath = Join-Path $ArtifactDirectory 'desktop-p0-offload-receipt.json'
$receipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
Add-Artifact 'desktop-p0-offload-receipt' $receiptPath | Out-Null
$receipt.artifacts = $artifacts
$receipt | ConvertTo-Json -Depth 12 -Compress

try { & git -C $repo worktree remove --force $wt317 2>$null } catch {}
try { & git -C $repo worktree remove --force $wt318 2>$null } catch {}
try { & git -C $repo worktree prune 2>$null } catch {}

if (-not $overall) { exit 2 }
