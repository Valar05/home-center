# Heartbeat Skill Head Content Binding

## Purpose

Prevent a clean-looking Git worktree from certifying `repository_skill` provenance when the exact observed `SKILL.md` bytes do not equal the blob committed at the certified HEAD.

## Why this exists

The sole provenance owner already has strong topology, bounded traversal, tracked-path, content-custody, snapshot, and expected-head gates. That still leaves a distinct authority seam: Git index flags such as `assume-unchanged` and `skip-worktree` intentionally alter ordinary worktree checking. `git status` cleanliness plus `git ls-files` membership therefore must not substitute for an exact content-to-HEAD binding.

Code-first review exposed a second authority wrinkle: replacement refs can make normal Git object traversal observe a replacement graph rather than the raw named objects. Authority-facing Git subprocesses now reuse the shared sanitized environment with `GIT_NO_REPLACE_OBJECTS=1`; HEAD blob observation must inherit that environment rather than trusting replacement-aware porcelain semantics.

## Existing organs to compose

- `tools/try_forever_skill_provenance_probe.py` — sole provenance owner.
- `tools/try_forever_skill_content_custody.py` — one bounded stable worktree artifact supplies title + SHA.
- `tools/try_forever_tracked_skill_observation.py` — exact candidate membership in Git's tracked set.
- `tools/try_forever_repository_emission_observation.py` — bounded one-process HEAD + cleanliness observation and shared authority-facing Git environment; replacement objects are disabled there in source.
- `tools/try_forever_skill_head_blob_observation.py` — supporting source: exact ordinary blob OID per already-bounded candidate from the named raw HEAD tree.
- `tools/try_forever_skill_head_content_binding.py` — supporting source: Git blob object identity for exact bytes and fail-closed comparison with the HEAD blob.

## Contract

1. **HEAD tree, not clean-status inference, owns committed content identity.** Every authority-facing candidate must name exactly one ordinary regular-file blob at the certified HEAD.
2. **Raw named Git objects own authority.** Authority-facing subprocesses must disable replacement objects. A replacement graph is not the same evidence as the named HEAD/tree/blob graph.
3. **Exact bytes own the worktree side.** Compare the exact bytes from the same bounded stable content observation used for skill evidence. Do not reopen the path merely to compute the binding.
4. **Repository hash format is explicit.** A 40-hex HEAD blob selects Git SHA-1 object framing; a 64-hex HEAD blob selects Git SHA-256 object framing. Unknown or non-canonical OID shapes fail closed.
5. **SHA-1 here is compatibility framing, not a security primitive.** Python hashing is explicitly requested with `usedforsecurity=False` for Git SHA-1 object-format compatibility; SHA-256 repositories use Git SHA-256 framing.
6. **Mismatch is not repairable by status.** `STABLE_CLEAN`, tracked-path membership, mtime, size, or other convenience evidence cannot override an exact content mismatch.
7. **No partial alias authority from a broken HEAD observation.** If the bounded HEAD-tree query cannot return exactly one ordinary blob for every requested candidate, the observation yields zero blob authority.
8. **Do not create a second provenance owner.** These helpers are organs for the existing probe only.
9. **Do not overclaim atomicity.** A future owner composition must preserve the existing content-custody and file-identity race boundaries. This policy proves equality of two exact identities, not universal filesystem atomicity.

## Regression source

- `tools/test_try_forever_skill_head_blob_observation.py`
- `tools/test_try_forever_skill_head_content_binding.py`
- `tools/test_try_forever_skill_head_content_owner_boundary.py` — intentionally RED until the sole owner composes the new organs.
- `tools/test_try_forever_repository_emission_observation.py` — pins replacement-object suppression in the shared Git authority environment.

The fixtures are regression **source**, not executed test evidence until an authorized runner actually executes them.

## Current capability membrane

- Shared authority-facing Git environment disables replacement objects: **YES / SOURCE_WIRED**
- Supporting HEAD-tree blob observation source: **YES**
- Supporting exact Git-blob content binding source: **YES**
- Hostile regression source: **YES / UNEXECUTED**
- Existing provenance owner consumes HEAD blob observation: **NO**
- Existing skill-content observation exposes exact Git blob identity to owner: **NO**
- Existing owner gates repository-skill authority on content↔HEAD equality: **NO**
- TESTED: **NO**
- Runtime UI / TalkBack: **NO**
- Deployed / callable / executed / delivered / accepted: **NO**
- Phone/P0 consumption or mutation: **NO**

## Next owner cut

Do not add a second content read. Extend the existing single-artifact content observation with the Git blob identity derived from those exact observed bytes, observe bounded raw HEAD blob OIDs for the same candidate set, then make the sole owner refuse authority when any emitted record's exact content identity disagrees with HEAD.
