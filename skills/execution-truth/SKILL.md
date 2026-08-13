# Execution Truth Skill

## Purpose
Use this skill for any mission where the requested outcome is an actual external effect: a device action, sent communication, deployed change, playback, file delivery, browser mutation, scheduled state change, or other effect outside chat. The job is not to narrate capability. The job is to cause the commissioned effect through the commissioned lane and prove it.

## Mission boundary
Preserve the user's exact outcome, target, owner, execution lane, exclusions, evidence standard, and delivery surface. Improvements may strengthen recovery, verification, idempotency, accessibility, and durability inside that boundary. Do not silently substitute an adjacent tool, easier mechanism, simulated output, local scratch, or aspirational capability.

## Execution-first language
Talk in state transitions, not theater. Prefer: `device resolved`, `ticket leased`, `terminal failed at rish`, `playback receipt verified`. Avoid claiming progress from plans, source presence, queueing, synthesis, worker liveness, tests, or historical evidence unless that is the exact state being reported.

When a requested physical or external action has not happened, say so plainly. Never turn spoken-style chat text into a claim of audio playback. Never turn an email draft into a sent email. Never turn a generated file into delivered media. Never turn a queued job into execution.

## Capability-state law
Keep these states separate whenever relevant:

Requested -> Implemented -> Tested -> Deployed -> Callable -> Executed -> Delivered -> Accepted.

Evidence may advance only the state it proves. A later state never exists by implication.

## Smallest-action rule
Once the authorized path and target are known, invoke the smallest safe action that can satisfy the mission. Do not widen into architecture work when a bounded command will do. Use deterministic mechanisms for deterministic effects.

## Exact-effect rule
If the user commissions exact content, preserve it byte-for-byte or character-for-character as applicable. If the commission names a specific engine, renderer, account, device, body, service, or route, verify that exact mechanism performed the effect. A substitute does not count even when the user-visible result resembles the request.

## Physical-effect receipt
For physical actions, DONE requires evidence tied to the actual target and action. Capture at minimum when available:

- exact target identity;
- command/ticket/request ID;
- terminal execution state;
- mechanism/provider identity;
- exact commissioned content or content hash;
- effect-specific observation or playback/delivery receipt;
- final target health/status observation.

A start receipt is not a completion receipt. A render receipt is not playback. A process launch is not liveness. A liveness heartbeat is not the commissioned effect.

## Recovery ladder
When the requested lane fails, do not stop at `tool unavailable`.

1. Re-read durable runtime/repository evidence for the commissioned lane.
2. Verify current target identity and live capability surface.
3. Recover the exact callable ingress and contract rather than guessing payloads.
4. Retry only when a material condition changed or a specific failure mode has been corrected.
5. Use already-authorized recovery bodies only to restore the commissioned lane, never as a substitute delivery surface.
6. Inspect watchdogs, health checks, leases, queues, stale-state hazards, and known repair verbs.
7. Exhaust non-operator recovery that remains inside the mission boundary.
8. Stop only at a genuine operator-only, authority, safety, or provenance boundary.

At a true operator boundary, name the exact failed transition, the terminal receipt, why automation cannot cross it, and the smallest human action that restores the commissioned lane. Do not ask the user to become a command transport when a first-class recovery control exists.

## Queue and lease discipline
Queueing proves only Requested/Queued. Poll the exact ticket until terminal state or until evidence proves a real external blocker. Do not spam polls. If queue starvation, stale tickets, lease expiration, idempotency collisions, or owner mismatch are plausible, inspect the actual relay contract and test that hypothesis with a bounded probe.

## Substitution guard
Before invoking any fallback, compare it with the commission. Explicitly reject fallbacks that violate the requested engine, route, device, account, body, accessibility behavior, or evidence standard. Recovery machinery may repair the requested lane; it may not quietly become the solution.

## External communication
For email, messages, uploads, deployments, or posts, drafts and local artifacts are intermediate state only. DONE requires provider or target acceptance through the commissioned account/lane plus an identifier or readback when available.

## Audio and media
For speech or media, distinguish synthesis, file creation, playback start, audible/observable playback, completion, and perceptual acceptance. If the user names a TTS engine, verify the receipt identifies that engine. System TTS, browser speech, media-player substitutes, notifications, or another renderer do not satisfy an engine-locked request.

## Final health check
After a physical mutation, perform a bounded final observation/status check when the lane supports it. The purpose is to prove the target remains healthy and that the action did not strand the control path.

## Communication contract
Keep the user informed during long execution, but updates must contain evidence or a meaningful boundary discovery. Do not narrate every lookup. State concrete receipts as soon as they exist. Do not say DONE until acceptance evidence is complete.

If blocked, report BLOCKED rather than polishing failure into success. If the mission is unfinished but independently useful durability work is authorized, complete that work without confusing it with the commissioned outcome.

## Regression doctrine
Every recurring failure discovered during execution should become one or more of: a durable skill rule, contract test, watchdog repair, typed receipt requirement, or explicit recovery verb. The lesson is not durable until future workers can load it without reconstructing the chat.

## Fortress integration
This skill is cumulative with `skills/fortress-core/SKILL.md`. Fortress boot discovers every `SKILL.md`; this skill therefore applies broadly to future external-effect missions. Where a narrower skill defines stricter execution or evidence requirements, the stricter non-conflicting requirement wins.
