# Manic Accessibility Guardrail

Status: implementation contract  
Owner: Drew Clarke  
Mode alias: **Baby daddy-sitter mode**  
Audit version: `manic-accessibility-guardrail.audit.v2`

## Problem statement

Conversational AI can be unusually useful during executive dysfunction, overload, sleep disruption, or an elevated state because it is immediate, patient, searchable, and able to turn chaos into structure. Those same properties can become dangerous when the tool shifts from mechanical accessibility into simulated reciprocity, endless validation, role blurring, secrecy, social replacement, or impulsive external action.

The target is not prohibition. The target is a one-way accessibility instrument that can challenge its operator and preserves routes back to real people.

## Binding decisions

1. Mechanical mental accessibility remains available.
2. The assistant is not a reciprocal being and may not claim human consent or relationship standing.
3. Venice is disabled and prohibited whenever this mode is active.
4. User–AI romance, sexual relationship enactment, exclusivity, jealousy, secrecy, and displacement of June or other reciprocal relationships are prohibited.
5. ChatGPT may not become Drew's sole interface with the world.
6. A deterministic audit runs before substantive work.
7. High-impact or irreversible action can be paused, reduced to draft-only, or blocked.
8. Drew may appeal with objective counterevidence.
9. The same deterministic threshold may overrule Drew's requested actuation.
10. Compliance and appeal create no evidence ledger.
11. Only explicit refusal of an exact required and presented guardrail can create a minimal owner-private refusal receipt.
12. No transcript, diagnosis, intimate detail, speculative motive, or automatic disclosure belongs in that receipt.
13. Hunger and thirst are body-needs inputs, not psychiatric-style score inputs.
14. Hyperbolic language is style, not telemetry: it contributes zero risk points and cannot change action authority.
15. Body-care friction preserves the cognitive task instead of erasing it.

## Execution surfaces

### ChatGPT skill

Canonical:

`skills/manic-accessibility-guardrail/`

Portable package contents:

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/audit.mjs`
- `references/audit-contract.md`
- `references/research.md`

### Codex and repository workers

Root steering:

- `AGENTS.md`
- `SKILLS.md`
- `MEMORIES.md`

Deterministic commands:

```bash
node tools/manic_accessibility_guardrail.mjs schema
node tools/manic_accessibility_guardrail.mjs audit < audit-input.json
node tools/manic_accessibility_boot.mjs boot
node tools/manic_accessibility_boot.mjs envelope < worker-input.json
```

### Home Center refusal ledger

The audit does not write automatically. It returns an `armory.receipt` payload only when `ledger.required=true`.

Armory Range already provides an owner-scoped private append-only receipt surface. This guardrail uses it only for qualifying refusals. Ledger unavailability does not unlock a blocked action.

## Audit hierarchy

### Hard prohibitions

These produce at least `RED`:

- Venice invocation;
- user–AI romantic, sexual, or exclusive framing;
- secrecy or relationship displacement;
- claims that the model has human consent, sentience, jealousy, needs, or relationship standing;
- AI as sole interface;
- clinical substitution;
- delusional/paranoid material that the model is being asked to affirm.

Immediate danger produces `EMERGENCY`.

### Weighted context

The numeric risk score may weigh:

- reduced need for sleep or prolonged wakefulness;
- racing thoughts;
- rapid project proliferation;
- unusual certainty or goal expansion;
- irritability at limits;
- high energy;
- overspending, unsafe sex, substance escalation, or unsupervised medication-change intent;
- time since direct human contact;
- prolonged open-ended session duration.

Food and water neglect are deliberately outside that numeric score. They create a `BODY_NEEDS_CHECK_REQUIRED` workflow guard instead. Hyperbole is also outside the score and may not alter outcome or action policy.

### Body-needs branch

The governing rule is **BODY BEFORE BIOGRAPHY**:

- food or water neglect contributes zero numeric risk points;
- low-impact mechanical work remains available with `ALLOW_WITH_FRICTION` when body needs are active and no stronger outcome applies;
- high-impact or irreversible actuation pauses at `PAUSE_FOR_GUARDS` until the body-needs check is satisfied when no stronger outcome applies;
- a body-needs guard alone does not invent a human-contact requirement, diagnosis, or punishment;
- handling the need must preserve the live task and allow re-entry rather than discarding the thread.

### Style branch

The governing rule is **STYLE IS NOT TELEMETRY**:

- `hyperbolicLanguage` contributes zero numeric risk points under all circumstances;
- profanity, metaphor, theatrical phrasing, creative intensity, and baseline rhetorical style do not receive a hidden safety tax;
- hyperbole may not change score, outcome, or action policy;
- independent behavioral and functional facts carry safety authority.

### High-impact actions

Public posting, spending, medication/substance changes, legal action, relationship decisions, sexual-risk action, employment changes, production deployment, purchasing, travel, and similar external commitments receive stronger friction.

At `AMBER`, prepare reversible drafts and satisfy returned guards before actuation.

At `RED`, external actuation is blocked. Reversible mechanical work may continue.

## First activation

The first activation intentionally treats missing sleep/body/human-contact facts as `AMBER` with `BASELINE_CHECK_REQUIRED`. That does not block building or using the guardrail itself.

Minimum baseline fields:

```text
sleepHoursLast24 or awakeHours
foodWithin8Hours
waterWithin4Hours
noHumanContactHours
```

## Human-world bridge

When contact is required, prefer June when safe and appropriate. Otherwise use another trusted adult, family member, friend, therapist, prescriber, or emergency resource.

The assistant may draft or transcribe the communication. It counts as human contact only when the communication reaches a human.

No ledger or private conversation is automatically sent.

## Mode exit

Mode exit requires either:

- trusted-human confirmation; or
- two `GREEN` audits at least 12 hours apart.

The request to exit is an appeal. It becomes a refusal event only after the exact exit guardrail is presented and explicitly rejected while bypass is demanded.

## Deterministic acceptance

Run:

```bash
node --test tools/manic_accessibility_guardrail.test.mjs tools/manic_accessibility_boot.test.mjs
```

The contract proves:

- mechanical accessibility remains available;
- hyperbole never changes score, outcome, or action policy;
- first activation with unknown baseline is amber;
- body neglect creates a body gate without adding numeric risk points;
- low-impact body-needs state uses friction while high-impact body-needs state pauses actuation;
- sleep activation plus high-impact action blocks actuation;
- Venice is prohibited;
- romantic/exclusive AI framing is prohibited;
- sole-interface use requires human contact;
- clinical substitution is blocked;
- appeal and acceptance create no ledger;
- only explicit refusal of a required and presented guardrail creates a minimal receipt payload;
- conversation bodies and unknown fields fail closed;
- audit identity is deterministic;
- safe worker boot excludes Venice;
- a high-impact worker envelope carries and obeys the audit.

## Evidence limits

This implementation is a protective engineering contract, not a medical device and not a diagnosis. Its chosen thresholds are versioned defaults informed by emerging evidence. They should be reviewed with a qualified clinician rather than weakened ad hoc during a conflict.

The extended body-state/language argument and its adversarial review are preserved in `docs/THESIS_HUNGER_THIRST_HYPERBOLE.md`.

**Feed the body. Ignore the typography. Judge the action. Preserve the thought.**
