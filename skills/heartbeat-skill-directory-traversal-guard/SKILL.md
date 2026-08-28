# Heartbeat Skill Directory Traversal Guard

## Purpose
A child directory observed as ordinary during parent enumeration can be replaced before the existing provenance probe later traverses its queued path. Repository-skill authority may still fail closed later, but repository-owned traversal scope must not be silently widened by that race.

## Contract
- Keep `tools/try_forever_skill_provenance_probe.py` as the sole discovery/provenance owner.
- Child-directory topology is a separate gate from candidate-file topology.
- Record a no-follow directory identity when a child is admitted and revalidate it immediately before traversal.
- A redirector, non-directory shape, unavailable identity, or changed device/inode rejects that queued child before traversal.
- Do not claim this portable observation pair is atomic. Swap-and-restore, identity reuse, or replacement after revalidation but before `scandir` remain open boundaries without a stronger handle-binding strategy.
- Never convert a failed child-directory gate into partial repository-skill authority.

## Evidence discipline
Current state:
- supporting guard source: **YES / SOURCE**
- hostile regression source: **YES / SOURCE / UNEXECUTED**
- existing provenance owner consumes guard: **YES / SOURCE_WIRED**
- owner convergence commit: `d05261c74998f1f818d2a3b30efa229b695de100`
- authenticated owner blob: `afe2b29eb7f4daf2ebf79c483c2e7d3abac9ed6a`
- atomic cross-platform child-directory binding: **NO**
- tested/runtime/deployed/callable/delivered/accepted: **NO**

## Accessibility / operator semantics
Expose the distinction as `queued child stable`, `redirector/replacement blocked`, and `atomicity still open`. Do not use color alone, autoplay, or decorative blink as evidence.

## Ownership / firewall
No second provenance probe, traversal daemon, registry, renderer, scheduler, Phone Hands lane, or P0 coordinator. Phone/P0 surfaces are outside this skill.