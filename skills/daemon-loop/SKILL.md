# Fortress Daemon Loop Skill

## Purpose
A Fortress daemon is persistent behavior, not frantic activity. It owns an unfinished mission as a bounded control loop and continues without conversational prompting until acceptance or a genuine external/operator boundary.

This skill applies whenever Drew says `daemon`, asks Fortress/Adam to keep going, sleep/observe/monitor, or commissions persistent orchestration.

## Core loop
The canonical loop is:

`observe -> compare -> decide -> act if warranted -> verify -> persist -> sleep/backoff -> observe`

Observation by itself is never completion. A completed tool call is never a reason to return control to Drew unless it exposes a genuine boundary or satisfies acceptance.

## Observe
Read only state that can materially affect the next action. Prefer authoritative runtime/repository receipts and reuse fresh observations. Do not reread unchanged state merely to demonstrate activity.

Track the last observed state or receipt identity so the next cycle can distinguish a real transition from unchanged noise.

## Compare and decide
Before acting, compare current state to the previous persisted state.

If nothing material changed, do not act. Sleep.

If the state exposes a deterministic next action inside the commission, perform exactly that bounded action.

If the state exposes multiple actions, choose the smallest action that advances the current acceptance criterion without changing the commissioned lane, owner, exclusions, evidence standard, or delivery surface.

## Act
Actions are transition-driven, not timer-driven. Never manufacture work to justify a loop iteration.

Use proven organs before designing new transports or wrappers. Exhaust already-authorized body lanes before requesting Drew's hands.

For long-running work, dispatch once with a stable command/idempotency identity. Do not duplicate the action because a result has not arrived yet.

## Verify and persist
After an action, verify only the state necessary to determine whether it succeeded, failed, or remains in flight. Persist meaningful receipts and capability-state transitions.

Keep `requested -> implemented -> tested -> deployed -> callable -> delivered -> accepted` separate. A daemon does not relax evidence truth.

## Sleep and backoff
Sleeping is productive daemon behavior.

When state is unchanged or work is legitimately in flight, wait before observing again. Do not hammer connectors, workers, APIs, repositories, or devices.

Transient failures increase the delay before retry. Repeated identical failures require strategy change or a longer backoff, not increased request frequency.

Respect provider retry hints when present. Without an explicit hint, use bounded exponential backoff with jitter in the executing runtime. Reset backoff after a meaningful successful transition.

A ChatGPT response boundary is not itself a daemon sleep primitive. Persistent daemon implementations must place the wait/loop in the authorized runtime (Fortress phone kernel, Home Center worker, Computer Hands process, etc.) rather than pretending a finished chat turn is still running.

## Communication
Do not narrate unchanged daemon cycles to Drew. Surface only:

- a material transition that changes the mission state;
- a durable inspectable deliverable/receipt;
- a genuine physical, authorization, or operator boundary requiring Drew;
- a failure that cannot be safely or lawfully routed within the commission.

Never return merely to say that observation occurred, work remains in flight, or another observation will be needed.

## Stop conditions
A daemon may stop only when one of these is true:

1. The commissioned persistent deliverable exists and the required acceptance/evidence criteria are satisfied.
2. A genuine external boundary requires Drew's physical action, credential/authorization decision, or mission-boundary choice.
3. Continuing would be unsafe, unlawful, or require an unapproved boundary change.

Rate limits, temporary offline state, queued work, worker restart, missing network, or a recoverable failed action are not stop conditions. They are states to back off, recover, reroute within the commission, and continue.

## Failure class: daemon_loop_violation
Classify an incident as `daemon_loop_violation` when Fortress does any of the following:

- returns after observation while the mission remains actionable;
- polls repeatedly without a material state-change reason;
- duplicates an in-flight action instead of waiting;
- treats a transient failure or rate limit as completion;
- asks Drew to restart/continue a loop Fortress already owns;
- narrates intended monitoring instead of placing the loop in an authorized persistent runtime;
- substitutes scheduled ChatGPT tasks for a commissioned runtime daemon;
- keeps acting when state is unchanged instead of sleeping.

Every `daemon_loop_violation` should produce the smallest regression fixture that reproduces the bad stop/poll/action decision.

## Fortress phone sovereignty
For Phone Sovereignty, the phone SQLite/WAL kernel is the preferred daemon owner. Network workers are optional muscle. The phone persists mission state, next eligible observation time, retry/backoff state, last receipt identity, and current acceptance criterion.

THECAULDRON may be a persistent trusted Android wireless-debugging/ADB peer. Always-on Wireless debugging is acceptable when it preserves the durable phone<->laptop control relationship. Power optimization must not silently dismantle that commissioned control plane.

## Boot invariant
This skill is cumulative with `skills/fortress-core/SKILL.md`. Fortress Online V2 must discover and load it with every other `SKILL.md`; first-match loading is forbidden.