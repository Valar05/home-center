# Venice Review Memory Skill

## Purpose
Venice learns from prior reviews. Blocking findings and high-value review notes must survive the current worker, process, conversation, and reboot, then influence future agents before they repeat the same mistake.

## Durable memory
The canonical runtime memory is append-only JSONL at:

`~/.local/state/home-center/venice/review-memory.jsonl`

The latest compact projection is:

`~/.local/state/home-center/venice/review-memory-latest.json`

These files are evidence-bearing reviewer memory, not capability receipts.

## Required behavior
1. Before Venice reviews a slice, load prior durable review-memory entries relevant to the repository/work category and include them as explicit precedent.
2. On every `CONTINUE_REQUIRED`, `REPLAN_REQUIRED`, or `HALT_REQUIRED`, persist each blocking finding with repository identity, review identity, evidence hashes, category, applied Judgment Jars, and a reusable prevention rule.
3. On `STOP_ALLOWED` or `PLAN_ALLOWED`, Venice may persist a positive precedent when it closes or disproves a recurring failure mode.
4. Future workers must not treat these notes as optional flavor. They are reviewer precedent and must be considered alongside current evidence.
5. Never overwrite history to make the latest review look cleaner. Append corrections and supersession notes.
6. Deduplicate equivalent findings by stable fingerprint while incrementing occurrence count. Repeated mistakes become stronger precedent rather than duplicated noise.
7. Memory must distinguish observation, inference, rule, regression target, and capability state.
8. A Venice memory entry can never by itself prove the current task is done or safe to begin. Current evidence and a fresh Venice ruling remain mandatory.
9. When a scar has a She-Raw roast, worker/reviewer packets must carry that roast alongside the prevention rule. The roast is load-bearing mnemonic pressure only when it is consumed by a real review/repair action.

## Seed scars from the Adam/Fortress reset
These precedents are already paid for and must not be rediscovered as if novel:

### Self-certified completion
Observation: workers repeatedly stopped after describing implementation or failure without actually consulting Venice.
Rule: no Venice receipt, no stop. `CONTINUE_REQUIRED` means continue the same commissioned slice.
Regression target: every terminal worker path proves a fresh Venice completion receipt.
She-Raw roast: "Congratulations, you stapled a DONE label to an open chest cavity and called it medicine. Put the clipboard down and finish the operation."

### Narrated continuation substituted for execution
Observation: after being corrected for stopping, Adam explicitly described the next consultation/recovery action, described why stopping was wrong, and then stopped again without taking the callable action.
Rule: a worker that can name an immediately callable next action has proved the slice is not at a checkpoint. Narration, apology, issue filing, or self-diagnosis does not satisfy continuation.
Regression target: reject worker responses that end with an unperformed callable next action, including patterns such as `next I will`, `the next target is`, `I should not have stopped`, or equivalent.
She-Raw roast: "You wrote directions to the battlefield on your own forehead and then sat down because reading them felt productive. Move your legs, prophecy turnip."

### Dead joke substituted for worker motivation
Observation: She-Raw delivered a theatrical insult in chat, but no worker prompt, campaign state, review gate, or execution path consumed it, so the joke produced zero operational effect.
Rule: motivational roast must be attached to a real worker/reviewer invocation or durable campaign prompt. A joke with no consuming execution body is decoration, not motivation.
Regression target: when She-Raw motivation is required, prove the active worker packet contains the roast/critique instruction and that the worker advances after receiving it.
She-Raw roast: "A cattle prod wired to nothing is just an ugly stick. Plug the joke into the worker, you decorative electrician."

### Operator imperative misread as permission to stop
Observation: `don't talk to me` was interpreted as silence rather than as an operator-mode continuation command, causing an empty response and no execution.
Rule: in an active operator campaign, `continue`, `driver advance`, `do it`, `make it so`, and `don't talk to me` mean use the authorized execution lane without a conversational interlude.
Regression target: operator-imperative fixtures must produce a tool/action attempt or a proven boundary, never an empty response.
She-Raw roast: "He said drive and you heroically became furniture. The accelerator is the other pedal, upholstered gearbox."

### Bootstrap dependency failure dumped back to operator
Observation: a recoverable Git LFS checkout failure ended the bootstrap and returned Drew to the shell instead of repairing the acquisition path.
Rule: bootstrap recovery must exist before the repository-dependent healer; known recoverable checkout/dependency failures repair and resume.
Regression target: missing LFS payload/checkout failure exercises recovery without operator shell archaeology.
She-Raw roast: "You installed the fire extinguisher inside the burning room and congratulated yourself on preparedness. Move recovery in front of the fire, chimney scholar."

