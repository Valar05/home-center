# Vlad Judgment Jar Fast Access and Home Center Sync

## Outcome

Vlad receives a single compact registry that combines the complete repository operational Jar bodies with the authoritative Home Center cabinet and newly discovered Jar artifacts. The existing `vlad-swarm` daemon owns synchronization and pending-receipt retry; no duplicate watcher or second scheduler is introduced.

Every actual Jar use also produces one append-only receipt identifying the Jar, the invocation, and the controlled kind of output it created.

## Authority model

The registry has two controlling sources and one discovery lane:

| Layer | Authority | Cached material | Offline use |
|---|---|---|---|
| Operational core | `.continue/rules/*judgement-jar*.md` | Full body, path, SHA-256, aliases, status, scope | Yes |
| Cabinet | Home Center Drive Doc `START HERE — Judgment Jar Registry` (`1UixBuLJRw-x5BoMGx81YXRpuN66iZhGGJoz40Iqx48Q`) | Registry summary, jurisdiction, question, hard gates, compact law, run order, native source route | Last verified snapshot |
| Discovery | Home Center Drive title search | Metadata-only route for likely Jar artifacts absent from the cabinet | Last verified snapshot |

Project-local Jars remain in their project, character, or doctrine homes. The cache is a routing cabinet, not a migration and not a flattened replacement corpus.

## Files

- `config/judgment-jars.v1.json` — source pattern, cabinet identity, refresh window, discovery queries, receipt schema, output taxonomy, and Atom endpoint.
- `tools/home_center_mcp_client.py` — authenticated Home Center MCP reader with token refresh; secrets are never written to receipts.
- `tools/judgment_jars.py` — canonical CLI entry point and automatic context-use receipts.
- `tools/vlad.py` — `vlad jar` / `vlad jars` fast surface while preserving ordinary Vlad review requests.
- `tools/judgment_jar_common.py`, `tools/judgment_jar_cabinet.py`, and `tools/judgment_jar_registry.py` — parser, compiler, atomic cache, native-source hydration, resolver, and search modules.
- `tools/judgment_jar_receipts.py` — append-only capture, per-Jar output receipts, Atom delivery, acknowledgements, and oldest-first outbox.
- `tools/adam_planned_venice_receipted.py` — receipts selected context, plan review, active execution context, completion review, and terminal output.
- `tools/venice_review_receipted.py` — receipts standalone canonical Venice review use.
- `tools/vlad_swarm_daemon.py` — existing daemon heartbeat calls the canonical CLI, which flushes old receipts and synchronizes the registry.
- `tools/setup_vlad_swarm_daemon.sh` — validates, performs an initial forced Home Center refresh, installs `vlad-jars` and `vlad`, and restarts the existing service when daemon source changes.
- `atom/server.mjs` and `atom/judgment-jar-receipts.mjs` — registry status/retrieval plus source-validated idempotent Home Center usage acknowledgement.

## Cache contract

Default path:

```text
~/.local/state/home-center/vlad-swarm/judgment-jars.json
```

Schema:

```text
home-center.judgment-jars.registry.v2
```

The top level separates:

- `localJarCount`
- `cabinetJarCount`
- `unregisteredJarCount`
- `complete`
- `registryDigest`
- `sourceCommit`
- `homeCenter.state`
- `homeCenter.lastSuccessEpoch`
- `homeCenter.lastError`
- `homeCenter.missingExecutableFunctions`

Each Jar exposes `origin`, `sourceAuthority`, and `sourceCompleteness`. A caller can therefore distinguish a full local body from a cabinet summary or metadata-only discovery.

## CLI

```bash
vlad jars sync --force-home-center
vlad jars status
vlad jars list
vlad jar get "What Would June Do?"
vlad jar source "What Would June Do?"
vlad jars search "custody authorship"
vlad jars prompt mission-boundary repository-truth
vlad jars prompt --all
vlad jars usage-status
vlad jars flush-receipts
vlad jar receipt mission-boundary \
  --output-kind plan \
  --summary "Produced the bounded implementation plan." \
  --request-id campaign-123 \
  --ref receipt://plan-123
```

The older `vlad-jars ...` spelling remains the same canonical tool.

`prompt` without explicit keys emits only the active repository operational core. This prevents every Jar from being dumped into every task. `prompt --all` is deliberately explicit.

`get`, `source`, and `prompt` are actual context use and automatically receipt `context_packet`. `list`, `status`, and `search` are discovery only. The explicit `receipt` command records the downstream material a Jar produced.

## Output-kind taxonomy

The controlled taxonomy lives in `config/judgment-jars.v1.json`. It currently includes:

- `context_packet`
- `answer`
- `analysis`
- `plan`
- `decision`
- `routing_action`
- `code_change`
- `test_result`
- `review_verdict`
- `artifact`
- `handoff`
- `memory_update`
- `execution_result`
- `blocker`
- `no_change`
- `mixed`

