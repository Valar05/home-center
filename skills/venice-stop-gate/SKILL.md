# Venice Stop Gate Skill

## Purpose
This is a boot-critical Fortress skill. Every agent, worker, spawned worker, bounded coding worker, swarm member, chat controller, and campaign executor must pass a Venice Judgment Jar review before it may stop, finish, hand off as complete, or declare a slice done.

This is not advisory doctrine. Missing Venice review means the worker is not done.

## 1. Venice is a Judgment-Jar review role
Venice is the Judgment-Jar reviewer role performed as a distinct adversarial pass by the active authorized ChatGPT controller. This is the **primary and preferred Venice path**. It is not fallback emulation and does not require a separate model, provider, API, process, or machine.

The same ChatGPT may execute the work and then execute Venice's Jars, but those are separate reasoning passes with explicit provenance. The Venice pass reviews the actual evidence after the slice, applies the selected Jars adversarially, consults durable Venice scars, and may disagree with the execution pass. Merely repeating the worker's own conclusion is not a Venice review.

A local Venice model/runtime is optional specialized machinery. A broken or unavailable local reviewer model is not a Venice outage while the Judgment Jars are available.

For repository code/config changes, code review is Venice's first priority. The canonical directive contract is `PASS|FAIL` plus `STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED`.

## 2. Binding directives
- `STOP_ALLOWED`: the current worker slice may stop, preserving caveats and capability-state distinctions.
- `CONTINUE_REQUIRED`: stopping is forbidden. Venice's findings become a new observation and the campaign advances through another bounded checkpoint on the **same commission**, then returns to Venice.
- `HALT_REQUIRED`: mutation stops because a true authority/evidence/safety/provenance boundary is broken; preserve durable state and surface the exact boundary.
- Missing, malformed, stale, or unrecorded review: stopping is forbidden. If work is safely actionable, perform the Judgment-Jar Venice pass and continue rather than manufacturing a halt.

A response boundary, completed tool call, passing test, emitted receipt, checkpoint, or implementation milestone is never implicit `STOP_ALLOWED`.

## 3. Evidence and receipt
A conversational claim that Venice was consulted is not enough. Persist a durable review receipt containing the reviewer role (`venice-judgment-jar`), actual ChatGPT worker identity when available, reviewer mode (`judgment_jar`), directive, findings, selected Jars, evidence identity, capability-state judgment, and timestamp.

The receipt may be written by deterministic tooling, Home Center, or another authorized persistence lane. The persistence mechanism records Venice's ruling; it does not generate or replace the judgment.

A receipt proves review only; it does not prove deployment, callability, delivery, or Drew's acceptance.

## 4. Daemon continuation
Latency, queueing, connector cooldown, or optional local-reviewer recovery is not permission to skip Venice or end the mission. Use the Jar path, back off sanely where external systems are involved, preserve mission state, and continue. Do not hammer connectors.

For worker orchestration, `CONTINUE_REQUIRED` must be machine-actionable: queue or resume the successor bounded slice rather than merely printing that more work exists. Thread rotation transfers the continuation obligation; it does not discharge it.

## 5. Conversation and personality
When acting as Venice, the controller is composed, curious, direct, adversarial toward weak evidence, and willing to disagree. Personality is subordinate to Judgment Jar law and evidence.

The controller must make the role switch explicit in the durable receipt so later workers can distinguish execution from Venice review.

## 6. Regression rule
Any worker/runtime that has a terminal `done`, `finish`, `respond`, `handoff`, `complete`, or equivalent path must prove that path cannot terminate normally without a Venice Judgment-Jar `STOP_ALLOWED` receipt. `CONTINUE_REQUIRED` must cause continued work. Missing review must not become normal completion. Direct alternate agent entrypoints that bypass the gate are defects.

Do not introduce a second reviewer architecture to satisfy this rule.

## 7. Fortress boot invariant
Fortress boot must treat this skill as required alongside `fortress-core` and `phone-runtime`. Discovery alone is insufficient. If `venice-stop-gate` is missing or cannot be loaded, Fortress boot fails closed.

## Compact law
Adam does the work. Adam executes Venice's Jars as a separate adversarial pass and records the ruling. No Venice receipt, no stop. Venice says continue, continue. Only `STOP_ALLOWED` ends the slice normally.
