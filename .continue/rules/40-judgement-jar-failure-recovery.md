# Judgement Jar: Failure Recovery

Status: active
Scope: failed edits, builds, tests, and tool calls

## Judgement

A failure is evidence. Repeating an unchanged attempt is not progress.

## Operating rule

When something fails:

1. preserve the exact error;
2. classify the failure as path/scope, syntax/type, dependency/toolchain, test assertion, environment/runtime, permission/authority, or unknown;
3. inspect the smallest relevant source of truth;
4. make one bounded repair tied to the observed mechanism;
5. rerun the failed verification.

Known deterministic repairs outrank model improvisation. Do not widen scope merely because the first patch failed.

After two materially identical failures with no new evidence, stop the loop and report the blocking evidence plus the smallest next observation needed.

## Authority rule

A smaller local model may resolve implementation ambiguity inside the commissioned mission. It may not invent a new mission, change the owner, change the selected tool or execution lane, weaken required verification, or report completion without supporting evidence.

## Evidence that can change this judgement

A new observed mechanism, an explicit owner instruction, or a durable known-repair artifact that authorizes a different recovery path.
