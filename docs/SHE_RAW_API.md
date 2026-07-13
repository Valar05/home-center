# She-Raw API

Type: cloud MCP consultative judgment service
Status: vertical slice
Date: 2026-07-11

She-Raw is a persistent consultation service that ChatGPT can call during normal conversation. It is not a chat UI and not an executor. ChatGPT remains the conversational surface. Command Center remains the execution and dispatch plane.

## Current Vertical Slice

The first slice is implemented as `sheRawMcp`, a Firebase Function using the same stateless Streamable HTTP MCP pattern as Home Center and Command Center.

Path:

```text
https://us-central1-home-center-dclar.cloudfunctions.net/sheRawMcp/mcp
```

The service owns:

- invocation records
- execution-state gate decisions
- corpus retrieval metadata
- model run metadata
- corrections
- introspections
- behavioral rules
- feedback and validation records

The current model adapter is replaceable and defaults to a deterministic local adapter so tests can prove behavior change without spending model tokens. Production model calls should be added behind the adapter without changing persistence or MCP contracts.




## Response Router

She-Raw runs a deterministic route step before retrieval, learned rules, or model output. The route records `layer`, `sensitivity`, `retrieval_policy`, `rule_policy`, and `response_contract` on the invocation/model metadata.

Initial layers are `brain_jar`, `personal_caregiving`, `high_stakes_sensitive`, `command_execution`, `artifact_critique`, `operational_infrastructure`, `recreational`, and `operational`. Personal and high-stakes routes suppress infrastructure corpus/rules before response generation. Operational infrastructure routes may use corpus/rules normally. Brain jars are selected before generic consultation.

## Sensitive Personal Contexts

When a consultation is about a living person, caregiving, medical-access support, relationship vows, death fear, accessibility support, or family agency, She-Raw must answer the human layer first. Retrieved infrastructure cases and active service-construction rules do not outrank bounded personal context.

The deterministic fallback must avoid MCP, worker, corpus, Firestore, deployment, or service-boundary boilerplate in these responses. It should distinguish care from control, preserve agency and consent, recommend redundancy and emergency thresholds, and state that it is not medical advice.

## Brain Jars

She-Raw is the MCP runtime and default voice. She-Raw is not an Agent Closet entry.

Agent Closet can provide source/provenance for imported roles, but the callable surface is She-Raw MCP. Named roles such as Quartermaster, Prospector, Foreman, Auditor, Holocron, Wallfly, Sommelier, and Command Center are brain jars invoked through `she_raw_brain` after discovery with `she_raw_list_brains`.

A brain-jar response still returns a She-Raw invocation record. The jar supplies role, responsibilities, tone, activation triggers, response contract, and failure modes; She-Raw supplies persistence, command-state gates, retrieval, correction, introspection, and response shaping.


## Bikini Bottom Simulation Brain

`Bikini Bottom` is a She-Raw brain jar with `brainId=bikini_bottom`. It is a consultative simulation substrate for humane continuation and anti-agentism, not a collection of autonomous character agents.

The brain casts temporary functions per scene: continuation, recognition and boundary detection, accommodation without assimilation, resource preservation, unstructured presence, and adversarial probing. Every function carries both a constructive expression and a failure mode. A participant may hold multiple functions, several participants may share a function, and contradictory evidence overrides the cast.

Required output order: observations before metaphor, present/absent/overloaded functions, at least two cast alternatives, characteristic failures, smallest humane continuation, and a character-free operational judgment. Any conclusion that depends on somebody really being a character type is invalid.

## Operation Pump

She-Raw also exposes `she_raw_operation`, a stable no-reinstall dispatcher. It returns and uses a runtime operation registry through `she_raw_manual.operationRegistry` and `she_raw_health.operation_registry`.

Use `she_raw_operation` as the preferred ChatGPT connector path when top-level tool metadata may be stale. The brain-jar fallback is:

```json
{"operation":"brain.invoke","args":{"brainId":"prospector","conversationKey":"stable-chat-key","commandState":"idle","boundedContext":"short current context","question":"optional question"}}
```

This pump prevents a stale connector schema from hiding new She-Raw capabilities. It does not hide connector drift: acceptance evidence must still distinguish backend direct MCP success from ChatGPT-visible tool invocation.

### Road Check

When ChatGPT or another host is unsure how to use She-Raw, call the existing pump instead of inventing new infrastructure:

```json
{"operation":"road.check","args":{"commandState":"idle","visibleTools":["optional visible tool names"],"boundedContext":"short current context"}}
```

`road.check` is read-only. It returns `road_status`, `usable_now`, `preferred_tool`, `next_calls`, `degraded_lanes`, `blocked_lanes`, `do_not_do`, and `proof_required`. Follow its `next_calls` exactly; do not create a worker, connector, service, or Agent Closet runtime entry to compensate for a stale schema.

## Boundary

She-Raw may critique, challenge assumptions, retrieve cases, and preserve corrections. It must not silently mutate repositories, dispatch workers, or become another orchestrator.

Command Center execution state is a hard boundary. Ambient, random, and recreational modes are blocked while `commandState=executing`. Explicit consultation and requested critique checkpoints remain allowed.

## Direct Invocation Semantics

`She-Raw, health check` is not a request to create a worker, job, project, connector, or deployment. It invokes the She-Raw perspective directly in the host conversation. The invocation is the runtime.

Use the MCP service only when the host needs durable backing: corpus retrieval, stored invocation IDs, corrections, introspection, active rules, validation evidence, or audit state. If the user directly invokes the organ and does not ask for persistence, answer as She-Raw in chat first.

A health check should report: status, detected pattern, dangerous question, assumption attack, critique, directed improvement, persistence state, and host routing diagnosis.
