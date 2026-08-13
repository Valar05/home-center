# Vlad Judgment Jar Fast Access, Typed Receipts, and Home Center Sync

## Outcome

Vlad receives one compact dynamic registry that combines complete repository operational Jar bodies with the authoritative Home Center cabinet and newly discovered Jar artifacts. Every material Jar context load and every result created from that context leaves a typed receipt. The existing `vlad-swarm` daemon owns synchronization and delivery; no duplicate watcher or second scheduler is introduced.

## Surface law

Exactly three fast-access surfaces exist:

1. **Judgment Jars** — governed criteria and native provenance.
2. **Home Center** — authoritative durable sync and verified delivery.
3. **Vlad** — deterministic phone continuity, routing, scarcity, restart, and adversarial judgment.

**Command Center does not exist.** Historical source identifiers containing `command_center` are compatibility debt only; they do not name a product, queue, owner, architecture, or fourth operator surface.

## Authority model

| Layer | Authority | Cached material | Offline use |
|---|---|---|---|
| Operational core | `.continue/rules/*judgement-jar*.md` | Full body, path, SHA-256, aliases, status, scope | Yes |
| Cabinet | Home Center Doc `START HERE — Judgment Jar Registry` (`1UixBuLJRw-x5BoMGx81YXRpuN66iZhGGJoz40Iqx48Q`) | Registry summary, jurisdiction, hard gates, compact law, run order, native source route | Last verified snapshot |
| Discovery | Home Center Drive title search | Metadata-only route for likely Jar artifacts absent from the cabinet | Last verified snapshot |

Project-local Jars remain in their project, character, or doctrine homes. The cache is a routing cabinet, not a migration or flattened replacement corpus. Exact scoring, formulas, criteria, or case execution reads the linked native Sheet or Doc.

## Files

- `config/judgment-jars.v1.json` — source, cabinet, receipt kinds, state, retry, and delivery contract.
- `tools/judgment_jars.py` — `vlad-jars` registry/context CLI, import coordinator, and existing-heartbeat flush entrypoint.
- `tools/judgment_jar_common.py`, `tools/judgment_jar_cabinet.py`, `tools/judgment_jar_registry.py` — registry parser/compiler/cache/native-source modules.
- `tools/judgment_jar_receipts.py` — append-only receipt capture, oldest-first outbox, Home Center ledger append, and exact readback.
- `tools/judgment_jar_receipt_truth.py` — public fail-closed state facade; any quarantine remains an explicit failed state.
- `tools/jar_receipt.py` — explicit typed created-output receipt CLI.
- `tools/judgment_jar_atom_import.py` — imports Atom context receipts without losing malformed shards.
- `tools/judgment_jar_review_import.py` — imports durable Venice plan/completion review outputs as `review_verdict` receipts.
- `tools/judgment_jar_runtime.py` and `tools/adam_receipted_worker.py` — installed Adam/Vlad phone worker uses the receipted fast path.
- `tools/vlad_swarm_daemon.py` — existing daemon heartbeat calls `vlad-jars sync`; it remains the only watcher.
- `atom/judgment-jar-receipts.mjs` — Atom captures local Jar use as `CAPTURED`/`PENDING_HOME_CENTER`, never false delivery.

## Registry cache

Default path:

```text
~/.local/state/home-center/vlad-swarm/judgment-jars.json
```

Schema:

```text
home-center.judgment-jars.registry.v2
```

The cache keeps source authority and completeness explicit, including `registryDigest`, `sourceCommit`, Home Center freshness/error state, local/cabinet/unregistered counts, and each Jar’s native route.

## Receipt contract

Context access and created output are separate facts:

- `get`, `source`, and `prompt` create one `context_packet` receipt for each Jar actually loaded;
- the resulting answer, analysis, plan, decision, route, code change, test, review verdict, artifact, handoff, memory update, execution result, blocker, no-change result, or mixed output creates its own typed receipt.

Every material receipt preserves timestamp, surface, actor, intent, input/context digest, Jar identity/origin/source hash/registry digest, decision/action, output kind/status/digest, references, and a stable deduplication fingerprint.

Receipt states are not interchangeable:

- `CAPTURED` — durable local outbox record exists;
- `PENDING_HOME_CENTER` — captured, but Home Center delivery is not verified;
- `DELIVERED` — the exact receipt ID and fingerprint survived Home Center append plus readback;
- `QUARANTINED` / `IMPORT_QUARANTINED` — a preserved shard requires explicit repair and the public command fails closed.

The Home Center native ledger title is:

```text
Judgment Jar Usage Receipts — Vlad and Home Center
```

Local JSON, Atom capture, process exit, scheduler completion, or a successful function return is never `DELIVERED`.

## CLI

```bash
vlad-jars sync --force-home-center
vlad-jars status
vlad-jars list
vlad-jars get "What Would June Do?"
vlad-jars source "What Would June Do?"
vlad-jars search "custody authorship"
vlad-jars prompt mission-boundary repository-truth
vlad-jars prompt --all
vlad-jars registry
vlad-jars receipt-status
vlad-jars flush-receipts

python3 tools/jar_receipt.py record mission-boundary \
  --output-kind decision \
  --intent "preserve the commissioned architecture" \
  --decision-action "rejected a fourth control surface" \
  --summary "Kept Judgment Jars, Home Center, and Vlad as the three surfaces"
```

`prompt` without explicit keys emits only the active repository operational core. `prompt --all` deliberately includes the complete cached registry. Both paths receipt every Jar they load.

## Atom API

```text
GET /v1/atom/vlad/jars
GET /v1/atom/vlad/jars?id=<id-or-alias>
GET /v1/atom/vlad/jars?q=<terms>
```

Atom’s local context-access receipts remain pending until the existing Vlad heartbeat imports them and Home Center confirms exact readback.

## Daemon behavior

On each existing heartbeat, `vlad-jars sync`:

1. rebuilds/refreshes the dynamic registry when due;
2. imports new Atom context receipts;
3. imports durable Venice review outputs;
4. fails closed if any importer or outbox quarantine remains;
5. flushes the oldest valid pending receipt first;
6. verifies exact receipt ID and fingerprint through Home Center readback.

Transient failure preserves the receipt, error, attempt count, and bounded retry time. It never overwrites or drops an older shard.

## Failure and recovery

- Registry and receipt state writes are atomic.
- Home Center failure preserves the last verified cabinet and every pending receipt.
- Repository Jars rebuild from current source while Home Center is unavailable.
- A first-run Home Center failure yields a useful but incomplete local registry.
- Newly discovered artifacts remain `unregistered` until the cabinet indexes them.
- Malformed Atom/review imports are append-only quarantined rather than silently skipped.
- Quarantine remains visibly failed across later heartbeats until repaired.

## Deterministic verification

- `tools/test_judgment_jar_registry.py` exercises registry discovery, stale preservation, context receipts, separate review-output receipts, Venice import, fake Home Center append, and exact readback.
- `tools/test_judgment_jar_receipt_quarantine_truth.py` proves quarantine cannot be rounded up to delivered.
- `tools/judgment_jar_receipt_contract_check.py` verifies the three surfaces, missing Command Center, configured output kinds, strict public imports, and readback law.
- `atom/test/judgment-jars.test.mjs` verifies Atom registry access.
- `tools/run_fortress_local_contracts.sh` is the authorized local validation entrypoint. A repository commit does not prove those tests ran, the phone was updated, or Home Center delivery occurred.
