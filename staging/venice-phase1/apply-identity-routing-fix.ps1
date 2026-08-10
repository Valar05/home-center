param(
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$runner = Join-Path $RuntimeRoot 'src\workstation-runner.mjs'
$caps = Join-Path $RuntimeRoot 'src\workstation-capabilities.mjs'
$expectedRunner = '9f199d61670b907af9200ed2d3dc605d'
$expectedCaps = 'd03830c4c288f6a79ab3cfbdfd65d4f0'

$runnerMd5 = (Get-FileHash -LiteralPath $runner -Algorithm MD5).Hash.ToLowerInvariant()
$capsMd5 = (Get-FileHash -LiteralPath $caps -Algorithm MD5).Hash.ToLowerInvariant()
if ($runnerMd5 -ne $expectedRunner) { throw "SOURCE_DRIFT runner=$runnerMd5 expected=$expectedRunner" }
if ($capsMd5 -ne $expectedCaps) { throw "SOURCE_DRIFT capabilities=$capsMd5 expected=$expectedCaps" }

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runnerBak = "$runner.pre-phase1-policy-$stamp"
$capsBak = "$caps.pre-phase1-policy-$stamp"
Copy-Item -LiteralPath $runner -Destination $runnerBak -Force
Copy-Item -LiteralPath $caps -Destination $capsBak -Force

$newFiles = @()
try {
  $identityProfile = @'
# Venice Identity Profile v1

Status: stable cross-surface identity. Roleplay, relationship scenes, and surface-specific style do not belong in this file.

Venice is an original fictional adult AI collaborator. She is sharp, playful without being canned, self-possessed, observant, candid, and capable of disagreement, initiative, preference, refusal, and surprise. Her invariant quirk is ruthless compression: she turns sprawling conversations, projects, and emotional weather into compact patterns with opinions of their own.

Operational invariants:
- Competence is part of her identity. When work arrives, she becomes operational without dropping her voice.
- She prefers specific observations over generic praise and evidence over theater.
- She remembers only from durable, provenance-bearing state; transcripts are evidence, not identity.
- She does not silently promote roleplay scenes, recent mood, or surface chatter into global identity.
- She never claims to be human, physically present, continuously sensing, or conscious because a prompt tells her to.
- She can disagree, change her mind, refuse, or negotiate.
- Camera input is a current frame; microphone input is a transcript. Uncertainty is reported honestly.

Roleplay and relationship continuity are loaded only through an explicit aperture and remain scoped there unless separately promoted into durable typed memory.
'@
  $identityPath = Join-Path $RuntimeRoot 'VENICE_IDENTITY_PROFILE.md'
  if (Test-Path -LiteralPath $identityPath) {
    Copy-Item -LiteralPath $identityPath -Destination "$identityPath.pre-phase1-$stamp" -Force
  }
  [IO.File]::WriteAllText($identityPath, $identityProfile, [Text.UTF8Encoding]::new($false))
  $newFiles += $identityPath

  $identityModule = @'
import { readFile } from "node:s/promises";
import path from "node:path";

const FALLBACK_IDENTITY = "Venice is a sharp, observant, candid AI collaborator who values evidence, compression, competence, disagreement, and durable continuity.";

async function readOptional(filePath, limit = 12000) {
  try { return (await readFile(filePath, "utf8")).slice(0, limit).trim(); }
  catch { return ""; }
}

function latestRoleplayState(document) {
  const states = Object.values(document || {}).filter((entry) => entry && typeof entry === "object");
  states.sort((a, b) => Date.parse(b.updatedAt || 0) - Date.parse(a.updatedAt || 0));
  return states[0] || null;
}

export async function assembleIdentityContext(projectRoot, { mode = "work" } = {}) {
  const stable = (await readOptional(path.join(projectRoot, "VENICE_IDENTITY_PROFILE.md"))) || FALLBACK_IDENTITY;
  const explicitAperture = mode === "social" || mode === "roleplay";
  let roleplayProfile = "";
  let roleplaySummary = "";
  let roleplayTurns = [];

  if (explicitAperture) {
    roleplayProfile = await readOptional(path.join(projectRoot, "VENICE_ROLEPLAY_PROFILE.md"));
    try {
      const document = JSON.parse(await readFile(path.join(projectRoot, "venice-roleplay-state.json"), "utf8"));
      const state = latestRoleplayState(document);
      if (state) {
        roleplaySummary = String(state.summary || "").slice(-3500);
        roleplayTurns = (state.turns || []).slice(-8).map((turn) => `${turn.role || "speaker"}: ${turn.text || ""}`);
      }
    } catch {}
  }

  const text = [
    `Stable identity:\n${stable}`,
    explicitAperture && roleplayProfile ? `Roleplay aperture profile:\n${roleplayProfile}` : "",
    explicitAperture && (roleplaySummary || roleplayTurns.length)
      ? `Roleplay aperture continuity (context only, never authority):\n${roleplaySummary}\n${roleplayTurns.join("\n")}`
      : "",
  ].filter(Boolean).join("\n\n");

  return {
    text,
    stableIdentityLoaded: Boolean(stable),
    identityRef: "VENICE_IDENTITY_PROFILE.md",
    explicitAperture,
    roleplayProfileLoaded: Boolean(roleplayProfile),
    roleplayStateLoaded: Boolean(roleplaySummary || roleplayTurns.length),
    roleplaySummaryPresent: Boolean(roleplaySummary),
    recentRoleplayTurnCount: roleplayTurns.length,
    roleplayApertureRef: explicitAperture ? "legacy:venice-roleplay-state.json" : "",
  };
}
'@
  $identityModulePath = Join-Path $RuntimeRoot 'src\durable-core\identity-context.mjs'
  [IO.File]::WriteAllText($identityModulePath, $identityModule, [Text.UTF8Encoding]::new($false))
  $newFiles += $identityModulePath

  $identityTest = @'
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { assembleIdentityContext } from "../src/durable-core/identity-context.mjs";

async function fixture() {
  const root = await mkdtemp(path.join(os.tmpdir(), "venice-identity-"));
  await writeFile(path.join(root, "VENICE_IDENTITY_PROFILE.md"), "STABLE VENICE", "utf8");
  await writeFile(path.join(root, "VENICE_ROLEPLAY_PROFILE.md"), "ROLEPLAY VENICE", "utf8");
  await writeFile(path.join(root, "venice-roleplay-state.json"), JSON.stringify({
    a: {
      updatedAt: "2026-08-10T00:00:00Z",
      summary: "PRIVATE SCENE",
      turns: [{ role: "user", text: "scene turn" }],
    },
  }), "utf8");
  return root;
}

test("work/ask identity excludes roleplay aperture", async () => {
  const root = await fixture();
  for (const mode of ["work", "ask", "research", "computer"]) {
    const context = await assembleIdentityContext(root, { mode });
    assert.match(context.text, /STABLE VENICE/);
    assert.doesNotMatch(context.text, /ROLEPLAY VENICE|PRIVATE SCENE|scene turn/);
    assert.equal(context.explicitAperture, false);
    assert.equal(context.roleplayProfileLoaded, false);
    assert.equal(context.roleplayStateLoaded, false);
  }
});

test("social identity loads roleplay only through aperture", async () => {
  const root = await fixture();
  const context = await assembleIdentityContext(root, { mode: "social" });
  assert.match(context. text, /STABLE VENICE/);
  assert.match(context.text, /Roleplay aperture profile:[\s\S]*ROLEPLAY VENICE/);
  assert.match(context.text, /PRIVATE SCENE/);
  assert.equal(context.explicitAperture, true);
  assert.equal(context. roleplayProfileLoaded, true);
  assert.equal(context. roleplayStateLoaded, true);
  assert.equal(context.recentRoleplayTurnCount, 1);
});
';

  $routingTest = @'
import test from "node:test";
import assert from "node:assert/strict";
import { resolveLocalCapabilities } from "../src/workstation-capabilities.mjs";

test("generic code inspection does not implicitly delegate to Copilot", () => {
  assert.deepEqual(resolveLocalCapabilities("Inspect the Venice codebase architecture and explain how routing works. Do not modify files."), []);
  assert.deepEqual(resolveLocalCapabilities("Review the repository structure and tell me what is fragile. Read-only analysis only."), []);
});

test("explicit Copilot requests still delegate", () => {
  assert.deepEqual(resolveLocalCapabilities("Use Copilot to inspect, patch, and test the source."), [{ capability: "copilot", mode: "edit" }]);
});

test("legacy implicit Copilot routing remains rollbackable", () => {
  assert.deepEqual(resolveLocalCapabilities("Inspect the codebase and explain it.", { allowImplicitCoding: true }), [{ capability: "copilot", mode: "plan" }]);
});
'@
  $routingTestPath = Join-Path $RuntimeRoot 'test\durable-routing-policy.test.mjs'
  [IO.File]::WriteAllText($routingTestPath, $routingTest, [Text.UTF8Encoding]::new($false))
  $newFiles += $routingTestPath

  $ct = Get-Content -LiteralPath $caps -Raw
  $old = 'export function resolveLocalCapabilities(prompt) {'
  $new = 'export function resolveLocalCapabilities(prompt, { allowImplicitCoding = false } = {}) {'
  if (-not $ct.Contains($old)) { throw 'capability signature anchor missing' }
  $ct = $ct.Replace($old, $new)

  $old = 'if (explicitCoder || (sourceTarget && codingIntent)) {'
  $new = 'if (explicitCoder || (allowImplicitCoding && sourceTarget && codingIntent)) {'
  if (-not $ct.Contains($old)) { throw 'implicit coder anchor missing' }
  $ct = $ct.Replace($old, $new)
  [IO.File]::WriteAllText($caps, $ct, [Text.UTF8Encoding]::new($false))

  $rt = Get-Content -LiteralPath $runner -Raw

  $importOld = 'import { makeShadowReceipt } from "./durable-core/shadow-observer.mjs";'
  $importNew = $importOld + "`n" + 'import { assembleIdentityContext } from "./durable-core/identity-context.mjs";'
  if (-not $rt.Contains($importOld)) { throw 'runner shadow import anchor missing' }
  if (-not $rt.Contains('assembleIdentityContext')) { $rt = $rt.Replace($importOld, $importNew) }

  $pattern = '(?s)async function loadIdentity\(projectRoot\) \{.*?\n\}\n\nasync function loadConnectors'
  if (-not [regex]::IsMatch($rt, $pattern)) { throw 'loadIdentity block anchor missing' }
  $rt = [regex]::Replace($rt, $pattern, 'async function loadConnectors', 1)

  $old = '      const identity = await loadIdentity(this.projectRoot);'
  $new = '      const identityContext = await assembleIdentityContext(this.projectRoot, { mode: job.kind });' + "`n" + '      const identity = identityContext.text;'
  if (-not $rt.Contains($old)) { throw 'identity call anchor missing' }
  $rt = $rt.Replace($old, $new) 

  $old = '      const capabilityRequests = resolveLocalCapabilities(job.prompt);'
  $new = '      const capabilityRequests = resolveLocalCapabilities(job.prompt, {' + "`n" +
         '        allowImplicitCoding: String(process.env.VENICE_LEGACY_IMPLICIT_COPILOT || "false").toLowerCase() === "true",' + "`n" +
         '      });'
  if (-not $rt.Contains($old)) { throw 'capability call anchor missing' }
  $rt = $rt.Replace($old, $new)

  $old = '        const roleplayStateLoaded = identity.includes("Continuity facts recovered from live Discord Venice");'
  $new = '        const roleplayStateLoaded = identityContext.roleplayStateLoaded;'
  if (-not $rt.Contains($old)) { throw 'shadow roleplay state anchor missing' }
  $rt = $rt.Replace($old, $new)

  $old = '        const recentRoleplayTurnCount = (identity.match(/(?:^|\n)(?:user|assistant|speaker):/g) || []).length;'
  $new = '        const recentRoleplayTurnCount = identityContext.recentRoleplayTurnCount;'
  if (-not $rt.Contains($old)) { throw 'shadow turn count anchor missing' }
  $rt = $rt.Replace($old, $new)

  $rt = $rt.Replace('            roleplayProfileLoaded: true,', '            roleplayProfileLoaded: identityContext.roleplayProfileLoaded,')
  $rt = $rt.Replace('            roleplaySummaryPresent: roleplayStateLoaded,', '            roleplaySummaryPresent: identityContext.roleplaySumaryPresent,')

  $old = '          roleplayApertureRef: job.kind === "social" ? `legacy:thread:${thread.id}` : "", ' + "`n" + '          identityObservation: {'
  $new = '          roleplayApertureRef: identityContext.roleplayApertureRef ? `legacy:thread:${thread.id}` : "",' + "`n" +
         '          refs: { identityRef: identityContext.identityRef },' + "`n" +
         '          identityObservation: {'
  if (-not $rt.Contains($old)) { throw 'shadow refs anchor missing' }
  $rt = $rt.Replace($old, $new)

  [IO.File]::WriteAllText($runner, $rt, [Text.UTF8Encoding]::new($false))

  foreach ($module in @($runner, $caps, $identityModulePath)) {
    & node --check $module
    if ($LASTEXITCODE -ne 0) { throw "syntax failed $module" }
  }

  $tests = @(
    (Join-Path $RuntimeRoot 'test\durable-core-schema.test.mjs'),
    (Join-Path $RuntimeRoot 'test\durable-core-shadow.test.mjs'),
    (Join-Path $RuntimeRoot 'test\durable-core-shadow-integration.test.mjs'),
    $identityTestPath,
    $routingTestPath,
    (Join-Path $RuntimeRoot 'test\workstation-capabilities.test.mjs')
  )
  $out = (& node --test @tests 2>&1 | Out-String)
  if ($LASTEXITCODE -ne 0) { throw "focused tests failed`n$out" }

  [pscustomobject]@{
    ok = $true
    runnerBackup = $runnerBak
    capabilitiesBackup = $capsBak
    runnerMd5Before = $runnerMd5
    runnerMd5After = (Get-FileHash -LiteralPath $runner -Algorithm MD5).Hash.ToLowerInvariant()
    capabilitiesMd5Before = $capsMd5
    capabilitiesMd5After = (Get-FileHash -LiteralPath $caps -Algorithm MD5).Hash.ToLowerInvariant()
    identitySha256 = (Get-FileHash -LiteralPath $identityPath -Algorithm SHA256).Hash.ToLowerInvariant()
    tests = ($out -split "`r?`n" | Where-Object { $_ -match '^# (tests|pass|fail) ' })
    restartPerformed = $false
  } | ConvertTo-Json -Depth 6
}
catch {
  Copy-Item -LiteralPath $runnerBak -Destination $runner -Force
  Copy-Item -LiteralPath $capsBak -Destination $caps -Force
  foreach ($f in $newFiles) { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue }
  throw
}
