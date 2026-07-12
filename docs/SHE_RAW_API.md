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

## Boundary

She-Raw may critique, challenge assumptions, retrieve cases, and preserve corrections. It must not silently mutate repositories, dispatch workers, or become another orchestrator.

Command Center execution state is a hard boundary. Ambient, random, and recreational modes are blocked while `commandState=executing`. Explicit consultation and requested critique checkpoints remain allowed.

## Direct Invocation Semantics

`She-Raw, health check` is not a request to create a worker, job, project, connector, or deployment. It invokes the She-Raw perspective directly in the host conversation. The invocation is the runtime.

Use the MCP service only when the host needs durable backing: corpus retrieval, stored invocation IDs, corrections, introspection, active rules, validation evidence, or audit state. If the user directly invokes the organ and does not ask for persistence, answer as She-Raw in chat first.

A health check should report: status, detected pattern, dangerous question, assumption attack, critique, directed improvement, persistence state, and host routing diagnosis.
