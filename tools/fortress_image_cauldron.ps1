$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RequestPath = 'C:\Users\Public\fortress-image-request.json'
$ResultPath = 'C:\Users\Public\fortress-image-result.json'
$PrimaryPng = 'C:\Users\Public\fortress-image-latest.png'
$ComfyRoot = Join-Path $env:LOCALAPPDATA 'VeniceImageBridge\ComfyUI'
$CheckpointRoot = Join-Path $ComfyRoot 'models\checkpoints'
$LoraRoot = Join-Path $ComfyRoot 'models\loras'
$OutputRoot = Join-Path $ComfyRoot 'output'
$Comfy = 'http://127.0.0.1:8188'

function Write-Result([System.Collections.IDictionary]$Result) {
    $Result['runtime'] = 'fortress_image_cauldron.ps1'
    $Result['generatedAt'] = (Get-Date).ToString('o')
    $Result | ConvertTo-Json -Depth 30 | Set-Content -Encoding UTF8 $ResultPath
    $Result | ConvertTo-Json -Compress -Depth 30
}

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Assert-SafeFilename([string]$Name, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Name) -or
        [IO.Path]::GetFileName($Name) -ne $Name -or
        -not $Name.EndsWith('.safetensors', [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must be a .safetensors basename: $Name"
    }
}

function Resolve-AssetPath($Asset) {
    Assert-SafeFilename ([string]$Asset.filename) 'managed asset filename'
    switch ([string]$Asset.kind) {
        'checkpoint' { return Join-Path $CheckpointRoot ([string]$Asset.filename) }
        'lora' { return Join-Path $LoraRoot ([string]$Asset.filename) }
        default { throw "Unsupported managed asset kind: $($Asset.kind)" }
    }
}

function Get-ManagedAssetStatus($Asset) {
    $path = Resolve-AssetPath $Asset
    $exists = Test-Path -LiteralPath $path -PathType Leaf
    $actual = if ($exists) { Get-Sha256 $path } else { $null }
    $expected = ([string]$Asset.sha256).ToLowerInvariant()
    $bytes = if ($exists) { (Get-Item -LiteralPath $path).Length } else { 0 }
    return [ordered]@{
        kind = [string]$Asset.kind
        filename = [string]$Asset.filename
        path = $path
        exists = [bool]$exists
        bytes = [int64]$bytes
        sha256 = $actual
        expectedSha256 = $expected
        verified = [bool]($exists -and $actual -eq $expected)
        source = [string]$Asset.source
        revision = [string]$Asset.revision
    }
}

