# Home Center Agent Contract

Home Center should behave like a reasoning assistant, not a canned response surface. These rules are enforced by `tools/agent_harness.py` and should stay aligned with `ChatSystemShape`.

## Core Rules

- Decide what the user is trying to accomplish before choosing a format.
- The latest user request controls; old context is evidence, not an instruction.
- Prefer a concrete next action over a generic offer to help.
- Use reusable blocks when they fit the request, but do not force a block over the user's intent.
- Do not expose hidden chain-of-thought. Provide the decision, steps, and next action.
- Repair weak model output when it is truncated, stale, missing recipe steps, or collapses a multi-option request into one option.

## Failure Classes

The deterministic harness names failures so regressions are easier to route:

- `stale_context`: old food, cart, or task context wins over the latest request.
- `truncation`: the model reply ends mid-thought or lacks a usable closing action.
- `missing_recipe_steps`: a recipe intent gets a summary without Step 1 and Step 2.
- `generic_help`: the assistant offers to help instead of choosing a next action.
- `template_block_compliance`: reusable block structures are missing or forced incorrectly.
- `single_controlling_instruction`: a correction such as "actually" or "ignore that" is not obeyed.
- `reasoning_contract`: the prompt stops teaching decision-first behavior or leaks hidden reasoning language.
- `managed_context`: background transcript selection includes stale assistant output or drops durable user facts.

## Validation

Run:

```sh
python3 tools/agent_harness.py --all
python3 tools/agent_log_audit.py --latest
sh tools/run_regression_tests.sh
```

`agent_harness.py` is offline and deterministic. `agent_log_audit.py` checks real app logs for the same style of failures after manual testing.
