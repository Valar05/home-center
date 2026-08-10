param(
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime',
  [string]$ExpectedMd5 = '7285e675ec400618946292d3c71550c7'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$p = Join-Path $RuntimeRoot 'src\workstation-runner.mjs'
$current = (Get-FileHash -LiteralPath $p -Algorithm MD5).Hash.ToLowerInvariant()
if ($current -ne $ExpectedMd5) { throw "SOURCE_DRIFT workstation-runner.mjs md5=$current expected=$ExpectedMd5" }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$p.pre-restart-recovery-$stamp"
Copy-Item -LiteralPath $p -Destination $backup -Force

try {
  $t = Get-Content -LiteralPath $p -Raw
  $anchor = @'
  cancelActive() {
    const primary = this.active ? this.cancel(this.active) : false;
    const social = this.socialActive ? this.cancel(this.socialActive) : false;
    return primary || social;
  }

  async drainSocial() {
'@
  $replacement = @'
  cancelActive() {
    const primary = this.active ? this.cancel(this.active) : false;
    const social = this.socialActive ? this.cancel(this.socialActive) : false;
    return primary || social;
  }

  recoverPendingJobs() {
    const recovered = [];
    const heldForReview = [];
    const unsafeEventTypes = new Set(["function", "computer", "authorization"]);
    const safeRunningStages = new Set(["", "queued", "thinking", "local_core", "social"]);
    const now = new Date().toISOString();

    for (const job of this.store.listActiveJobs()) {
      const events = this.store.listToolEvents(job.id, 0);
      const possiblySideEffecting = events.some((event) =>
        unsafeEventTypes.has(event.type)
        || (event.type === "stage" && ["tool", "computer", "waiting_approval"].includes(String(event.payload?.stage || ""))),
      );
      const stage = String(job.progress?.stage || "");
      const resumable = !possiblySideEffecting
        && (job.status === "queued" || (job.status === "running" && safeRunningStages.has(stage)));

      if (resumable) {
        const updated = this.store.updateJob(job.id, {
          status: "queued",
          error: "",
          progress: {
            ...job.progress,
            stage: "recovered_queued",
            recoveredAt: now,
            recoveredFromStatus: job.status,
            recoveredFromStage: stage,
          },
        });
        const target = updated.kind === "social" ? this.socialQueue : this.queue;
        const activeId = updated.kind === "social" ? this.socialActive : this.active;
        if (activeId !== updated.id && !target.includes(updated.id)) target.push(updated.id);
        recovered.push({ jobId: updated.id, threadId: updated.threadId, kind: updated.kind, fromStatus: job.status, fromStage: stage });
        this.publish({ type: "job", job: updated, threadId: updated.threadId, recovery: true });
        continue;
      }

      const reason = job.status === "waiting_approval"
        ? "Interrupted while waiting for approval; explicit review is required before re-execution."
        : "Interrupted after a possibly side-effecting tool/computer boundary; explicit review is required before re-execution.";
      const updated = this.store.updateJob(job.id, {
        status: "failed",
        error: reason,
        progress: {
          ...job.progress,
          stage: "recovery_required",
          recoveredAt: now,
          recoveredFromStatus: job.status,
          recoveredFromStage: stage,
          recoveryReason: reason,
        },
      });
      const notification = this.store.notify("Venice recovery review needed", `Job ${updated.id} was not replayed after restart because it may have crossed a side-effect boundary.`, { threadId: updated.threadId, jobId: updated.id, recoveryRequired: true });
      this.publish({ type: "job", job: updated, threadId: updated.threadId, recovery: true });
      this.publish({ type: "notification", notification });
      heldForReview.push({ jobId: updated.id, threadId: updated.threadId, kind: updated.kind, status: "recovery_required", reason, promptPreview: String(updated.prompt || "").replace(/\s+/g, " ").trim().slice(0, 320) });
    }

    if (recovered.some((item) => item.kind !== "social")) queueMicrotask(() => this.drain());
    if (recovered.some((item) => item.kind === "social")) queueMicrotask(() => this.drainSocial());
    return { recovered, heldForReview };
  }

  async drainSocial() {
'@
  if (-not $t.Contains($anchor)) { throw 'restart recovery insertion anchor missing' }
  $t = $t.Replace($anchor, $replacement)
  [IO.File]::WriteAllText($p, $t, [Text.UTF8Encoding]::new($false))
  & node --check $p
  if ($LASTEXITCODE -ne 0) { throw 'workstation-runner syntax check failed' }
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
