# Operator Owner Surgery Descriptor Custody

## Purpose
Strengthen TRY FOREVER owner-surgery **root and candidate custody** on runtimes that expose the required POSIX descriptor primitives, without rewriting the canonical portable v10 owner or pretending descriptor custody is universal filesystem atomicity.

This skill owns one source/evidence distinction. It does **not** own a second custody probe, patch executor, overlay controller, scheduler, recovery daemon, phone lane, P0 coordinator, or physical acceptance chain.

## Core laws
`HELD DIRECTORY DESCRIPTOR + DESCRIPTOR-RELATIVE NAME OPERATIONS != UNIVERSAL FILESYSTEM ATOMICITY`.

`ENUMERATED NAME + CAPTURED NO-FOLLOW OBJECT IDENTITY != ATOMIC CANDIDATE-NAME BINDING`.

`STRONGER CUSTODY BACKEND != PERMISSION TO DROP EXISTING OWNER EVIDENCE FIELDS`.

`STRICT UTF-8 ADMISSION FAILURE != RAW DECODER EXCEPTION ESCAPING THE CUSTODY DOMAIN`.

`AUTHORITY-FACING FILESYSTEM I/O FAILURE != RAW OS ERROR ESCAPING THE CUSTODY DOMAIN`.

`ROOT DESCRIPTOR SETUP I/O FAILURE != HALF-ESTABLISHED ROOT CUSTODY`.

`INVENTORY I/O FAILURE != PARTIAL CANDIDATE AUTHORITY`.

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
1. opens the named root once with `O_DIRECTORY|O_NOFOLLOW`, mapping root-open failure to bounded `PosixDirectoryHandleCustodyUnavailable` instead of leaking raw `OSError`;
2. verifies the held descriptor is an ordinary directory with usable inode identity, mapping root-descriptor `fstat` failure to the same bounded unavailable domain and preserving the original setup wound if cleanup close itself fails;
3. opens a **fresh `.` directory handle relative to the held root for each inventory scan**, so repeated scans do not inherit directory-stream position from an earlier enumeration while remaining anchored to the same held root;
4. maps fresh scan-handle open failure to bounded `DescriptorArtifactCustodyError` with no inventory returned;
5. enumerates candidate names through that fresh descriptor-relative handle with independent entry/candidate budgets and maps enumeration I/O failure to bounded custody rejection;
6. captures each matching candidate's no-follow device/inode/size/mtime identity during that held-root enumeration and retains its file mode; candidate stat I/O failure is a typed inventory rejection;
7. retains **total directory entries observed, including unrelated entries**, alongside the candidate count so a future canonical-owner composition can preserve v10's `artifactDirectoryEntriesObserved` and `artifactCandidatesObserved` evidence rather than quietly weakening the receipt;
8. rejects traversal syntax before descriptor-relative file operations;
9. no-follow stats the candidate relative to the held directory and, when an enumerated candidate is supplied, requires the pre-open identity to equal the enumerated identity;
10. opens that same basename relative to the held directory with `O_NOFOLLOW` and `O_NONBLOCK` where available;
11. requires pre-stat/open-fd identity agreement;
12. reads complete content inside a hard max+1 byte throat;
13. requires post-read descriptor stability;
14. requires the still-held directory name to identify the same regular-file object after the read;
15. contains authority-facing pre-stat/open/read/post-stat OS failures inside bounded `DescriptorArtifactCustodyError` boundaries rather than leaking raw `OSError` subclasses;
16. decodes strict UTF-8 and converts malformed text into bounded `DescriptorArtifactCustodyError` rather than leaking `UnicodeDecodeError` outside the custody domain;
17. returns exact SHA-256 evidence only with the admitted observation.

`candidate_inventory(...)` is the full evidence-bearing source surface. `candidate_entries(...)` and `candidate_names(...)` remain compatibility projections.

The root descriptor is the authority anchor for the operation. The source does not re-resolve the root pathname for candidate work.

### Review scar: scan position is state
The first supporting-source draft passed the authority descriptor itself directly to `os.scandir`. Review rejected that as too casual because directory stream position is state; a later scan must not depend on where an earlier scan left the descriptor. The corrected source opens `.` relative to the held authority root for every scan. This preserves root custody while giving each bounded inventory pass a fresh directory position.

