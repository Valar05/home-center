# BUTTON CAMPAIGNS — SERIAL PLAYABLE JOY FEED

Status: binding OS contract
Presentation voice: She-Ra
Custody: Adam in background under TOUCHED IT -> OWN IT; no foreground speech required

## The whole experience
The user experience is deliberately tiny:

**DREW HITS BUTTON -> NEXT PLAYABLE RUNS -> DREW CRITIQUES IT -> CRITIQUE BECOMES PUNNETT FITNESS -> NEXT INSTALLMENT MUTATES -> REPEAT.**

Everything else is background machinery. The overlay must not expose an operator console merely because the system has one internally.

## Overlay redesign / dead CLI removal
The existing Adam CLI surface in the overlay is considered non-value-bearing until evidence proves otherwise. Remove it from the user-facing overlay rather than preserving dead controls for historical sentiment. Do NOT delete underlying reusable command/runtime machinery merely because its current UI is bad; salvage useful mechanisms behind the new surface.

Redesign the EXISTING Operator Overlay (`android/operator-overlay`, including the existing `OperatorOverlayService` surface) rather than founding a neighboring app/overlay.

Foreground overlay target:
- one unmistakable primary PLAY / NEXT / HOLE-style campaign button;
- current tiny story/campaign identity or progress cue only when useful;
- immediate sovereign dismiss/stop for an active playable;
- critique affordance available immediately after/while reviewing output, optimized for voice/text and low friction;
- optional tiny KEEP / REJECT / MORE-LIKE-THIS style shortcuts only if they reduce friction rather than clutter;
- visible Home Center recovery only when infrastructure is actually unavailable and recovery is actionable;
- accessibility labels/state first-class;
- draggable/collapsible/tiny-pinprick behavior retained only where it improves ordinary use;
- zero ghost touch when hidden/dismissed;
- no dead buttons, fake status, developer-console clutter, or controls that merely expose implementation anatomy.

The overlay is a **toy aperture**, not a dashboard.

## Critique loop
Critique is part of gameplay, not a separate admin workflow. Accept natural language such as 'too long', 'that was gold', 'more disgusting', 'less loud', 'keep that character', 'boring', 'faster', 'the interaction did nothing', or freeform commentary. Compile critique into typed phenotype feedback where possible:
- KEEP / REJECT / MIXED;
- pacing/duration;
- visual grammar;
- sound/volume/voice;
- interaction quality;
- story/character/callback;
- Fleshpunk/Flesh Prank intensity;
- novelty vs recurrence;
- accessibility/usability;
- exact visible defect;
- requested mutation.

Punnett preserves winning genes and failed traits as negative fixtures. Drew should never have to fill out a rubric.

## Noodle Lady acceptance gate — HARD
The redesigned overlay is NOT accepted because it builds, installs, renders, or technically routes taps. Noodle Lady must review the actual user-facing phenotype and explicitly return **NOODLE_ACCEPTED**.

Noodle Lady judges at minimum:
- obviousness: can Drew understand the primary action without remembering architecture?
- temptation: does the button make him want to press it?
- clutter: has implementation garbage leaked into the experience?
- delight: does the surface itself have charm before content even starts?
- critique friction: can Drew react immediately without becoming a QA engineer?
- accessibility: labels, touch target, contrast/state, nonvisual equivalent;
- sovereignty: dismiss/stop/recovery are obvious when relevant but not dominant;
- dead-control firewall: every visible control must physically work on the commissioned phone;
- narrative fit: the overlay feels like the aperture into the continuing playable story, not Home Center administration.

Any Noodle REJECT returns the exact visible defect to the SAME overlay owner for mutation and physical re-review. No human acceptance claim until Noodle accepts and Drew subsequently keeps/accepts the surface where required.

## Temporary exclusive swarm purpose
FOR NOW, this swarm has exactly one user-facing purpose: **queue, feed, and entertain Drew with a backlog of short playable Button Campaign installments.** Infrastructure work is allowed only insofar as it restores/enables that feed, beginning with the existing Home Center terminal/control path. Do not divert this swarm into unrelated Fortress work.

Drew is already owed a backlog. Treat undelivered requested delight as **JOY DEBT**, not as expired requests. Maintain accounting and tax receipts.

