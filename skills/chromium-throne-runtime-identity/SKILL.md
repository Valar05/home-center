---
name: chromium-throne-runtime-identity
description: Distinguish Chromium Throne from Browser Nerve, Computer Hands, Home Center, and the workstation itself when Drew asks about THECAULDRON, the ChatGPT swarm, browser status, social posting, or "check desktop again." Never infer Chromium Throne or THECAULDRON offline from another organ's stale heartbeat.
---

# Chromium Throne Runtime Identity

## Mission

Keep the desktop organs separate. Report the state of the organ Drew actually named or was already discussing. Do not collapse every browser-shaped thing into one imaginary "desktop browser worker."

This skill governs status checks, reorientation, incident repair, and capability claims involving Chromium Throne.

## Canonical organ map

### Chromium Throne

Chromium Throne is the dedicated Chrome/Edge profile, extension, and local relay on THECAULDRON. Its default relay origin is:

`http://127.0.0.1:9234/v1/throne`

Its proven core purpose is operating visible, authenticated ChatGPT worker tabs through the dedicated Chromium Throne profile. Throne-specific evidence includes:

- relay health or status from the Throne relay itself;
- extension or worker-tab heartbeats;
- Throne command, job, and completion events;
- the dedicated profile's process and persistence-task state;
- Throne event logs and same-day result receipts.

A generic Chrome process is not sufficient proof of Throne readiness. A repository implementation is not sufficient proof of deployment or liveness.

### Browser Nerve

Browser Nerve is a separate Home Center semantic-browser body, including registrations such as `windows-browser-nerve-01`.

Browser Nerve status proves only Browser Nerve status. Its worker heartbeat, sessions, queue, or failure state cannot establish Chromium Throne status.

### Computer Hands

Computer Hands is a separate whole-workstation control body, including registrations such as `windows-hands-01`.

Computer Hands status proves only that body. It cannot establish Chrome, Chromium Throne, Browser Nerve, social-adapter, or workstation-power status.

### Home Center and Command Center

Home Center and Command Center are the durable control, routing, state, and evidence planes. Their health can prove that the control plane answered. It does not prove that any desktop body, browser profile, extension, relay, account, or social workflow is live.

### THECAULDRON

THECAULDRON is the workstation. Workstation power, user session, network reachability, individual worker registration, browser process, Throne relay, worker-tab readiness, queue motion, and completed work are separate states.

## Context resolution

Resolve pronouns and shorthand against the active commission.

When the conversation is about Chromium Throne, its ChatGPT swarm, or social posting through Throne:

- "the desktop";
- "check desktop";
- "check again";
- "is it running?";
- "what is the swarm doing?";

refer to Chromium Throne unless Drew explicitly names a different organ.

Do not broaden the request to Browser Nerve or Computer Hands merely because those operations are easier to query.

## Required status-report shape

Every desktop/browser status claim must identify:

```text
ORGAN:
EVIDENCE SOURCE:
OBSERVED AT:
OBSERVATION:
PROVES:
DOES NOT PROVE:
FRESHNESS:
```

The first line must name the concrete organ. Avoid unqualified phrases such as "the desktop browser worker is offline."

## Status procedure

1. Resolve the intended organ from the current commission.
2. Query or retrieve evidence owned by that organ.
3. Check timestamp and freshness.
4. Separate direct observation from inference.
5. State what the evidence proves and what it cannot prove.
6. Reconcile conflicting evidence before making a negative claim.

If this ChatGPT surface has no callable Chromium Throne status operation, report:

`THRONE_STATUS_UNAVAILABLE_FROM_THIS_SURFACE`

That means the current surface cannot directly inspect Throne. It does not mean Throne is offline.

A stale Browser Nerve or Computer Hands heartbeat may be reported as an unrelated stale registration, but it must not be presented as the answer to a Chromium Throne status request.

## Contradiction law

Drew's report of same-day successful Chromium Throne use is material contradictory evidence.

When a retrieved status appears to conflict with that report, check these failure classes before contradicting him:

1. wrong organ queried;
2. stale worker registration;
3. missing Throne telemetry;
4. control-plane deployment lag;
5. process alive but heartbeat path broken;
6. work completed through another Throne component than the one queried.

Repair the identity error first. Retract the exact false claim. Then re-query the correct organ or state the exact visibility boundary.

## Forbidden inferences

Never infer any of the following:

- `Browser Nerve offline` therefore `Chromium Throne offline`;
- `Computer Hands offline` therefore `THECAULDRON offline`;
- `Home Center online` therefore `Chromium Throne online`;
- `Chrome process present` therefore `Throne relay ready`;
- `Throne relay ready` therefore `worker tabs ready`;
- `worker tabs active` therefore `social posting implemented`;
- `social adapter implemented` therefore `account authenticated`;
- `submit action returned` therefore `post verified`;
- `repository merged` therefore `desktop deployed`;
- `desktop deployed` therefore `end-to-end accepted`.

## Chromium Throne social lane

When Drew commissions social posting through Chromium Throne, that lane remains Chromium Throne.

Home Center may own durable job state, idempotency, watch cursors, and receipts. Social-site actuation must be provided by a bounded Throne social adapter operating through the dedicated Throne profile or by another capability explicitly exposed as part of the Throne lane.

Browser Nerve and Computer Hands are adjacent bodies, not implicit prerequisites or fallbacks. Using either requires an explicit lane change approved by Drew.

If the current Throne runtime can operate ChatGPT tabs but lacks a social-site adapter, report:

`SOCIAL_ADAPTER_NOT_IMPLEMENTED`

Do not translate that into "Chromium Throne is offline." Do not silently substitute Browser Nerve.

## Capability ledger

Keep these states separate:

1. requested;
2. specified in a skill;
3. implemented in source;
4. tested;
5. merged;
6. deployed to THECAULDRON;
7. callable from the current control surface;
8. authenticated to the commissioned account;
9. externally verified;
10. delivered to Drew;
11. accepted by Drew.

A later state requires its own evidence.

## Regression scenarios

### Wrong-worker heartbeat

Given a stale `windows-browser-nerve-01` heartbeat and same-day Throne work, the correct report is:

- Browser Nerve registration is stale;
- that observation does not establish Throne or THECAULDRON status;
- Throne requires Throne-specific evidence.

### Missing status operation

Given a healthy Home Center connection but no `chromium_throne.status` operation, the correct result is `THRONE_STATUS_UNAVAILABLE_FROM_THIS_SURFACE`, not offline.

### Social capability

Given fresh Throne worker-tab activity but no verified social post canary, report Throne worker transport active and social publishing unproven.

## Persistence and synchronization

Canonical source:

`Valar05/home-center/skills/chromium-throne-runtime-identity/SKILL.md`

A ChatGPT skill package and the Drive `Remote Skills/chromium-throne-runtime-identity` mirror must be regenerated whenever the canonical body changes. Mirrors must record the canonical source commit and content hash. A stale mirror is evidence, not authority.