### Review scar: candidate name is not candidate object
The 08:57 source returned only candidate names. That meant a persistent replacement after enumeration but before the first authority-facing stat could be observed as though the replacement were the object that had been enumerated. The current supporting source carries enumeration-time no-follow identity forward and rejects persistent identity drift before open/read.

This narrows the wound; it does **not** close swap-and-restore or identity-reuse atomicity.

### Review scar: stronger backend must preserve evidence metrics
A first owner-composition review found the descriptor helper had candidate identities but not the total directory-entry count exposed by canonical v10. The helper now returns a `DescriptorCandidateInventory` with both `entries_observed` and candidate identities/count. Descriptor owner integration remains NO until the canonical owner can consume this without changing its published evidence semantics or portable fallback.

### Review scar: budget overflow returns no partial inventory
The descriptor inventory source already enforced independent directory-entry and matching-candidate budgets, but those two throats were not pinned by hostile fixtures. The regression source now covers unrelated-entry max+1 and candidate max+1. Both require an exception rather than a partial `DescriptorCandidateInventory`, so a stronger backend cannot quietly preserve the first N objects as authority after its declared budget is exceeded.

### Review scar: strict text failure is still custody failure
The descriptor backend originally performed `raw.decode("utf-8", errors="strict")` directly inside observation construction. A malformed text artifact therefore escaped as raw `UnicodeDecodeError` even though every other authority rejection on this source surface uses `DescriptorArtifactCustodyError`. The source now keeps strict UTF-8 admission but converts decoder failure into a bounded custody-domain error with no observation returned. This changes error containment, not the bytes, SHA, identity gates, resource budget, canonical-owner state, or atomicity claims.

### Review scar: disappearance and descriptor failure are still custody wounds
Code-first review after the UTF-8 repair found a separate failure channel: pre-open `stat`, descriptor-relative `open`, descriptor reads/fstats, and the post-read named-path recheck could still leak raw `OSError` subclasses. The source now maps those authority-facing I/O failures to bounded custody-domain errors. A candidate disappearing after enumeration therefore fails as a typed custody wound rather than an unstructured `FileNotFoundError`. This does not make the operation more atomic; it makes failure evidence deterministic and composable.

### Review scar: inventory I/O is authority-facing too
The 12:57 review deliberately left `candidate_inventory(...)` with raw `os.open(".")`, `os.scandir(...)`, and `DirEntry.stat(...)` failure channels. Those happen **before** any inventory can earn authority and therefore belong inside the custody domain just as much as later artifact I/O. The current supporting source maps all three channels to bounded `DescriptorArtifactCustodyError` and returns no partial inventory. Caller-supplied `is_candidate(...)` exceptions are deliberately not relabeled as filesystem custody failures.

### Review scar: root setup failure cannot masquerade as a usable held root
The same review found root construction still leaked raw `os.open`/`os.fstat` failures before `root_identity` existed. The current supporting source converts those setup failures to `PosixDirectoryHandleCustodyUnavailable`, tears down any partially opened descriptor without masking the original setup wound, and leaves no half-initialized custody object as authority.

### Next exact wound: scan cleanup can still be a separate failure channel
`candidate_inventory(...)` still closes the fresh scan fd in `finally` with raw `os.close(scan_fd)`. A close failure can therefore become a raw cleanup exception and, in the worst combined case, can mask an earlier typed inventory rejection. This is **not** being silently folded into the completed open/scandir/stat slice. It remains a distinct future source target; no TESTED or owner-integration claim depends on it being solved now.

## Regression source
`tools/test_try_forever_posix_directory_handle_custody.py` — **UNEXECUTED**.

It includes:
- held root survives named root replacement;
- candidate enumeration remains on the held original directory after root-path replacement;
- repeated candidate scans return the same deterministic inventory rather than inheriting old stream position;
- inventory evidence counts unrelated directory entries separately from matching candidates;
- unrelated directory-entry max+1 rejects the entire inventory rather than returning partial authority;
- matching-candidate max+1 rejects the entire inventory rather than returning partial authority;
- enumerated candidate identity survives into the bounded read;
- persistent candidate replacement after enumeration is rejected before authority-facing read;
- disappearing candidate after enumeration produces typed custody rejection rather than raw OS error;
- descriptor-relative symlink artifact rejection;
- max+1 byte rejection with no prefix authority;
- malformed UTF-8 produces typed custody rejection with no admitted observation authority;
- traversal-name rejection.

