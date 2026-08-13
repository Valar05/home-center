# Vlad Judgment Jar Fast Access and Home Center Sync

## Outcome

Vlad receives a single compact registry that combines the complete repository operational Jar bodies with the authoritative Home Center cabinet and newly discovered Jar artifacts. The existing `vlad-swarm` daemon owns synchronization; no duplicate watcher or second scheduler is introduced.

## Authority model

The registry has two controlling sources and one discovery lane:

| Layer | Authority | Cached material | Offline use |
|---|---|---|---|
| Operational core | `.continue/rules/*judgement-jar*.md` | Full body, path, SHA-256, aliases, status, scope | Yes |
| Cabinet | Home Center Drive Doc `START HERE — Judgment Jar Registry` (`1UixBuLJRw-x5BoMGx81YXRpuN66iZhGGJoz40Iqx48Q`) | Registry summary, jurisdiction, question, hard gates, compact law, run order, native source route | Last verified snapshot |
| Discovery | Home Center Drive title search | Metadata-only route for likely Jar artifacts absent from the cabinet | Last verified snapshot |

Project-local Jars remain in their project, character, or doctrine homes. The cache is a routing cabinet, not a migration and not a flattened replacement corpus.

## Files

- `config/judgment-jars.v1.json` — source pattern, cabinet identity, refresh window, discovery queries.
- `tools/home_center_mcp_client.py` — authenticated Home Center MCP reader with token refresh; secrets are never written to receipts.
- `tools/judgment_jars.py` — CLI entry point.
- `tools/judgment_jar_common.py`, `tools/judgment_jar_cabinet.py`, and `tools/judgment_jar_registry.py` — parser, compiler, atomic cache, native-source hydration, resolver, and search modules.
- `tools/vlad_swarm_daemon.py` — existing daemon heartbeat calls the compiler and records material sync transitions.
- `tools/setup_vlad_swarm_daemon.sh` — validates, performs an initial forced Home Center refresh, installs `vlad-jars`, and restarts the existing service when daemon source changes.
- `atom/server.mjs` — exposes registry status, listing, lookup, and search through `/v1/atom/vlad/jars`.

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
vlad-jars sync --force-home-center
vlad-jars status
vlad-jars list
vlad-jars get "What Would June Do?"
vlad-jars source "What Would June Do?"
vlad-jars search "custody authorship"
vlad-jars prompt mission-boundary repository-truth
vlad-jars prompt --all
vlad-jars registry
```

`prompt` without explicit keys emits only the active repository operational core. This prevents every Jar from being dumped into every task. `prompt --all` is deliberately explicit.

## Atom API

```text
GET /v1/atom/vlad/jars
GET /v1/atom/vlad/jars?id=<id-or-alias>
GET /v1/atom/vlad/jars?q=<terms>
```

The status surface includes coverage counts, digest, source commit, Home Center freshness, registry file ID, last error, and missing executable functions. Jar results include native source IDs/URLs when available. `vlad-jars source` reads the authoritative linked Sheet or Doc through Home Center and atomically caches the last verified source snapshot; a transient outage returns the stale verified snapshot instead of erasing it.

## Daemon behavior

The existing Vlad daemon invokes a cheap compiler pass on heartbeat. Local SHA comparison and the configured Home Center freshness window prevent broad remote reads on every heartbeat. A material change or failed Home Center refresh creates a durable daemon receipt.

The setup script writes the service environment and compares the daemon source SHA-256 with the installed stamp. A changed daemon is restarted so repository edits do not masquerade as deployed behavior while an old process remains resident.

## Failure and recovery

- Cache writes are atomic.
- Home Center failure preserves the last verified cabinet and marks it stale.
- Repository operational Jars are rebuilt from current source even while Home Center is unavailable.
- A first-run Home Center failure yields a useful but incomplete local registry.
- Newly discovered artifacts stay `unregistered` until the cabinet actually indexes them.
- Exact native Jar execution requires reading the linked Sheet or Doc; metadata and cabinet summaries are not laundered into full criteria.

## Deterministic verification

`tools/test_judgment_jar_registry.py` verifies dynamic local discovery, cabinet parsing, unregistered discovery, alias compatibility, atomic replacement, and stale-cache preservation.

`atom/test/judgment-jars.test.mjs` verifies Atom status, counts, full-body retrieval, Home Center source routes, unregistered status, and search.