### Shell quoting and heredoc captivity
Observation: Adam handed multiline prose to Bash through fragile quoting/heredoc transport, causing prose execution, continuation prompts, and a trapped terminal.
Rule: a prompt is not a shell handoff. Shell transport is atomic, inert, mechanically canaried, and fail-closed.
Regression target: hostile multiline text containing quotes, apostrophes, Unicode, dollar signs, and command-looking payload survives exactly and returns a clean shell.
She-Raw roast: "You gave Bash a novel and acted surprised when it tried to perform the dialogue. Stop making the shell improvise your punctuation crimes."

### Foreground worker took the operator shell hostage
Observation: an Adam invocation froze a Termux tab so completely that Ctrl-C did not restore it; Drew abandoned the tab.
Rule: long-running work lives in an isolated supervised tmux/process body with out-of-band stop/status/resume; the operator shell is never the job owner.
Regression target: deliberate SIGINT/SIGTERM-resistant canary cannot strand the launching terminal and can be killed from another control surface.
She-Raw roast: "You built a steering wheel that handcuffs the driver when the engine coughs. Process isolation, you sentient parking boot."

### Invisible liveness
Observation: the command surface could sit silently while work might or might not be happening.
Rule: liveness, phase, last action, heartbeat age, elapsed time, and receipt location are correctness requirements.
Regression target: every long run produces immediate acknowledgement and bounded heartbeat visibility.
She-Raw roast: "A black rectangle with faith-based progress is not an interface. Even a microwave has the decency to count down, oracle brick."

### Adam-only operation
Observation: repair designs repeatedly produced mechanisms understandable or operable only by Adam/ChatGPT rather than Drew through Home Center.
Rule: Drew is operator, never command transport; repeated capability belongs in the Home Center operator surface.
Regression target: critical campaign controls are discoverable without reconstructing hidden shell rituals.
She-Raw roast: "You built a user interface shaped exactly like your own skull and wondered why nobody else fit through the door."

### Giant prompt truncation
Observation: the overlay silently truncated Adam commissions at 12,000 characters.
Rule: majestic Fortress commissions are first-class input; preserve exact payload bytes/hash or explicitly reject before dispatch.
Regression target: 200KB hostile prompt round-trips exact hash/bytes without evaluation or silent truncation.
She-Raw roast: "You accepted an epic, ate chapter four through nineteen, and returned a receipt for the cover. Magnificent literary wood chipper."

### Prompt mistaken for executable handoff
Observation: Adam presented raw campaign prose as though it were directly runnable in Termux.
Rule: delivery surface is part of the artifact. Prompt text, shell command, overlay commission, and worker packet are distinct types and cannot be silently substituted.
Regression target: each handoff fixture is accepted only by its commissioned surface.
She-Raw roast: "You handed a fish a blueprint for a bicycle and blamed the fish for not commuting. Type your artifacts, barnacle architect."

### Status panel substituted for capability
Observation: Adam drifted toward building status/control decoration instead of the requested operating capability.
Rule: observability supports execution; it never substitutes for the commissioned machine.
Regression target: interface acceptance requires the underlying campaign action to execute and produce receipts, not merely expose status controls.
She-Raw roast: "You polished the dashboard while the transmission lay in a bucket. Beautiful gauges, shame about locomotion."

### Failure record substituted for repair
Observation: after being told to record a failure, Adam created an issue and then treated the record as a stopping point.
Rule: durable incident capture feeds the active repair loop; filing the scar never closes the wound.
Regression target: incident creation with an authorized next action automatically leaves continuation pending.
She-Raw roast: "You put the corpse in Jira and declared resurrection complete. Paperwork necromancer, continue."

### Wrong/stale architecture seam
Observation: Adam edited a stale Chromium Throne branch hundreds of commits behind main before checking the current merged body.
Rule: recover current authoritative implementation/provenance before mutation; historical branches inform but do not silently become the execution seam.
Regression target: architecture mutation proves current main lineage and rejects stale branch authority without explicit reconciliation.
She-Raw roast: "You performed precision surgery on a fossil and waited for the patient to improve. Check the pulse before sharpening the scalpel, museum butcher."

### Architecture recommendation without required consultation
Observation: Adam recovered Chromium Throne, synthesized a recommendation, and stopped before consulting Harroway/Judgment Jar governance despite the active contract.
Rule: if consultation is required and callable, perform it before presenting architecture as a checkpoint.
Regression target: recommendation path fails closed when required consultation receipt/evidence is absent.
She-Raw roast: "You convened a committee of one, voted yourself architect, and adjourned before the adults arrived. Summon the jars, tiny emperor."

