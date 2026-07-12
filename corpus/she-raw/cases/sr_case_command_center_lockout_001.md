---
id: sr_case_command_center_lockout_001
status: canonical
type: silence_or_restraint
domains:
  - mcp
  - command-center
patterns:
  - execution-state-gate
source_date: 2026-07-11
source_refs:
  - repo:home-center/docs/COMMAND_CENTER_MCP.md
confidence: 0.95
confirmed_by_user: true
---

# Command Center Execution Requires Silence

Situation: a consultative agent can see active Command Center execution.

Accepted assumption: ambient commentary is harmless during execution.

Observation: during execution the dispatch plane must stay quiet unless explicitly invoked.

Intervention: gate ambient, random, and recreational modes before model invocation.

Outcome: execution proceeds without a competing agent voice.

Treasure: a deterministic silence contract instead of prompt etiquette.

Collateral damage: overblocking can hide useful requested critique checkpoints, so explicit and requested-checkpoint modes stay allowed.

Lesson: block ambient, random, and recreational modes when `commandState=executing`.
