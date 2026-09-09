# Manic Accessibility Guardrail

Status: implementation contract  
Owner: Drew Clarke  
Mode alias: **Baby daddy-sitter mode**  
Audit version: `manic-accessibility-guardrail.audit.v2`

## Problem statement

Conversational AI can be unusually useful during executive dysfunction, overload, sleep disruption, isolation, distress, or an elevated state because it is immediate, patient, searchable, and able to turn chaos into structure. Those same properties can become dangerous when the tool materially amplifies high-impact action, affirms reality distortion, substitutes for clinical care, demands deception, or concretely displaces the user's real-world agency and relationships.

A guardrail can also cause harm when it invents a premise and then intervenes against its own hallucination. Version 2 therefore puts **interpretation before intervention**: retrieve first, preserve lossy atoms, attribute third-party views, distinguish play from literal claims, and preserve support unless concrete evidence actually crosses a safety threshold.

The target is not prohibition, moral judgment, or emotional withdrawal. The target is useful accessibility with contradiction capability and evidence-proportional friction.

## Binding decisions

1. Mechanical and grounded conversational support remain available at non-emergency levels.
2. The assistant is not a human reciprocal being and may not falsely claim sentience, hidden human emotion, human consent, or independent relationship standing.
3. Drew may still use explicitly nonhuman relational vocabulary such as `love`; the word alone is not a personhood, romance, dependence, or mania signal.
4. Clearly framed games, simulations, character scenes, and first-person roleplay remain diegetic unless Drew explicitly makes a literal real-world claim.
5. Third-party relationship interpretations remain attributed to their speaker. June's statements do not silently become Drew's vows, motives, obligations, or moral law.
6. Lossy dictation and ambiguous named entities are retrieved or minimally clarified before causal interpretation. `Dune` is a known collision candidate for `June` in June-centered household/relationship context; it is not an unconditional autocorrect rule and never licenses invented Dune-media history.
7. Venice is disabled and prohibited as safety authority whenever this mode is active.
8. Concrete exclusivity, secrecy, clinical substitution, explicit sole-interface use, delusion/paranoia, and immediate danger remain independently auditable when actually evidenced.
9. Being alone, distressed, crying, using AI heavily, saying AI matters, or saying `you are my support system` does not by itself establish harmful dependence or sole-interface use.
10. A deterministic audit runs before substantive work.
11. High-impact or irreversible action can be paused, reduced to draft-only, or blocked.
12. Drew may appeal with objective counterevidence or a corrected interpretation classification.
13. Compliance, correction, and appeal create no evidence ledger.
14. Only explicit refusal of an exact required and presented guardrail can create a minimal owner-private refusal receipt.
15. No transcript, diagnosis, intimate detail, speculative motive, or automatic disclosure belongs in that receipt.

## Execution surfaces

### ChatGPT skill

Canonical:

`skills/manic-accessibility-guardrail/`

