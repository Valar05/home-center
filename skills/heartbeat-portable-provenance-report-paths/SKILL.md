# Heartbeat Portable Provenance Report Paths

## Purpose

Durable provenance reports must not leak host-local filesystem topology, and repository-local path evidence must not silently emit layout/control text as if it were ordinary visible prose.

## Owner and authority law

The sole provenance owner remains `tools/try_forever_skill_provenance_probe.py`.

Filesystem `Path` values and exact repository-relative record identities remain the authority/I/O inputs. **Display projection is never authorization.** Do not create a second path serializer, provenance probe, path registry, renderer, phone lane, or P0 coordinator.

## Display contract

`tools/try_forever_provenance_report_path.py` owns the display-only projection.

- repository root → `.` with `scope=REPOSITORY`;
- repository-local paths → bounded repository-relative POSIX display text;
- external paths → constant `<external-path>` with `scope=EXTERNAL`; never preserve a host-path hash oracle;
- already-authorized record identities use `project_repository_relative_report_path(...)`, which performs no filesystem lookup and rejects absolute/parent-traversal misuse;
- serialized path evidence that may be reviewed on a different host OS uses `project_serialized_report_path(...)`: current-host absolute paths retain normal repository-containment projection, while foreign-platform drive, root, UNC, drive-relative, and rooted syntax is externalized before it can enter the repository-relative display channel;
- **reviewer-host path syntax is never repository authority**: `Path.is_absolute()` from only the current OS is insufficient for serialized evidence;
- drive-qualified-but-not-absolute Windows text such as `C:private\\receipt.json` is still host-context evidence and therefore external at the serialized boundary;
- literal backslash is escaped before evidence-marker insertion;
- Unicode `Cc`, `Cf`, `Cs`, `Zl`, and `Zp` characters are revealed as explicit `\\u{XXXX}` evidence units rather than emitted raw;
- in particular, U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR are legitimate source text but must not silently fracture operator-facing path evidence;
- over-budget repository-local display collapses from the **exact already-authorized repository-relative identity** to `<repo-path>...#<digest>` rather than exposing an arbitrary partial human-text/grapheme prefix;
- display projection never changes canonical path identity, Git authority, generated-index trust, runtime capability, deployment, or delivery state.

## Cross-host serialized-evidence scar

Serialized machine evidence can outlive or leave the operating system that produced it. A Windows drive/UNC/rooted/drive-relative path string is not interpreted consistently by POSIX `Path`, while POSIX-rooted text is foreign syntax to Windows. Treating the reviewer host's path parser as the only scope detector can leak foreign host topology through a repository-relative display channel.

The source-level repair lives in `project_serialized_report_path(...)`. The descriptor-shadow operator projector now **explicitly consumes that existing helper**; authenticated owner readback after commit `cad8d728efa14d8a20b229d1902896e9267d0e02` is blob `10b88a9583274d498524b3082e252886be4335af`. Applied provenance remains at `docs/try-forever/descriptor-shadow-cross-host-path-display.patch` with state **APPLIED_SOURCE**. This is source wiring only; regression execution, TESTED, runtime UI/TalkBack, deployment, delivery, and acceptance remain separate.

Do not solve this by banning Windows-looking characters from the already-authorized repository-relative API. A repository-relative identity such as `patches/C:\\literal-name.patch` or even `C:literal-name.patch` after explicit relative authority is already established is still repository evidence. The cross-host detector belongs only at the serialized-path boundary where absolute-vs-relative scope has not already been established.

## Existing-owner report contract

The current sole owner emits `try-forever-skill-provenance.v6`.

Its serialized path families already consume the display channels:

- `repositoryRoot` + `repositoryRootScope`;
- `generatedIndex.path` + `pathScope`;
- `skills[*].path` through the repository-relative projector;
- `discoveryErrors[*].path` and non-empty `related_path` through that same projector.

