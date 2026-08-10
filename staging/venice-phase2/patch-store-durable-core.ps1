param(
  [string]$RuntimeRoot = 'G:\My Drive\Venice Runtime',
  [string]$ExpectedMd5 = '49586463d182f6aa3875a4252ddfcbe9'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$p = Join-Path $RuntimeRoot 'src\workstation-store.mjs'
$current = (Get-FileHash -LiteralPath $p -Algorithm MD5).Hash.ToLowerInvariant()
if ($current -ne $ExpectedMd5) { throw "SOURCE_DRIFT workstation-store.mjs md5=$current expected=$ExpectedMd5" }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$p.pre-durable-core-$stamp"
Copy-Item -LiteralPath $p -Destination $backup -Force

try {
  $t = Get-Content -LiteralPath $p -Raw
  $sqlAnchor = @'
      CREATE INDEX IF NOT EXISTS memories_scope ON memories(scope, scope_id, updated_at DESC);
      CREATE TABLE IF NOT EXISTS notifications (
'@
  $sqlReplacement = @'
      CREATE INDEX IF NOT EXISTS memories_scope ON memories(scope, scope_id, updated_at DESC);
      CREATE TABLE IF NOT EXISTS durable_events (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL UNIQUE,
        occurred_at TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        event_kind TEXT NOT NULL,
        correlation_id TEXT NOT NULL,
        state_version_before INTEGER,
        state_version_after INTEGER,
        event_json TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS durable_events_seq ON durable_events(seq);
      CREATE INDEX IF NOT EXISTS durable_events_kind ON durable_events(event_kind, seq);
      CREATE TABLE IF NOT EXISTS durable_memories (
        memory_id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        scope_kind TEXT NOT NULL,
        scope_id TEXT,
        key TEXT,
        status TEXT NOT NULL,
        authority_rank INTEGER NOT NULL DEFAULT 0,
        promoted_at TEXT NOT NULL,
        memory_json TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS durable_memories_scope ON durable_memories(scope_kind, scope_id, status, authority_rank DESC, promoted_at DESC);
      CREATE TABLE IF NOT EXISTS durable_working_state (
        organism_id TEXT PRIMARY KEY,
        state_version INTEGER NOT NULL,
        derived_through_event_id TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        state_json TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS durable_migration_receipts (
        migration_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        receipt_json TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS notifications (
'@
  if (-not $t.Contains($sqlAnchor)) { throw 'durable SQL anchor missing' }
  $t = $t.Replace($sqlAnchor, $sqlReplacement)

  $methodAnchor = @'
  deleteMemory(id) { return this.db.prepare("DELETE FROM memories WHERE id=?").run(id).changes > 0; }

  notify(title, body, metadata = {}) {
'@
  $methodReplacement = @'
  deleteMemory(id) { return this.db.prepare("DELETE FROM memories WHERE id=?").run(id).changes > 0; }

  durableEventCount() {
    return Number(this.db.prepare("SELECT COUNT(*) AS count FROM durable_events").get()?.count || 0);
  }
  getDurableEvent(eventId) {
    const row = this.db.prepare("SELECT event_json FROM durable_events WHERE event_id=?").get(eventId);
    return row ? parse(row.event_json, null) : null;
  }
  listDurableEventsAfter(eventId = null, limit = 1000) {
    let afterSeq = 0;
    if (eventId) {
      const row = this.db.prepare("SELECT seq FROM durable_events WHERE event_id=?").get(eventId);
      if (!row) throw new Error(`Durable event not found: ${eventId}`);
      afterSeq = Number(row.seq || 0);
    }
    return this.db.prepare("SELECT event_json FROM durable_events WHERE seq>? ORDER BY seq LIMIT ?").all(afterSeq, Math.max(1, Math.min(5000, Number(limit) || 1000))).map((row) => parse(row.event_json, null)).filter(Boolean);
  }
  loadDurableWorkingState() {
    const row = this.db.prepare("SELECT state_json FROM durable_working_state ORDER BY state_version DESC LIMIT 1").get();
    return row ? parse(row.state_json, null) : null;
  }
  commitDurableTransition(event, state) {
    if (!event?.eventId || !event?.eventKind || !state?.organismId || !Number.isInteger(state?.stateVersion) || !state?.derivedThroughEventId) {
      throw new TypeError("Durable transition requires a typed event and working state.");
    }
    if (state.derivedThroughEventId !== event.eventId) throw new TypeError("Working state must derive through the transition event.");
    const eventJson = json(event); const stateJson = json(state);
    this.db.exec("BEGIN IMMEDIATE");
    try {
      const existingEvent = this.db.prepare("SELECT event_json FROM durable_events WHERE event_id=?").get(event.eventId);
      if (existingEvent) {
        if (existingEvent.event_json !== eventJson) throw new Error(`Durable event idempotency conflict: ${event.eventId}`);
      } else {
        this.db.prepare("INSERT INTO durable_events(event_id,occurred_at,recorded_at,event_kind,correlation_id,state_version_before,state_version_after,event_json) VALUES(?,?,?,?,?,?,?,?)").run(
          event.eventId, event.occurredAt, event.recordedAt, event.eventKind, event.correlationId,
          event.stateVersionBefore ?? null, event.stateVersionAfter ?? null, eventJson,
        );
      }
      const current = this.db.prepare("SELECT state_version,derived_through_event_id,state_json FROM durable_working_state WHERE organism_id=?").get(state.organismId);
      if (current && Number(current.state_version) > state.stateVersion) throw new Error(`Durable state regression ${state.stateVersion} < ${current.state_version}`);
      if (current && Number(current.state_version) === state.stateVersion && current.derived_through_event_id !== state.derivedThroughEventId) {
        throw new Error(`Durable state version conflict at ${state.stateVersion}`);
      }
      this.db.prepare(`INSERT INTO durable_working_state(organism_id,state_version,derived_through_event_id,updated_at,state_json)
        VALUES(?,?,?,?,?) ON CONFLICT(organism_id) DO UPDATE SET state_version=excluded.state_version,derived_through_event_id=excluded.derived_through_event_id,updated_at=excluded.updated_at,state_json=excluded.state_json`).run(
        state.organismId, state.stateVersion, state.derivedThroughEventId, state.updatedAt, stateJson,
      );
      this.db.exec("COMMIT");
    } catch (error) {
      try { this.db.exec("ROLLBACK"); } catch {}
      throw error;
    }
    return { event: this.getDurableEvent(event.eventId), state: this.loadDurableWorkingState() };
  }
  putDurableMemory(record) {
    if (!record?.memoryId || !record?.type || !record?.scope?.kind || !record?.status || !record?.promotedAt) throw new TypeError("Typed durable memory record is required.");
    const payload = json(record);
    const existing = this.db.prepare("SELECT memory_json FROM durable_memories WHERE memory_id=?").get(record.memoryId);
    if (existing) {
      if (existing.memory_json !== payload) throw new Error(`Durable memory idempotency conflict: ${record.memoryId}`);
      return parse(existing.memory_json, null);
    }
    this.db.prepare("INSERT INTO durable_memories(memory_id,type,scope_kind,scope_id,key,status,authority_rank,promoted_at,memory_json) VALUES(?,?,?,?,?,?,?,?,?)").run(
      record.memoryId, record.type, record.scope.kind, record.scope.id || null, record.key || null, record.status, record.authorityRank || 0, record.promotedAt, payload,
    );
    return record;
  }
  listDurableMemories({ scopeKind = null, scopeId = null, status = "active" } = {}) {
    const rows = scopeKind
      ? this.db.prepare("SELECT memory_json FROM durable_memories WHERE scope_kind=? AND (scope_id IS ? OR scope_id IS NULL) AND status=? ORDER BY authority_rank DESC,promoted_at DESC").all(scopeKind, scopeId, status)
      : this.db.prepare("SELECT memory_json FROM durable_memories WHERE status=? ORDER BY authority_rank DESC,promoted_at DESC").all(status);
    return rows.map((row) => parse(row.memory_json, null)).filter(Boolean);
  }
  saveDurableMigrationReceipt(receipt) {
    if (!receipt?.migrationId || !receipt?.status || !receipt?.updatedAt) throw new TypeError("Typed migration receipt is required.");
    this.db.prepare(`INSERT INTO durable_migration_receipts(migration_id,status,updated_at,receipt_json) VALUES(?,?,?,?)
      ON CONFLICT(migration_id) DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at,receipt_json=excluded.receipt_json`).run(
      receipt.migrationId, receipt.status, receipt.updatedAt, json(receipt),
    );
    return receipt;
  }
  listDurableMigrationReceipts() {
    return this.db.prepare("SELECT receipt_json FROM durable_migration_receipts ORDER BY updated_at DESC").all().map((row) => parse(row.receipt_json, null)).filter(Boolean);
  }

  notify(title, body, metadata = {}) {
'@
  if (-not $t.Contains($methodAnchor)) { throw 'durable method anchor missing' }
  $t = $t.Replace($methodAnchor, $methodReplacement)
  [IO.File]::WriteAllText($p, $t, [Text.UTF8Encoding]::new($false))
  & node --check $p
  if ($LASTEXITCODE -ne 0) { throw 'workstation-store syntax check failed' }
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
