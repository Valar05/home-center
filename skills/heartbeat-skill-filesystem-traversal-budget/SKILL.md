# Heartbeat Skill Filesystem Traversal Budget

## Purpose

Bound the **entire repository-skill filesystem walk** before any `repository_skill` record can earn title/hash authority. Candidate count alone is not enough: a tree may contain very few `SKILL.md` files behind arbitrarily many unrelated entries and directories.

This skill composes into the existing provenance probe only. It owns no second probe, registry, renderer, scheduler, phone lane, Phone Hands surface, P0 recovery chain, deployment path, or physical acceptance action.

## Canonical traversal contract

`tools/try_forever_skill_provenance_probe.py::bounded_skill_candidates` is the owner.

1. `MAX_SKILL_TRAVERSAL_ENTRIES = 32768` bounds **every encountered directory entry**, candidate or not.
2. Root-open work is constant; child directories themselves count as entries in their parent.
3. The traversal stores at most the admitted entry budget across the current directory snapshot plus pending directory stack; it does not materialize an unbounded recursive path list.
4. Each directory snapshot is sorted only after its entries have fit inside the remaining global traversal budget, preserving deterministic downstream behavior without resurrecting `sorted(rglob(...))`.
5. Directory symlinks are not followed. A `SKILL.md` file symlink may be observed as a candidate, but the existing resolved-path containment gate still decides whether it can earn authority.
6. Max+1 traversal entries raise `SkillTraversalResourceLimitError`.
7. Any traversal `OSError` fails the global discovery throat.
8. Traversal failure returns **no partial `SkillRecord` authority** and occurs before title/hash work.

## Why global failure is required

A missing unvisited path may hide a case-insensitive identity collision, path-escape wound, or additional candidate. Therefore a partial traversal cannot certify the repository-skill namespace. Do not emit "first N entries looked healthy" as authority.

## Structured wound

Traversal resource overflow:

- `path = skills`
- `stage = traversal`
- `error_type = SkillTraversalResourceLimitError`
- bounded reason states that the entry budget was exceeded and partial repository-skill authority is forbidden.

Traversal I/O failure uses the same `path` and `stage`, preserves the typed exception class, and never copies raw exception prose into the operator-facing reason.

## Symlink law

Do not recurse directory symlinks. This prevents cycles and scope expansion outside the `skills` tree. The existing `is_within(...)` resolved-path gate remains authoritative for any admitted `SKILL.md` file path; this traversal skill does not weaken or replace it.

## Regression source

`tools/test_try_forever_skill_filesystem_traversal_budget.py` pins:

- exact-entry-limit acceptance with deterministic candidate ordering;
- max+1 overflow caused entirely by non-candidate entries;
- zero partial authority and zero title/hash calls after traversal overflow;
- structured traversal I/O failure without raw exception leakage;
- directory-symlink non-recursion when the platform supports symlink creation;
- zero-budget first-entry rejection;
- negative-budget programmer-error behavior.

Regression source is not test execution. Promote to TESTED only from an authorized runner receipt.

## Composition order

`bounded filesystem traversal -> bounded candidate admission -> path identity/collision -> bounded title -> bounded exact whole-file SHA -> stable pre/post repository snapshot -> optional generated-index classification`

Each stage has a distinct failure class. Do not merge their evidence states for convenience.

## Capability membrane

Preserve independently:

`requested -> implemented source -> exact repository readback -> probe executed -> regression tested -> runtime UI consumed -> deployed -> callable -> executed -> delivered -> accepted`

A bounded repository walk does not prove the probe ran, tests passed, Android rendered, TalkBack exercised, phone delivery occurred, or P0 recovery changed state.

## P0 / phone firewall

Phone/P0 consumption **0** and mutation **0** for this skill. Do not wake, queue, probe, retask, or route around canonical Phone Hands / recovery ownership. If source archaeology exposes a P0 defect, preserve one concise finding for the canonical P0 owner only.

## Done

This light is active only when traversal-work truth materially changes: an unbounded walk gains a hard entry throat, symlink recursion is repaired, global failure semantics change, or fresh evidence invalidates those claims. Otherwise it stays dark.
