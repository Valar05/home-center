param(
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$expected = @{
  'src\index.mjs' = '6015b0a7a9ff7f1419bf1f34ac4d8b8b'
  'src\local-image.mjs' = 'ec398108204e33e05a32fa36cc3b6a18'
  'src\workstation-tools.mjs' = 'ab87301f60f2451c633b63c1faaaaf2d'
  'src\workstation-runner.mjs' = '1e56c5923583c5d0e7c24232fa46ae66'
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backups = @{}
foreach ($rel in $expected.Keys) {
  $p = Join-Path $RuntimeRoot $rel
  $md5 = (Get-FileHash -LiteralPath $p -Algorithm MD5).Hash.ToLowerInvariant()
  if ($md5 -ne $expected[$rel]) { throw "SOURCE_DRIFT $rel md5=$md5 expected=$($expected[$rel])" }
  $bak = "$p.pre-image-contract-$stamp"
  Copy-Item -LiteralPath $p -Destination $bak -Force
  $backups[$p] = $bak
}
$newFiles = @()
try {
  $repo = 'C:\Users\dclar\workspace\home-center'
  & git -C $repo fetch --quiet origin main
  if ($LASTEXITCODE -ne 0) { throw 'git fetch origin main failed' }
  $intent = (& git -C $repo show 'origin/main:staging/venice-phase3/image-identity-intent.mjs') -join "`n"
  $intentTest = (& git -C $repo show 'origin/main:staging/venice-phase3/image-identity-intent.test.mjs') -join "`n"
  if ([string]::IsNullOrWhiteSpace($intent) -or [string]::IsNullOrWhiteSpace($intentTest)) { throw 'image intent staging files missing' }
  $intentPath = Join-Path $RuntimeRoot 'src\image-identity-intent.mjs'
  $intentTestPath = Join-Path $RuntimeRoot 'test\image-identity-intent.test.mjs'
  [IO.File]::WriteAllText($intentPath, $intent, [Text.UTF8Encoding]::new($false))
  [IO.File]::WriteAllText($intentTestPath, $intentTest, [Text.UTF8Encoding]::new($false))
  $newFiles += $intentPath, $intentTestPath

  $indexPath = Join-Path $RuntimeRoot 'src\index.mjs'
  $t = Get-Content -LiteralPath $indexPath -Raw
  $importAnchor = 'import { generateLocalImage, validateLocalBridgeUrl } from "./local-image.mjs";'
  if (-not $t.Contains($importAnchor)) { throw 'index local-image import anchor missing' }
  if (-not $t.Contains('from "./image-identity-intent.mjs"')) {
    $t = $t.Replace($importAnchor, $importAnchor + "`n" + 'import { extractVoiceImagePrompt, requestsVeniceIdentity } from "./image-identity-intent.mjs";')
  }
  $pattern = '(?s)function extractVoiceImagePrompt\(transcript\) \{.*?\n\}\n\nfunction extractVoiceVideoRequest'
  if (-not [regex]::IsMatch($t, $pattern)) { throw 'index voice image helper anchor missing' }
  $t = [regex]::Replace($t, $pattern, 'function extractVoiceVideoRequest', 1)
  $t = $t.Replace('generateLocalImage({ bridgeUrl: comfyBridgeUrl, token: comfyBridgeToken, prompt, seed })', 'generateLocalImage({ bridgeUrl: comfyBridgeUrl, token: comfyBridgeToken, prompt, seed, includeIdentity: requestsVeniceIdentity(prompt) })')
  $t = $t.Replace('generateLocalImage({ bridgeUrl: comfyBridgeUrl, token: comfyBridgeToken, prompt })', 'generateLocalImage({ bridgeUrl: comfyBridgeUrl, token: comfyBridgeToken, prompt, includeIdentity: requestsVeniceIdentity(prompt) })')
  [IO.File]::WriteAllText($indexPath, $t, [Text.UTF8Encoding]::new($false))

  $localPath = Join-Path $RuntimeRoot 'src\local-image.mjs'
  $t = Get-Content -LiteralPath $localPath -Raw
  $old = 'export async function generateLocalImage({ bridgeUrl, token, prompt, negativePrompt = "", seed, timeoutMs = 310_000, onProgress = null, fetchImpl = globalThis.fetch }) {'
  $new = 'export async function generateLocalImage({ bridgeUrl, token, prompt, negativePrompt = "", seed, includeIdentity = false, timeoutMs = 310_000, onProgress = null, fetchImpl = globalThis.fetch }) {'
  if (-not $t.Contains($old)) { throw 'local-image signature anchor missing' }
  $t = $t.Replace($old, $new)
  $old = '  const payload = { prompt };'
  $new = '  const payload = { prompt, include_identity: Boolean(includeIdentity) };'
  if (-not $t.Contains($old)) { throw 'local-image payload anchor missing' }
  $t = $t.Replace($old, $new)
  [IO.File]::WriteAllText($localPath, $t, [Text.UTF8Encoding]::new($false))

  $toolsPath = Join-Path $RuntimeRoot 'src\workstation-tools.mjs'
  $t = Get-Content -LiteralPath $toolsPath -Raw
  $importAnchor = 'import { generateLocalImage } from "./local-image.mjs";'
  if (-not $t.Contains($importAnchor)) { throw 'tools image import anchor missing' }
  if (-not $t.Contains('from "./image-identity-intent.mjs"')) {
    $t = $t.Replace($importAnchor, $importAnchor + "`n" + 'import { requestsVeniceIdentity } from "./image-identity-intent.mjs";')
  }
  $t = $t.Replace("        prompt,`n        negativePrompt,", "        prompt,`n        includeIdentity: requestsVeniceIdentity(prompt),`n        negativePrompt,")
  $t = $t.Replace("            prompt: panelPrompt,`n            negativePrompt:", "            prompt: panelPrompt,`n            includeIdentity: requestsVeniceIdentity(panelPrompt),`n            negativePrompt:")
  $t = $t.Replace("            prompt: visualPrompts[index],`n            seed:", "            prompt: visualPrompts[index],`n            includeIdentity: requestsVeniceIdentity(visualPrompts[index]),`n            seed:")
  $old = 'metadata: { prompt, negativePrompt, provider: "local-comfyui", seed: generated.seed }'
  $new = 'metadata: { prompt, negativePrompt, provider: "local-comfyui", seed: generated.seed, conditioning: generated.conditioning || null }'
  if (-not $t.Contains($old)) { throw 'artifact conditioning metadata anchor missing' }
  $t = $t.Replace($old, $new)
  [IO.File]::WriteAllText($toolsPath, $t, [Text.UTF8Encoding]::new($false))

  $runnerPath = Join-Path $RuntimeRoot 'src\workstation-runner.mjs'
  $t = Get-Content -LiteralPath $runnerPath -Raw
  $old = 'Render exactly the requested subjects and composition. Do not substitute a default Venice or ordinary-human portrait unless the request explicitly asks for one.'
  $new = 'Render exactly the requested subjects and composition. Do not substitute the assistant, narrator, or a generic human portrait unless the request explicitly asks for one.'
  if (-not $t.Contains($old)) { throw 'runner adherence anchor missing' }
  $t = $t.Replace($old, $new)
  [IO.File]::WriteAllText($runnerPath, $t, [Text.UTF8Encoding]::new($false))

  $localTest = Join-Path $RuntimeRoot 'test\local-image.test.mjs'
  $testText = Get-Content -LiteralPath $localTest -Raw
  if ($testText -notmatch 'include_identity') {
    $testText = $testText.Replace('    negativePrompt: "ordinary human women, no animal traits",', '    negativePrompt: "ordinary human women, no animal traits",' + "`n" + '    includeIdentity: false,')
    $testText = $testText.Replace('  assert.equal(requestBody.negative_prompt, "ordinary human women, no animal traits");', '  assert.equal(requestBody.negative_prompt, "ordinary human women, no animal traits");' + "`n" + '  assert.equal(requestBody.include_identity, false);')
    $testText += @'

test("local image identity is an explicit caller contract", async () => {
  let requestBody;
  await generateLocalImage({
    bridgeUrl: "http://127.0.0.1:8787",
    token: "test-token",
    prompt: "portrait of Venice wearing a red coat",
    includeIdentity: true,
    fetchImpl: async (_url, options) => {
      requestBody = JSON.parse(options.body);
      return { ok: true, json: async () => ({ ok: true, seed: 7, conditioning: { identityApplied: true }, image_data_url: "data:image/png;base64,aGVsbG8=" }) };
    },
  });
  assert.equal(requestBody.include_identity, true);
});
'@
    [IO.File]::WriteAllText($localTest, $testText, [Text.UTF8Encoding]::new($false))
  }

  foreach ($p in @($intentPath, $indexPath, $localPath, $toolsPath, $runnerPath)) {
    & node --check $p
    if ($LASTEXITCODE -ne 0) { throw "syntax failed $p" }
  }
  $tests = @($intentTestPath, $localTest, (Join-Path $RuntimeRoot 'test\durable-routing-policy.test.mjs'), (Join-Path $RuntimeRoot 'test\workstation-capabilities.test.mjs'))
  $out = (& node --test @tests 2>&1 | Out-String)
  if ($LASTEXITCODE -ne 0) { throw "runtime image contract tests failed`n$out" }
  [pscustomobject]@{
    ok = $true
    backups = $backups
    hashes = @{
      index = (Get-FileHash -LiteralPath $indexPath -Algorithm MD5).Hash.ToLowerInvariant()
      localImage = (Get-FileHash -LiteralPath $localPath -Algorithm MD5).Hash.ToLowerInvariant()
      tools = (Get-FileHash -LiteralPath $toolsPath -Algorithm MD5).Hash.ToLowerInvariant()
      runner = (Get-FileHash -LiteralPath $runnerPath -Algorithm MD5).Hash.ToLowerInvariant()
    }
    tests = ($out -split "`r?`n" | Where-Object { $_ -match '^# (tests|pass|fail) ' })
    restartPerformed = $false
  } | ConvertTo-Json -Depth 6
} catch {
  foreach ($p in $backups.Keys) { Copy-Item -LiteralPath $backups[$p] -Destination $p -Force }
  foreach ($p in $newFiles) { Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue }
  throw
}
