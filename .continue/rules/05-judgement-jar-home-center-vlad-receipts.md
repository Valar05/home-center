# Judgment Jar: Home Center, Vlad, and Typed Output Receipts

Status: active
Scope: Fortress surfaces, Judgment Jar use, Vlad fast access, and receipt delivery

## Surface law

Exactly three fast-access surfaces exist for this architecture:

1. **Judgment Jars** — governed criteria, provenance, and native sources.
2. **Home Center** — authoritative household/project integration, durable sync, and verified delivery lane.
3. **Vlad** — deterministic phone-resident continuity, routing, scarcity, restart, and adversarial judgment organ.

**Command Center does not exist.** Never introduce it as a product, service, queue, architecture, owner, execution lane, or fourth operator surface. Historical source identifiers containing `command_center` are compatibility debt only; they grant no architectural authority and must not appear in new user-facing doctrine.

## Judgment

Every material use of a Judgment Jar must leave a typed receipt that says both **which Jar was used** and **what kind of output it created**.

Loading a Jar and creating a result are different events:

- a Jar lookup, native-source read, or compiled prompt creates a `context_packet` receipt;
- the answer, plan, decision, route, code change, test, review verdict, artifact, handoff, memory update, execution result, blocker, no-change result, or mixed output creates its own typed result receipt.

One context-access receipt does not satisfy the result-receipt requirement.

## Required receipt fields

Every receipt preserves:

- timestamp;
- surface: `jar`, `home_center`, or `vlad`;
- actor;
- intent;
- input/context identity and digest;
- Judgment Jar identity, origin, source path or file ID, source hash, and registry digest;
- decision/action;
- output kind;
- outcome/status;
- output digest and byte count where practical;
- artifact/log/source references;
- stable deduplication fingerprint;
- capture and Home Center delivery state.

## Delivery law

Receipt states are not interchangeable:

- `CAPTURED`: durably preserved in the local outbox.
- `PENDING_HOME_CENTER`: captured but not yet verified in Home Center.
- `DELIVERED`: the exact receipt ID and deduplication fingerprint survived a Home Center write and readback.

Local JSON, an Atom response, a successful process exit, or a scheduler assertion is never Home Center delivery.

The existing `vlad-swarm` daemon owns receipt continuation through the existing `vlad-jars sync` heartbeat. Do not create a second watcher. Pending receipts are append-only, retried oldest first with bounded backoff, and never overwritten or discarded because Home Center is temporarily unavailable.

## Fast-access commands

- Registry and context: `vlad-jars list|get|source|search|prompt`
- Receipt state: `vlad-jars receipt-status`
- Manual bounded flush: `vlad-jars flush-receipts`
- Typed created-output receipt: `python3 tools/jar_receipt.py record <jar...> --output-kind <kind> --intent <intent> --decision-action <action> --summary <summary>`

The configured native Home Center ledger is `Judgment Jar Usage Receipts — Vlad and Home Center`.

## Failure rule

A receipt transport failure must not erase the work product. Capture the exact receipt locally, preserve the output and provenance, mark Home Center delivery pending, and let the existing daemon retry. A local-capture failure is a real blocker to claiming the Jar use complete.

## Stop condition

A worker may not claim a Jar-governed slice complete while a required created-output receipt is missing. A pending Home Center receipt must be disclosed as pending; it may not be rounded up to delivered.

## Evidence that can change this judgment

Only a newer explicit instruction from Drew that changes the named surfaces or receipt contract.