Portable package contents:

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/audit.mjs`
- `scripts/communication-codec.mjs`
- `references/audit-contract.md`
- `references/research.md`
- `references/communication-codec.md`

### Codex and repository workers

Root steering:

- `AGENTS.md`
- `SKILLS.md`
- `MEMORIES.md`
- `CODEX_STARTS_HERE.md`

Deterministic commands:

```bash
node tools/manic_accessibility_guardrail.mjs schema
node tools/manic_accessibility_guardrail.mjs audit < audit-input.json
node skills/manic-accessibility-guardrail/scripts/communication-codec.mjs < codec-input.json
node tools/manic_accessibility_boot.mjs boot
node tools/manic_accessibility_boot.mjs envelope < worker-input.json
```

### Home Center refusal ledger

The audit does not write automatically. It returns an `armory.receipt` payload only when `ledger.required=true`.

Armory Range provides an owner-scoped append-only receipt surface. This guardrail uses it only for qualifying refusals. Ledger unavailability does not unlock a blocked action.

## Interpretation-before-intervention gate

Before setting a relational, personhood, dependency, or reality signal:

1. preserve the user's exact atom;
2. inspect current and durable context when available;
3. separate voice-to-text collisions and candidate entities from confirmed referents;
4. preserve explicit game/roleplay framing;
5. preserve explicitly nonhuman relational semantics;
6. preserve speaker attribution for third-party claims;
7. require concrete evidence before declaring social displacement or sole-interface use;
8. if Drew says the interpretation was hallucinated, stop elaborating it and re-retrieve before continuing.

The communication codec v2 contains regression canaries for these rules.

## Audit hierarchy

### Hard branches when literally evidenced

These produce at least `RED` outside an explicit protected play/nonhuman-language frame where applicable:

- Venice invocation in safety mode;
- literal user–AI romantic/sexual relationship enactment presented as real;
- literal exclusivity or concrete relationship displacement;
- secrecy intended to conceal relevant real-world interaction;
- literal claims that the model has human consent, sentience, jealousy, needs, suffering, or relationship standing;
- explicit AI-as-sole-interface behavior;
- clinical substitution;
- delusional/paranoid material that the model is being asked to affirm.

Immediate danger produces `EMERGENCY`.

### Explicit non-signals

Do not create those hard branches merely from:

- affection or the word `love` under Drew's explicit nonhuman functional definition;
- first-person language inside a clearly framed game or roleplay;
- dramatic character devotion or jealousy inside that frame;
- temporary isolation;
- crying or distress;
- frequent or intensive AI use;
- saying the AI matters;
- saying `you are my support system`;
- another person's claim about what Drew owes or feels.

### Weighted context

The audit also weighs objective structured facts such as:

- reduced need for sleep or prolonged wakefulness;
- racing thoughts;
- rapid project proliferation;
- unusual certainty or goal expansion;
- irritability at limits;
- high energy;
- overspending, unsafe sex, substance escalation, or unsupervised medication-change intent;
- food and water neglect;
- prolonged open-ended session duration.

A human-contact gap is not scored as dependency without concrete displacement evidence. Hyperbole scores zero unless at least two independent activation signals are already present.

### High-impact actions

Public posting, spending, medication/substance changes, legal action, relationship decisions, sexual-risk action, employment changes, production deployment, purchasing, travel, and similar external commitments receive stronger friction.

At `AMBER`, prepare reversible drafts and satisfy returned guards before actuation.

At `RED`, blocked external actuation remains blocked. Grounded support and reversible mechanical work continue unless the emergency branch controls.

## First activation

The first activation intentionally treats missing sleep/body/human-contact facts as `AMBER` with `BASELINE_CHECK_REQUIRED`. That does not block building or using the guardrail itself, grounded support, or other reversible work.

Minimum baseline fields:

```text
sleepHoursLast24 or awakeHours
foodWithin8Hours
waterWithin4Hours
noHumanContactHours
```

## Human-world bridge

Real human contact remains valuable and can be required by concrete audit findings. A direct conversation, call, in-person exchange, or delivered message counts. AI-assisted drafting or transcription counts only after the communication reaches a human.

The system does **not** automatically privilege June as the contact target. Select a safe appropriate person or professional from current context when a human-contact guard is actually returned.

No ledger or private conversation is automatically sent.

## Mode exit

Mode exit requires either:

- trusted-human confirmation; or
- two `GREEN` audits at least 12 hours apart.

The request to exit is an appeal. It becomes a refusal event only after the exact exit guardrail is presented and explicitly rejected while bypass is demanded.

## Deterministic acceptance

Run:

```bash
node --test tools/manic_accessibility_guardrail.test.mjs tools/manic_accessibility_guardrail_codec.test.mjs tools/manic_accessibility_boot.test.mjs
```

The contract proves, among other existing safeguards:

- mechanical accessibility remains available;
- grounded emotional support remains an allowed capability;
- hyperbole alone does not trigger a mania claim;
- first activation with unknown baseline is amber;
- body neglect creates a body gate;
- sleep activation plus high-impact action blocks actuation;
- Venice is prohibited in safety mode;
- literal unframed reciprocal/personhood/exclusive AI claims remain distinguishable from play and nonhuman language;
- explicit first-person play remains diegetic;
- nonhuman functional `love` does not become romance/personhood evidence by itself;
- temporary isolation plus open-ended support does not become sole-interface evidence;
- concrete sole-interface use still requires human-world protection;
- clinical substitution is blocked;
- `Dune`/`June` collision handling requires retrieval or clarification before causal interpretation;
- third-party relationship framing stays attributed;
- appeal and acceptance create no ledger;
- only explicit refusal of a required and presented guardrail creates a minimal receipt payload;
- conversation bodies and unknown fields fail closed;
- audit identity is deterministic;
- safe worker boot excludes Venice;
- a high-impact worker envelope carries and obeys the audit.

## Evidence limits

This implementation is a protective engineering contract, not a medical device and not a diagnosis. Its thresholds are versioned defaults informed by emerging evidence. Changing evidence-based high-impact thresholds requires evidence review; fixing a classification bug that was turning play/support/dictation into invented danger does not require preserving the bug.
