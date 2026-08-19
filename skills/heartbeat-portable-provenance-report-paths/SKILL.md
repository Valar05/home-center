# Heartbeat Portable Provenance Report Paths

## Purpose

Durable provenance reports must not leak host-local filesystem topology merely because the probe executed on a particular machine, and repository-local evidence must not speak invisible/control path text as if it were ordinary visible text.

## Contract

- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Filesystem paths and repository-relative identities used for I/O and authority remain exact internal values. **Display projection is never authorization.**
- Repository-root display projects to `.`.
- Repository-local report paths project to bounded repo-relative POSIX text.
- `project_repository_relative_report_path(...)` is for identities already established as repository-relative by the owner. It performs no filesystem lookup, rejects absolute/parent-traversal misuse, and therefore cannot grant repository authority.
- Repository-relative display projection reveals Unicode `Cc`, `Cf`, and `Cs` code points as explicit `\u{XXXX}` evidence units rather than emitting them raw.
- Literal backslash is escaped before semantic markers, so literal source text cannot collide with the projection of an actual invisible character.
- Hard bounding may truncate only between complete projection units.
- External report paths project to the constant marker `<external-path>`; do not preserve a host-path hash oracle.
- Display projection must never become repository identity, generated-index trust, filesystem authority, or runtime capability.

## Existing-owner schema v4

Schema `try-forever-skill-provenance.v4` currently uses `project_report_path(...)` for:

- `repositoryRoot`, which emits `.` plus `repositoryRootScope=REPOSITORY`; and
- `generatedIndex.path`, which emits a bounded repository-relative path or the constant `<external-path>` plus an explicit scope.

The exact generated-index `Path` is retained separately inside the process for initial and late artifact custody I/O. The display path never feeds those gates.

## New supporting source: repository-relative record projection

`tools/try_forever_provenance_report_path.py` now also provides `project_repository_relative_report_path(...)` for path-bearing report records whose repository-relative authority was established earlier. The new helper reuses the exact same collision-safe invisible-character/backslash projection and bounded-fingerprint law as root/index report projection without reconstructing a host path or touching the filesystem.

Hostile regression source now pins:

- ordinary repository-relative skill paths;
- newline, bidi-control, and ZWJ visibility;
- literal marker versus actual invisible-character collision resistance;
- hard bounds that do not split `\u{XXXX}` projection units; and
- fail-closed rejection of absolute, parent-traversing, or empty misuse of the repository-relative channel.

These are **SOURCE / REGRESSION_SOURCE** claims only. No authorized runner result has promoted them to TESTED.

## Current owner wound: record families remain unwired

Code-first owner readback still shows:

- `skills[*].path` serialized from `asdict(record)`; and
- `discoveryErrors[*].path` / `related_path` serialized from `asdict(error)`.

Those values therefore do **not yet consume** the new repository-relative display helper. The report authority prose says operator-facing paths are portable, so this is a real report-contract mismatch, not a cosmetic improvement.

The safe owner surgery is narrow: keep exact `SkillRecord` / `DiscoveryError` values for internal authority and diagnostics, project only their serialized path fields, and use an explicit schema revision because report-path semantics change. Do not create a second serializer or reinterpret display text as authority.

## Evidence discipline

Keep internal filesystem identity, report display projection, provenance authority, source implementation, tests, runtime, deployment, delivery, and acceptance separate.

## Current state

- pure absolute/external path-projection policy: **YES / SOURCE**
- repository-relative record projection policy: **YES / SOURCE**
- collision-safe control/format/surrogate evidence projection: **YES / SOURCE**
- path-policy source blob: **5c3e25121d2cca52561b235084d37ae2cea074a3**
- hostile path regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**
- regression blob: **8acb40c6cdf78dd48c4ba5ccb76eebed39edc894**
- existing owner projects repository root: **YES / SOURCE_WIRED**
- existing owner projects generated-index display path: **YES / SOURCE_WIRED**
- existing owner projects skill record paths through repository-relative policy: **NO**
- existing owner projects discovery-error paths through repository-relative policy: **NO**
- overall portable report-path owner wiring: **PARTIAL**
- owner schema: **try-forever-skill-provenance.v4**
- owner blob at latest authenticated readback before this supporting-source slice: **f6f1bafc6b9e99030ad29b408d74cd088f910b82**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall

No second provenance probe, serializer daemon, path registry, overlay controller, Phone Hands lane, or P0 owner may be created. Compose the existing provenance owner only. Phone/P0 consumption and mutation remain zero.
