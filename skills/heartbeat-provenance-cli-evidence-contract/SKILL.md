# Heartbeat Provenance CLI Evidence Contract

## Purpose
Keep authority-facing provenance CLI parameters exact before they can influence repository/index certification or durable report evidence.

## Trigger
Use this skill when a provenance command accepts caller-supplied expected repository identity, freshness windows, or similar values that participate in authority decisions.

## Contract

- `--expected-head` is either empty/no binding or one exact canonical lowercase Git SHA-1/SHA-256 object id.
- Do not trim, case-fold, Unicode-normalize, extract, or otherwise repair rejected expected-head text into authority.
- Rejected expected-head text must not be echoed into durable authority/error evidence as if it were trusted metadata.
- Generated-index freshness windows are finite and non-negative.
- Reject `NaN`, positive/negative infinity, negative values, booleans, and text masquerading as numbers.
- Do not silently clamp negative freshness to zero.
- Do not let infinity disable freshness comparison by arithmetic accident.
- The sole owner must compose `admit_cli_evidence(...)` exactly once before either caller value enters authority or report logic.
- A durable provenance report must expose the exact admitted expected-head binding and max-index-age window that governed its authority decisions. A `VERIFIED_CURRENT` verdict without the freshness bound used is not self-auditing evidence.
- Adding that authority-input contract changes the durable report contract: the owner must advance explicitly from `try-forever-skill-provenance.v5` to `try-forever-skill-provenance.v6`; do not silently widen v5.
- Keep source policy, owner wiring, regression source, executed tests, runtime, deployment, delivery, and acceptance as separate capability states.

## Existing owner
`tools/try_forever_skill_provenance_probe.py` remains the sole provenance owner. This skill does not authorize a second parser/probe/controller.

## Exact owner surgery

`patches/try-forever-provenance-cli-evidence-owner.delta.json` is base-blob locked to owner blob `cd94af837245f6c9d6c64ad4f4620699acbb19fb` and records the only accepted owner delta for this source slice:

1. import the existing CLI evidence policy;
2. admit caller evidence before authority use;
3. use admitted freshness and expected-head values everywhere they govern authority;
4. advance the report schema to v6;
5. serialize `cliEvidence.expectedHead` and `cliEvidence.maxIndexAgeHours` from admitted values.

Patch/delta existence is not owner implementation. The delta is **PROPOSED_NOT_APPLIED** until authenticated owner readback proves the sole owner changed.

## Current capability state

- Pure CLI evidence policy: **YES / SUPPORTING_SOURCE**
- Hostile pure regression source: **YES / UNEXECUTED**
- RED existing-owner admission regression: **YES / UNEXECUTED / STRENGTHENED**
- RED durable-report auditability regression: **YES / UNEXECUTED / STRENGTHENED**
- Exact base-blob-locked owner delta: **YES / PROPOSED_NOT_APPLIED**
- Existing owner consumes `admit_cli_evidence`: **NO**
- Existing owner reports admitted `cliEvidence`: **NO**
- Existing owner report schema: **v5**
- Required owner report schema after this surgery: **v6**
- Tested: **NO**
- Runtime UI / TalkBack: **NO**
- Deployed / callable / executed / delivered / accepted: **NO**

## P0 / phone firewall
This skill owns no phone execution, Phone Hands queue, Home Center recovery, Nightcore, Pocket TTS, Chromium, Context Organ, or physical-acceptance action.
