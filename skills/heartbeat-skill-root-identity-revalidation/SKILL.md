# Heartbeat Skill Root Identity Revalidation

## Purpose

Prevent a repository-skill provenance probe from treating a path name as durable directory ownership when the `skills` root can be replaced between topology admission and later traversal/per-file authority.

This skill composes into the existing `tools/try_forever_skill_provenance_probe.py`. It owns no second provenance probe, registry daemon, renderer, controller, scheduler, phone lane, Phone Hands surface, P0 recovery path, deployment action, or physical acceptance chain.

## Platform truth

Python 3.13 exposes `os.scandir(file_descriptor)` on Unix, not as one universal cross-platform primitive. Windows also has directory junctions as name-surrogate reparse points distinct from ordinary symbolic links. Therefore do not claim one portable atomic no-follow directory-handle implementation unless the exact target platform proves it.

The portable source policy in `tools/try_forever_skill_root_identity.py` instead provides:

1. one no-follow root stat observation;
2. redirector classification from that observation (`symlink` / Windows mount-point junction where the platform exposes the reparse tag);
3. device/inode identity capture;
4. a second no-follow observation before per-file title/hash authority;
5. fail-closed identity comparison.

## What this closes

When consumed by the existing provenance probe, a persistent root replacement, root type change, or redirector state that remains visible at the second observation can be rejected before any `SkillRecord` earns title/hash authority.

If stable device/inode identity is unavailable, the portable revalidation must fail closed rather than calling a path string "the same directory."

## What this does not close

Two path observations are not an atomic handle binding. A hostile actor could theoretically swap the root after the first observation and restore the original object before the second. The helper must not advertise elimination of that swap-and-restore race.

Closing that stronger wound would require a platform-specific handle-relative/no-follow traversal-and-file-read design, or another capability that proves equivalent atomicity. Do not smuggle a Unix-only directory-fd claim into Windows support.

## Junction law

On Windows, `os.stat(..., follow_symlinks=False)` exposes `st_reparse_tag`; `stat.IO_REPARSE_TAG_MOUNT_POINT` identifies the mount-point reparse class used for directory junctions. A junction root is redirected topology and must not earn repository-owned-root authority merely because `Path.is_symlink()` is false.

## Regression source

`tools/test_try_forever_skill_root_identity.py` pins:

- same-directory revalidation when a stable identity token exists;
- persistent root replacement detection;
- no-follow symlink classification;
- Windows mount-point reparse classification where the interpreter exposes the constant;
- fail-closed behavior when device/inode identity is unavailable;
- redirector/type change taking priority over superficial token equality.

Regression source is not test execution.

## Owner integration state

`patches/try-forever-skill-root-identity-revalidation.patch` is an exact proposed delta against source blob `f7fe082751875e27213a9e324d85bc371f46f335`.

Current capability truth:

- policy helper source: **YES**
- hostile regression source: **YES**
- exact owner integration patch: **YES / PROPOSED_NOT_APPLIED**
- existing provenance probe consumes helper: **NO**
- atomic cross-platform root binding: **NO**
- probe executed by authorized runner: **NO**
- regression tested: **NO**
- runtime UI/TalkBack: **NO**
- deployed/callable/executed/delivered/accepted: **NO**

## Evidence discipline

Keep these states separate:

`requested -> policy source -> owner source wired -> exact repository readback -> probe executed -> regression tested -> runtime UI -> deployed -> callable -> executed -> delivered -> accepted`

A helper, patch artifact, or unit-test fixture is not owner integration. A path-level identity revalidation is not an atomic directory-handle guarantee.

## P0 / phone firewall

Phone/P0 consumption **0**, mutation **0**, duplicate architecture **0**. Never wake, queue, retask, probe, or route around canonical P0/Phone Hands ownership for this skill.

## Done

This light stays active only while root identity/topology truth materially changes. Once the existing probe consumes the policy and the remaining atomicity boundary is explicitly preserved, stop polishing it and move to a different independent wound.
