# Heartbeat Generated-Index Emission Custody

## Purpose

Keep a generated index's `VERIFIED_CURRENT` claim bound to both the repository state and the exact finite generated-index artifact that earned that verdict.

## Law

Repository custody and generated-index artifact custody are separate evidence domains.

A generated index may be inspected against a certified clean repository snapshot. A prior `VERIFIED_CURRENT` result may survive report emission only when:

1. the final repository-custody verdict is `STABLE_CLEAN`, and
2. the exact generated-index content identity observed during inspection is revalidated as `STABLE` for emission.

A stable repository HEAD/cleanliness verdict cannot certify continuity of a separately mutable external index file. If the index cannot be re-read, its whole-artifact SHA-256 is missing/non-canonical, or the emission digest differs from the inspected digest, positive currentness is withheld as `UNRESOLVED`.

The prior generated-index status itself is a typed evidence value, not free-form prose. Only string values `VERIFIED_CURRENT`, `STALE`, and `UNRESOLVED` are declared prior statuses. An unknown, case-drifted, or non-string runtime shape fails closed to `UNRESOLVED` at emission rather than being copied into durable operator evidence or raising through the authority-facing path. A green late repository/artifact gate cannot rescue an undeclared prior status.

## Named-path preservation and finite inspection admission

The artifact gate can reject a symlink, junction, reparse point, or other redirecting spelling only if the existing provenance owner passes the caller's **named path** into that gate. Path normalization before topology admission is therefore lexical only: make a relative CLI path absolute without dereferencing it.

`Path.resolve()` is not acceptable before topology admission. It follows a redirector and replaces the caller's named path with its target, which can make a later no-follow topology gate certify an ordinary target while never seeing the redirector that was actually supplied.

The existing owner now composes both halves of this admission boundary in source:

- `resolve_repo_path()` preserves the named spelling with lexical `abspath` normalization; and
- `inspect_generated_index()` delegates its authority-facing content read to `observe_generated_index_artifact(...)` before JSON semantics.

Owner commit `e4de3002b3e338345eb9ab9f03c790689d8e3dc0`, owner blob `d24157e8c56538cf88615176e3fd3c5a4b7faed6`. The regression `tools/test_try_forever_generated_index_named_path_owner_boundary.py` now pins both lexical preservation and symlink rejection before semantic metadata can earn authority. This still does **not** bind the inspection digest into late report-emission revalidation.

## Finite-artifact throat

**Bounded bytes are not bounded I/O.** A byte ceiling applied only after `open()`/`read()` begins does not stop a FIFO, named pipe, socket, device, redirector, reparse-backed object, or other special object from blocking or inheriting finite-file authority.

`tools/try_forever_generated_index_artifact_observation.py` owns this source contract before authority-facing content is admitted:

1. no-follow pre-open observation must identify an ordinary regular file with usable inode/file-index identity;
2. redirectors and non-regular special files fail closed before authority-facing open/read;
3. on Windows, the named path is checked through the Win32 file-attribute surface before `lstat`/open; any `FILE_ATTRIBUTE_REPARSE_POINT` fails closed;
4. where exposed, `O_NONBLOCK` and `O_NOFOLLOW` are applied to descriptor open;
5. the opened descriptor is independently `fstat`-verified and must match the pre-open device/inode/size/mtime observation;
6. complete content must reach EOF inside the caller's existing byte budget before exact SHA-256/text is returned;
7. descriptor identity/size/mtime is revalidated after the complete read;
8. on Windows the named path is checked again for the raw reparse attribute after EOF, then required to identify the same stable descriptor observation;
9. max+1 rejects without returning prefix digest authority;
10. UTF-8 decoding is strict.

These checks close special-file/FIFO admission, persistent Windows named-path reparse admission, and common pre-open replacement / post-open persistent replacement / in-read mutation wounds. They still do **not** prove a universal atomic filesystem snapshot, eliminate swap-and-restore or identity reuse that evades all observations, impose a universal wall-clock deadline on ordinary storage, or certify runtime delivery.

## Hostile fixtures

- generated-index CLI path spelling remains intact until topology admission;
- the existing owner rejects a supplied symlink before JSON semantics can see its target;
- exact-max ordinary artifact reaches EOF and earns a whole-artifact digest;
- max+1 rejects without prefix digest authority;
- invalid UTF-8 cannot become semantic index text;
- FIFO/special-file and Windows reparse topology reject before authority-facing semantic trust;
- replacement/drift between path, descriptor, read, and final path observation rejects;
- external content A → content B yields `CHANGED` artifact custody even while repository custody can remain stable;
- unknown/case-drifted/non-string prior status becomes `UNRESOLVED` rather than a fourth ad-hoc state.

## Current capability truth

- pure artifact-custody + emission policy source: **IMPLEMENTED_SOURCE**
- bounded exact artifact-observation primitive: **IMPLEMENTED_SOURCE**
- finite regular-artifact topology gate: **IMPLEMENTED_SOURCE**
- named-path-preservation owner patch: **APPLIED_SOURCE**
- existing owner preserves caller named path: **YES / SOURCE_WIRED**
- existing owner consumes finite-artifact admission for initial generated-index inspection: **YES / SOURCE_WIRED**
- owner source commit/blob for finite inspection: **e4de3002b3e338345eb9ab9f03c790689d8e3dc0 / d24157e8c56538cf88615176e3fd3c5a4b7faed6**
- named-path + owner inspection regression source: **REGRESSION_SOURCE / UNEXECUTED**
- existing owner binds inspection artifact SHA into late emission custody: **NO**
- existing owner consumes late repository/artifact emission composition: **NO**
- prior report-boundary patch: **REJECTED_UNSAFE / DO NOT APPLY**
- universal wall-clock I/O deadline / atomic artifact binding: **NO**
- tested: **NO**
- runtime UI / TalkBack / deployment / callability / execution / delivery / acceptance: **NO**

## Ownership

Compose only into `tools/try_forever_skill_provenance_probe.py`. Do not create a second provenance probe, serializer daemon, scheduler, recovery controller, Phone Hands lane, or P0 coordinator.

## P0 firewall

This skill is repository-evidence policy only. It does not consume or mutate the primary-phone surface, Phone Hands, recovery queues/relays, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance.