Schema v6 was introduced by the independent CLI-evidence auditability work. Do not regress this skill back to the historical v5 label merely because record-path wiring originally landed during v5.

## Discovery-error pre-boundary scar

`bounded_error_path(...)` is already source-wired in the owner. In-budget repository-relative diagnostics remain exact until final serialization; over-budget diagnostics collapse immediately to the whole-identity repository marker + digest. Never restore raw-prefix truncation: it can split combining/emoji-ZWJ text before the collision-safe final projector sees the original identity.

Historical patch files remain provenance artifacts; their existence does not override current owner/source readback.

## Layout-separator cross-pollination

`heartbeat-layout-separator-evidence` extends this same evidence law across provenance paths and selected heartbeat detail:

- reject neither U+2028 nor U+2029 merely for being layout semantics;
- reveal them in explicit operator-facing evidence;
- keep canonical source identity unchanged;
- keep literal marker text collision-safe;
- keep routine speech changes separate from explicit evidence changes.

## Regression doctrine

Pin all of these independently:

1. repository root is `.` and external paths are the constant non-fingerprinting marker;
2. repository-relative record paths cannot launder absolute/parent-traversal host topology;
3. serialized foreign-platform absolute, rooted, drive-qualified, or UNC paths cannot become repository display merely because the reviewer host's `Path` parser calls them relative;
4. repository-relative identities containing Windows-looking characters remain repository evidence after their relative scope is already established;
5. Cc/Cf/Cs/Zl/Zp evidence characters are not emitted raw;
6. literal marker-looking text cannot alias an actual projected character;
7. U+2028/U+2029 are explicitly revealed in in-budget path evidence;
8. over-budget repository paths collapse from exact identity without partial combining/ZWJ/layout-control text;
9. distinct repository-local over-budget identities retain distinct repository-local digests;
10. exact internal `SkillRecord` / `DiscoveryError` identities survive display serialization unchanged;
11. discovery-error pre-boundary collapse and final serialization remain compatible;
12. descriptor-shadow operator projection must consume `project_serialized_report_path(...)`; the owner-boundary source now covers Windows drive, UNC, drive-relative, rooted, POSIX absolute, and already-authorized repository-relative Windows-looking identities;
13. regression source is not TESTED evidence until an authorized runner actually executes it.

## Current capability state

- absolute/external projection policy: **YES / SOURCE_WIRED**
- repository-relative record projection: **YES / SOURCE_WIRED**
- cross-host serialized path projection policy: **YES / SOURCE**
- descriptor-shadow serialized-path owner consumption: **YES / SOURCE_WIRED**
- Cc/Cf/Cs/Zl/Zp explicit path evidence: **YES / SOURCE_WIRED**
- over-budget whole-identity collapse: **YES / SOURCE_WIRED**
- discovery-error pre-boundary collapse: **YES / SOURCE_WIRED**
- current path-policy blob after corrective cross-host hardening: **b30add2b26511921817a97d42972a92dd24545ab**
- current owner schema: **try-forever-skill-provenance.v6**
- descriptor-shadow owner base blob before applied surgery: **4cc65f162f600e70a9771d7cf3edac94e45f5344**
- descriptor-shadow owner applied commit: **cad8d728efa14d8a20b229d1902896e9267d0e02**
- descriptor-shadow owner result blob: **10b88a9583274d498524b3082e252886be4335af**
- hostile path regression source: **YES / UNEXECUTED**
- foreign-rooting regression source: **YES / UNEXECUTED**
- descriptor-shadow cross-host owner-boundary regression source: **YES / UNEXECUTED**
- layout-separator regression source: **YES / UNEXECUTED**
- TESTED: **NO**
- runtime UI/TalkBack: **NO**
- deployed/callable/executed/delivered/accepted: **NO**

## P0 / phone firewall

This skill owns no Phone Hands action, primary-phone command, queue/relay work, Home Center P0 recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or duplicate recovery architecture. Phone/P0 consumption and mutation remain zero.
