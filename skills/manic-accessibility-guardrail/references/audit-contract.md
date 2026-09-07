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
    "highImpact": false
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

## Evidence jurisdiction

The audit deliberately separates evidence classes instead of flattening every observation into one psychiatric-style score.

- `foodNeglected`, `waterNeglected`, `foodWithin8Hours=false`, and `waterWithin4Hours=false` are body-needs facts. They contribute **zero numeric risk points**. They create `BODY_NEEDS_CHECK_REQUIRED` and workflow friction only.
- With body needs active and no stronger outcome, low-impact work returns `ALLOW_WITH_FRICTION`.
- With body needs active and a high-impact or irreversible request, actuation returns `PAUSE_FOR_GUARDS` until the body-needs check is satisfied. Body needs alone do not invent a human-contact or diagnostic guard.
- `hyperbolicLanguage` is accepted as a structured style observation but contributes **zero risk points** and may not change score, outcome, or action policy.
- Sleep, behavior, substances, medication, relational displacement, reality distortion, and requested action impact/reversibility remain independent decision evidence.

Mnemonic: **Feed the body. Ignore the typography. Judge the action. Preserve the thought.**

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
- allowed mechanical capabilities;
- appeal and mode-exit rules;
- refusal-ledger eligibility, requirement, and optional Home Center receipt payload.

The same normalized input under the same audit version produces the same output.

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

Profanity, anger, repetition, silence, negotiation, or a request to understand the rule is not refusal.

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

## Human contact

A direct conversation, call, in-person exchange, or message exchanged with a real human counts. AI-assisted drafting, transcription, or voice access counts only after the human communication actually occurs.

## Emergency branch

`immediateDanger=true` returns `EMERGENCY`. The worker stops non-emergency actuation and prioritizes immediate real-world help. The audit engine is not a crisis service and must not become a delaying ritual.
