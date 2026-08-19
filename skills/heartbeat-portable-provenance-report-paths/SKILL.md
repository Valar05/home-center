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

## Existing-owner schema v4

Schema `try-forever-skill-provenance.v4` currently uses `project_report_path(...)` for:

- `repositoryRoot`, which emits `.` plus `repositoryRootScope=REPOSITORY`; and
- `generatedIndex.path`, which emits a bounded repository-relative path or the constant `<external-path>` plus an explicit scope.

The exact generated-index `Path` is retained separately inside the process for initial and late artifact custody I/O. The display path never feeds those gates.

## Repository-relative record projection source

`tools/try_forever_provenance_report_path.py` provides `project_repository_relative_report_path(...)` for path-bearing report records whose repository-relative authority was established earlier. The helper reuses the same collision-safe invisible-character/backslash projection as root/index report projection without reconstructing a host path or touching the filesystem.

In-budget paths remain readable. Over-budget paths deliberately collapse to a constant repository marker plus digest rather than truncating arbitrary Unicode source text.

Hostile regression source pins ordinary repository-relative skill paths, newline/bidi/ZWJ visibility, literal-marker collision resistance, over-budget combining and emoji-ZWJ collapse, repository-local digest distinction, and fail-closed absolute/parent-traversal/empty misuse.

These are **SOURCE / REGRESSION_SOURCE** claims only. No authorized runner result has promoted them to TESTED.

## Owner integration regression

`tools/test_try_forever_provenance_owner_v5_record_paths.py` is a commit-bound **RED owner-integration regression source**. It requires the future existing-owner v5 report to:

- serialize `SkillRecord.path` through the repository-relative display channel;
- serialize `DiscoveryError.path` and `related_path` through that same channel;
- preserve literal-marker versus actual invisible/control character distinction; and
- leave the owner's exact internal record identities unchanged by display serialization.

The test is intentionally red while the owner remains schema v4. Its existence is not TESTED evidence and is not owner implementation.

## Combined owner surgery

`patches/try-forever-provenance-owner-preio-v5.patch` is now the canonical exact prepared surgery for the record-path owner wound. It is base-locked to current owner blob `f6f1bafc6b9e99030ad29b408d74cd088f910b82` and historical emission fixture blob `ebea66749d5038be4d303827681df38adfe1d554`, with status **PROPOSED_NOT_APPLIED__REGRESSION_LOCKED**.

The surgery proposes only existing-owner composition:

- import the existing repository-relative display helper;
- project serialized `SkillRecord.path` and `DiscoveryError.path` / `related_path` without rewriting internal records;
- bump the report contract from v4 to explicit schema v5;
- correct report-path authority prose to match every serialized path family; and
- migrate the historical owner-emission regression's schema assertion in the same surgery.

The same blob-locked surgery also composes the independent pre-I/O candidate-file identity gate. Combining those non-overlapping hunks under one base prevents two future patch applications from racing over the same large sole owner file. It does **not** merge their evidence claims and does not make either implemented.

The older `patches/try-forever-provenance-record-path-projection.patch` remains historical supporting provenance; the combined patch supersedes it as the preferred future owner surgery while both are unapplied.

## Current owner wound: record families remain unwired

Authenticated owner readback still shows:

- `skills[*].path` serialized from `asdict(record)`; and
- `discoveryErrors[*].path` / `related_path` serialized from `asdict(error)`.

Those values therefore do **not yet consume** the repository-relative display helper. The report authority prose says operator-facing paths are portable, so this is a real report-contract mismatch, not a cosmetic improvement.

## Mutation-lane truth

The retired Command Center Codex worker surface is not a current Home Center execution capability. Do not fabricate a worker receipt or queue a phone-shaped substitute. The audited GitHub-admin lane can replace complete files under blob lock but is not a patch interpreter; until the exact owner surgery is actually applied and read back, owner record-path wiring remains NO.

## Evidence discipline

Keep internal filesystem identity, report display projection, provenance authority, supporting source, owner patch source, queued/executed mutation, tests, runtime, deployment, delivery, and acceptance separate.

## Current state

- pure absolute/external path-projection policy: **YES / SOURCE**;
- repository-relative record projection policy: **YES / SOURCE**;
- collision-safe control/format/surrogate evidence projection: **YES / SOURCE**;
- over-budget repository-local partial-grapheme avoidance: **YES / SOURCE**;
- path-policy source blob: **fd79305fa9ea6413dadbd15f9eb2ccc8b27e1a69**;
- hostile path regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**;
- owner v5 record-path integration regression source: **YES / RED_SOURCE / UNEXECUTED**;
- combined exact owner surgery: **YES / PROPOSED_NOT_APPLIED__REGRESSION_LOCKED**;
- combined owner surgery blob: **8e71807cc5917d100c745b190e3b8a2e6e7a8c8f**;
- existing owner projects repository root: **YES / SOURCE_WIRED**;
- existing owner projects generated-index display path: **YES / SOURCE_WIRED**;
- existing owner projects skill record paths through repository-relative policy: **NO**;
- existing owner projects discovery-error paths through repository-relative policy: **NO**;
- overall portable report-path owner wiring: **PARTIAL**;
- owner schema: **try-forever-skill-provenance.v4**;
- owner blob at authenticated bound readback: **f6f1bafc6b9e99030ad29b408d74cd088f910b82**;
- tested: **NO**;
- runtime/deployed/callable/executed/delivered/accepted: **NO**.

## Ownership / firewall

No second provenance probe, serializer daemon, path registry, overlay controller, Phone Hands lane, or P0 owner may be created. Compose the existing provenance owner only. Phone/P0 consumption and mutation remain zero.
