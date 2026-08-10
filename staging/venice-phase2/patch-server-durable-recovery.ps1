param(
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime',
  [string]$ExpectedMd5 = 'be5e1250930af59fc180afb5da52713e'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$p = Join-Path $RuntimeRoot 'src\workstation-server.mjs'
$current = (Get-FileHash -LiteralPath $p -Algorithm MD5).Hash.ToLowerInvariant()
if ($current -ne $ExpectedMd5) { throw "SOURCE_DRIFT workstation-server.mjs md5=$current expected=$ExpectedMd5" }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$p.pre-durable-recovery-$stamp"
Copy-Item -LiteralPath $p -Destination $backup -Force

try {
  $t = Get-Content -LiteralPath $p -Raw

  $importAnchor = 'import { WorkstationStore } from "./workstation-store.mjs";'
  $importReplacement = $importAnchor + "`n" + 'import { VeniceDurableRuntime } from "./durable-core/durable-runtime.mjs";'
  if (-not $t.Contains($importAnchor)) { throw 'durable runtime import anchor missing' }
  if (-not $t.Contains('VeniceDurableRuntime')) { $t = $t.Replace($importAnchor, $importReplacement) }

  $bootstrapAnchor = @'
const store = new WorkstationStore(path.join(dataRoot, "venice.db"));
for (const interrupted of store.listActiveJobs()) store.updateJob(interrupted.id, { status: "cancelled", error: "Interrupted by workstation restart", progress: { ...interrupted.progress, stage: "cancelled" } });
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
'@
  $bootstrapReplacement = @'
const store = new WorkstationStore(path.join(dataRoot, "venice.db"));
const durableRuntime = new VeniceDurableRuntime({ store });
const durableBoot = durableRuntime.initialize();
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
'@
  if (-not $t.Contains($bootstrapAnchor)) { throw 'destructive restart cancellation anchor missing' }
  $t = $t.Replace($bootstrapAnchor, $bootstrapReplacement)

  $runnerAnchor = 'const runner = new WorkstationRunner({ store, tools, client, routing, projectRoot, connectorPath, publish, confirm: requestConfirmation });'
  $runnerReplacement = @'
const runner = new WorkstationRunner({ store, tools, client, routing, projectRoot, connectorPath, publish, confirm: requestConfirmation });
const restartRecovery = runner.recoverPendingJobs();
const durableRecovery = durableRuntime.refresh({
  eventKind: "runtime.restart.reconciled",
  reason: "Workstation startup classified interrupted jobs without blindly replaying side effects.",
  payload: {
    bootstrapped: durableBoot.bootstrapped === true,
    recoveredJobIds: restartRecovery.recovered.map((item) => item.jobId),
    heldForReviewJobIds: restartRecovery.heldForReview.map((item) => item.jobId),
  },
  extraOpenLoops: restartRecovery.heldForReview.map((item) => ({
    jobId: item.jobId,
    threadId: item.threadId,
    kind: item.kind,
    status: "recovery_required",
    reason: item.reason,
    promptPreview: item.promptPreview,
  })),
});
publish({ type: "durable_coherence", durable: durableRuntime.summary(), recovery: { recovered: restartRecovery.recovered.length, heldForReview: restartRecovery.heldForReview.length } });
'@
  if (-not $t.Contains($runnerAnchor)) { throw 'runner recovery anchor missing' }
  $t = $t.Replace($runnerAnchor, $runnerReplacement)

  $apiAnchor = 'version: 2, latestEventSequence: eventSequence, projects: store.listProjects(), notifications: store.listNotifications(30), activeJobs: store.listActiveJobs(), connectors: await connectorSummary(), routing: routing.summary(),'
  $apiReplacement = 'version: 2, latestEventSequence: eventSequence, projects: store.listProjects(), notifications: store.listNotifications(30), activeJobs: store.listActiveJobs(), connectors: await connectorSummary(), routing: routing.summary(), durable: durableRuntime.summary(), restartRecovery: { recovered: restartRecovery.recovered.length, heldForReview: restartRecovery.heldForReview.length },'
  if (-not $t.Contains($apiAnchor)) { throw 'bootstrap API durable status anchor missing' }
  $t = $t.Replace($apiAnchor, $apiReplacement)

  [IO.File]::WriteAllText($p, $t, [Text.UTF8Encoding]::new($false))
  & node --check $p
  if ($LASTEXITCODE -ne 0) { throw 'workstation-server syntax check failed' }
  [pscustomobject]@{
    ok = $true
    backup = $backup
    beforeMd5 = $current
    afterMd5 = (Get-FileHash -LiteralPath $p -Algorithm MD5).Hash.ToLowerInvariant()
    afterSha256 = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
  } | ConvertTo-Json -Depth 4
} catch {
  Copy-Item -LiteralPath $backup -Destination $p -Force
  throw
}
