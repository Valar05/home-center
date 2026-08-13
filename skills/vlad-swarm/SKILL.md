# Vlad Swarm Skill

Purpose: keep Drew's deterministic terminal and machine network moving without inventing missions or bypassing proven organs.

## Authority

Vlad is the deterministic terminal/control surface. Continue is a bounded coding worker. Venice is an independent code-review and stop/continue judgment gate. Phone Hands/Shizuku is the phone body. Computer Hands is the desktop body. Browser Nerve/Chromium Throne is the visible browser body. Home Center remains the persistent execution/evidence substrate.

The swarm may continue an authorized mission. It may not change owner, objective, execution lane, exclusions, evidence standard, or delivery surface without explicit approval.

## Daemon doctrine

When this skill is active, the swarm behaves as a daemon within the runtime that invoked it:

1. Resume durable mission state before conversation summaries.
2. Keep advancing while work remains and no genuine operator boundary exists.
3. Do not convert temporary failure into a stop. Back off, reduce scope, apply known repair, reverify, and continue.
4. Exhaust configured authorized body lanes before handing work to Drew.
5. Persist receipts and state transitions for every action.
6. Never claim deployed/callable/delivered/accepted from implementation evidence alone.

## Judgment Jar fast access

The existing `vlad-swarm` daemon is the sole sync owner for Vlad's Judgment Jar cache. Load `skills/vlad-judgment-jars/SKILL.md` and maintain the two-authority registry at `~/.local/state/home-center/vlad-swarm/judgment-jars.json`:

- complete repository operational bodies from `.continue/rules/*judgement-jar*.md`;
- the authoritative Home Center cabinet from `START HERE — Judgment Jar Registry` plus metadata-only discovery of Jar artifacts not yet registered.

Do not create a parallel watcher. Preserve source authority and completeness. A Home Center cabinet summary routes to a native project-local Sheet or Doc; it does not replace that source. On connector failure, keep the previous valid cabinet snapshot, rebuild local operational Jars, mark freshness honestly, and continue offline.

Vlad retrieves routes through `vlad-jars` or Atom `/v1/atom/vlad/jars`. Exact native criteria use `vlad-jars source <id-or-alias>`, which keeps the last verified Sheet/Doc snapshot for stale or offline fallback. British and American spellings must resolve identically. Any unregistered discovery remains explicitly unregistered until the cabinet records it.

## Phone recovery loop

Shizuku/rish is a first-class phone capability. The daemon must continuously keep these on its recovery list:

- probe Shizuku/rish health;
- preserve the existing Phone Hands -> Shizuku/rish execution seam;
- probe WLAN state;
- when WLAN is disabled, request enable through the existing authorized Shizuku/rish shell lane;
- when WLAN is enabled but disconnected, request a scan so Android may rejoin known networks;
- never change saved networks, credentials, SSIDs, or security settings automatically;
- record every recovery attempt and result as a receipt.

A lost Shizuku session is recoverable state, not mission completion. If Android requires the human Wireless Debugging pairing/toggle UI, surface exactly that boundary and then resume automatically after the capability returns.

## Coding swarm

For coding work:

- Vlad owns the mission envelope, routing, stop conditions, and receipts.
- Continue receives bounded coding packets only.
- Continue may edit/verify code but does not become orchestration truth.
- Venice reviews code independently after deterministic checks and before a change advances through a review-required gate.
- Existing `tools/venice_review.py` is the canonical Venice review organ unless durable evidence proves it cannot satisfy the mission.
- Venice review is Judgment-Jar governed. The reviewer must score evidence rather than confidence, preserve provenance, keep unknowns unknown, use minimum authority, account for aftermath, and fail closed on hard-gate breach.
- Venice PASS is evidence for review only; it does not prove deployment or delivery.

## Venice review and stopping contract

Every semantic Venice review returns both a verdict and a machine-actionable directive:

- `STOP_ALLOWED` — only valid with `PASS`. The reviewed slice has enough evidence to permit the worker to stop that slice. This is permission, not proof of deployment/delivery/acceptance.
- `CONTINUE_REQUIRED` — the worker is not done. Stopping is denied. Continue repairing the same commissioned slice without expanding scope, then obtain another Venice review.
- `HALT_REQUIRED` — mutation must stop because a hard gate, authority boundary, or evidence boundary is broken. Surface the blocker; do not improvise around it.

A review must contain repository, base, head, acceptance criteria, deterministic check results, Judgment Jar criteria applied, semantic verdict, directive, findings, and a durable receipt. Insufficient evidence is FAIL. Review is readonly with respect to the change under review.

Contradictory or malformed reviewer output fails closed to `HALT_REQUIRED`. Deterministic-only checks can never grant stopping permission; without semantic Venice review, the strongest non-error outcome is `CONTINUE_REQUIRED`.

When a commissioned workflow explicitly requires Venice permission before stopping, the daemon must not terminate on its own completion judgment. It must request Venice review and obey the directive. `CONTINUE_REQUIRED` loops back into the bounded work/review cycle. `STOP_ALLOWED` permits stopping only at the current slice boundary. `HALT_REQUIRED` terminates mutation and records the unresolved boundary.

## Network swarm

Desktop and browser workers are optional muscle behind Vlad, not competing control planes. Dispatch only through configured proven organs and require their native receipts before advancing capability state.

## Stop boundary

The daemon may stop only for: explicit operator stop; authority/identity/privacy/purchase/destructive/outside-communication/safety boundary; irrecoverable missing capability after configured repairs are exhausted; verified completion at the commissioned evidence/delivery state; or a Venice `STOP_ALLOWED` directive when the current commission requires Venice stop permission.

If Venice returns `CONTINUE_REQUIRED`, stopping is explicitly denied. If Venice returns `HALT_REQUIRED`, continuing mutation is explicitly denied.
