# Vlad Judgment Jar Fast Access

## Purpose

Give Vlad one deterministic, phone-cheap route to every known Judgment Jar and preserve a typed receipt for every Jar context load and every result the Jar helps create.

## Trigger

Load this skill whenever Vlad plans, routes, challenges, reviews, resumes, explains work, retrieves a Jar, compiles Jar context, or records a Jar-governed result.

## Surface law

Exactly three fast-access surfaces exist:

1. Judgment Jars
2. Home Center
3. Vlad

Command Center does not exist. Historical identifiers containing `command_center` are compatibility debt only; they do not name an active product, queue, architecture, owner, or fourth surface.

## Authoritative Jar layers

1. **Repository operational core** — every `.continue/rules/*judgement-jar*.md`; complete bodies remain usable offline.
2. **Home Center cabinet** — `START HERE — Judgment Jar Registry`, file ID `1UixBuLJRw-x5BoMGx81YXRpuN66iZhGGJoz40Iqx48Q`, plus Home Center discovery for newly reachable Jar artifacts.

The cabinet routes to native sources. Exact scoring, formulas, criteria, or case execution must read the linked native Sheet or Doc rather than treating a cabinet summary as the complete Jar.

## Fast access

- Registry cache: `~/.local/state/home-center/vlad-swarm/judgment-jars.json`
- Registry/context CLI: `vlad-jars`
- Typed created-output CLI: `python3 tools/jar_receipt.py`
- Receipt implementation: `tools/judgment_jar_receipts.py`
- Atom capture importer: `tools/judgment_jar_atom_import.py`
- Venice review importer: `tools/judgment_jar_review_import.py`
- Configuration: `config/judgment-jars.v1.json`
- Sync owner: the existing `vlad-swarm` daemon through `vlad-jars sync`; never create a second watcher.

Useful commands:

```text
vlad-jars status
vlad-jars list
vlad-jars get "Vlad"
vlad-jars source "Vlad"
vlad-jars search restart scarcity
vlad-jars prompt mission-boundary failure-recovery
vlad-jars prompt --all
vlad-jars receipt-status
vlad-jars flush-receipts
python3 tools/jar_receipt.py record mission-boundary \
  --output-kind decision \
  --intent "preserve the commissioned architecture" \
  --decision-action "rejected a fourth control surface" \
  --summary "Kept Judgment Jars, Home Center, and Vlad as the three surfaces"
```

`get`, `source`, and `prompt` automatically record `context_packet` receipts for every Jar loaded. That does not replace the separate typed receipt for the answer, plan, decision, route, code change, test, review verdict, artifact, handoff, memory update, execution result, blocker, no-change result, or mixed result created with that context.

## Required receipt fields

Every material receipt preserves:

- timestamp;
- surface: `jar`, `home_center`, or `vlad`;
- actor and intent;
- input/context digest;
- Jar identity, origin, source route/hash, and registry digest;
- decision/action;
- output kind and status;
- output digest and size when practical;
- artifact, log, or source references;
- stable deduplication fingerprint.

## Delivery truth

- `CAPTURED`: durable local outbox record exists.
- `PENDING_HOME_CENTER`: local capture exists, but Home Center delivery is not verified.
- `DELIVERED`: the exact receipt ID and fingerprint survived a Home Center append and readback in `Judgment Jar Usage Receipts — Vlad and Home Center`.

Local JSON, Atom capture, process exit, scheduler completion, or a successful function return is never Home Center delivery.

On every existing daemon heartbeat, `vlad-jars sync` imports Atom context receipts and durable Venice review outputs, then flushes the oldest pending receipt first. Malformed imports are preserved in quarantine. Transient Home Center failure keeps the receipt pending with bounded backoff; it never discards or overwrites the shard.

## Failure behavior

A connector failure preserves the previous valid Home Center cabinet snapshot, current repository Jars, every pending receipt, exact error, and explicit stale/degraded state. A receipt transport failure must not erase the work product. A local capture failure does block claiming the Jar use complete.

## Routing law

Select only the Jars materially relevant to the bounded case. A Jar title, voice, or cabinet presence does not transfer ownership, consent, canon authority, or stop authority. American `judgment` and British `judgement` spellings resolve to the same aliases.

## Acceptance

The feature passes only when:

1. new repository Jars appear without a hard-coded list change;
2. Home Center cabinet entries resolve by title and alias;
3. failed refresh preserves the previous cabinet and pending outbox;
4. context loads produce `context_packet` receipts;
5. created results produce their own configured output kind;
6. `CAPTURED`, `PENDING_HOME_CENTER`, and `DELIVERED` remain distinct;
7. Home Center delivery requires exact ID/fingerprint readback;
8. the existing Vlad daemon owns refresh and retry after restart;
9. no active doctrine introduces Command Center.
