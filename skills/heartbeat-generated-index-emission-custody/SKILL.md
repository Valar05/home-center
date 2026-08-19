# Heartbeat Generated-Index Emission Custody

## Purpose

Keep a generated index's `VERIFIED_CURRENT` claim bound to both the repository state and the exact finite generated-index artifact that earned that verdict.

## Law

Repository custody and generated-index artifact custody are separate evidence domains.

A generated index may be inspected against a certified clean repository snapshot. A prior `VERIFIED_CURRENT` result may survive report emission only when:

1. the final repository-custody verdict is `STABLE_CLEAN`, and
2. the exact generated-index content identity observed during inspection is revalidated as `STABLE` for emission.

A stable repository HEAD/cleanliness verdict cannot certify continuity of a separately mutable external index file. If the index cannot be re-read, its whole-artifact SHA-256 is missing/non-canonical, or the emission digest differs from the inspected digest, positive currentness is withheld as `UNRESOLVED`.

## Named-path preservation before topology admission

The artifact gate can reject a symlink, junction, reparse point, or other redirecting spelling only if the existing provenance owner passes the caller's **named path** into that gate. Path normalization before topology admission must therefore be lexical only: make a relative CLI path absolute without dereferencing it.

`Path.resolve()` is not an acceptable pre-gate normalization for the generated-index argument. It follows a redirector and replaces the caller's named path with its target, which can make a later no-follow topology gate certify an ordinary target while never seeing the redirector that was actually supplied.

The source regression `tools/test_try_forever_generated_index_named_path_owner_boundary.py` pins that requirement. `patches/try-forever-generated-index-named-path-preservation.patch` is an exact base-blob-locked owner delta, but it remains **PROPOSED_NOT_APPLIED**. Patch existence is not owner wiring.

## Finite-artifact throat

**Bounded bytes are not bounded I/O.** A byte ceiling applied only after `open()`/`read()` begins does not stop a FIFO, named pipe, socket, device, redirector, reparse-backed object, or other special object from blocking or inheriting finite-file authority.

`tools/try_forever_generated_index_artifact_observation.py` therefore owns this source contract before authority-facing content is admitted:

1. no-follow pre-open observation must identify an ordinary regular file with usable inode/file-index identity;
2. redirectors and non-regular special files fail closed before authority-facing open/read;
3. **on Windows, regular-file shape is not enough:** the named path is checked through the Win32 file-attribute surface before `lstat`/open because Python may resolve non-name-surrogate reparse kinds even under no-follow stat semantics; any `FILE_ATTRIBUTE_REPARSE_POINT` fails closed, with no approved tag exceptions;
4. where the platform exposes them, `O_NONBLOCK` and `O_NOFOLLOW` are applied to the descriptor open;
5. the opened descriptor is independently `fstat`-verified as a regular non-reparse object and must match the pre-open device/inode/size/mtime observation;
6. complete content must reach EOF inside the caller's existing byte budget before exact SHA-256/text is returned;
7. the opened descriptor is revalidated after the complete read; device/inode/size/mtime drift or reparse metadata rejects the observation rather than returning mixed or stale authority-facing evidence;
8. on Windows the named path is checked again for the raw reparse attribute after EOF, then re-observed and required to identify the same stable descriptor observation; persistent replacement/reparse topology therefore fails closed;
9. max+1 rejects without returning prefix digest authority;
10. UTF-8 decoding is strict.

Python exposes `st_file_attributes` / `st_reparse_tag` on Windows stat results, while Win32 `GetFileAttributesW` is the named-path reparse-bit check. The source uses the direct named-path check specifically because Python documents that non-name-surrogate reparse kinds may be resolved by the operating system even for no-follow stat calls. This is evidence admission, not permission to follow or classify any reparse tag.

These checks close special-file/FIFO admission, persistent Windows named-path reparse admission, and common pre-open replacement / post-open persistent replacement / in-read mutation wounds. They still do **not** prove a universal atomic filesystem snapshot, eliminate swap-and-restore or identity reuse that evades all observations, impose a universal wall-clock deadline on ordinary storage, or certify runtime delivery. Those are separate claims.

Already-negative `STALE`/`UNRESOLVED` diagnostics remain diagnostic and are never promoted.

## Hostile fixtures

- generated-index CLI path spelling remains intact until topology admission; a symlink must not be erased by pre-gate `Path.resolve()`;
- exact-max ordinary artifact reaches EOF and earns a whole-artifact digest;
- max+1 rejects without prefix digest authority;
- invalid UTF-8 cannot become semantic index text;
- a FIFO/special file is rejected before authority-facing `os.open`;
- a simulated Windows named path carrying `FILE_ATTRIBUTE_REPARSE_POINT` is rejected before `Path.lstat` or authority-facing `os.open`;
- a regular-shaped stat/fstat observation carrying Windows reparse metadata is rejected;
- a symlink cannot inherit its target's regular-file authority;
- replacement between no-follow admission and descriptor open rejects before authority is returned;
- descriptor identity/size/mtime drift observed after the complete read rejects the observation;
- persistent named-path replacement after descriptor open rejects at the post-read path gate;
- external content A → content B yields `CHANGED` artifact custody even while repository custody can remain stable;
- identical complete ordinary content can yield `STABLE` artifact custody.

## Current capability truth

- pure artifact-custody + emission policy source: **IMPLEMENTED_SOURCE**
- bounded exact artifact-observation primitive: **IMPLEMENTED_SOURCE**
- finite regular-artifact topology gate: **IMPLEMENTED_SOURCE**
- direct Windows named-path reparse admission gate: **IMPLEMENTED_SOURCE**
- Windows stat/fstat reparse metadata gate: **IMPLEMENTED_SOURCE**
- pre-open path → opened-descriptor identity gate: **IMPLEMENTED_SOURCE**
- post-read descriptor stability gate: **IMPLEMENTED_SOURCE**
- post-read named-path stability gate: **IMPLEMENTED_SOURCE**
- named-path-preservation regression source: **REGRESSION_SOURCE / UNEXECUTED**
- named-path-preservation owner patch: **PROPOSED_NOT_APPLIED**
- existing provenance owner preserves caller named path for the future artifact gate: **NO**
- hostile regression source including special-file/resource/UTF-8/reparse/replacement/drift/external-mutation cases: **REGRESSION_SOURCE / UNEXECUTED**
- existing provenance owner consumption of artifact/emission custody: **NO**
- prior report-boundary patch: **REJECTED_UNSAFE / DO NOT APPLY** until a replacement composes coherent late repository observation, exact generated-index artifact custody, and this finite-artifact throat
- universal wall-clock I/O deadline / atomic artifact binding: **NO**
- tested: **NO**
- runtime UI / TalkBack / deployment / callability / execution / delivery / acceptance: **NO**

## Ownership

Compose only into `tools/try_forever_skill_provenance_probe.py`. Do not create a second provenance probe, serializer daemon, scheduler, recovery controller, Phone Hands lane, or P0 coordinator.

## P0 firewall

This skill is repository-evidence policy only. It does not consume or mutate the primary-phone surface, Phone Hands, recovery queues/relays, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.
