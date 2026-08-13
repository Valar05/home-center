# Vlad Judgment Jar Fast Access

## Purpose

Give Vlad one deterministic, phone-cheap route to every known Judgment Jar without flattening project-local jurisdiction or depending on repeated broad Drive searches.

## Trigger

Load this skill whenever Vlad plans, routes, challenges, reviews, resumes, or explains work; whenever a worker asks which Judgment Jars apply; or whenever Home Center Jar state may have changed.

## Two authoritative layers

1. **Repository operational core** — every file matching `.continue/rules/*judgement-jar*.md`. These are cached with complete bodies and remain usable offline.
2. **Home Center cabinet** — the native Drive document `START HERE — Judgment Jar Registry`, file ID `1UixBuLJRw-x5BoMGx81YXRpuN66iZhGGJoz40Iqx48Q`, plus Home Center Drive discovery for Jar artifacts newer than or absent from that cabinet.

The cabinet supplies names, jurisdictions, governing questions, hard gates, compact laws, run orders, status, and native source routes. It does not replace a linked project-local Sheet or Doc. Exact scoring, formulas, criteria, or case execution must read the native source.

## Fast-access surfaces

- Cache: `~/.local/state/home-center/vlad-swarm/judgment-jars.json`
- CLI: `vlad-jars`
- Atom endpoint: `GET /v1/atom/vlad/jars`
- Compiler/synchronizer: `tools/judgment_jars.py`
- Configuration: `config/judgment-jars.v1.json`
- Sync owner: the existing `vlad-swarm` daemon. Do not create a second Jar watcher.

Useful commands:

```text
vlad-jars status
vlad-jars list
vlad-jars get "Vlad"
vlad-jars source "Vlad"
vlad-jars search restart scarcity
vlad-jars prompt mission-boundary failure-recovery
vlad-jars prompt --all
vlad-jars registry
```

`vlad-jars get` is the cheap cached route. `vlad-jars source` reads the controlling native Sheet or Doc through Home Center and atomically caches its last verified source snapshot for offline/stale fallback.

American `judgment` and British `judgement` spellings resolve to the same aliases.

## Sync contract

On each daemon heartbeat, rebuild the repository core when source content changes. Refresh the Home Center cabinet only when its configured freshness window expires or an explicit force sync is requested. Search Home Center for newly reachable Jar artifacts and add metadata-only `unregistered` routes when the cabinet has not indexed them yet.

Every cache entry records its authority and completeness:

- `repository-operational-core` / `full-body`
- `home-center-cabinet` / `registry-summary`
- `home-center-discovery` / `metadata-only`

Never report a summary or metadata-only route as the complete native Jar.

## Failure behavior

A connector failure must not erase the cabinet. Preserve the previous valid Home Center snapshot, recompile current repository Jars, label the cache `stale` or `degraded`, retain the error, and continue offline with explicit completeness state. Atomic replacement is mandatory; a partial cache may never replace the last valid cache.

If there has never been a successful Home Center sync, local operational Jars remain callable but the registry is incomplete. That is degraded operation, not an empty cabinet and not permission to invent missing Jars.

## Routing law

Select only the Jars materially relevant to the bounded case. Venice remains mandatory where Fortress doctrine requires her. A Jar title, character voice, or cabinet presence does not transfer ownership, consent, canon authority, or stop authority.

When a search result is `unregistered`, use its source route for inspection and flag cabinet-index debt. Do not silently promote it to registered or mature status.

## Acceptance

The feature passes only when:

1. future `.continue` Jar files appear without a hard-coded list change;
2. registered Home Center cabinet entries resolve by title and alias;
3. newly discovered unregistered Drive Jars appear without replacing cabinet truth;
4. a failed Home Center refresh preserves the previous cabinet snapshot;
5. Atom exposes counts, digest, freshness, authority, completeness, and native source route;
6. the existing Vlad daemon owns refresh and survives restart with the same cache.
