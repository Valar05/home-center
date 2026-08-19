# Heartbeat Portable Provenance Report Paths

## Purpose

Durable provenance reports must not leak host-local filesystem topology merely because the probe executed on a particular machine, and repository-local evidence must not speak invisible/control path text as if it were ordinary visible text.

## Contract

- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Filesystem paths used for I/O and authority remain exact internal values. **Display projection is never authorization.**
- Repository-root display projects to `.`.
- Repository-local report paths project to bounded repo-relative POSIX paths.
- Repository-relative display projection reveals Unicode `Cc`, `Cf`, and `Cs` code points as explicit `\u{XXXX}` evidence units rather than emitting them raw.
- Literal backslash is escaped before semantic markers, so literal source text cannot collide with the projection of an actual invisible character.
- Hard bounding may truncate only between complete projection units.
- External report paths project to the constant marker `<external-path>`; do not preserve a host-path hash oracle.
- Display projection must never become repository identity, generated-index trust, filesystem authority, or runtime capability.

## Existing-owner schema v4

Schema `try-forever-skill-provenance.v4` now uses `project_report_path(...)` for:

- `repositoryRoot`, which emits `.` plus `repositoryRootScope=REPOSITORY`; and
- `generatedIndex.path`, which emits a bounded repository-relative path or the constant `<external-path>` plus an explicit scope.

The exact generated-index `Path` is retained separately inside the process for initial and late artifact custody I/O. The display path never feeds those gates.

## Regnet wound: portable-path wiring is not yet complete

Code-first review after the owner v4 surgery found that two path-bearing families still bypass the explicit report projection:

- `skills[*].path` is serialized from the existing repository-relative `SkillRecord.path`; and
- `discoveryErrors[*].path` / `related_path` are serialized from their existing bounded relative diagnostic strings.

Those values are already repository-relative and `json.dumps` escapes control code points in transport, but they have **not** been routed through the collision-safe `Cc`/`Cf`/`Cs` display projection. Therefore the owner must not be described as having complete portable-report-path wiring yet. This is the next source seam, not permission to rewrite authority identity or create a second serializer.

Any repair must preserve exact internal record identity separately from operator-facing display projection and must use the existing provenance owner/schema-v4 report assembly.

## Evidence discipline

Keep internal filesystem identity, display projection, provenance authority, source implementation, tests, runtime, deployment, delivery, and acceptance separate.

## Current state

- pure path-projection policy: **YES / SOURCE**
- collision-safe control/format/surrogate evidence projection: **YES / SOURCE**
- policy source blob: **94c473490f1745b11ac11040e1f25a6196bbd8e4**
- existing owner projects repository root: **YES / SOURCE_WIRED**
- existing owner projects generated-index display path: **YES / SOURCE_WIRED**
- existing owner projects skill record paths through this policy: **NO**
- existing owner projects discovery-error paths through this policy: **NO**
- overall portable report-path owner wiring: **PARTIAL**
- owner schema: **try-forever-skill-provenance.v4**
- owner commit/blob: **90054f3f0761b0993d635527d60ad43f68c20a8d / f6f1bafc6b9e99030ad29b408d74cd088f910b82**
- owner-v4 regression source covering root/generated-index path behavior: **YES / REGRESSION_SOURCE / UNEXECUTED**
- regression commit/blob: **19dd1621093eaefc830b13938404a2192c979584 / ebea66749d5038be4d303827681df38adfe1d554**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall

No second provenance probe, serializer daemon, path registry, overlay controller, Phone Hands lane, or P0 owner may be created. Compose the existing provenance owner only. Phone/P0 consumption and mutation remain zero.
