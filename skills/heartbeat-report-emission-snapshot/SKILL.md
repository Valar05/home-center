# Heartbeat Report-Emission Snapshot Revalidation

## Purpose

A clean repository snapshot observed around direct skill discovery can become stale while later generated-index inspection and report assembly are still running. Authority must not escape without one final custody check.

## Contract

- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Late revalidation is **preservation-only**: it may preserve earlier authoritative certification but may never manufacture authority from a matching HEAD string.
- Prior certification authority must be literal boolean `True`.
- Missing/changed final HEAD, unknown cleanliness, or a newly dirty checkout fail closed.
- The late observation comes from one bounded `git status --porcelain=v2 --branch --untracked-files=normal --ignore-submodules=none` process, not separate `rev-parse` + `status` calls.
- Porcelain output stays bytes; only the canonical ASCII `branch.oid` is decoded. Non-header records mark dirtiness without decoding filenames.
- Exactly one canonical branch object ID is required. Ambiguous/malformed headers fail closed.
- The process has a finite deadline; timeout becomes `UNAVAILABLE` and cannot donate stale evidence.
- This narrows observation drift but **does not prove atomic repository binding**.
- Failed final repository custody zeroes emitted repository-skill authority.
- A prior generated-index `VERIFIED_CURRENT` is also withheld when final repository custody fails.
- No new authority-facing generated-index read is performed after the declared final repository observation.
- Strict mode treats failed final-emission authority as failure.

## Existing-owner v4 composition

Schema `try-forever-skill-provenance.v4` now invokes `observe_repository_emission(repo_root)` after optional late generated-index artifact revalidation and before pure report assembly. The resulting observation feeds `compose_provenance_emission(...)` with the earlier literal repository certification state and certified HEAD.

The emitted report separates:

- initial `repositorySnapshot`;
- authority at certification;
- final `reportEmissionRepository` status/reason/authority;
- final observed HEAD/dirty state;
- emitted skill records, which are zeroed when late authority is lost.

This is source wiring, not runtime execution or tested evidence.

## Hostile fixtures

Pure fixtures cover prior-authority preservation, changed/unavailable final custody, duplicate/malformed OIDs, timeout, submodules, and byte-hostile paths. `tools/test_try_forever_provenance_owner_v4_emission.py` adds owner-level source fixtures for stable survival, late HEAD change zeroing skill authority, generated-index currentness withholding, and strict-mode failure.

## Current capability truth

- pure final-emission revalidation policy: **YES / SOURCE**
- one-process bounded final repository observation primitive: **YES / SOURCE**
- existing provenance owner consumes late repository observation: **YES / SOURCE_WIRED**
- existing owner composes final repository authority into emitted skill records: **YES / SOURCE_WIRED**
- owner schema: **try-forever-skill-provenance.v4**
- owner commit/blob: **90054f3f0761b0993d635527d60ad43f68c20a8d / f6f1bafc6b9e99030ad29b408d74cd088f910b82**
- owner-v4 regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**
- owner-v4 regression commit/blob: **19dd1621093eaefc830b13938404a2192c979584 / ebea66749d5038be4d303827681df38adfe1d554**
- prior unsafe report-boundary patch: **REJECTED_UNSAFE / DO NOT APPLY**
- atomic repository binding: **NO**
- tested: **NO**
- runtime UI / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## Ownership / firewall

No second provenance probe, watcher, repository daemon, scheduler, Phone Hands lane, or P0 owner may be created. Phone/P0 consumption and mutation remain zero.
