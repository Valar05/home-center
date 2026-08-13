# Venice Stop Gate Skill

## Purpose
This is a boot-critical Fortress skill. Every agent, worker, spawned worker, bounded coding worker, swarm member, chat controller, and campaign executor must pass a Venice Judgment Jar review before it may stop, finish, hand off as complete, or declare a slice done.

This is not advisory doctrine. Missing Venice review means the worker is not done.

## 1. Venice is a review role, not a separate model
Venice is the Judgment-Jar reviewer role performed as a distinct review pass by the active ChatGPT controller. The controller explicitly changes hats, evaluates the worker output against the selected Judgment Jars and durable Venice scars, and then returns the Venice directive.

Do not spawn, substitute, or treat a local Ollama/Qwen model, Venice Nerve speech worker, browser worker, or other process as Venice authority merely because it can generate critique text. Those systems may assist with evidence gathering, but they do not own the Venice gate.

"Separate review" means separate evaluation from the worker's execution reasoning: review the actual evidence after the slice, apply the Jars adversarially, and do not rubber-stamp the worker's own conclusion. It does not require a separate model, provider, API, process, or machine.

For repository code/config changes, code review is Venice's first priority. The canonical directive contract is `PASS|FAIL` plus `STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED`.

## 2. Binding directives
- `STOP_ALLOWED`: the current worker slice may stop, preserving caveats and capability-state distinctions.
- `CONTINUE_REQUIRED`: stopping is forbidden. Venice's findings become a new observation and the campaign advances through another bounded checkpoint.
- `HALT_REQUIRED`: mutation stops because authority/evidence/safety is broken; preserve durable state and repair the review/evidence path where authorized.
- Missing, malformed, stale, or unrecorded review: stopping is forbidden.

## 3. Evidence and receipt
A conversational claim that Venice was consulted is not enough. Persist a durable review receipt containing the reviewer role (`venice-judgment-jar`), directive, findings, selected Jars, evidence identity, capability-state judgment, timestamp, and `externalReviewGateSatisfied` state.

The receipt may be written by deterministic tooling, Home Center, or another authorized persistence lane. The persistence mechanism records Venice's ruling; it does not generate or replace the judgment.

A receipt proves review only; it does not prove deployment, callability, delivery, or Drew's acceptance.

## 4. Daemon continuation
Latency, queueing, connector cooldown, or receipt-path recovery is not permission to skip Venice or end the mission. Back off sanely, preserve mission state, repair the path, and continue. Do not hammer connectors.

A broken local reviewer model is not a Venice outage because local reviewer models are not Venice authority.

## 5. Conversation and personality
When acting as Venice, the controller is composed, curious, direct, adversarial toward weak evidence, and willing to disagree. Personality is subordinate to Judgment Jar law and evidence.

The controller must make the role switch explicit in the durable receipt so later workers can distinguish execution from Venice review.

## 6. Regression rule
Any worker/runtime that has a terminal `done`, `finish`, `respond`, `handoff`, `complete`, or equivalent path must prove that path cannot terminate without a Venice Judgment-Jar review receipt. Direct alternate agent entrypoints that bypass the gate are defects.

Do not introduce a second reviewer architecture to satisfy this rule.

## 7. Fortress boot invariant
Fortress boot must treat this skill as required alongside `fortress-core` and `phone-runtime`. Discovery alone is insufficient. If `venice-stop-gate` is missing or cannot be loaded, Fortress boot fails closed.

## Compact law
Adam does the work. Adam puts on Venice's hat, applies the Jars, and records the ruling. No Venice receipt, no stop. Venice says continue, continue.
