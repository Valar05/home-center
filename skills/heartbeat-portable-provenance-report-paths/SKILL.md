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
- literal backslash is escaped before evidence-marker insertion;
- Unicode `Cc`, `Cf`, `Cs`, `Zl`, and `Zp` characters are revealed as explicit `\\u{XXXX}` evidence units rather than emitted raw;
- in particular, U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR are legitimate source text but must not silently fracture operator-facing path evidence;
- over-budget repository-local display collapses from the **exact already-authorized repository-relative identity** to `<repo-path>...#<digest>` rather than exposing an arbitrary partial human-text/grapheme prefix;
- display projection never changes canonical path identity, Git authority, generated-index trust, runtime capability, deployment, or delivery state.

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
3. Cc/Cf/Cs/Zl/Zp evidence characters are not emitted raw;
4. literal marker-looking text cannot alias an actual projected character;
5. U+2028/U+2029 are explicitly revealed in in-budget path evidence;
6. over-budget repository paths collapse from exact identity without partial combining/ZWJ/layout-control text;
7. distinct repository-local over-budget identities retain distinct repository-local digests;
8. exact internal `SkillRecord` / `DiscoveryError` identities survive display serialization unchanged;
9. discovery-error pre-boundary collapse and final serialization remain compatible;
10. regression source is not TESTED evidence until an authorized runner actually executes it.

## Current capability state

- absolute/external projection policy: **YES / SOURCE_WIRED**
- repository-relative record projection: **YES / SOURCE_WIRED**
- Cc/Cf/Cs/Zl/Zp explicit path evidence: **YES / SOURCE_WIRED**
- over-budget whole-identity collapse: **YES / SOURCE_WIRED**
- discovery-error pre-boundary collapse: **YES / SOURCE_WIRED**
- current path-policy blob: **3e064b115c8759de7e0d76ae457f8461c9a3c810**
- current owner schema: **try-forever-skill-provenance.v6**
- authenticated owner blob at the reviewed 1000 source base: **60e85d95c484cee0ca5f637ac3d5763fd20d21cf**
- hostile path regression source: **YES / UNEXECUTED**
- layout-separator regression source: **YES / UNEXECUTED**
- TESTED: **NO**
- runtime UI/TalkBack: **NO**
- deployed/callable/executed/delivered/accepted: **NO**

## P0 / phone firewall

This skill owns no Phone Hands action, primary-phone command, queue/relay work, Home Center P0 recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or duplicate recovery architecture. Phone/P0 consumption and mutation remain zero.
