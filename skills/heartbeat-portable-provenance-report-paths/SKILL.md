# Heartbeat Portable Provenance Report Paths

## Purpose
Durable provenance reports must not leak host-local filesystem topology merely because the probe executed on a particular machine.

## Contract
- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Filesystem paths used for I/O and authority remain exact internal values. **Display projection is never authorization.**
- Repository-root display projects to `.`.
- Repository-local report paths project to bounded repo-relative POSIX paths.
- External report paths project to the constant marker `<external-path>`. Do not preserve a deterministic hash of the absolute host path: a digest can become a dictionary oracle over usernames, home directories, drive roots, mount points, or temporary-directory layouts.
- Long repository-relative report paths are hard-bounded with a deterministic suffix because that text is already within the allowed repository-relative evidence domain.
- The display budget has a declared semantic minimum; a caller may not shrink it until `<external-path>` or the bounded-suffix contract becomes amputated nonsense.
- Display projection must never become repository identity, generated-index trust, filesystem authority, or runtime capability.

## Evidence discipline
Keep internal filesystem identity, display projection, provenance authority, source implementation, tests, runtime, deployment, delivery, and acceptance separate.

Current state:
- pure path-projection policy: **YES / SOURCE**
- hostile regression source: **YES / SOURCE / UNEXECUTED**
- first deterministic external-path fingerprint design: **REJECTED DURING SOURCE REVIEW**
- first tiny-budget marker-amputation behavior: **REJECTED DURING SOURCE REVIEW**
- existing provenance owner consumes the policy: **NO**
- owner report schema changed: **NO**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, serializer daemon, path registry, overlay controller, Phone Hands lane, or P0 owner may be created for this rule. Compose the existing provenance owner if/when owner wiring is authorized and reviewed. Phone/P0 surfaces are outside this skill.
