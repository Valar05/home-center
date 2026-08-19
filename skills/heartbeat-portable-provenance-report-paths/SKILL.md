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
- **Over-budget repository-local display does not expose a partial human-text prefix.** It collapses to `<repo-path>...#<digest>` where the digest is computed only from already-authorized repository-relative identity. This avoids splitting combining, modifier, or ZWJ graphemes while preserving a bounded repository-local disambiguator.
- External report paths project to the constant marker `<external-path>`; do not preserve a host-path hash oracle.
- Display projection must never become repository identity, generated-index trust, filesystem authority, or runtime capability.

## Existing-owner schema v4

Schema `try-forever-skill-provenance.v4` currently uses `project_report_path(...)` for:

- `repositoryRoot`, which emits `.` plus `repositoryRootScope=REPOSITORY`; and
- `generatedIndex.path`, which emits a bounded repository-relative path or the constant `<external-path>` plus an explicit scope.

The exact generated-index `Path` is retained separately inside the process for initial and late artifact custody I/O. The display path never feeds those gates.

## Repository-relative record projection source

`tools/try_forever_provenance_report_path.py` provides `project_repository_relative_report_path(...)` for path-bearing report records whose repository-relative authority was established earlier. The helper reuses the same collision-safe invisible-character/backslash projection as root/index report projection without reconstructing a host path or touching the filesystem.

In-budget paths remain readable. Over-budget paths deliberately collapse to a constant repository marker plus digest rather than truncating arbitrary Unicode source text. This pays the already-established accessibility scar that human-facing projections must not manufacture a partial user-perceived grapheme merely to preserve a pretty prefix.

Hostile regression source pins:

- ordinary repository-relative skill paths;
- newline, bidi-control, and ZWJ visibility while in budget;
- literal marker versus actual invisible-character collision resistance;
- over-budget combining and emoji-ZWJ cases collapsing without partial grapheme output;
- distinct over-budget repository-local identities retaining distinct repository-local digests; and
- fail-closed rejection of absolute, parent-traversing, or empty misuse of the repository-relative channel.

These are **SOURCE / REGRESSION_SOURCE** claims only. No authorized runner result has promoted them to TESTED.

## Owner integration is regression-locked, not applied

`tools/test_try_forever_provenance_owner_v5_record_paths.py` is a commit-bound **RED owner-integration regression source**. It requires the future existing-owner v5 report to:

- serialize `SkillRecord.path` through the repository-relative display channel;
- serialize `DiscoveryError.path` and `related_path` through that same channel;
- preserve literal-marker versus actual invisible/control character distinction; and
- leave the owner's exact internal record identities unchanged by display serialization.

The test is intentionally red while the owner remains schema v4. Its existence is not TESTED evidence and is not owner implementation.

`patches/try-forever-provenance-record-path-projection.patch` remains base-locked to owner blob `f6f1bafc6b9e99030ad29b408d74cd088f910b82` and is explicitly **PROPOSED_NOT_APPLIED__REGRESSION_LOCKED**. It proposes only:

- importing the existing repository-relative display helper;
- projecting serialized `SkillRecord.path` and `DiscoveryError.path` / `related_path` without rewriting internal records;
- bumping the report contract from v4 to explicit schema v5;
- correcting report-path authority prose to match every serialized path family; and
- migrating the historical owner-emission regression's schema assertion in the same surgery, so applying v5 cannot knowingly create a deterministic v4 assertion failure.

The helper changed after that patch was authored, but the patch imports/calls the helper rather than embedding its old truncation implementation; the proposed owner surgery therefore naturally inherits the current helper behavior if eventually applied against its still-matching base owner blob.

## Current owner wound: record families remain unwired

Authenticated owner readback at the bound source head still shows:

- `skills[*].path` serialized from `asdict(record)`; and
- `discoveryErrors[*].path` / `related_path` serialized from `asdict(error)`.

Those values therefore do **not yet consume** the repository-relative display helper. The report authority prose says operator-facing paths are portable, so this is a real report-contract mismatch, not a cosmetic improvement.

## Mutation-lane truth

The deployed non-phone Computer Hands worker currently reports offline while `lane-try-forever-provenance-owner` is present among its active lanes. An active lane is not an exact request identity. No duplicate owner request may be created merely from lane presence; owner execution remains unresolved until an exact existing request/worker receipt or authenticated owner mutation readback establishes it.

The Home Center GitHub-admin lane can replace a complete file under a blob lock, but it is not a patch interpreter. The large sole provenance owner must not be reconstructed from partial context merely to turn a safe unapplied patch into an implementation claim.

## Evidence discipline

Keep internal filesystem identity, report display projection, provenance authority, supporting source, owner patch source, queued/executed mutation, tests, runtime, deployment, delivery, and acceptance separate.

## Current state

- pure absolute/external path-projection policy: **YES / SOURCE**
- repository-relative record projection policy: **YES / SOURCE**
- collision-safe control/format/surrogate evidence projection: **YES / SOURCE**
- over-budget repository-local partial-grapheme avoidance: **YES / SOURCE**
- path-policy source blob: **fd79305fa9ea6413dadbd15f9eb2ccc8b27e1a69**
- hostile path regression source: **YES / REGRESSION_SOURCE / UNEXECUTED**
- path-regression blob: **45112f8e3533b2999b214314d80af8d7fcd6b5cb**
- owner v5 record-path integration regression source: **YES / RED_SOURCE / UNEXECUTED**
- owner-v5-regression blob: **f813b2cb170ded33038ec86d0cf7d18e7b1ad52e**
- exact owner patch source: **YES / PROPOSED_NOT_APPLIED__REGRESSION_LOCKED**
- owner patch blob: **99e6a5bf2eac42b338274104ed7b9a38e1c9ccec**
- existing owner projects repository root: **YES / SOURCE_WIRED**
- existing owner projects generated-index display path: **YES / SOURCE_WIRED**
- existing owner projects skill record paths through repository-relative policy: **NO**
- existing owner projects discovery-error paths through repository-relative policy: **NO**
- overall portable report-path owner wiring: **PARTIAL**
- owner schema: **try-forever-skill-provenance.v4**
- owner blob at authenticated bound readback: **f6f1bafc6b9e99030ad29b408d74cd088f910b82**
- Computer Hands provenance owner execution: **UNRESOLVED / WORKER_OFFLINE / ACTIVE_LANE_NOT_REQUEST_ID / NO_DUPLICATE_REQUEST**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall

No second provenance probe, serializer daemon, path registry, overlay controller, Phone Hands lane, or P0 owner may be created. Compose the existing provenance owner only. Phone/P0 consumption and mutation remain zero.
