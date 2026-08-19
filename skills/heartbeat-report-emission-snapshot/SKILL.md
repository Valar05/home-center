# Heartbeat Report-Emission Snapshot Revalidation

## Purpose

A clean repository snapshot observed around direct skill discovery can become stale while generated-index inspection and report assembly are still running. Authority must not escape without one final custody check.

## Contract

- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Late revalidation is **preservation-only**: it may preserve earlier authoritative certification but may never manufacture authority from a matching HEAD string.
- Prior certification authority must be literal boolean `True`.
- Missing/changed final HEAD, unknown cleanliness, or a newly dirty checkout fail closed.
- The late observation comes from one bounded `git status --porcelain=v2 --branch --untracked-files=normal --ignore-submodules=none` process, not separate `rev-parse` + `status` calls.
- Porcelain output stays bytes; only the canonical ASCII `branch.oid` is decoded. Non-header records mark dirtiness without decoding filenames.
- Exactly one canonical branch object ID is required. Ambiguous/malformed headers fail closed.
- The process has a finite deadline; timeout becomes `UNAVAILABLE` and cannot donate stale evidence.
- The observer removes inherited Git repository-redirection environment (`GIT_DIR`, `GIT_WORK_TREE`, common-dir/index/object/namespace/shallow overrides) while preserving ordinary process environment such as `PATH`. `cwd=repo_root` alone is not sufficient evidence that Git observed the requested repository.
- This narrows observation drift and parent-process injection but **does not prove atomic repository binding**.
- Failed final repository custody zeroes emitted repository-skill authority.
- A prior generated-index `VERIFIED_CURRENT` is also withheld when final repository custody or exact late artifact custody fails.
- No new authority-facing generated-index read is performed after the declared final repository observation.
- Strict mode treats failed final-emission authority as failure.

## Existing-owner v5 composition

Schema `try-forever-skill-provenance.v5` invokes exact generated-index late artifact revalidation only for prior positive currentness, then invokes `observe_repository_emission(repo_root)` as the final repository custody observation before pure report assembly. `compose_provenance_emission(...)` receives the earlier literal repository certification state, certified HEAD, exact initial generated-index inspection SHA, optional late artifact SHA, and final repository observation.

The emitted report separates:

- initial `repositorySnapshot`;
- authority at certification;
- final `reportEmissionRepository` status/reason/authority;
- final observed HEAD/dirty state;
- exact initial/late generated-index artifact identities;
- emitted skill records, which are zeroed when late repository authority is lost.

This is source wiring, not runtime execution or tested evidence.

## Cross-pollinated initial-snapshot wound

The final-emission observer is stronger than the owner's current **initial** snapshot plumbing. `main()` still builds the pre/post-discovery certification snapshot from separate `git_head()` and `git_dirty()` subprocesses. Those calls lack the final observer's one-process coherence, byte-safe porcelain handling, submodule-ignore override, finite deadline, and repository-redirection environment isolation.

The existing final-emission organ should be reused for the two initial bracket observations as well. This is a composition improvement, not permission to rename it atomic. A dedicated RED owner-boundary regression and exact proposed owner delta preserve that cut.

## Hostile fixtures

Pure fixtures cover prior-authority preservation, changed/unavailable final custody, duplicate/malformed OIDs, timeout, submodules, byte-hostile paths, exact generated-index artifact A→B change, negative-state late-I/O suppression, and inherited Git repository-redirection variables. Owner-level source fixtures cover stable survival, late HEAD change zeroing skill authority, generated-index currentness withholding, strict-mode failure, and portable v5 report projection.

`tools/test_try_forever_repository_emission_observation.py` now explicitly poisons `GIT_DIR`, `GIT_WORK_TREE`, common-dir/index/object/namespace/shallow environment while preserving a benign `PATH`, and requires the observer subprocess environment to remove every repository redirect. This is **REGRESSION_SOURCE / UNEXECUTED**.

The initial-snapshot owner boundary `tools/test_try_forever_provenance_initial_snapshot_owner_boundary.py` requires the existing bounded one-process observer before discovery, after discovery, and again at final emission; it is **REGRESSION_SOURCE / UNEXECUTED**.

## Current capability truth

- pure final-emission revalidation policy: **YES / SOURCE**
- one-process bounded final repository observation primitive: **YES / SOURCE**
- repository-redirection environment isolation in that primitive: **YES / SOURCE**
- repository-observation regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**
- existing provenance owner consumes late repository observation: **YES / SOURCE_WIRED**
- existing owner composes final repository + generated-index artifact custody into emitted authority: **YES / SOURCE_WIRED**
- owner schema: **try-forever-skill-provenance.v5**
- authenticated owner blob before initial-snapshot surgery: **e1d10fb4c917813bc89780486c79a5e2d2bc4bea**
- initial pre/post discovery use of the same one-process observer: **NO**
- initial-snapshot owner delta: `patches/try-forever-provenance-initial-snapshot-observation.patch` **YES / PROPOSED_NOT_APPLIED**
- initial-snapshot regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**
- atomic repository binding: **NO**
- tested: **NO**
- runtime UI / TalkBack: **NO**
- deployed / callable / executed / delivered / accepted: **NO**

## Ownership / firewall

No second provenance probe, watcher, repository daemon, scheduler, Phone Hands lane, or P0 owner may be created. Reuse the existing repository-observation organ and sole provenance owner. Phone/P0 consumption and mutation remain zero.
