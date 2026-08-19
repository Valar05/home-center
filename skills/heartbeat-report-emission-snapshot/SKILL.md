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
- The one-process observation narrows split-observation drift but **does not prove atomic repository binding**. Git may observe a moving worktree while scanning; swap-and-restore, identity reuse, or mutation after the command remain outside the claim.
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

## Evidence discipline
Keep discovery-time snapshot certification, prior-authority state, generated-index inspection, final-emission observation, atomic binding, source implementation, regression source, execution, tests, runtime, deployment, delivery, and acceptance separate.

Current state:
- pure final-emission revalidation policy: **YES / SOURCE**
- explicit strict-boolean prior-authority gate: **YES / SOURCE**
- single-command final repository observation primitive: **YES / SOURCE**
- hostile regression source including non-empty/non-authoritative and truthy-nonboolean prior state: **YES / SOURCE / UNEXECUTED**
- generated-index emission-custody projection policy: **YES / SOURCE**
- existing provenance owner consumes the late observation primitive: **NO**
- prior report-boundary owner patch: **REJECTED_UNSAFE / DO NOT APPLY**
- authenticated owner readback: **schema v3 / owner integration NO**
- atomic repository binding: **NO**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, watcher, repository daemon, scheduler, Phone Hands lane, or P0 owner may be created for this rule. Compose the existing provenance owner only. Phone/P0 surfaces are outside this skill.
