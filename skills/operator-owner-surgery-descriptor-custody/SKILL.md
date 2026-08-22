# Operator Owner Surgery Descriptor Custody

## Purpose
Strengthen TRY FOREVER owner-surgery **root and candidate custody** on runtimes that expose the required POSIX descriptor primitives, without rewriting the canonical portable v10 owner or pretending descriptor custody is universal filesystem atomicity.

This skill owns one source/evidence distinction. It does **not** own a second custody probe, patch executor, overlay controller, scheduler, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core laws
`HELD DIRECTORY DESCRIPTOR + DESCRIPTOR-RELATIVE NAME OPERATIONS != UNIVERSAL FILESYSTEM ATOMICITY`.

`ENUMERATED NAME + CAPTURED NO-FOLLOW OBJECT IDENTITY != ATOMIC CANDIDATE-NAME BINDING`.

A root opened once with `O_DIRECTORY|O_NOFOLLOW` and then used through descriptor-relative scan/open/stat cannot be silently redirected by replacing the **root pathname after the descriptor is held**. That is materially stronger than a pre/post pathname bracket.

A candidate whose no-follow identity is captured during held-root enumeration can also reject **persistent replacement between enumeration and the later authority-facing stat/open/read**. It still does not prove:
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
5. captures each matching candidate's no-follow device/inode/size/mtime identity during that held-root enumeration and retains its file mode;
6. rejects traversal syntax before descriptor-relative file operations;
7. no-follow stats the candidate relative to the held directory and, when an enumerated candidate is supplied, requires the pre-open identity to equal the enumerated identity;
8. opens that same basename relative to the held directory with `O_NOFOLLOW` and `O_NONBLOCK` where available;
9. requires pre-stat/open-fd identity agreement;
10. reads complete content inside a hard max+1 byte throat;
11. requires post-read descriptor stability;
12. requires the still-held directory name to identify the same regular-file object after the read;
13. decodes strict UTF-8 and returns exact SHA-256 evidence.

`candidate_names(...)` remains as a compatibility projection; `candidate_entries(...)` is the stronger identity-bearing source surface.

The root descriptor is the authority anchor for the operation. The source does not re-resolve the root pathname for candidate work.

### Review scar: scan position is state
The first supporting-source draft passed the authority descriptor itself directly to `os.scandir`. Review rejected that as too casual because directory stream position is state; a later scan must not depend on where an earlier scan left the descriptor. The corrected source opens `.` relative to the held authority root for every scan. This preserves root custody while giving each bounded inventory pass a fresh directory position.

### Review scar: candidate name is not candidate object
The 08:57 source returned only candidate names. That meant a persistent replacement after enumeration but before the first authority-facing stat could be observed as though the replacement were the object that had been enumerated. The current supporting source carries enumeration-time no-follow identity forward and rejects persistent identity drift before open/read.

This narrows the wound; it does **not** close swap-and-restore or identity-reuse atomicity.

## Regression source
`tools/test_try_forever_posix_directory_handle_custody.py` — **UNEXECUTED**.

It now includes:
- held root survives named root replacement;
- candidate enumeration remains on the held original directory after root-path replacement;
- repeated candidate scans return the same deterministic inventory rather than inheriting old stream position;
- enumerated candidate identity survives into the bounded read;
- persistent candidate replacement after enumeration is rejected before authority-facing read;
- descriptor-relative symlink artifact rejection;
- max+1 byte rejection with no prefix authority;
- traversal-name rejection.

`tools/test_try_forever_directory_handle_binding_capability.py` is also **UNEXECUTED** and pins descriptor-relative no-follow stat as a required primitive.

## Canonical owner relationship
Canonical owner-surgery custody remains `tools/try_forever_owner_surgery_custody_probe.py` v10. It is already **SOURCE_WIRED** for portable persistent-drift root revalidation.

Descriptor-bound custody is currently:
- supporting implementation **YES**;
- authenticated GitHub source readback **YES**;
- enumeration→read candidate identity handoff **YES / SUPPORTING SOURCE**;
- regression source **YES / UNEXECUTED**;
- canonical v10 owner consumption **NO**;
- atomic root binding **NO**;
- atomic candidate binding **NO**;
- TESTED **NO**;
- runtime/deployed/delivered/accepted **NO**.

Do not replace v10 merely because this POSIX source exists. Any future owner composition must preserve the portable fallback and must re-enter exact owner custody/review before mutation.

## Current inventory companion
`tools/test_try_forever_owner_surgery_current_inventory.py` independently targets whether the actual current `patches/` inventory is fully admissible under v10's stricter exact textual state grammar. It is **REGRESSION SOURCE / UNEXECUTED** and must not be reported as a successful inventory audit until it has an authorized execution receipt.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → supporting source → authenticated source readback → regression source → regression executed → canonical owner composition → authenticated owner readback → TESTED → runtime → deployed → callable → executed → delivered → accepted`.

Current state at 2026-08-22 10:02 CT: supporting source **YES** · authenticated GitHub source readback **YES** · enumeration→read candidate identity **YES / SUPPORTING SOURCE** · regressions **SOURCE / UNEXECUTED** · canonical owner integration **NO** · atomic root binding **NO** · atomic candidate binding **NO** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.
