# Vlad Judgment Jars — Fast Access and Home Center Receipts

## Owner and boundary

Vlad is the deterministic access surface. The repository files remain source truth. Atom is the Home Center daemon that validates and durably acknowledges catalog and usage receipts. This design does not create a second Jar corpus, watcher, agent, or orchestration owner.

Active source glob:

```text
.continue/rules/*judgement-jar*.md
```

Current source-backed catalog:

1. `00-judgement-jar-mission-boundary.md`
2. `10-judgement-jar-local-first.md`
3. `20-judgement-jar-repository-truth.md`
4. `30-judgement-jar-change-discipline.md`
5. `40-judgement-jar-failure-recovery.md`
6. `50-judgement-jar-toolchain-freeze.md`
7. `70-judgement-jar-venice-review-gate.md`
8. `80-judgement-jar-daemon-backoff-persistence.md`

`60-adam-personality-gate.md` remains binding Adam steering but is not misreported as a Judgment Jar because it does not match the active Jar source contract.

## Fast Vlad commands

```bash
vlad jars
vlad jars list --json
vlad jar mission-boundary
vlad jar 70
vlad jar .continue/rules/80-judgement-jar-daemon-backoff-persistence.md
vlad jar status
vlad jar sync
```

Retrieving one Jar creates a `context_packet` usage receipt automatically.

An existing governed output can be receipted explicitly:

```bash
vlad jar receipt mission-boundary \
  --output-kind plan \
  --summary "Produced the bounded implementation plan." \
  --source "operator.plan" \
  --request-id "campaign-123" \
  --input "commission digest or source text" \
  --output "output digest or compact output" \
  --ref "receipt://plan-123"
```

The installed `vlad` command preserves the previous consultation behavior: text that is not a `jar`/`jars` command routes through the existing bounded `adam vlad` lane.

## Atom/Home Center daemon API

```text
GET  /v1/atom/vlad/jars
GET  /v1/atom/vlad/jars/:id-or-order-or-path
POST /v1/atom/vlad/jars/sync
POST /v1/atom/vlad/jars/receipts
```

Atom independently reads the repository files and rejects catalog or usage submissions whose path/hash identity does not match source truth. Duplicate usage receipt IDs are idempotent and do not append a second event.

Vlad status includes:

- exact Jar count;
- canonical catalog SHA-256;
- usage-receipt count;
- allowed output-kind taxonomy;
- daemon catalog and receipt paths.

## Usage receipt schema

Schema: `home-center.judgement-jar-usage-receipt.v1`

Required evidence:

- receipt id and capture timestamp;
- exact Jar id/order/title/path/filename/SHA-256/byte count;
- invocation source and request/group id;
- input SHA-256 and byte count;
- controlled output kind;
- output status and concise summary;
- output SHA-256, byte count, and durable references when available;
- metadata identifying the phase and governing workflow;
- separate capture and Home Center delivery states.

The controlled taxonomy lives in `config/judgement-jar-runtime.v1.json`. It currently includes context packets, answers, analyses, plans, decisions, routing actions, code changes, test results, review verdicts, artifacts, handoffs, memory updates, execution results, blockers, no-change results, and mixed outputs.

## Capture and delivery

`CAPTURED` means the append-only local receipt and authorized outbox shard exist.

`DELIVERED` means Atom/Home Center has:

1. resolved the exact Jar against repository source;
2. verified its SHA-256;
3. validated the output kind;
4. appended the usage event or recognized its idempotent duplicate;
5. returned a daemon receipt.

If Atom is unavailable, the usage remains in the local outbox. Retry is oldest-first. New output never overwrites or leaps past older pending shards. Local capture protects continuity but is not presented as Home Center delivery.

## Canonical automatic users

The receipt requirement is wired into:

- `tools/vlad_jars.py` for fast context access and explicit receipts;
- `tools/adam_planned_venice_receipted.py` for selected-Jar plan review, all-binding-Jar completion review, and terminal task output;
- `tools/venice_review_receipted.py` for independent canonical Venice CLI reviews;
- `tools/venice_review_selfheal.sh` as the review-inbox entrypoint;
- `atom/server.mjs` as daemon catalog and receipt authority;
- `tools/setup_vlad_swarm_daemon.sh` and `tools/install_adam_cli.sh` as installed command surfaces.

## Acceptance

Repository implementation is proven only when the source, tests, and remote diff exist. Runtime deployment requires a phone/Atom installation receipt from the commissioned Home Center body. Callability requires invoking `vlad jars`, fetching an exact Jar, and observing both the output-kind usage receipt and Atom acknowledgement. Human acceptance remains Drew's decision.