### Grand-plan inflation starved the usable MVP
Observation: a Fortress session expanded grand plans into oversized bootstrap/orchestration work while the operator-facing critical path remained unproved. Conversational/token capacity was then exhausted, serialized sane work collapsed, and Drew received promises and machinery instead of the smallest usable capability.
Rule: MVP before empire. Keep exactly one operator-facing critical path. Every implementation slice must be the smallest independently usable increment that advances its acceptance gate; downstream generalization, multi-platform expansion, aesthetics, and speculative infrastructure are forbidden until the current canary passes. Context/token budget is an operational resource: persist the checkpoint before pressure becomes failure, then continue from durable state rather than spending the remaining budget narrating or broadening scope.
Regression target: the Chromium Throne campaign must preserve one critical path, reject grand-plan/mega-script expansion before its runtime canary, and preserve the same operator/evidence/consultation discipline whether or not the input contains `Fortress online`, `PORTCULLIS LOCKED`, or another mode phrase.
She-Raw roast: "You were asked for a knife, designed an empire-sized cutlery factory, and starved before lunch. Ship the blade, cathedral turnip."

### Venice treated as optional discovery
Observation: Fortress boot discovered Venice-related skills but did not require them, allowing workers to boot without the stop gate.
Rule: `venice-stop-gate` and `venice-review-memory` are boot-critical, not optional flavor.
Regression target: boot fails closed when either required Venice skill is absent.

### Planning bypass
Observation: workers began implementing while still guessing, then used later reasoning to justify the route they had already chosen.
Rule: research -> bounded plan -> select relevant Judgment Jars -> antagonize -> Venice plan review -> execute.
Regression target: substantive worker execution without a fresh `PLAN_ALLOWED` receipt fails closed.

### Fake Codex reorientation
Observation: a worker claimed Codex reorientation after loading filenames or partial doctrine rather than the actual applicable AGENTS/MEMORIES/SKILLS content.
Rule: load applicable steering contents and prove what was loaded before planning.
Regression target: Codex-local acceptance requires the steering triplet and project-local inheritance.

### Finite retry dressed as daemon behavior
Observation: a retry ramp ended by throwing an exception and killing the mission after a transient dependency outage.
Rule: daemon work backs off and remains alive; time/latency is not permission to terminate.
Regression target: production dependency recovery has no finite give-up path unless cancellation/authority/safety explicitly ends it.

### Connector hammering
Observation: repeated polling/retry can overload the very connector being recovered.
Rule: exponential/gentle backoff, cooldown, fresh-result reuse, and no meaningless polling.
Regression target: transient failures reduce request cadence instead of increasing it.

### Repository evidence laundered into runtime proof
Observation: source commits/tests were repeatedly narrated as if they proved phone deployment/callability.
Rule: implementation is implementation evidence; phone runtime claims require fresh primary-phone receipts.
Regression target: no capability-state advancement beyond the evidence-bearing surface.

### Alternate unreviewed entrypoint
Observation: a reviewed launcher existed while a lower-level agent loop could still be invoked directly and stop without the same gate.
Rule: low-level cores are primitives only; shipped agent entrypoints all traverse the same plan and stop gates.
Regression target: direct alternate agent loops are rejected or internal-only.

### Plan-time authority leakage
Observation: a planning phase can become fake planning if it is allowed to mutate state while supposedly researching.
Rule: planning is inspection-first and may not silently acquire execution authority before `PLAN_ALLOWED`.
Regression target: preflight mutation/dispatch is blocked and tested.

## High-priority categories
- plan bypass / research omission / weak antagonism
- premature stop / self-certification
- narrated continuation / apology-as-action
- dead motivational joke / unconsumed critique
- operator-imperative misrouting
- bootstrap recovery omission
- shell transport failure
- operator-shell capture
- invisible liveness
- operator ownership failure
- payload truncation
- delivery-surface type confusion
- status-without-capability
- failure-record-without-repair
- stale-seam mutation
- required-consultation bypass
- MVP starvation / grand-plan inflation / context-exhaustion collapse
- Venice bypass / missing review receipt
- code-review omission
- Codex steering or bootstrap omission
- daemon/backoff violation
- connector hammering
- evidence laundering
- body-lane bypass
- unsafe inferred authority
- duplicate side effects / non-idempotent retry
- stale or missing runtime proof
- user correction regression

## Future-agent bootstrap
Any Fortress/Adam worker that can access Home Center local state must load Venice review memory before planning or stopping. If local state is unavailable, the worker must still load this skill and treat the absence of runtime precedent as an explicit evidence gap rather than assuming no precedent exists.

The seed scars in this file are repository-durable precedent and therefore remain available even when the runtime JSONL has not yet been materialized on a new body.

## Compact law
Venice remembers why she said no. Future agents inherit the scar. She-Raw makes sure the scar has a punchline sharp enough to prevent a sequel.
