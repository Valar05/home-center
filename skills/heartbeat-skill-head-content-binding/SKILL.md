# Heartbeat Skill Head Content Binding

## Purpose

Prevent a clean-looking Git worktree from certifying `repository_skill` provenance when the exact observed `SKILL.md` bytes do not equal the blob committed at the certified HEAD.

## Why this exists

The sole provenance owner already has strong topology, bounded traversal, tracked-path, content-custody, snapshot, and expected-head gates. That still leaves a distinct authority seam: Git index flags such as `assume-unchanged` and `skip-worktree` intentionally alter ordinary worktree checking. `git status` cleanliness plus `git ls-files` membership therefore must not substitute for an exact content-to-HEAD binding.

Code-first review exposed a second authority wrinkle: replacement refs can make normal Git object traversal observe a replacement graph rather than the raw named objects. Authority-facing Git subprocesses now reuse the shared sanitized environment with `GIT_NO_REPLACE_OBJECTS=1`; HEAD blob observation must inherit that environment rather than trusting replacement-aware porcelain semantics.

## Existing organs to compose

- `tools/try_forever_skill_provenance_probe.py` — sole provenance owner.
- `tools/try_forever_skill_content_custody.py` — one bounded stable worktree artifact supplies title + raw SHA + Git blob object identity derived from the same strict-UTF-8 observation.
- `tools/try_forever_tracked_skill_observation.py` — exact candidate membership in Git's tracked set.
- `tools/try_forever_repository_emission_observation.py` — bounded one-process HEAD + cleanliness observation and shared authority-facing Git environment; replacement objects are disabled there in source.
- `tools/try_forever_skill_head_blob_observation.py` — supporting source: exact ordinary blob OID per already-bounded candidate from the named raw HEAD tree.
- `tools/try_forever_skill_head_content_binding.py` — supporting source: Git blob object identity for exact bytes and fail-closed comparison with the HEAD blob.

## Contract

1. **HEAD tree, not clean-status inference, owns committed content identity.** Every authority-facing candidate must name exactly one ordinary regular-file blob at the certified HEAD.
2. **Raw named Git objects own authority.** Authority-facing subprocesses must disable replacement objects. A replacement graph is not the same evidence as the named HEAD/tree/blob graph.
3. **Exact bytes own the worktree side.** Compare the Git blob identity derived from the same bounded stable content observation used for title/raw SHA evidence. Do not reopen the path merely to compute the binding.
4. **Strict UTF-8 round-trip must preserve the observed byte count.** The content-custody organ fails closed if its already-admitted text cannot reproduce the observed byte count before Git object framing.
5. **Repository hash format is explicit.** A 40-hex HEAD blob selects Git SHA-1 object framing; a 64-hex HEAD blob selects Git SHA-256 object framing. Unknown or non-canonical OID shapes fail closed.
6. **SHA-1 here is compatibility framing, not a security primitive.** Python hashing is explicitly requested with `usedforsecurity=False` for Git SHA-1 object-format compatibility; SHA-256 repositories use Git SHA-256 framing.
7. **Mismatch is not repairable by status.** `STABLE_CLEAN`, tracked-path membership, mtime, size, or other convenience evidence cannot override an exact content mismatch.
8. **No partial alias authority from a broken HEAD observation.** If the bounded HEAD-tree query cannot return exactly one ordinary blob for every requested candidate, the observation yields zero blob authority.
9. **Do not create a second provenance owner.** These helpers are organs for the existing probe only.
10. **Do not overclaim atomicity.** A future owner composition must preserve the existing content-custody and file-identity race boundaries. This policy proves equality of two exact identities, not universal filesystem atomicity.

## Source advance — 2026-08-20 0700

Authenticated Home Center GitHub-admin source mutation extended `tools/try_forever_skill_content_custody.py` so `SkillContentObservation` now exposes `git_blob_identity`. That identity is derived from the same strict-UTF-8 observation that already supplies title and raw SHA; no second `Path.open` or `git hash-object` subprocess was added. A byte-count invariant fails closed if the strict-UTF-8 round trip ever ceases to preserve the finite artifact observation.

`tools/test_try_forever_skill_content_custody.py` now pins title/raw-SHA/Git-blob identity to one mocked artifact observation and includes a byte-count-drift failure fixture. `tools/test_try_forever_skill_head_content_owner_boundary.py` remains intentionally RED and now requires the sole owner to compose the existing HEAD-tree and content-binding organs before `SkillRecord` append.

A base-blob-locked exact owner surgery is preserved at `patches/try-forever-skill-head-content-owner.delta.json`. Its base owner blob is `1882ed3b6cf7fe7a9ab5c44862640a6f415bdd1d`. The delta is **PROPOSED_NOT_APPLIED**: source preparation is not owner implementation.

## Regression source

- `tools/test_try_forever_skill_content_custody.py`
- `tools/test_try_forever_skill_head_blob_observation.py`
- `tools/test_try_forever_skill_head_content_binding.py`
- `tools/test_try_forever_skill_head_content_owner_boundary.py` — intentionally RED until the sole owner composes the existing organs.
- `tools/test_try_forever_repository_emission_observation.py` — pins replacement-object suppression in the shared Git authority environment.

The fixtures are regression **source**, not executed test evidence until an authorized runner actually executes them.

## Current capability membrane

- Shared authority-facing Git environment disables replacement objects: **YES / SOURCE_WIRED**
- Supporting HEAD-tree blob observation source: **YES**
- Supporting exact Git-blob content binding source: **YES**
- Existing single-artifact content observation exposes Git blob identity: **YES / SOURCE_WIRED**
- Same-observation helper regression source: **YES / UNEXECUTED**
- Sole-owner integration regression: **YES / RED / UNEXECUTED**
- Exact sole-owner integration delta: **YES / PROPOSED_NOT_APPLIED**
- Existing provenance owner consumes HEAD blob observation: **NO**
- Existing owner gates repository-skill authority on content↔HEAD equality: **NO**
- TESTED: **NO**
- Runtime UI / TalkBack: **NO**
- Deployed / callable / executed / delivered / accepted: **NO**
- Phone/P0 consumption or mutation: **NO**

## Current execution boundary

The non-phone Computer Hands worker currently reports `online=false` with `lane-try-forever-provenance-owner` already active and queue depth 4. Active lane identity is not an exact request identity, so this swarm must not enqueue a duplicate owner surgery merely to make the heartbeat look busy. Direct repository source preparation through Home Center remains valid; owner promotion still requires one safe existing-owner mutation plus authenticated readback.

## Next owner cut

Apply the base-blob-locked delta only through a safe existing-owner lane: pass the already-observed discovery HEAD into the sole owner, observe the bounded raw-HEAD blob set once for the bounded candidate set, and reject unavailable/mismatched content before `SkillRecord` append using `content.git_blob_identity`. Preserve every existing root/tracked/file/content/snapshot/final-emission gate. No second content read. No second provenance owner.
