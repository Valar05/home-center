# Heartbeat Skill Filesystem Traversal Budget

## Purpose

Bound the **entire repository-skill filesystem walk** before any `repository_skill` record can earn title/hash authority. Candidate count alone is not enough: a tree may contain very few `SKILL.md` files behind arbitrarily many unrelated entries and directories. Repository-owned topology is also a prerequisite: the `skills` root itself may not be a symlink.

This skill composes into the existing provenance probe only. It owns no second probe, registry, renderer, scheduler, phone lane, Phone Hands surface, P0 recovery chain, deployment path, or physical acceptance action.

## Canonical traversal contract

`tools/try_forever_skill_provenance_probe.py::discover_skills` owns root-topology admission; `bounded_skill_candidates` owns the bounded walk after admission.

1. `skills_root = repo_root / "skills"` is inspected **before traversal**. If that root is a symlink, discovery fails with `SymlinkedSkillsRoot`; the target is never traversed, even if it resolves to a directory inside the repository.
2. A broken `skills` symlink is still a symlink wound, not laundered into `MissingSkillsDirectory`.
3. `MAX_SKILL_TRAVERSAL_ENTRIES = 32768` bounds **every encountered directory entry**, candidate or not.
4. Root-open work is constant; child directories themselves count as entries in their parent.
5. The traversal stores at most the admitted entry budget across the current directory snapshot plus pending directory stack; it does not materialize an unbounded recursive path list.
6. Each directory snapshot is sorted only after its entries have fit inside the remaining global traversal budget, preserving deterministic downstream behavior without resurrecting `sorted(rglob(...))`.
7. Directory symlinks below the admitted root are not followed. A `SKILL.md` file symlink may be observed as a candidate, but the existing resolved-path containment gate still decides whether it can earn authority.
8. Max+1 traversal entries raise `SkillTraversalResourceLimitError`.
9. Any traversal `OSError` fails the global discovery throat.
10. Root-topology or traversal failure returns **no partial `SkillRecord` authority** and occurs before title/hash work.

## Why global failure is required

A symlinked root can redirect the bounded walk into topology the repository does not own. A missing unvisited path may also hide a case-insensitive identity collision, path-escape wound, or additional candidate. Therefore neither redirected-root traversal nor a partial traversal can certify the repository-skill namespace. Do not emit "the target looked healthy" or "first N entries looked healthy" as authority.

## Structured wounds

Symlinked root:

- `path = skills`
- `stage = repository`
- `error_type = SymlinkedSkillsRoot`
- bounded reason states that traversal outside repository-owned topology is forbidden.

Traversal resource overflow:

- `path = skills`
- `stage = traversal`
- `error_type = SkillTraversalResourceLimitError`
- bounded reason states that the entry budget was exceeded and partial repository-skill authority is forbidden.

Traversal I/O failure uses the same `path` and `stage`, preserves the typed exception class, and never copies raw exception prose into the operator-facing reason.

## Symlink law

Reject the **root** symlink before `is_dir()` or `os.scandir()`. This ordering matters: a broken root symlink must remain a topology wound rather than degrading into a generic missing-directory result. After a real repository-owned root is admitted, do not recurse child directory symlinks. The existing `is_within(...)` resolved-path gate remains authoritative for any admitted `SKILL.md` file path; this traversal skill does not weaken or replace it.

## Regression source

`tools/test_try_forever_skill_root_topology.py` pins:

- symlinked-root rejection before bounded traversal, title extraction, or hashing;
- broken-root-symlink classification as `SymlinkedSkillsRoot` rather than missing directory;
- a real `skills` directory continuing to the bounded candidate gate.

`tools/test_try_forever_skill_filesystem_traversal_budget.py` continues to pin:

- exact-entry-limit acceptance with deterministic candidate ordering;
- max+1 overflow caused entirely by non-candidate entries;
- zero partial authority and zero title/hash calls after traversal overflow;
- structured traversal I/O failure without raw exception leakage;
- directory-symlink non-recursion when the platform supports symlink creation;
- zero-budget first-entry rejection;
- negative-budget programmer-error behavior.

Regression source is not test execution. Promote to TESTED only from an authorized runner receipt.

## Composition order

`repository-owned skills-root topology -> bounded filesystem traversal -> bounded candidate admission -> path identity/collision -> bounded title -> bounded exact whole-file SHA -> stable pre/post repository snapshot -> optional generated-index classification`

Each stage has a distinct failure class. Do not merge their evidence states for convenience.

## Capability membrane

Preserve independently:

`requested -> implemented source -> exact repository readback -> probe executed -> regression tested -> runtime UI consumed -> deployed -> callable -> executed -> delivered -> accepted`

A rejected root symlink or bounded repository walk does not prove the probe ran, tests passed, Android rendered, TalkBack exercised, phone delivery occurred, or P0 recovery changed state.

## P0 / phone firewall

Phone/P0 consumption **0** and mutation **0** for this skill. Do not wake, queue, probe, retask, or route around canonical Phone Hands / recovery ownership. If source archaeology exposes a P0 defect, preserve one concise finding for the canonical P0 owner only.

## Done

This light is active only when repository-root topology or traversal-work truth materially changes: a symlinked root gains a fail-closed admission gate, an unbounded walk gains a hard entry throat, child symlink recursion is repaired, global failure semantics change, or fresh evidence invalidates those claims. Otherwise it stays dark.