function Install-ManagedAsset($Asset) {
    $status = Get-ManagedAssetStatus $Asset
    if ($status.verified) {
        $status['state'] = 'already_verified'
        return $status
    }

    $dest = [string]$status.path
    $dir = Split-Path -Parent $dest
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $tmp = "$dest.download-$PID"
    Remove-Item -Force -ErrorAction SilentlyContinue $tmp

    $url = [string]$Asset.url
    if (-not $url.StartsWith('https://huggingface.co/', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Managed image assets may only download from pinned huggingface.co URLs: $url"
    }

    & curl.exe -L --fail --retry 3 --retry-delay 2 --output $tmp $url
    if ($LASTEXITCODE -ne 0) {
        Remove-Item -Force -ErrorAction SilentlyContinue $tmp
        throw "curl.exe failed downloading $($Asset.filename), exit $LASTEXITCODE"
    }

    $actual = Get-Sha256 $tmp
    $expected = ([string]$Asset.sha256).ToLowerInvariant()
    if ($actual -ne $expected) {
        Remove-Item -Force -ErrorAction SilentlyContinue $tmp
        throw "SHA-256 mismatch for $($Asset.filename): expected=$expected actual=$actual"
    }

    $expectedBytes = [int64]$Asset.bytes
    $actualBytes = (Get-Item -LiteralPath $tmp).Length
    if ($expectedBytes -gt 0 -and $actualBytes -ne $expectedBytes) {
        Remove-Item -Force -ErrorAction SilentlyContinue $tmp
        throw "Byte-length mismatch for $($Asset.filename): expected=$expectedBytes actual=$actualBytes"
    }

    if (Test-Path -LiteralPath $dest) { Remove-Item -Force -LiteralPath $dest }
    Move-Item -Force -LiteralPath $tmp -Destination $dest
    $after = Get-ManagedAssetStatus $Asset
    if (-not $after.verified) { throw "Managed asset failed readback verification: $dest" }
    $after['state'] = 'downloaded_and_verified'
    return $after
}

function Assert-Comfy {
    try {
        $stats = Invoke-RestMethod -TimeoutSec 5 "$Comfy/system_stats"
        return $stats
    } catch {
        throw "ComfyUI unavailable on 127.0.0.1:8188: $($_.Exception.Message)"
    }
}

function Get-PresetAssetStatus($Req) {
    $rows = @()
    foreach ($asset in @($Req.managedAssets)) {
        $rows += Get-ManagedAssetStatus $asset
    }

    if (-not [string]::IsNullOrWhiteSpace([string]$Req.checkpoint)) {
        Assert-SafeFilename ([string]$Req.checkpoint) 'checkpoint'
        $p = Join-Path $CheckpointRoot ([string]$Req.checkpoint)
        $rows += [ordered]@{
            kind='selected_checkpoint'; filename=[string]$Req.checkpoint; path=$p
            exists=[bool](Test-Path -LiteralPath $p -PathType Leaf)
            sha256=(Get-Sha256 $p)
        }
    }

    foreach ($spec in @($Req.loras)) {
        Assert-SafeFilename ([string]$spec.filename) 'LoRA'
        $p = Join-Path $LoraRoot ([string]$spec.filename)
        $rows += [ordered]@{
            kind='selected_lora'; filename=[string]$spec.filename; path=$p
            exists=[bool](Test-Path -LiteralPath $p -PathType Leaf)
            sha256=(Get-Sha256 $p)
            strengthModel=[double]$spec.model; strengthClip=[double]$spec.clip
        }
    }
    return $rows
}

function Invoke-ComfyRender($Req, [int64]$Seed) {
    Assert-SafeFilename ([string]$Req.checkpoint) 'checkpoint'
    $checkpointPath = Join-Path $CheckpointRoot ([string]$Req.checkpoint)
    if (-not (Test-Path -LiteralPath $checkpointPath -PathType Leaf)) {
        throw "Checkpoint missing: $checkpointPath"
    }

    $workflow = @{}
    $workflow['1'] = @{
        class_type = 'CheckpointLoaderSimple'
        inputs = @{ ckpt_name = [string]$Req.checkpoint }
    }
    $modelRef = @('1', 0)
    $clipRef = @('1', 1)
    $node = 2
    $loraReceipts = @()

    foreach ($spec in @($Req.loras)) {
        $name = [string]$spec.filename
        Assert-SafeFilename $name 'LoRA'
        $path = Join-Path $LoraRoot $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "LoRA missing: $path"
        }
        $id = [string]$node
        $workflow[$id] = @{
            class_type = 'LoraLoader'
            inputs = @{
                model = $modelRef
                clip = $clipRef
                lora_name = $name
                strength_model = [double]$spec.model
                strength_clip = [double]$spec.clip
            }
        }
        $modelRef = @($id, 0)
        $clipRef = @($id, 1)
        $loraReceipts += [ordered]@{
            filename=$name
            strengthModel=[double]$spec.model
            strengthClip=[double]$spec.clip
            sha256=(Get-Sha256 $path)
        }
        $node++
    }

    $positiveId = [string]$node; $node++
    $negativeId = [string]$node; $node++
    $latentId = [string]$node; $node++
    $samplerId = [string]$node; $node++
    $decodeId = [string]$node; $node++
    $saveId = [string]$node

    $prefix = ([string]$Req.positivePrefix).Trim()
    $rawPrompt = ([string]$Req.prompt).Trim()
    $positive = if ($prefix) { "$prefix, $rawPrompt" } else { $rawPrompt }

    $workflow[$positiveId] = @{
        class_type='CLIPTextEncode'
        inputs=@{ text=$positive; clip=$clipRef }
    }
    $workflow[$negativeId] = @{
        class_type='CLIPTextEncode'
        inputs=@{ text=[string]$Req.negative; clip=$clipRef }
    }
    $workflow[$latentId] = @{
        class_type='EmptyLatentImage'
        inputs=@{ width=[int]$Req.width; height=[int]$Req.height; batch_size=1 }
    }
    $workflow[$samplerId] = @{
        class_type='KSampler'
        inputs=@{
            model=$modelRef
            seed=$Seed
            steps=[int]$Req.steps
            cfg=[double]$Req.cfg
            sampler_name=[string]$Req.sampler
            scheduler=[string]$Req.scheduler
            positive=@($positiveId,0)
            negative=@($negativeId,0)
            latent_image=@($latentId,0)
            denoise=1.0
        }
    }
    $workflow[$decodeId] = @{
        class_type='VAEDecode'
        inputs=@{ samples=@($samplerId,0); vae=@('1',2) }
    }
    $workflow[$saveId] = @{
        class_type='SaveImage'
        inputs=@{ filename_prefix="Fortress_$($Req.profile)_$Seed"; images=@($decodeId,0) }
    }

    $body = @{prompt=$workflow} | ConvertTo-Json -Depth 30
    $queued = Invoke-RestMethod -Method Post -ContentType 'application/json' -Body $body "$Comfy/prompt"
    $promptId = [string]$queued.prompt_id
    if (-not $promptId) { throw 'ComfyUI returned no prompt_id' }

    $deadline = (Get-Date).AddMinutes(8)
    $out = $null
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 700
        $history = Invoke-RestMethod -TimeoutSec 10 "$Comfy/history/$promptId"
        $record = $history.PSObject.Properties[$promptId].Value
        if ($record -and $record.outputs) {
            $prop = $record.outputs.PSObject.Properties[$saveId]
            if ($prop -and $prop.Value.images -and $prop.Value.images.Count -gt 0) {
                $out = $prop.Value.images[0]
                break
            }
        }
        if ($record -and $record.status -and $record.status.status_str -eq 'error') {
            throw "ComfyUI prompt failed: $($record.status | ConvertTo-Json -Compress -Depth 12)"
        }
    }
    if (-not $out) { throw "Timed out waiting for ComfyUI prompt $promptId" }

    $filename = [string]$out.filename
    $subfolder = [string]$out.subfolder
    $src = if ($subfolder) {
        Join-Path (Join-Path $OutputRoot $subfolder) $filename
    } else {
        Join-Path $OutputRoot $filename
    }
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
        throw "Generated image missing: $src"
    }

    return [ordered]@{
        seed=$Seed
        promptId=$promptId
        filename=$filename
        subfolder=$subfolder
        sourcePath=$src
        sha256=(Get-Sha256 $src)
        loraStack=$loraReceipts
    }
}

