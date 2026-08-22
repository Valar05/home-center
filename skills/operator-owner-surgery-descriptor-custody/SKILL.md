# Operator Owner Surgery Descriptor Custody

## Purpose
Strengthen TRY FOREVER owner-surgery **root custody** on runtimes that expose the required POSIX descriptor primitives, without rewriting the canonical portable v10 owner or pretending pathname revalidation is universal filesystem atomicity.

This skill owns one source/evidence distinction. It does **not** own a second custody probe, patch executor, overlay controller, scheduler, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core law
`HELD DIRECTORY DESCRIPTOR + DESCRIPTOR-RELATIVE NAME OPERATIONS != UNIVERSAL FILESYSTEM ATOMICITY`.

A root opened once with `O_DIRECTORY|O_NOFOLLOW` and then used through descriptor-relative scan/open/stat cannot be silently redirected by replacing the **root pathname after the descriptor is held**. That is materially stronger than a pre/post pathname bracket.

It still does not prove:
- atomic candidate-name binding across every filesystem;
- immunity to candidate swap-and-restore between observations;
- immunity to inode/file-index reuse;
- Windows parity;
- regression execution;
- canonical owner integration;
- TESTED/runtime/deployment/phone delivery/acceptance.

## Capability admission
`tools/try_forever_directory_handle_binding_capability.py` may report `SUPPORTED_POSIX_PRIMITIVES` only when the current runtime exposes all of:
- POSIX runtime identity;
- `scandir(fd)`;
- `open(..., dir_fd=...)`;
- `stat(..., dir_fd=...)`;
- `stat(..., follow_symlinks=False)`;
- `O_DIRECTORY`;
- `O_NOFOLLOW`.

Missing any one primitive means `PORTABLE_ATOMIC_BINDING_UNAVAILABLE`. Do not downgrade the requirement to make a platform look greener.

## Source organ
`tools/try_forever_posix_directory_handle_custody.py` is supporting source only.

It:
1. opens the named root once with `O_DIRECTORY|O_NOFOLLOW`;
2. verifies the held descriptor is an ordinary directory with usable inode identity;
3. opens a **fresh `.` directory handle relative to the held root for each inventory scan**, so repeated scans do not inherit directory-stream position from an earlier enumeration while remaining anchored to the same held root;
4. enumerates candidate names through that fresh descriptor-relative handle with independent entry/candidate budgets;
5. rejects traversal syntax before descriptor-relative file operations;
6. no-follow stats a candidate relative to the held directory;
7. opens that same basename relative to the held directory with `O_NOFOLLOW` and `O_NONBLOCK` where available;
8. requires pre-stat/open-fd identity agreement;
9. reads complete content inside a hard max+1 byte throat;
10. requires post-read descriptor stability;
11. requires the still-held directory name to identify the same regular-file object after the read;
12. decodes strict UTF-8 and returns exact SHA-256 evidence.

The root descriptor is the authority anchor for the operation. The source does not re-resolve the root pathname for candidate work.

### Review scar: scan position is state
The first supporting-source draft passed the authority descriptor itself directly to `os.scandir`. Review rejected that as too casual because directory stream position is state; a later scan must not depend on where an earlier scan left the descriptor. The corrected source opens `.` relative to the held authority root for every scan. This preserves root custody while giving each bounded inventory pass a fresh directory position.

## Regression source
`tools/test_try_forever_posix_directory_handle_custody.py` — **UNEXECUTED**.

It includes:
- held root survives named root replacement;
- candidate enumeration remains on the held original directory after root-path replacement;
- repeated candidate scans return the same deterministic inventory rather than inheriting old stream position;
- descriptor-relative symlink artifact rejection;
- max+1 byte rejection with no prefix authority;
- traversal-name rejection.

`tools/test_try_forever_directory_handle_binding_capability.py` is also **UNEXECUTED** and now pins descriptor-relative no-follow stat as a required primitive.

## Canonical owner relationship
Canonical owner-surgery custody remains `tools/try_forever_owner_surgery_custody_probe.py` v10. It is already **SOURCE_WIRED** for portable persistent-drift root revalidation.

Descriptor-bound custody is currently:
- supporting implementation **YES**;
- authenticated GitHub source readback **YES**;
- regression source **YES / UNEXECUTED**;
- canonical v10 owner consumption **NO**;
- TESTED **NO**;
- runtime/deployed/delivered/accepted **NO**.

Do not replace v10 merely because this POSIX source exists. Any future owner composition must preserve the portable fallback and must re-enter exact owner custody/review before mutation.

## Current inventory companion
`tools/test_try_forever_owner_surgery_current_inventory.py` independently targets the 08:02 wound: whether the actual current `patches/` inventory is fully admissible under v10's stricter exact textual state grammar. It is **REGRESSION SOURCE / UNEXECUTED** and must not be reported as a successful inventory audit until it has an authorized execution receipt.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → supporting source → authenticated source readback → regression source → regression executed → canonical owner composition → authenticated owner readback → TESTED → runtime → deployed → callable → executed → delivered → accepted`.

Current state at 2026-08-22 08:57 CT: supporting source **YES** · authenticated GitHub source readback **YES** · regressions **SOURCE / UNEXECUTED** · canonical owner integration **NO** · atomic candidate binding **NO** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.
