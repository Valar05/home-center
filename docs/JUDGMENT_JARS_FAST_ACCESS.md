# Judgment Jars — Vlad Fast Access and Home Center Sync

Status: implemented contract and executable cache; deployment/callability require body receipts.

## Owner and law

Home Center is the authoritative owner of every Judgment Jar. Vlad does not own a second jar library. Vlad receives a checksum-bound snapshot, serves it from a local SQLite cache, and returns append-only usage receipts.

The cache may continue serving the last verified snapshot while offline. Offline state never becomes newer source truth. A complete authoritative snapshot may tombstone jars that disappeared; a partial snapshot may not.

## What counts as “all jars”

The Home Center source adapter must enumerate the full authoritative set on every complete snapshot. Discovery includes:

- artifacts whose metadata type is `judgment_jar` or `judgement_jar`;
- artifacts whose canonical title identifies them as a Judgment/Judgement Jar;
- explicit members of the authoritative jar registry, including jars whose title does not use those words.

The sync is dynamic. Adding a new jar to Home Center makes it available to Vlad on the next verified snapshot without editing a hard-coded list.

## Files

- `config/judgment-jars.v1.json` — ownership, discovery, sync, lookup, and receipt contract.
- `functions/judgment_jar_registry.js` — Home Center snapshot compiler and idempotent receipt-ingestion service.
- `tools/vlad_judgment_jars.py` — local SQLite cache, alias/search API, two-phase usage receipts, durable outbox, and daemon loop.
- `functions/judgment_jar_registry.test.js` and `tools/vlad_judgment_jars_test.py` — deterministic contract tests.

## Home Center daemon adapters

Wire `createJudgmentJarRegistry` to the existing Home Center daemon with two explicit adapters:

```js
const { createJudgmentJarRegistry } = require('./judgment_jar_registry');

const judgmentJars = createJudgmentJarRegistry({
  source: {
    // Return every authoritative record, with source_ref and source_revision.
    listAllJudgmentJars: () => homeCenterJarSource.listAll(),
  },
  receiptStore: {
    // Append-only and idempotent by receipt_id.
    has: (receiptId) => homeCenterReceiptLedger.has(receiptId),
    append: (receipt) => homeCenterReceiptLedger.append(receipt),
  },
});
```

Expose the returned operations through the existing authenticated Home Center daemon lane:

- `judgment_jars.snapshot` → `judgmentJars.snapshot()`
- `judgment_jars.receipts.ingest` → `judgmentJars.ingestReceipts(envelope)`

Do not introduce a second Drive connector or a second watcher. The source adapter must use Home Center Drive v2 and its existing audit/receipt rules.

## Vlad boot

The daemon reads these environment variables:

- `HOME_CENTER_JUDGMENT_JARS_SNAPSHOT_URL`
- `HOME_CENTER_JUDGMENT_JARS_RECEIPT_URL`
- `HOME_CENTER_TOKEN`
- optional `VLAD_JUDGMENT_JARS_DB`

Run continuously:

```bash
python tools/vlad_judgment_jars.py daemon
```

The loopback API defaults to `127.0.0.1:8767`.

Administrative endpoints:

- `GET /v1/status`
- `GET /v1/jars`
- `GET /v1/jars/<id-or-alias>`
- `GET /v1/search?q=<terms>`

Actual judgment endpoints:

- `POST /v1/use` — resolves the jar and opens a receipt.
- `POST /v1/receipts/<receipt-id>/complete` — records output kind/reference/digest and queues delivery.
- `POST /v1/sync` — pulls the newest snapshot and pushes oldest pending receipts.

`GET /v1/jars/<...>` is inspection only. Vlad must use `POST /v1/use` for actual judgment so no output escapes without a receipt.

## CLI example

```bash
python tools/vlad_judgment_jars.py use venice \
  --request-id fortress-20260813-001 \
  --worker vlad \
  --campaign inner-fortress \
  --input-file /path/to/commission.txt

python tools/vlad_judgment_jars.py complete <receipt-id> \
  --output-kind plan_review \
  --output-ref home-center://reviews/fortress-20260813-001 \
  --output-file /path/to/verdict.txt

python tools/vlad_judgment_jars.py push-receipts
```

Each completed receipt records the exact jar and revision, request ID, worker, campaign, input digest, output kind, output reference, output digest, timestamps, terminal status, and delivery state.

## Failure behavior

- Home Center unavailable: serve the last verified snapshot and retain completed receipts in SQLite.
- Receipt delivery fails: increment attempts, preserve the error, and retry oldest pending first.
- Snapshot is partial: merge records but do not tombstone missing jars.
- Alias collision: reject the whole snapshot; do not silently route to the wrong jar.
- Duplicate request/jar use: return the existing receipt identity instead of opening an ambiguous second use.
- Jar disappears from a complete snapshot: tombstone it; do not erase historical receipts.

## Capability states

- Requested: all authoritative jars available quickly to Vlad and synchronized with Home Center.
- Implemented: config contract, Home Center service module, SQLite cache/API/daemon, two-phase receipts, offline outbox, tests, and CI workflow.
- Tested: only after the branch CI run is green.
- Deployed: only after the Home Center daemon operations and Vlad daemon are running on authorized bodies.
- Callable: only after a live snapshot pull, alias lookup, jar use, receipt close, and Home Center receipt ingest succeed.
- Accepted: only after Drew observes the intended fast access and receipt behavior.