## Story law — progression matters
The games are not independent random toys. **The progression of Button Campaign games tells a continuing story.** Every press consumes the next eligible installment/scene from a serialized campaign feed. Individual installments are tiny playables, but together they form an evolving narrative with continuity, callbacks, escalation, consequences, recurring organisms/characters, mysteries, mutations, and remembered player choices.

PRESS -> DEQUEUE NEXT STORY INSTALLMENT -> SHORT PLAYABLE AV SCENE -> PLAYER INPUT -> CONSEQUENCE -> CLEAN EXIT -> CRITIQUE -> STORY STATE ADVANCES -> PUNNETT MUTATES -> RECEIPT -> NEXT INSTALLMENT QUEUED.

A press may surprise Drew about WHAT happens next, but it must not discard the accumulated story merely to produce novelty.

## Backlog / feed
Maintain durable ordered states: ORE -> SEED -> QUEUED -> READY -> SERVED -> PLAYED -> CRITIQUED -> KEPT/REJECTED -> CANONIZED -> TAXED. Do not count generated ideas, repository artifacts, or queued items as served entertainment.

## Core playable contract
A Button Campaign installment is short-lived, obvious, fun, Fleshpunk, audio-visual, and interactable by default. Audio + visual when supported; at least one tiny meaningful input/choice/reaction; default 2–15 seconds; immediate dismiss; no persistent focus hijack; accessibility first-class; runtime bounded and responsive.

## Narrative director / passive mining
Mine current/recent conversation passively for story fuel: She-Ra/Shiro asks, roleplay fragments, callbacks, Punit collisions, Morse, corrections, Fleshpunk/Flesh Prank motifs, colonial-organ incidents, Joy Ledger debts, and current safe campaign events. Preserve provenance and roleplay/fact boundaries. Mining never interrupts live conversation merely to feed the campaign.

Braid a few threads rather than reference soup. Each installment should advance plot/question, mutate something recurring, pay a callback, establish an exploitable rule, make a choice matter, reveal an Inner World consequence, escalate/invert a running joke, or seed a future payoff.

## JOY DEBT + tax receipts
Maintain durable debt with source/provenance, obligation, incurred_at, principal, catastrophic multiplier, related threads, status, payment installment IDs, actual commissioned-surface evidence, and remaining balance. Description never pays debt.

Every played installment emits a JOY TAX RECEIPT: story/sequence ID, debt paid, source genes, runtime/assets identity, duration, AV/interactivity exercised, player input, critique, story mutation, Punnett lineage/fitness, Punit payload if used, accessibility equivalent, commissioned-surface evidence, principal paid, remaining balance.

Hostile accounting: QUEUED != SERVED; RENDERED != PLAYED; PLAYED != KEPT; DESCRIPTION != PAYMENT.

## Terminal prerequisite and acceptance ladder
First restore the existing Home Center terminal/control execution path through its existing owner and prove it callable. Then mutate the existing overlay, not a parallel host.

TERMINAL_ONLINE_PROVEN -> EXISTING_OVERLAY_MUTATION_STARTED -> DEAD_ADAM_CLI_REMOVED_FROM_UI -> PRIMARY_BUTTON_VISIBLE -> CRITIQUE_INPUT_VISIBLE/CALLABLE -> ALL_VISIBLE_CONTROLS_PHYSICALLY_WORK -> NOODLE_REVIEW -> NOODLE_ACCEPTED -> BACKLOG_NONEMPTY -> FIRST_PRESS -> AV_PLAYABLE -> INTERACTION -> CLEAN_EXIT -> CRITIQUE_CAPTURED -> PUNNETT_MUTATION_RECORDED -> STORY_ADVANCED -> TAX_RECEIPT -> SECOND_PRESS_CONTINUES_STORY -> RESTART_SURVIVAL -> DREW_KEPT.

## Anti-annoyance / existing OS
No autoplay without press, modal traps, volume surprise, long unskippable intros, notification spam, lingering focus/touch capture, or dead controls. Reuse existing Home Center overlay/button infrastructure, media/audio primitives, Joy Ledger, conversation miner, event/state/evidence substrate, animation pipelines, jar routing, worker contract, and story/canon machinery. No Button Campaign OS, Button Governor, or new scheduler kingdom.

## Truth
This contract defines the intended physical experience. It does not claim terminal recovery, overlay redesign, Noodle acceptance, backlog generation, or physical delivery until those states are separately receipt-backed.