function New-ContactSheet($Images, [int]$Cols, [int]$Width, [int]$Height, [string]$Path) {
    Add-Type -AssemblyName System.Drawing
    $rows = [int][Math]::Ceiling($Images.Count / [double]$Cols)
    $labelHeight = 28
    $sheet = New-Object System.Drawing.Bitmap ($Cols * $Width), ($rows * ($Height + $labelHeight))
    $g = [System.Drawing.Graphics]::FromImage($sheet)
    $g.Clear([System.Drawing.Color]::FromArgb(20,20,20))
    $font = New-Object System.Drawing.Font 'Arial', 13
    $brush = [System.Drawing.Brushes]::White
    try {
        for ($i=0; $i -lt $Images.Count; $i++) {
            $col = $i % $Cols
            $row = [Math]::Floor($i / $Cols)
            $x = [int]($col * $Width)
            $y = [int]($row * ($Height + $labelHeight))
            $img = [System.Drawing.Image]::FromFile([string]$Images[$i].sourcePath)
            try {
                $g.DrawImage($img, $x, $y, $Width, $Height)
                $g.FillRectangle([System.Drawing.Brushes]::Black, $x, $y + $Height, $Width, $labelHeight)
                $g.DrawString(("seed {0}" -f $Images[$i].seed), $font, $brush, $x + 6, $y + $Height + 5)
            } finally {
                $img.Dispose()
            }
        }
        $sheet.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $font.Dispose()
        $g.Dispose()
        $sheet.Dispose()
    }
}

if (-not (Test-Path -LiteralPath $RequestPath -PathType Leaf)) {
    throw "Request missing: $RequestPath"
}
Remove-Item -Force -ErrorAction SilentlyContinue $ResultPath
$req = Get-Content -Raw -LiteralPath $RequestPath | ConvertFrom-Json
$action = [string]$req.action

