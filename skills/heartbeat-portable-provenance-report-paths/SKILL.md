# Heartbeat Portable Provenance Report Paths

## Purpose

Durable provenance reports must not leak host-local filesystem topology merely because the probe executed on a particular machine, and repository-local evidence must not speak invisible/control path text as if it were ordinary visible text.

## Contract

- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Filesystem paths and repository-relative identities used for I/O and authority remain exact internal values. **Display projection is never authorization.**
- Repository-root display projects to `.`.
- Repository-local report paths project to bounded repo-relative POSIX text while they fit the display budget.
- `project_repository_relative_report_path(...)` is for identities already established as repository-relative by the owner. It performs no filesystem lookup, rejects absolute/parent-traversal misuse, and therefore cannot grant repository authority.
- Repository-relative display projection reveals Unicode `Cc`, `Cf`, and `Cs` code points as explicit `\u{XXXX}` evidence units rather than emitting them raw.
- Literal backslash is escaped before semantic markers, so literal source text cannot collide with the projection of an actual invisible character.
- **Over-budget repository-local display does not expose a partial human-text prefix.** It collapses to `<repo-path>...#<digest>` where the digest is computed only from already-authorized repository-relative identity.
- External report paths project to the constant marker `<external-path>`; do not preserve a host-path hash oracle.
- Display projection must never become repository identity, generated-index trust, filesystem authority, or runtime capability.

## Existing-owner schema v5

Schema `try-forever-skill-provenance.v5` now uses display projection for every serialized path family:

- `repositoryRoot` projects to `.` plus `repositoryRootScope=REPOSITORY`;
- `generatedIndex.path` uses bounded repository-relative or constant `<external-path>` projection plus explicit scope;
- `skills[*].path` uses `project_repository_relative_report_path(...)`; and
- `discoveryErrors[*].path` and non-empty `related_path` use that same repository-relative display channel.

The exact generated-index `Path`, `SkillRecord.path`, and `DiscoveryError` path identities remain internal authority/evidence inputs. The display text is created only at report serialization.

## Repository-relative projection source

`tools/try_forever_provenance_report_path.py` provides `project_repository_relative_report_path(...)`. In-budget paths remain readable and collision-safe. Over-budget paths deliberately collapse to a constant repository marker plus digest rather than truncating arbitrary Unicode source text.

Hostile regression source pins ordinary repository-relative skill paths, newline/bidi/ZWJ visibility, literal-marker collision resistance, over-budget combining and emoji-ZWJ collapse, repository-local digest distinction, and fail-closed absolute/parent-traversal/empty misuse.

## Owner integration source

`tools/test_try_forever_provenance_owner_v5_record_paths.py` pins existing-owner v5 serialization. It requires:

- `SkillRecord.path` through the repository-relative display channel;
- `DiscoveryError.path` and `related_path` through that same channel;
- literal-marker versus actual invisible/control character distinction; and
- exact internal record identities unchanged by display serialization.

The owner source now contains the matching integration. The regression remains **UNEXECUTED** until an authorized runner produces evidence.

## Applied surgery provenance

`patches/try-forever-provenance-owner-preio-v5.patch` records the applied owner surgery. It was base-locked to owner blob `f6f1bafc6b9e99030ad29b408d74cd088f910b82`; owner source landed at commit `bf91827aa74651e1500edd916a26ff9f6acac13e`, authenticated blob `e1d10fb4c917813bc89780486c79a5e2d2bc4bea`.

The historical owner emission fixture was migrated to schema v5 at commit `fc9a26d0f2670977f0b90dfc8734d0d6720a88f`, blob `492a66c6a2145b167c16fb05564b461d4391c012`.

The same source surgery also composes the independent pre-I/O candidate-file identity gate. Combining the non-overlapping hunks under one exact base prevented competing whole-file mutations; it does **not** merge the evidence claims.

The older `patches/try-forever-provenance-record-path-projection.patch` is historical proposal provenance only and is superseded by the applied combined surgery.

## Evidence discipline

Keep internal filesystem identity, report display projection, provenance authority, implemented source, tests, runtime, deployment, delivery, and acceptance separate.

## Current state

- pure absolute/external path-projection policy: **YES / SOURCE**;
- repository-relative record projection policy: **YES / SOURCE**;
- collision-safe control/format/surrogate evidence projection: **YES / SOURCE**;
- over-budget repository-local partial-grapheme avoidance: **YES / SOURCE**;
- path-policy source blob: **fd79305fa9ea6413dadbd15f9eb2ccc8b27e1a69**;
- hostile path regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**;
- owner v5 record-path integration regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**;
- existing owner projects repository root: **YES / SOURCE_WIRED**;
- existing owner projects generated-index display path: **YES / SOURCE_WIRED**;
- existing owner projects skill record paths through repository-relative policy: **YES / SOURCE_WIRED**;
- existing owner projects discovery-error paths through repository-relative policy: **YES / SOURCE_WIRED**;
- overall portable report-path owner wiring: **YES / SOURCE_WIRED**;
- owner schema: **try-forever-skill-provenance.v5**;
- authenticated owner blob: **e1d10fb4c917813bc89780486c79a5e2d2bc4bea**;
- applied surgery provenance blob: **580bdc724c02086a14aacddddc568608968dc293**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## Ownership / firewall

No second provenance probe, serializer daemon, path registry, overlay controller, Phone Hands lane, or P0 owner may be created. Phone/P0 consumption and mutation remain zero.
