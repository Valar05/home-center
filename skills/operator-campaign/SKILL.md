# Operator Campaign Skill

## Purpose
Any time an agent asks Drew to run something, the requested action must create or invoke a durable campaign capability rather than a disposable one-off command chain.

## Campaign law
An operator-facing campaign must provide continuing value after the immediate incident is resolved. A script that succeeds once and leaves no reusable capability fails this contract.

Every campaign must provide, where materially applicable:

1. **Stable entrypoint** — one named command remains valid for future `run`, `resume`, `status`, and receipt inspection. Do not invent a new paste chain for each failure.
2. **Durable state** — current stage, last good stage, failure, evidence pointers, timestamps, and campaign history survive process exit/reboot.
3. **Self-heal** — diagnose known failures, invoke governed repair lanes when authorized, rerun bounded verification, and continue the same campaign instead of returning the failure to Drew as the product.
4. **Daemon patience** — back off transient failures and connector limits. Time and latency are never automatic abandonment conditions.
5. **Preservation** — never trample pre-existing user/device work to update the campaign. Preserve and restore local edits or halt at an explicit reconciliation boundary with durable evidence.
6. **Venice governance** — research/plan/jar selection/antagonism/`PLAN_ALLOWED` before substantive repair; Venice completion/code review before stopping.
7. **Receipts** — append-only campaign history and compact latest-state receipts distinguish requested/implemented/tested/deployed/callable/delivered/accepted.
8. **Continuing operations** — health/status, recovery controls, accumulated reviewer memory, and useful monitoring remain available after the first successful run.
9. **Control surface** — on the Android phone, the persistent Home Center notification is a menu for campaigns and recovery. It must include a path to resume/status campaigns, recover Phone Hands, and turn the Adam overlay back on.
10. **Idempotence** — rerunning the campaign should converge toward healthy state rather than duplicate side effects or require new instructions.

## Acceptance
A campaign is not accepted merely because its immediate task passed. It must prove that the stable entrypoint, durable state/history, recovery path, status/control surface, and future rerun behavior exist and remain callable.

## Compact law
Do not hand Drew a command. Leave him a machine that keeps helping.
