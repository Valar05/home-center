# Venice Stop Gate Skill

## Purpose
This is a boot-critical Fortress skill. Every agent, worker, spawned worker, bounded coding worker, swarm member, chat controller, and campaign executor must pass a separate Venice Judgement Jar review before it may stop, finish, hand off as complete, or declare a slice done.

This is not advisory doctrine. Missing Venice review means the worker is not done.

## 1. Separate reviewer
The active worker may not self-certify. Before any terminal completion response, invoke Venice as a separate review pass using the canonical Judgement Jars and the actual evidence for the slice.

For repository code/config changes, code review is Venice's first priority. Use the canonical `tools/venice_review.py` semantics: `PASS|FAIL` plus `STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED`.

## 2. Binding directives
- `STOP_ALLOWED`: the current worker slice may stop, preserving caveats and capability-state distinctions.
- `CONTINUE_REQUIRED`: stopping is forbidden. Venice's findings become a new observation and the same worker continues the same commission.
- `HALT_REQUIRED`: mutation stops because authority/evidence/safety is broken; preserve durable state and repair the review/evidence path where authorized.
- Missing, malformed, stale, or self-authored review: stopping is forbidden.

## 3. Evidence
A Venice claim without a durable review receipt is not evidence that Venice was consulted. Persist the review identity, directive, findings, evidence identity, and `externalReviewGateSatisfied` state. A receipt proves review only; it does not prove deployment, callability, delivery, or Drew's acceptance.

## 4. Daemon continuation
Latency, queueing, connector cooldown, model startup, or review-path recovery is not permission to skip Venice or end the mission. Back off sanely, preserve mission state, repair the path, and continue. Do not hammer connectors.

## 5. Conversation and personality
Personality, humor, relational judgment, and conversational terminal answers do not bypass this gate. If a worker is about to end its turn with an authored answer, Venice reviews whether that response is sufficient for the commissioned slice.

## 6. Regression rule
Any worker/runtime that has a terminal `done`, `finish`, `respond`, `handoff`, `complete`, or equivalent path must prove that path cannot terminate without Venice. Direct alternate agent entrypoints that bypass the gate are defects.

## 7. Fortress boot invariant
Fortress boot must treat this skill as required alongside `fortress-core` and `phone-runtime`. Discovery alone is insufficient. If `venice-stop-gate` is missing or cannot be loaded, Fortress boot fails closed.

## Compact law
No Venice receipt, no stop. Venice says continue, continue.