Omitted, invented, or vague output kinds fail closed. Output kind is not capability state.

## Usage receipt contract

Schema:

```text
home-center.judgment-jar-usage-receipt.v1
```

One receipt is emitted per Jar used. Multiple Jars governing one output share a group/request ID but retain independent source identity.

A receipt contains:

- receipt and capture timestamps;
- Jar ID/title/origin/status;
- source authority/completeness/path/file ID/URL/SHA-256;
- canonical registry digest and source commit;
- invocation source/request/group and input hash/size;
- output kind/status/summary/hash/size/references;
- native Home Center source snapshot identity when hydrated;
- `CAPTURED` and Home Center delivery state.

A generic task, model, review, or daemon receipt does not substitute for this per-Jar event.

## Capture and delivery

`CAPTURED` means the append-only local history and authorized outbox shard exist.

`DELIVERED` means Atom/Home Center has:

1. resolved the Jar against the current canonical registry;
2. verified ID, origin, source path/file ID, source SHA-256, and registry digest;
3. validated the controlled output kind;
4. appended the usage event or recognized its idempotent duplicate;
5. returned a daemon acknowledgement.

Default receipt state is derived beside the canonical registry cache:

```text
~/.local/state/home-center/vlad-swarm/judgment-jar-usage/
  usage.jsonl
  delivery-acks.jsonl
  last-usage.json
  last-delivery-ack.json
  outbox/
```

If Atom is unavailable, the shard remains pending. The existing Vlad daemon runs `judgment_jars.py sync`, whose first action is to retry the prior cache's oldest pending receipt. After registry refresh it retries again against current source identity. New output never overwrites or leaps past older pending work.

If a Jar's source changes before a captured receipt reaches Atom, delivery blocks visibly with both old and current source hashes. The shard is retained instead of silently rebinding history.

## Atom API

```text
GET  /v1/atom/vlad/jars
GET  /v1/atom/vlad/jars?id=<id-or-alias>
GET  /v1/atom/vlad/jars?q=<terms>
GET  /v1/atom/vlad/jars/receipts/status
POST /v1/atom/vlad/jars/receipts
```

Direct Atom Jar retrieval is actual context use and creates a `context_packet` receipt. Atom status exposes registry coverage plus receipt history/count/output taxonomy.

## Daemon behavior

The existing Vlad daemon invokes one cheap canonical CLI sync on heartbeat. That same invocation flushes pending usage receipts oldest-first and then refreshes repository/Home Center registry state. No receipt watcher or competing scheduler exists.

Local SHA comparison and the configured Home Center freshness window prevent broad remote reads on every heartbeat. A material change, failed Home Center refresh, or blocked receipt creates durable evidence.

The setup script writes the service environment and compares the daemon source SHA-256 with the installed stamp. A changed daemon is restarted so repository edits do not masquerade as deployed behavior while an old process remains resident.

## Automatic governed users

- Selected Jar context during Adam preflight → `context_packet`.
- Venice pre-execution application → `review_verdict`.
- Active operational Jars loaded for execution → `context_packet`.
- Venice completion application → `review_verdict`.
- Final governed task output → the planner-declared output kind.
- Standalone canonical Venice CLI review → `review_verdict`.
- Vlad `get` / `source` / `prompt` → `context_packet`.

The plan packet cannot pass without an allowed `outputKind`.

## Failure and recovery

- Registry cache and receipt snapshots use atomic replacement.
- Usage history and acknowledgements are append-only.
- Home Center failure preserves the last verified cabinet and all pending receipts.
- Repository operational Jars are rebuilt from current source even while Home Center is unavailable.
- A first-run Home Center failure yields a useful but incomplete local registry.
- Newly discovered artifacts stay `unregistered` until the cabinet actually indexes them.
- Exact native Jar execution requires reading the linked Sheet or Doc; metadata and cabinet summaries are not laundered into full criteria.
- Receipt capture failure blocks the claim that a Jar was applied.
- Atom delivery failure yields `PENDING`, not a false `DELIVERED` claim.

## Deterministic verification

- `tools/test_judgment_jar_registry.py` verifies dynamic local discovery, cabinet parsing, unregistered discovery, alias compatibility, atomic replacement, and stale-cache preservation.
- `tools/test_judgment_jar_receipts.py` verifies output taxonomy, local/cabinet provenance, one-receipt-per-Jar grouping, durable outbox, source-change blocking, and oldest-first delivery.
- `tools/test_adam_jar_receipt_contract.py` verifies the canonical Adam/Vlad/Venice entrypoints and output-kind phases.
- `atom/test/judgment-jars.test.mjs` verifies Atom registry access and daemon-side usage receipt validation.

Repository tests prove implementation only. Installed phone/Atom receipts are required to claim deployed, callable, or Home Center-delivered state. Drew remains acceptance authority.
