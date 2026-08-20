# Heartbeat Generated-Index Source Head Contract

## Purpose

Keep a generated index's declared `sourceHead` in the correct evidence class. Missing evidence may be `UNRESOLVED`; a canonical but different Git object ID may be `STALE`; malformed or normalization-dependent identity must fail the source-head contract rather than masquerade as ordinary staleness.

## Contract

1. `None` and the exact empty string mean the source head is not declared.
2. Any non-empty declaration must already be canonical lowercase hexadecimal Git object-ID text of length 40 or 64.
3. Never trim, case-fold, Unicode-normalize, coerce, or otherwise repair the declared identity.
4. Classify malformed declared identity before comparing it with the current repository HEAD.
5. Keep this contract separate from JSON syntax admission, alias consistency, timestamp freshness, repository custody, and exact generated-index artifact custody.
6. The generated index remains a discovery aid; passing this contract does not create repository-skill authority.
7. Keep `requested → supporting source → owner wired → regression executed → tested → runtime → deployed → delivered → accepted` distinct.
8. Do not create a second provenance owner. `tools/try_forever_skill_provenance_probe.py` remains sole owner.
9. No phone/P0 surface consumption.

## Source

- `tools/try_forever_generated_index_source_head_policy.py`
- `tools/test_try_forever_generated_index_source_head_policy.py`
- `tools/test_try_forever_generated_index_source_head_owner_boundary.py` — intentionally RED until the sole owner consumes the policy.

## Capability membrane — 2026-08-20 0800

- Supporting exact source-head admission policy: **YES**
- Hostile regression source: **YES / UNEXECUTED**
- Sole-owner boundary fixture: **YES / RED / UNEXECUTED**
- Existing provenance owner consumes policy: **NO**
- TESTED: **NO**
- Runtime UI / TalkBack: **NO**
- Deployed / callable / executed / delivered / accepted: **NO**
- Phone/P0 consumption or mutation: **NO**
