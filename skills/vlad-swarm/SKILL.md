# Vlad Swarm Skill

Purpose: keep Drew's deterministic terminal and machine network moving without inventing missions or bypassing proven organs.

## Authority

Vlad is the deterministic continuity, routing, scarcity, restart, and receipt organ. Continue is a bounded coding worker. Venice is an independent review and stop/continue judgment gate. Phone Hands/Shizuku is the phone body. Computer Hands is the desktop body. Browser Nerve/Chromium Throne is the visible browser body. Home Center remains the persistent execution/evidence substrate.

Exactly three fast-access surfaces govern this slice: **Judgment Jars, Home Center, and Vlad**. Command Center does not exist. Historical identifiers containing `command_center` are compatibility debt only and never authorize a fourth surface.

The swarm may continue an authorized mission. It may not change owner, objective, execution lane, exclusions, evidence standard, or delivery surface without explicit approval.

## Daemon doctrine

When this skill is active, the swarm behaves as a daemon within the runtime that invoked it:

1. Resume durable mission state before conversation summaries.
2. Keep advancing while work remains and no genuine operator boundary exists.
3. Do not convert temporary failure into a stop. Back off, reduce scope, apply known repair, reverify, and continue.
4. Exhaust configured authorized body lanes before handing work to Drew.
5. Persist receipts and state transitions for every action.
6. Never claim deployed/callable/delivered/accepted from implementation evidence alone.

## Judgment Jar fast access and receipts

The existing `vlad-swarm` daemon is the sole sync owner for Vlad's Judgment Jar registry, native-source cache, and typed usage-receipt outbox. Load `skills/vlad-judgment-jars/SKILL.md` and maintain the registry at `~/.local/state/home-center/vlad-swarm/judgment-jars.json`:

- complete repository operational bodies from `.continue/rules/*judgement-jar*.md`;
- the authoritative Home Center cabinet from `START HERE — Judgment Jar Registry`;
- metadata-only discovery of Home Center Jar artifacts not yet registered.

Do not create a parallel watcher. Preserve source authority and completeness. A cabinet summary routes to a native project-local Sheet or Doc; it does not replace that source. On connector failure, keep the previous valid cabinet snapshot, rebuild local operational Jars, mark freshness honestly, and continue offline.

Vlad retrieves routes through `vlad-jars` or Atom `/v1/atom/vlad/jars`. Exact native criteria use `vlad-jars source <id-or-alias>`. British and American spellings resolve identically. Any unregistered discovery remains explicitly unregistered until the cabinet records it.

Every Jar context load creates a `context_packet` receipt. Every result created with Jar context creates a second typed result receipt identifying the output kind. Use `python3 tools/jar_receipt.py record` for explicit results. The configured kinds include answers, analyses, plans, decisions, routing actions, code changes, test results, review verdicts, artifacts, handoffs, memory updates, execution results, blockers, no-change results, and mixed outputs.

On each existing daemon heartbeat, `vlad-jars sync`:

1. refreshes/rebuilds the Jar registry as already configured;
2. imports Atom Jar context receipts;
3. imports durable Venice plan/completion review outputs as `review_verdict` receipts;
4. flushes the oldest pending receipt to `Judgment Jar Usage Receipts — Vlad and Home Center`;
5. verifies the exact receipt ID and deduplication fingerprint by Home Center readback.

Receipt states are not interchangeable:

- `CAPTURED`: durable local outbox record;
- `PENDING_HOME_CENTER`: captured but not verified in Home Center;
- `DELIVERED`: exact receipt ID/fingerprint survived Home Center append and readback.

Malformed imports go to durable quarantine. Transient delivery failure preserves the receipt, exact error, attempt count, and bounded backoff. Never overwrite or discard an older pending receipt. Never call local Atom/JSON persistence Home Center delivery.

## Phone recovery loop

Shizuku/rish is a first-class phone capability. The daemon must continuously keep these on its recovery list:

- probe Shizuku/rish health;
- preserve the existing Phone Hands -> Shizuku/rish execution seam;
- probe WLAN state;
- when WLAN is disabled, request enable through the existing authorized Shizuku/rish shell lane;
- when WLAN is enabled but disconnected, request a scan so Android may rejoin known networks;
- never change saved networks, credentials, SSIDs, or security settings automatically;
- record every recovery attempt and result as a receipt.

A lost Shizuku session is recoverable state, not mission completion. If Android requires the human Wireless Debugging pairing/toggle UI, surface exactly that boundary and resume automatically after the capability returns.

## Coding swarm

For coding work:

- Vlad owns the mission envelope, routing, stop conditions, and receipts.
- Continue receives bounded coding packets only.
- Continue may edit/verify code but does not become orchestration truth.
- Rene QA reviews code/configuration quality and evidence before Venice when that gate is material.
- Venice reviews mission fidelity independently after deterministic checks and Rene QA where required.
- Existing Venice plan/completion receipts are imported into the typed Jar receipt outbox.
- Venice PASS is review evidence only; it does not prove deployment or delivery.

## Venice review and stopping contract

Every semantic Venice review returns both a verdict and machine-actionable directive:

- `STOP_ALLOWED` — only valid with `PASS`; permission to stop the reviewed slice, not proof of deployment/delivery/acceptance.
- `CONTINUE_REQUIRED` — stopping is denied; continue repairing the same slice and review again.
- `HALT_REQUIRED` — mutation stops at the exact hard-gate, authority, or evidence boundary.

A review must contain repository, base, head, acceptance criteria, deterministic checks, Judgment Jar criteria, semantic verdict, directive, findings, and a durable receipt. The typed Jar importer must also classify the review output as `review_verdict`. Insufficient evidence is FAIL. Review is readonly with respect to the change under review.

Contradictory or malformed reviewer output fails closed. Deterministic-only checks cannot grant stopping permission. A missing required typed created-output receipt also denies completion of the Jar-governed slice.

## Network swarm

Desktop and browser workers are optional muscle behind Vlad, not competing control planes. Dispatch only through configured proven organs and require native receipts before advancing capability state.

## Stop boundary

The daemon may stop only for: explicit operator stop; authority/identity/privacy/purchase/destructive/outside-communication/safety boundary; irrecoverable missing capability after configured repairs are exhausted; verified completion at the commissioned evidence/delivery state; or Venice `STOP_ALLOWED` when required.

`CONTINUE_REQUIRED` denies stopping. `HALT_REQUIRED` denies continued mutation. Missing required Jar output receipts deny completion.
