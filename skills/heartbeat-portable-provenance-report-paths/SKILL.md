# Heartbeat Portable Provenance Report Paths

## Purpose
Durable provenance reports must not leak host-local filesystem topology merely because the probe executed on a particular machine.

## Contract
- The existing owner remains `tools/try_forever_skill_provenance_probe.py`.
- Filesystem paths used for I/O and authority remain exact internal values. **Display projection is never authorization.**
- Repository-root display projects to `.`.
- Repository-local report paths project to bounded repo-relative POSIX paths.
- External report paths project to an opaque deterministic marker; usernames, home directories, drive roots, mount points, and temporary-directory layouts do not enter durable operator-facing JSON.
- Long report paths are hard-bounded with a deterministic suffix.
- An external-path fingerprint is diagnostic only. It must never become repository identity, generated-index trust, filesystem authority, or runtime capability.

## Evidence discipline
Keep internal filesystem identity, display projection, provenance authority, source implementation, tests, runtime, deployment, delivery, and acceptance separate.

Current state:
- pure path-projection policy: **YES / SOURCE**
- hostile regression source: **YES / SOURCE / UNEXECUTED**
- existing provenance owner consumes the policy: **NO**
- owner report schema changed: **NO**
- tested: **NO**
- runtime/deployed/callable/executed/delivered/accepted: **NO**

## Ownership / firewall
No second provenance probe, serializer daemon, path registry, overlay controller, Phone Hands lane, or P0 owner may be created for this rule. Compose the existing provenance owner if/when owner wiring is authorized and reviewed. Phone/P0 surfaces are outside this skill.