`tools/test_try_forever_posix_directory_handle_io_failures.py` — **UNEXECUTED** — adds focused source fixtures for:
- missing-root open failure → typed root custody unavailable;
- root descriptor `fstat` failure → typed root custody unavailable;
- fresh scan-handle open failure → typed inventory rejection;
- `scandir` failure → typed inventory rejection;
- candidate `DirEntry.stat` failure → typed inventory rejection;
- caller `is_candidate` failure remains a caller/programmer failure and is not laundered into an I/O custody wound.

`tools/test_try_forever_directory_handle_binding_capability.py` is also **UNEXECUTED** and pins descriptor-relative no-follow stat as a required primitive.

## Canonical owner relationship
Canonical owner-surgery custody remains `tools/try_forever_owner_surgery_custody_probe.py` v10. It is already **SOURCE_WIRED** for portable persistent-drift root revalidation, exact base-owner identity admission, and exact authenticated current-owner identity admission.

Descriptor-bound custody is currently:
- supporting implementation **YES**;
- authenticated GitHub source readback **YES**;
- bounded inventory metrics compatible with v10 evidence fields **YES / SUPPORTING SOURCE**;
- independent inventory-budget hostile fixtures **YES / SOURCE / UNEXECUTED**;
- enumeration→read candidate identity handoff **YES / SUPPORTING SOURCE**;
- typed root setup I/O failure containment **YES / SUPPORTING SOURCE**;
- typed inventory open/enumeration/stat I/O failure containment **YES / SUPPORTING SOURCE**;
- typed artifact filesystem-I/O failure containment **YES / SUPPORTING SOURCE**;
- strict UTF-8 typed rejection **YES / SUPPORTING SOURCE**;
- focused root/inventory I/O regression source **YES / UNEXECUTED**;
- canonical v10 owner consumption **NO**;
- atomic root binding **NO**;
- atomic candidate binding **NO**;
- TESTED **NO**;
- runtime/deployed/delivered/accepted **NO**.

Do not replace v10 merely because this POSIX source exists. Any future owner composition must preserve the portable fallback, `artifactDirectoryEntriesObserved`, `artifactCandidatesObserved`, bounded error semantics, exact base-owner identity admission, exact current-owner identity admission, and exact owner custody/review before mutation.

## Current inventory companion
`tools/test_try_forever_owner_surgery_current_inventory.py` independently targets whether the actual current `patches/` inventory is fully admissible under v10's stricter exact textual state grammar and exact lowercase base-owner identity. It is **REGRESSION SOURCE / UNEXECUTED** and must not be reported as a successful inventory audit until it has an authorized execution receipt.

## P0 / phone firewall
This skill consumes no Phone Hands ticket, primary-phone command, recovery queue, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or P0 coordination. P0 receipts remain read-only evidence.

## Capability membrane
`requested → supporting source → authenticated source readback → regression source → regression executed → canonical owner composition → authenticated owner readback → TESTED → runtime → deployed → callable → executed → delivered → accepted`.

Current state at 2026-08-22 14:02 CT: supporting source **YES** · authenticated GitHub source readback **YES** · bounded inventory evidence metrics **YES / SUPPORTING SOURCE** · inventory-budget hostile fixtures **YES / SOURCE / UNEXECUTED** · enumeration→read candidate identity **YES / SUPPORTING SOURCE** · typed root setup I/O containment **YES / SUPPORTING SOURCE** · typed inventory I/O containment **YES / SUPPORTING SOURCE** · typed artifact filesystem-I/O containment **YES / SUPPORTING SOURCE** · strict UTF-8 typed rejection **YES / SUPPORTING SOURCE** · focused root/inventory I/O regression source **YES / UNEXECUTED** · scan-close cleanup containment **NO / NEXT WOUND** · canonical owner integration **NO** · atomic root binding **NO** · atomic candidate binding **NO** · TESTED/runtime/deployed/phone/delivered/accepted **NO**.
