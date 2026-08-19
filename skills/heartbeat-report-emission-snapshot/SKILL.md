# Heartbeat Report-Emission Snapshot Revalidation

## Purpose
A clean repository snapshot observed around direct skill discovery can become stale while later generated-index inspection and report assembly are still running. Authority should not escape without one final custody check.

## Contract
- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- A late revalidation is **preservation-only**: it may preserve an earlier authoritative certification but may never manufacture authority from a non-empty matching HEAD string.
- Prior certification authority is an explicit boolean input to the pure revalidation policy. Only literal `True` is authority-bearing; `False`, missing/unknown state, or arbitrary truthy values fail closed.
- Missing final HEAD, changed HEAD, unknown cleanliness, or a newly dirty checkout fail closed.
- **Do not synthesize the late observation from separate `git rev-parse` and `git status` subprocesses.** `tools/try_forever_repository_emission_observation.py` supplies HEAD plus worktree cleanliness from one Git-status process.
- The exact status command must carry `--ignore-submodules=none`. Repository custody may not inherit a local or `.gitmodules` ignore rule that hides dirty submodule worktrees from the final cleanliness observation.
- **One process must also be a bounded process.** The repository-emission observation owns a finite execution deadline. `subprocess.TimeoutExpired` becomes bounded `UNAVAILABLE` evidence with empty HEAD and unknown cleanliness; stale prior repository evidence may not be reused.
- **Porcelain path bytes are not authority text.** Capture status stdout as bytes. Decode only the ASCII `branch.oid` value needed for authority; any non-header record marks the observation dirty without decoding its filename/path payload. Host-locale decode failure or a non-UTF-8 filename must never crash the evidence lane or turn dirty state into unknown success.
- The one-process parser requires **exactly one canonical ASCII `branch.oid` header**. Duplicate headers are ambiguous even when identical; malformed-first/valid-later, non-ASCII OID text, first-wins, and last-wins evidence all fail closed.
- The one-process observation narrows split-observation drift but **does not prove atomic repository binding**. Git may observe a moving worktree while scanning; swap-and-restore, identity reuse, or mutation after the command remain outside the claim.
- A finite Git-status timeout bounds the helper-owned subprocess wait; it does **not** prove Git produced an atomic filesystem snapshot or that every underlying filesystem operation has an independent deadline.
- If the final gate fails after an earlier certification, authority-facing repository-skill records must be zeroed and the report must name an emission-snapshot failure rather than leave the earlier certification floating forward.
- A generated index that was `VERIFIED_CURRENT` against the earlier certified snapshot cannot remain current after the final custody gate fails. Its positive currentness is withheld as `UNRESOLVED`; already-negative `STALE`/`UNRESOLVED` diagnostics may remain diagnostic.
- Do not re-read or re-verify the generated index after the declared final repository-custody observation merely to recover a positive claim. That would create new evidence work after the supposed final gate.
- Strict mode must treat a failed final-emission gate as failure.
- Owner integration changes the durable report contract and therefore requires a new schema revision rather than silently mutating v3.

## Hostile fixtures
- non-authoritative prior snapshot + matching final HEAD remains `UNSTABLE`.
- arbitrary truthy prior authority such as string `"false"` remains `UNSTABLE`.
- duplicate/conflicting/malformed/non-ASCII `branch.oid` headers fail closed.
- non-UTF-8 bytes inside a changed/untracked path still mark the observation dirty without path decoding.
- finite status deadline survives timeout as `UNAVAILABLE`.
- the exact Git-status command includes `--ignore-submodules=none` and captures stdout as bytes.
- a porcelain-v2 submodule change record makes the observation dirty.

## Evidence discipline
Keep discovery-time snapshot certification, prior-authority state, generated-index inspection, final-emission observation, subprocess completion, raw porcelain bytes, submodule visibility, atomic binding, source implementation, regression source, execution, tests, runtime, deployment, delivery, and acceptance separate.

Current state:
- pure final-emission revalidation policy: **YES / SOURCE**
- explicit strict-boolean prior-authority gate: **YES / SOURCE**
- single-command final repository observation primitive: **YES / SOURCE**
- finite Git-status execution deadline + timeout fail-closed projection: **YES / SOURCE**
- explicit submodule-ignore override: **YES / SOURCE**
- byte-preserving porcelain capture + ASCII-only authority decode: **YES / SOURCE**
- repository-emission source blob: **e96d20fdf24bdc3d6e918b414b7b2f1cad47f48e**
- duplicate/conflicting/non-ASCII `branch.oid` fail-closed parser gate: **YES / SOURCE**
- hostile regression source including timeout, submodule-command, and non-UTF-8 path cases: **YES / SOURCE / UNEXECUTED**
- regression source blob: **df5595ae3d191938e6f03af6dac7ad4737b28836**
- generated-index emission-custody projection policy: **YES / SOURCE**
- existing provenance owner consumes the late observation primitive: **NO**
- prior report-boundary owner patch: **REJECTED_UNSAFE / DO NOT APPLY**
- authenticated owner readback: **schema v3 / owner integration NO**
- atomic repository binding: **NO**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, watcher, repository daemon, scheduler, Phone Hands lane, or P0 owner may be created for this rule. Compose the existing provenance owner only. Phone/P0 surfaces are outside this skill.
