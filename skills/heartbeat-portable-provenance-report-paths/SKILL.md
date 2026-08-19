# Heartbeat Portable Provenance Report Paths

## Purpose
Durable provenance reports must not leak host-local filesystem topology merely because the probe executed on a particular machine, and repository-local evidence must not speak invisible/control path text as if it were ordinary visible text.

## Contract
- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Filesystem paths used for I/O and authority remain exact internal values. **Display projection is never authorization.**
- Repository-root display projects to `.`.
- Repository-local report paths project to bounded repo-relative POSIX paths.
- Repository-relative display projection reveals Unicode `Cc`, `Cf`, and `Cs` code points as explicit `\u{XXXX}` evidence units rather than emitting them raw into operator/TalkBack text.
- Literal backslash is escaped before semantic markers, so source text that literally spells `\u{202E}` cannot collide with the projection of an actual U+202E path character.
- Hard bounding may truncate only between complete projection units; never return half an evidence marker.
- This **reveals** legitimate invisible Unicode; it does not reject or normalize the exact internal path. Authority and I/O keep the original `Path`.
- External report paths project to the constant marker `<external-path>`. Do not preserve a deterministic hash of the absolute host path: a digest can become a dictionary oracle over usernames, home directories, drive roots, mount points, or temporary-directory layouts.
- Long repository-relative report paths are hard-bounded with a deterministic suffix because that source text is already within the allowed repository-relative evidence domain.
- The display budget has a declared semantic minimum; a caller may not shrink it until `<external-path>` or the bounded-suffix contract becomes amputated nonsense.
- Display projection must never become repository identity, generated-index trust, filesystem authority, or runtime capability.
- Owner integration changes durable report semantics and therefore requires an explicit schema revision; the preserved owner composition target is newer than `try-forever-skill-provenance.v3` rather than silently changing v3.

## Evidence discipline
Keep internal filesystem identity, display projection, provenance authority, source implementation, tests, runtime, deployment, delivery, and acceptance separate.

Current state:
- pure path-projection policy: **YES / SOURCE**
- collision-safe control/format/surrogate evidence projection: **YES / SOURCE**
- policy source blob: **94c473490f1745b11ac11040e1f25a6196bbd8e4**
- hostile policy regression source: **YES / SOURCE / UNEXECUTED**
- regression source blob after code-first fixture correction: **0f5caeb7adbf94509e779ad4315bd31bd5f1b81d**
- existing provenance owner consumes the policy: **NO**
- authenticated current owner blob before owner composition: **afe2b29eb7f4daf2ebf79c483c2e7d3abac9ed6a**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, serializer daemon, path registry, overlay controller, Phone Hands lane, or P0 owner may be created for this rule. Compose the existing provenance owner only. Phone/P0 surfaces are outside this skill.
