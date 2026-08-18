# Heartbeat Skill Root Identity Revalidation

## Purpose

Prevent a repository-skill provenance probe from treating a path name as durable directory ownership when the `skills` root can be replaced between topology admission and later traversal/per-file authority.

This skill composes into the existing `tools/try_forever_skill_provenance_probe.py`. It owns no second provenance probe, registry daemon, renderer, controller, scheduler, phone lane, Phone Hands surface, P0 recovery path, deployment action, or physical acceptance chain.

## Platform truth

Python 3.13 exposes `os.scandir(file_descriptor)` on Unix, not as one universal cross-platform primitive. Windows also has directory junctions as name-surrogate reparse points distinct from ordinary symbolic links. Therefore do not claim one portable atomic no-follow directory-handle implementation unless the exact target platform proves it.

The portable source policy in `tools/try_forever_skill_root_identity.py` provides:

1. one no-follow root stat observation;
2. redirector classification from that observation (`symlink` / Windows mount-point junction where the platform exposes the reparse tag);
3. device/inode identity capture;
4. a second no-follow observation after candidate enumeration and before per-file title/hash authority;
5. fail-closed identity comparison.

## What this closes

The existing provenance probe now consumes this policy in source. An observable persistent root replacement, root type change, or redirector state that remains visible at the second observation is rejected before any `SkillRecord` earns title/hash authority **when the observed object identity/type differs**.

A filesystem device number by itself is not one-directory identity. The portable helper requires a non-zero inode/file-index component before `(device, inode)` may certify the same directory object; if that object identity is unavailable, revalidation fails closed.

## What this does not close

Two path observations are not an atomic handle binding. A hostile actor could theoretically swap the root after the first observation and restore the original object before the second. A replacement may also occur after the second observation while per-file work proceeds. Filesystem identity tokens can be reused after object deletion on some filesystems. The helper must not advertise elimination of any of these races merely because two observations compare equal.

Closing that stronger wound requires a platform-specific handle-relative/no-follow traversal-and-file-read design, or another capability that proves equivalent atomicity. Do not smuggle a Unix-only directory-fd claim into Windows support.

## Junction law

On Windows, `os.stat(..., follow_symlinks=False)` exposes `st_reparse_tag`; `stat.IO_REPARSE_TAG_MOUNT_POINT` identifies the mount-point reparse class used for directory junctions. A junction root is redirected topology and must not earn repository-owned-root authority merely because `Path.is_symlink()` is false.

## Regression source

`tools/test_try_forever_skill_root_identity.py` pins helper behavior. `tools/test_try_forever_skill_root_identity_integration.py` pins existing-owner composition:

- persistent root identity drift returns zero records before title/hash work;
- unavailable root identity returns zero records before title/hash work;
- a root junction is blocked before candidate traversal.

Regression source is not test execution.

## Owner integration state

Authenticated Home Center GitHub-admin mutation applied the former base-blob-locked delta to the existing owner:

- former base owner blob: `f7fe082751875e27213a9e324d85bc371f46f335`
- owner wiring commit: `3e3bdb5abc8d68dfe96c2337a931732e67a7a55a`
- wired owner blob: `e3627e342150c48f38099bb68fb118b3c54f2bf4`

Current capability truth:

- policy helper source: **YES**
- existing provenance probe consumes helper: **YES / SOURCE_WIRED**
- hostile helper regression source: **YES**
- hostile owner-integration regression source: **YES**
- exact authenticated repository readback: **YES**
- atomic cross-platform root binding: **NO**
- probe executed by authorized runner: **NO**
- regression tested: **NO**
- runtime UI/TalkBack: **NO**
- deployed/callable/executed/delivered/accepted: **NO**

## Evidence discipline

Keep these states separate:

`requested -> policy source -> owner source wired -> exact repository readback -> probe executed -> regression tested -> runtime UI -> deployed -> callable -> executed -> delivered -> accepted`

Owner source wiring does not prove the probe executed. Two path-level identity observations do not prove atomic directory-handle binding.

## P0 / phone firewall

Phone/P0 consumption **0**, mutation **0**, duplicate architecture **0**. Never wake, queue, retask, probe, or route around canonical P0/Phone Hands ownership for this skill.

## Done

The existing-owner integration seam is now source-wired and should go dark unless evidence changes it. The stronger atomic swap-and-restore / post-revalidation replacement / identity-reuse wound remains explicitly open for a different, platform-evidenced source slice.
