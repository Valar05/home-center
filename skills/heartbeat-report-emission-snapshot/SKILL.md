# Heartbeat Report-Emission Snapshot Revalidation

## Purpose
A clean repository snapshot observed around direct skill discovery can become stale while later generated-index inspection and report assembly are still running. Authority should not escape without one final custody check.

## Contract
- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- A late revalidation is **preservation-only**: it may preserve an earlier authoritative certification but may never manufacture authority from a non-empty matching HEAD string.
- Prior certification authority is an explicit boolean input to the pure revalidation policy. Only literal `True` is authority-bearing; `False`, missing/unknown state, or arbitrary truthy values fail closed.
- A late revalidation may certify only that an already-authoritative clean HEAD is observed again immediately before authority-facing report assembly.
- Missing final HEAD, changed HEAD, unknown cleanliness, or a newly dirty checkout fail closed.
- **Do not synthesize the late observation from separate `git rev-parse` and `git status` subprocesses.** `tools/try_forever_repository_emission_observation.py` supplies HEAD plus worktree cleanliness from one `git status --porcelain=v2 --branch --untracked-files=normal` process.
- **One process must also be a bounded process.** The repository-emission observation owns a finite execution deadline. `subprocess.TimeoutExpired` must become bounded `UNAVAILABLE` evidence with empty HEAD and unknown cleanliness; timeout may not escape and stale prior repository evidence may not be reused as if the late check succeeded.
- The one-process parser requires **exactly one canonical `branch.oid` header**. Duplicate headers are ambiguous even when identical; malformed-first/valid-later, first-wins, and last-wins evidence all fail closed rather than letting output order choose repository identity.
- The one-process observation narrows split-observation drift but **does not prove atomic repository binding**. Git may observe a moving worktree while scanning; swap-and-restore, identity reuse, or mutation after the command remain outside the claim.
- A finite Git-status timeout bounds the helper-owned subprocess wait; it does **not** prove Git produced an atomic filesystem snapshot or that every underlying filesystem operation has an independent deadline.
- If the final gate fails after an earlier certification, authority-facing repository-skill records must be zeroed and the report must name an emission-snapshot failure rather than leave the earlier certification floating forward.
- A generated index that was `VERIFIED_CURRENT` against the earlier certified snapshot cannot remain current after the final custody gate fails. Its positive currentness is withheld as `UNRESOLVED`; already-negative `STALE`/`UNRESOLVED` diagnostics may remain diagnostic.
- Do not re-read or re-verify the generated index after the declared final repository-custody observation merely to recover a positive claim. That would create new evidence work after the supposed final gate.
- Strict mode must treat a failed final-emission gate as failure.
- Owner integration changes the durable report contract and therefore requires a new schema revision rather than silently mutating v3.

## Hostile fixtures

`nonAuthoritativePriorSnapshotMustNotBecomeStableByMatchingFinalHead()`:
- prior observation has non-empty HEAD `abc123` but is non-authoritative;
- final observation is clean `abc123`;
- required verdict remains `UNSTABLE` and explicitly says late revalidation cannot manufacture authority;
- control: prior-authoritative `abc123` plus final-clean `abc123` may earn narrow `STABLE_CLEAN`.

`truthyNonBooleanPriorAuthorityMustFailClosed()`:
- a value such as string `"false"` must not satisfy the authority gate merely because Python considers it truthy;
- required verdict remains `UNSTABLE` and records `prior_authoritative=false`.

`duplicateBranchOidMustFailClosed()`:
- two identical canonical `branch.oid` headers are still ambiguous and return `UNAVAILABLE`;
- two conflicting canonical headers return `UNAVAILABLE`;
- malformed-first / valid-later output cannot repair itself into authority.

`repositoryEmissionObservationMustBoundGitStatusExecution()`:
- the exact Git-status call must carry the finite helper-owned deadline;
- simulated `subprocess.TimeoutExpired` returns `UNAVAILABLE`, empty HEAD, and unknown cleanliness;
- timeout must not escape and no stale prior observation may be substituted;
- a completed canonical porcelain-v2 observation still returns exact HEAD + cleanliness.

## Evidence discipline
Keep discovery-time snapshot certification, prior-authority state, generated-index inspection, final-emission observation, subprocess completion, atomic binding, source implementation, regression source, execution, tests, runtime, deployment, delivery, and acceptance separate.

Current state:
- pure final-emission revalidation policy: **YES / SOURCE**
- explicit strict-boolean prior-authority gate: **YES / SOURCE**
- single-command final repository observation primitive: **YES / SOURCE**
- finite Git-status execution deadline + timeout fail-closed projection: **YES / SOURCE**
- duplicate/conflicting `branch.oid` fail-closed parser gate: **YES / SOURCE**
- hostile regression source including prior-authority, duplicate-OID, and subprocess-timeout cases: **YES / SOURCE / UNEXECUTED**
- generated-index emission-custody projection policy: **YES / SOURCE**
- existing provenance owner consumes the late observation primitive: **NO**
- prior report-boundary owner patch: **REJECTED_UNSAFE / DO NOT APPLY**
- authenticated owner readback: **schema v3 / owner integration NO**
- atomic repository binding: **NO**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, watcher, repository daemon, scheduler, Phone Hands lane, or P0 owner may be created for this rule. Compose the existing provenance owner only. Phone/P0 surfaces are outside this skill.
