# Fortress Online V2

Status: EXPERIMENTAL / ISOLATED
Authority: Drew Clarke
Branch: `fortress-online-v2`
Non-interference lock: V2 must not mutate or replace active Fortress Online V1 until explicitly accepted.

## Purpose
Fortress Online V2 converts Tetsuya/Adam doctrine from advisory prose into deterministic runtime gates and an automatic learning cycle. It must retrieve material truth, preserve the cumulative commission, execute through the authorized lane, test its work, and improve its own V2 policy from observed failures without silently changing V1.

## Governing completion rule
An unfinished mission continues automatically. A handoff is permitted only when (a) direct operator input is genuinely required, or (b) the commissioned deliverable exists on its persistent surface and comprehensive relevant tests are green. A documented failure is not completion. A single happy-path test is not comprehensive evidence.

## Core gates
1. Required retrieval: material uncertainty becomes a lookup obligation.
2. Boundary fidelity: outcome, owner, lane/tool, exclusions, evidence and delivery surface cannot silently change.
3. Cumulative correction: later fixes preserve all earlier non-conflicting locks.
4. Capability truth: requested, implemented, tested, deployed, callable, delivered and accepted remain separate.
5. Continuation: unfinished work chooses the next safe authorized action rather than quitting.
6. Evidence: completion claims require persistent artifacts and the commissioned evidence standard.
7. V1 isolation: all V2 learning and self-modification remains on `fortress-online-v2` until explicit promotion.

## Automatic Tetsuya learning cycle
`observe -> classify -> candidate rule -> candidate regression -> encode -> full regression -> promote inside V2 -> observe`

Every correction or runtime failure is retained as an incident. Known classes automatically produce a policy candidate and regression specification. Unknown failures are retained for classification rather than disappearing. A candidate may become active V2 policy only when its regression has been encoded, the complete V2 suite is green, and no prior mission lock regressed. Promotion never mutates V1.

The learner currently recognizes retrieval failures, premature stopping, boundary substitution, correction regression, capability laundering, and transport failures. Transport failures include shell quoting and Git LFS smudge failures encountered during desktop validation.

## State machine
`requested -> implemented -> tested -> deployed -> callable -> delivered -> accepted`
No state implies a later state.

## Comprehensive test matrix
Promotion evidence must cover, where applicable:
- unit/contract behavior for every deterministic gate;
- historical incident replay;
- learner promotion and learner refusal paths;
- malformed/unknown incident behavior;
- cumulative-lock regression protection;
- transport failures and retry behavior;
- persistent-source readback;
- clean isolated desktop execution from the V2 branch;
- shadow missions drawn from real Fortress work, without mutating V1;
- capability-state truthfulness and completion refusal when evidence is incomplete.

GitHub Actions is desirable but not the only test runner. If GitHub refuses to start a runner because of account Actions budget, the connected Windows desktop is the authorized independent runner. Test evidence must identify the persistent commit tested and the exact pass/fail result.

## Acceptance gate for replacing V1
V2 remains quarantined until:
1. the deterministic suite is comprehensively green on an independent execution lane;
2. historical Fortress failures are encoded and green;
3. automatic learning promotion/refusal is green;
4. at least three live non-destructive shadow missions pass against real Fortress work;
5. source and test artifacts are persistently readable from GitHub;
6. V2 demonstrates improved retrieval, constraint preservation, automatic continuation, and truthful completion without materially increasing friction or quota burn;
7. Drew explicitly accepts promotion.

Until explicit acceptance, V1 remains active and V2 remains a tested successor candidate.