switch ($action) {
    'setup' {
        $installed = @()
        foreach ($asset in @($req.managedAssets)) {
            $installed += Install-ManagedAsset $asset
        }
        Write-Result ([ordered]@{
            schema='fortress-image-cauldron-setup.v1'
            ok=$true
            action='setup'
            profile=[string]$req.profile
            assets=$installed
        })
        exit 0
    }

    'models' {
        Write-Result ([ordered]@{
            schema='fortress-image-cauldron-models.v1'
            ok=$true
            action='models'
            profile=[string]$req.profile
            assets=@(Get-PresetAssetStatus $req)
        })
        exit 0
    }

    'doctor' {
        $null = Assert-Comfy
        $assets = @(Get-PresetAssetStatus $req)
        $missing = @($assets | Where-Object { $_.contains('exists') -and -not $_.exists })
        $badManaged = @($assets | Where-Object { $_.contains('verified') -and -not $_.verified })
        $ok = ($missing.Count -eq 0 -and $badManaged.Count -eq 0)
        Write-Result ([ordered]@{
            schema='fortress-image-cauldron-doctor.v2'
            ok=$ok
            action='doctor'
            profile=[string]$req.profile
            comfy='http://127.0.0.1:8188'
            assets=$assets
            missingCount=$missing.Count
            unverifiedManagedCount=$badManaged.Count
        })
        if (-not $ok) { exit 3 }
        exit 0
    }

    'generate' {
        $null = Assert-Comfy
        Remove-Item -Force -ErrorAction SilentlyContinue $PrimaryPng
        $count = [int]$req.count
        if ($count -lt 1 -or $count -gt 12) { throw "count must be 1..12" }
        $mode = [string]$req.mode
        if ($mode -notin @('single','sheet')) { throw "mode must be single or sheet" }
        if ($mode -eq 'single' -and $count -ne 1) { throw 'single mode requires count=1' }

        $images = @()
        for ($i=0; $i -lt $count; $i++) {
            $images += Invoke-ComfyRender $req ([int64]$req.seed + $i)
        }

        if ($mode -eq 'sheet') {
            New-ContactSheet $images ([int]$req.cols) ([int]$req.width) ([int]$req.height) $PrimaryPng
        } else {
            Copy-Item -Force -LiteralPath ([string]$images[0].sourcePath) -Destination $PrimaryPng
        }

        $pngSha = Get-Sha256 $PrimaryPng
        $checkpointPath = Join-Path $CheckpointRoot ([string]$req.checkpoint)
        $promptIds = @($images | ForEach-Object { $_.promptId })
        $firstPromptId = [string]$promptIds[0]
        $summary = "Generated local $mode image for requested scene: $([string]$req.prompt). Base seed $([int64]$req.seed). Preset $([string]$req.profile), checkpoint $([string]$req.checkpoint), $count source render(s). This summary describes the request and generation settings, not an independent visual inspection of the rendered pixels."

        Write-Result ([ordered]@{
            schema='fortress-image-phone-receipt.v2'
            contract='fortress-image-phone.v1'
            ok=$true
            action='generate'
            prompt=[string]$req.prompt
            positivePrefix=[string]$req.positivePrefix
            negative=[string]$req.negative
            seed=[int64]$req.seed
            profile=[string]$req.profile
            mode=$mode
            count=$count
            cols=[int]$req.cols
            width=[int]$req.width
            height=[int]$req.height
            checkpoint=[string]$req.checkpoint
            checkpointSha256=(Get-Sha256 $checkpointPath)
            loraStack=@($images[0].loraStack)
            lora=if ($images[0].loraStack.Count -gt 0) { [string]$images[0].loraStack[0].filename } else { $null }
            loraSha256=if ($images[0].loraStack.Count -gt 0) { [string]$images[0].loraStack[0].sha256 } else { $null }
            steps=[int]$req.steps
            cfg=[double]$req.cfg
            sampler=[string]$req.sampler
            scheduler=[string]$req.scheduler
            promptId=$firstPromptId
            promptIds=$promptIds
            sourceImages=@($images)
            requestDerivedAltText=$summary
            altTextProvenance='request_and_generation_settings_not_visual_inspection'
            remoteOutput=$PrimaryPng
            pngSha256=$pngSha
        })
        exit 0
    }

    default {
        throw "Unsupported fortress image action: $action"
    }
}
