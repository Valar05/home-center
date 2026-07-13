# She-Raw MCP Contract

She-Raw exposes these tools through `sheRawMcp`:

- `she_raw_operation`
- `she_raw_consult`
- `she_raw_critique`
- `she_raw_introspect`
- `she_raw_correct`
- `she_raw_feedback`
- `she_raw_review_learning`
- `she_raw_validate_correction`
- `she_raw_list_active_rules`
- `she_raw_forget_rule`
- `she_raw_ambient`
- `she_raw_recreational`
- `she_raw_review`
- `she_raw_search_corpus`
- `she_raw_get_case`
- `she_raw_set_command_state`
- `she_raw_list_brains`
- `she_raw_brain`
- `she_raw_health`

All tools use authenticated MCP transport. Writes preserve audit events and do not mutate external repositories.

## No-Reinstall Operation Pump

`she_raw_operation` is the stable no-reinstall dispatcher. It accepts `{operation, args}` and runs operations from `she_raw_manual.operationRegistry.operations` / `she_raw_health.operation_registry.operations`.

Use this tool first when ChatGPT's connector metadata may be stale. If `she_raw_brain` is hidden in the visible connector schema, call:

```json
{"operation":"brain.invoke","args":{"brainId":"prospector","conversationKey":"stable-chat-key","commandState":"idle","boundedContext":"short context","question":"optional question"}}
```

Backend success through `she_raw_operation` proves the service pump works. It does not prove ChatGPT's visible connector schema is fresh unless ChatGPT actually invokes the operation tool.

`operation="road.check"` is the recovery lane when the host is unsure how to use She-Raw. It is read-only and returns `road_status`, `usable_now`, `preferred_tool`, `next_calls`, `degraded_lanes`, `blocked_lanes`, `do_not_do`, and `proof_required`. Use it before creating any new worker, connector, service, Agent Closet entry, or Command Center dispatch.




## Route Pump Contract

Every consult builds a route before retrieval or learned-rule application. The route includes `layer`, `sensitivity`, `brain_id`, `command_state`, `retrieval_policy`, `rule_policy`, and `response_contract`.

Route policies are binding: `personal_caregiving` and `high_stakes_sensitive` use `retrieval_policy=none` and `rule_policy=none`; `brain_jar` uses the selected jar contract; `artifact_critique` preserves directed critique shape; `operational_infrastructure` may use corpus and learned rules. Ambient/random/recreational paths must consult the route and stay silent for execution or sensitive/high-stakes contexts.

## Personal Caregiving Guard

`she_raw_consult` classifies explicit personal/caregiving contexts before applying retrieved corpus cases or active learned rules. If the bounded context names a living-person support situation, relationship vow, medical-access support, accessibility support, or death fear, the response must address agency, consent, redundancy, thresholds, and bounded responsibility. It must not fall back to infrastructure, MCP, worker, Firestore, corpus, deployment, or service-boundary advice.

## Brain Jar Boundary

She-Raw is the MCP runtime and default voice. She-Raw itself is not a brain jar and must not be registered as an Agent Closet agent.

`she_raw_list_brains` returns available jars and their source provenance. `she_raw_brain` invokes one jar through She-Raw MCP and returns a durable `srbrain_*` invocation. Quartermaster, Prospector, Foreman, Auditor, Holocron, Wallfly, Sommelier, and Command Center are jars behind She-Raw, not standalone MCP services or Command Center workers.

Agent Closet is allowed as source/provenance for the role definitions. She-Raw MCP owns invocation, response shaping, persistence, learning, and the Command Center execution gate.


## Bikini Bottom Brain Jar

`bikini_bottom` is one brain jar behind She-Raw MCP. It must be invoked through `she_raw_brain` or `she_raw_operation` with `operation=brain.invoke`; do not create six character agents or a Command Center worker.

The jar is a detachable function-cast simulator. The symbols compress functions only after observations are stated, and the final judgment must be plain operational language that remains coherent after removing character names.

## Lockout Matrix

```text
executing + ambient      => blocked
executing + recreational => blocked
executing + random       => blocked
executing + explicit     => allowed
executing + requested critique checkpoint => allowed
```

This is enforced in `functions/she_raw_mcp.js` by `gateInvocation()` before retrieval or model response.

## Host Routing Rule

Direct perspective invocation outranks connector-shaped behavior. When the host hears `She-Raw, health check`, it should answer in the She-Raw perspective immediately and should not dispatch Command Center, create a job, or deploy infrastructure.

Call MCP only to persist or inspect state: `she_raw_correct`, `she_raw_introspect`, `she_raw_review_learning`, `she_raw_list_active_rules`, `she_raw_search_corpus`, or explicit tool-backed `she_raw_consult`.
