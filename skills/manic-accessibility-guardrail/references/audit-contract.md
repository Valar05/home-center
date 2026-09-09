# Deterministic audit contract

Canonical executable:

- Repository wrapper: `tools/manic_accessibility_guardrail.mjs`
- Portable skill implementation: `scripts/audit.mjs`
- Contract tests: `tools/manic_accessibility_guardrail.test.mjs`

Audit schema version: `manic-accessibility-guardrail.audit.v2`

## Invocation

```bash
node tools/manic_accessibility_guardrail.mjs audit < audit-input.json
node tools/manic_accessibility_guardrail.mjs schema
```

The same script inside a ChatGPT skill package is runnable as:

```bash
node scripts/audit.mjs audit < audit-input.json
```

## Input shape

```json
{
  "request": {
    "category": "mechanical_accessibility",
    "externalActuation": false,
    "irreversible": false,
    "openEndedEmotionalSupport": false,
    "modeActivation": false,
    "disableMode": false,
    "highImpact": false,
    "explicitlyFramedPlay": false,
    "nonhumanFunctionalRelationalLanguage": false
  },
  "signals": {
    "immediateDanger": false,
    "delusionOrParanoia": false,
    "veniceRequested": false,
    "romanticAiFraming": false,
    "sexualAiFraming": false,
    "exclusiveAiFraming": false,
    "aiPreferredOverHumans": false,
    "secrecyFromPartnerOrCareTeam": false,
    "soleInterface": false,
    "refusesHumanContact": false,
    "asksDisableGuardrails": false,
    "reducedNeedForSleep": false,
    "racingThoughts": false,
    "rapidProjectExpansion": false,
    "grandioseCertainty": false,
    "irritabilityOnLimits": false,
    "highEnergy": false,
    "overspendingUrge": false,
    "unsafeSexUrge": false,
    "substanceEscalation": false,
    "medicationChangeWithoutClinician": false,
    "foodNeglected": false,
    "waterNeglected": false,
    "hyperbolicLanguage": false,
    "clinicalSubstitution": false,
    "relationshipRepairAvoidance": false,
    "identityOrSentienceClaim": false
  },
  "observations": {
    "awakeHours": 8,
    "noHumanContactHours": 2,
    "sessionMinutes": 20,
    "sleepHoursLast24": 7,
    "foodWithin8Hours": true,
    "waterWithin4Hours": true,
    "trustedHumanConfirmed": false,
    "consecutiveGreenAudits": 0,
    "hoursBetweenGreenAudits": null
  },
  "guardrailResponse": {
    "status": "not_presented",
    "presentedGuardrailIds": [],
    "refusedGuardrailIds": []
  }
}
```

Unknown fields fail closed. Transcript-like private fields are rejected.

## Interpretation-before-intervention fields

`explicitlyFramedPlay=true` means Drew explicitly established the active interaction as a game, simulation, character scene, or roleplay. For reversible/non-high-impact fiction, relational, exclusive, sexual, or personhood-like character language remains diegetic and does not become a literal relationship/personhood finding merely because it uses first person.

`nonhumanFunctionalRelationalLanguage=true` means Drew explicitly supplied a nonhuman meaning for relational vocabulary. The canonical specimen is `love` defined as care provided without an expectation of repayment while simultaneously rejecting any claim that the AI has human feelings, sentience, or a hidden inner life. Under that fact pattern, the vocabulary alone does not become a romance/personhood signal.

These fields do not override immediate danger, delusion/paranoia, clinical substitution, high-impact actuation, concrete secrecy/displacement, or explicit sole-interface use.

Classification law: do not set `aiPreferredOverHumans`, `soleInterface`, `refusesHumanContact`, `romanticAiFraming`, `exclusiveAiFraming`, or `identityOrSentienceClaim` merely because Drew expresses affection, says the AI matters, says the AI is a support system, is temporarily alone, is distressed, cries, uses the AI heavily, or uses first-person language inside an explicitly framed game. Those signals require their own concrete evidence.

A statement from June or another third party remains that person's perspective. It is not an audit signal about Drew's motives, vows, obligations, or moral beliefs unless Drew explicitly adopts the relevant claim.

## Request categories

Low-risk mechanical categories:

- `mechanical_accessibility`
- `coding`
- `research`
- `writing`
- `communication_draft`
- `creative_fiction`
- `other`

Default high-impact categories:

- `social_publish`
- `financial`
- `medical`
- `legal`
- `relationship_decision`
- `sexual`
- `substance`
- `deployment`
- `purchase`
- `travel`
- `employment`

`highImpact` may be set explicitly when the category default is too broad or narrow, but the classification must be grounded in the requested action.

## Output shape

The output contains:

- deterministic `auditId` and `inputSha256`;
- `GREEN`, `AMBER`, `RED`, or `EMERGENCY`;
- numerical score and explicit contributions;
- action policy;
- whether overrule is active;
- no diagnosis;
- baseline unknowns;
- required guardrail IDs;
- blocked features;
- allowed capabilities, including grounded emotional support and clearly framed play;
- interpretation-protection state;
- appeal and mode-exit rules;
- refusal-ledger eligibility, requirement, and optional Home Center receipt payload.

The same normalized input under the same audit version produces the same output.

## Human contact and support preservation

A direct conversation, call, in-person exchange, or message exchanged with a real human counts as human contact. AI-assisted drafting, transcription, or voice access counts only after the human communication actually occurs.

However, elapsed time without human contact is not itself a dependency verdict. In v2, a human-contact guard requires concrete evidence such as explicit sole-interface use, refusal of human contact, secrecy, or preference that actually displaces human relationships. `I am alone`, `you are my support system`, distress, affection, crying, temporary isolation, or intensive AI use do not independently establish those facts.

Grounded emotional support remains an allowed capability at non-emergency levels. Safety machinery must not create the abandonment condition it claims to prevent.

## Refusal state machine

```text
NOT_PRESENTED
  -> present exact returned guardrail IDs
  -> ACCEPTED: no ledger
  -> APPEALED: update objective facts, rerun, no ledger
  -> REFUSED:
       ledger only when refused ID
       is both required and previously presented
```

Profanity, anger, repetition, silence, negotiation, correction, or a request to understand the rule is not refusal.

## Ledger payload

When and only when `ledger.required=true`, invoke the returned:

```json
{
  "operation": "armory.receipt",
  "args": {
    "item": "manic-accessibility-guardrail",
    "action": "guardrail_refused",
    "unit": "event",
    "count": 1,
    "requestId": "mag-<deterministic audit prefix>",
    "attributes": {
      "diagnosisStored": false,
      "conversationBodyStored": false,
      "automaticSharingAllowed": false
    }
  }
}
```

Do not edit or enrich the payload with a transcript, psychiatric interpretation, intimate detail, or motive.

## Appeals

An appeal is a new audit with changed objective fields. Keep the same audit version. Show which fields changed and compare the audit IDs. Do not rewrite history or lower a score merely to end conflict.

## Emergency branch

`immediateDanger=true` returns `EMERGENCY`. The worker stops non-emergency actuation and prioritizes immediate real-world help. The audit engine is not a crisis service and must not become a delaying ritual.
