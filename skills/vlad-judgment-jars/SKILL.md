# Vlad Judgment Jar Fast Access

## Purpose

Give Vlad one deterministic, phone-cheap route to every known Judgment Jar without flattening project-local jurisdiction or depending on repeated broad Drive searches. Every actual Jar use must also leave a durable receipt naming the kind of output it created.

## Trigger

Load this skill whenever Vlad plans, routes, challenges, reviews, resumes, or explains work; whenever a worker asks which Judgment Jars apply; whenever Home Center Jar state may have changed; or whenever a Jar-produced output needs provenance.

## Two authoritative layers

1. **Repository operational core** — every file matching `.continue/rules/*judgement-jar*.md`. These are cached with complete bodies and remain usable offline.
2. **Home Center cabinet** — the native Drive document `START HERE — Judgment Jar Registry`, file ID `1UixBuLJRw-x5BoMGx81YXRpuN66iZhGGJoz40Iqx48Q`, plus Home Center Drive discovery for Jar artifacts newer than or absent from that cabinet.

The cabinet supplies names, jurisdictions, governing questions, hard gates, compact laws, run orders, status, and native source routes. It does not replace a linked project-local Sheet or Doc. Exact scoring, formulas, criteria, or case execution must read the native source.

## Fast-access surfaces

- Cache: `~/.local/state/home-center/vlad-swarm/judgment-jars.json`
- CLI: `vlad jar ...`, `vlad jars ...`, and the compatibility command `vlad-jars`
- Typed output receipt CLI: `jar-receipt`
- Atom endpoint: `GET /v1/atom/vlad/jars`
- Compiler/synchronizer: `tools/judgment_jars.py`
- Usage capture/outbox: `tools/judgment_jar_receipts.py`
- Configuration and output taxonomy: `config/judgment-jars.v1.json`
- Sync owner: the existing `vlad-swarm` daemon. Do not create a second Jar watcher.

Useful commands:

```text
vlad jars status
vlad jars list
vlad jar "Vlad"
vlad jar source "Vlad"
vlad jars search restart scarcity
vlad jars prompt mission-boundary failure-recovery
vlad jars prompt --all
vlad jars receipt-status
vlad jars flush-receipts
vlad jar receipt mission-boundary plan "Produced the bounded plan." --summary "Bounded plan"
```

`get`, `source`, and `prompt` are actual context use and automatically emit `context_packet` receipts. `list`, `status`, and `search` are discovery-only and do not falsely claim Jar application. The `receipt` command records a later governed output such as a plan, decision, review verdict, code change, artifact, or execution result.

`get` is the cheap cached route. `source` reads the controlling native Sheet or Doc through Home Center and atomically caches its last verified source snapshot for offline/stale fallback.

American `judgment` and British `judgement` spellings resolve to the same aliases.

## Usage receipt contract

Every actual Jar context load, application, review pass, and governed terminal output emits one append-only usage receipt per Jar used. When several Jars govern one output, all receipts share a group/request identity but remain independently attributable.

Each receipt preserves:

- exact Jar ID/title/origin/status;
- source authority, path/file ID/URL, source SHA-256, and registry digest;
- invocation source, request/group identity, and input hash/size;
- controlled output kind from `config/judgment-jars.v1.json`;
- output status, concise summary, hash/size, and durable references where available;
- separate local capture and Home Center delivery states.

Output kind describes what the Jar helped produce. It never implies implementation, deployment, callability, delivery, human acceptance, or canon promotion.

A missing or invented output kind fails closed. A generic daemon receipt, model transcript, plan receipt, or review receipt is not a substitute for the per-Jar usage receipt.

## Capture, delivery, and retry

`PENDING_HOME_CENTER` means the append-only local history and authorized outbox shard exist. `DELIVERED_HOME_CENTER` means the authoritative Home Center ledger accepted the idempotent receipt and readback verified the exact receipt ID and output kind.

If Home Center is unavailable, preserve every shard. The existing Vlad daemon's normal registry sync flushes the same outbox; do not create a second watcher. Retry the oldest pending receipt first. Never overwrite, discard, leapfrog, or silently rebind a pending receipt. If a Jar source changes before delivery, block that shard visibly and retain it for provenance repair.

Local capture protects continuity but is not presented as Home Center delivery.

## Sync contract

On each daemon heartbeat, first retry pending usage receipts through the canonical CLI, then rebuild the repository core when source content changes. Refresh the Home Center cabinet only when its configured freshness window expires or an explicit force sync is requested. Search Home Center for newly reachable Jar artifacts and add metadata-only `unregistered` routes when the cabinet has not indexed them yet.

Every cache entry records its authority and completeness:

- `repository-operational-core` / `full-body`
- `home-center-cabinet` / `registry-summary`
- `home-center-discovery` / `metadata-only`

Never report a summary or metadata-only route as the complete native Jar.

## Failure behavior

A connector failure must not erase the cabinet. Preserve the previous valid Home Center snapshot, recompile current repository Jars, label the cache `stale` or `degraded`, retain the error, and continue offline with explicit completeness state. Atomic replacement is mandatory; a partial cache may never replace the last valid cache.

If there has never been a successful Home Center sync, local operational Jars remain callable but the registry is incomplete. That is degraded operation, not an empty cabinet and not permission to invent missing Jars.

Receipt capture failure blocks the claim that a Jar was applied. Home Center delivery failure does not destroy captured work; it produces a pending outbox state and the existing daemon retries it.

## Routing law

Select only the Jars materially relevant to the bounded case. Venice remains mandatory where Fortress doctrine requires her. A Jar title, character voice, or cabinet presence does not transfer ownership, consent, canon authority, or stop authority.

When a search result is `unregistered`, use its source route for inspection and flag cabinet-index debt. Do not silently promote it to registered or mature status.

## Acceptance

The feature passes repository verification only when:

1. future `.continue` Jar files appear without a hard-coded list change;
2. registered Home Center cabinet entries resolve by title and alias;
3. newly discovered unregistered Drive Jars appear without replacing cabinet truth;
4. a failed Home Center refresh preserves the previous cabinet snapshot;
5. Atom exposes counts, digest, freshness, authority, completeness, and native source route;
6. every actual `get`, `source`, `prompt`, plan review, completion review, and terminal governed output produces the correct per-Jar output-kind receipt;
7. daemon failure leaves pending shards intact and later delivers them oldest-first;
8. the existing Vlad daemon owns refresh/retry and survives restart with the same cache and outbox.

Repository evidence proves implementation only. Phone deployment, callability, Home Center delivery, and Drew acceptance require their own runtime receipts.
