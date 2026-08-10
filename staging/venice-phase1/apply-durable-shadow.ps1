param(
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime',
  [string]$ExpectedRunnerMd5 = '4c2b8c5e88da784a05b5c0560ecf5255'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$runner = Join-Path $RuntimeRoot 'src\workstation-runner.mjs'
$shadow = Join-Path $RuntimeRoot 'src\durable-core\shadow-observer.mjs'
$schemaTest = Join-Path $RuntimeRoot 'test\durable-core-schema.test.mjs'
$shadowTest = Join-Path $RuntimeRoot 'test\durable-core-shadow.test.mjs'
$integrationTest = Join-Path $RuntimeRoot 'test\durable-core-shadow-integration.test.mjs'

foreach ($required in @($runner,$shadow,$schemaTest,$shadowTest,$integrationTest)) {
  if (-not (Test-Path -LiteralPath $required)) { throw "Required Phase 1 file missing: $required" }
}

$currentMd5 = (Get-FileHash -LiteralPath $runner -Algorithm MD5).Hash.ToLowerInvariant()
if ($currentMd5 -ne $ExpectedRunnerMd5) {
  throw "SOURCE_DRIFT: workstation-runner.mjs md5=$currentMd5 expected=$ExpectedRunnerMd5. Refusing to overwrite neighboring Venice work."
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$runner.pre-durable-shadow-$stamp"
Copy-Item -LiteralPath $runner -Destination $backup -Force

try {
  $text = Get-Content -LiteralPath $runner -Raw

  $importOld = 'import { anthropomorphicConditioning } from "./image-conditioning.mjs";'
  $importNew = $importOld + "`n" + 'import { makeShadowReceipt } from "./durable-core/shadow-observer.mjs";'
  if (-not $text.Contains($importNew)) {
    if (-not $text.Contains($importOld)) { throw 'Shadow import anchor not found.' }
    $text = $text.Replace($importOld, $importNew)
  }

  $memoryOld = @'
      const memories = [
        ...this.store.listMemories("global", null),
        ...this.store.listMemories("project", project.id),
      ].slice(0, 80).map((memory) => `${memory.key}: ${memory.value}`).join("\n");
'@
  $memoryNew = @'
      const memoryRecords = [
        ...this.store.listMemories("global", null),
        ...this.store.listMemories("project", project.id),
      ].slice(0, 80);
      const memories = memoryRecords.map((memory) => `${memory.key}: ${memory.value}`).join("\n");
'@
  if (-not $text.Contains('const memoryRecords = [')) {
    if (-not $text.Contains($memoryOld)) { throw 'Memory assembly anchor not found.' }
    $text = $text.Replace($memoryOld, $memoryNew)
  }

  $routeOld = @'
      const capabilityRequests = resolveLocalCapabilities(job.prompt);
      const latestAudioArtifact = latestArtifacts.find((artifact) => artifact.kind === "audio" || String(artifact.mime || "").startsWith("audio/")) || null;
'@
  $routeNew = @'
      const capabilityRequests = resolveLocalCapabilities(job.prompt);
      const durableShadowEnabled = String(process.env.VENICE_DURABLE_CORE_SHADOW || "true").toLowerCase() !== "false";
      if (durableShadowEnabled) {
        const roleplayStateLoaded = identity.includes("Continuity facts recovered from live Discord Venice");
        const recentRoleplayTurnCount = (identity.match(/(?:^|\n)(?:user|assistant|speaker):/g) || []).length;
        const shadowReceipt = makeShadowReceipt({
          turnId: job.id,
          prompt: job.prompt,
          mode: job.kind,
          capabilityRequests,
          localImageIntent,
          localAudioIntent: isLocalFirstAudioRequest(job.prompt, job.kind),
          memoryIds: memoryRecords.map((memory) => memory.id).filter(Boolean),
          surfaceContextEventIds: recentMessages.map((message) => message.id).filter(Boolean),
          roleplayApertureRef: job.kind === "social" ? `legacy:thread:${thread.id}` : "",
          identityObservation: {
            mode: job.kind,
            roleplayProfileLoaded: true,
            roleplayStateLoaded,
            roleplaySummaryPresent: roleplayStateLoaded,
            recentRoleplayTurnCount,
          },
        });
        this.store.addToolEvent(job.id, "durable_shadow", shadowReceipt);
        this.publish({
          type: "durable_shadow",
          threadId: thread.id,
          jobId: job.id,
          shadowOnly: true,
          routeDecisionId: shadowReceipt.routeDecision.decisionId,
          selectedExecutor: shadowReceipt.routeDecision.selectedExecutor,
          warnings: [
            ...shadowReceipt.routeWarnings,
            ...shadowReceipt.identityObservation.warnings,
          ].map((warning) => ({ code: warning.code, severity: warning.severity })),
        });
      }
      const latestAudioArtifact = latestArtifacts.find((artifact) => artifact.kind === "audio" || String(artifact.mime || "").startsWith("audio/")) || null;
'@
  if (-not $text.Contains('type: "durable_shadow"')) {
    if (-not $text.Contains($routeOld)) { throw 'Capability route anchor not found.' }
    $text = $text.Replace($routeOld, $routeNew)
  }

  $tmp = "$runner.new"
  [IO.File]::WriteAllText($tmp, $text, [Text.UTF8Encoding]::new($false))
  Move-Item -LiteralPath $tmp -Destination $runner -Force

  & node --check $runner
  if ($LASTEXITCODE -ne 0) { throw 'workstation-runner.mjs syntax check failed.' }
  $testOutput = (& node --test $schemaTest $shadowTest $integrationTest 2>&1 | Out-String)
  if ($LASTEXITCODE -ne 0) { throw "durable shadow focused tests failed`n$testOutput" }

  [pscustomobject]@{
    ok = $true
    shadowOnly = $true
    behaviorCutover = $false
    backup = $backup
    beforeMd5 = $currentMd5
    afterMd5 = (Get-FileHash -LiteralPath $runner -Algorithm MD5).Hash.ToLowerInvariant()
    runnerSha256 = (Get-FileHash -LiteralPath $runner -Algorithm SHA256).Hash.ToLowerInvariant()
    tests = ($testOutput -split "`r?`n" | Where-Object { $_ -match '^# (tests|pass|fail) ' })
    restartPerformed = $false
  } | ConvertTo-Json -Depth 5
} catch {
  Copy-Item -LiteralPath $backup -Destination $runner -Force
  throw
}
