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
- The sole owner composes `admit_cli_evidence(...)` exactly once before either caller value enters authority or report logic.
- A durable provenance report exposes the exact admitted expected-head binding and max-index-age window that governed its authority decisions. A `VERIFIED_CURRENT` verdict without the freshness bound used is not self-auditing evidence.
- Adding that authority-input contract changed the durable report contract explicitly from `try-forever-skill-provenance.v5` to `try-forever-skill-provenance.v6`; do not silently widen an existing schema.
- Keep source policy, owner wiring, regression source, executed tests, runtime, deployment, delivery, and acceptance as separate capability states.

## Existing owner
`tools/try_forever_skill_provenance_probe.py` remains the sole provenance owner. This skill does not authorize a second parser/probe/controller.

## Applied existing-owner surgery

`patches/try-forever-provenance-cli-evidence-owner.delta.json` was base-blob locked to owner blob `cd94af837245f6c9d6c64ad4f4620699acbb19fb` and defined the accepted owner delta:

1. import the existing CLI evidence policy;
2. admit caller evidence before authority use;
3. use admitted freshness and expected-head values everywhere they govern authority;
4. advance the report schema to v6;
5. serialize `cliEvidence.expectedHead` and `cliEvidence.maxIndexAgeHours` from admitted values.

Authenticated Home Center GitHub-admin mutation applied that contract to the existing owner in commit `52e47781f5e9c11a17bc59c3b842700fcc784127`; authenticated owner readback blob is `2f3ebd530f46283a59bd6ff34149042a1b825d89`.

## Current capability state

- Pure CLI evidence policy: **YES / SUPPORTING_SOURCE**
- Hostile pure regression source: **YES / UNEXECUTED**
- Existing-owner admission regression source: **YES / UNEXECUTED**
- Durable-report auditability regression source: **YES / UNEXECUTED**
- Exact base-blob-locked owner delta: **YES / APPLIED_SOURCE**
- Existing owner consumes `admit_cli_evidence`: **YES / SOURCE_WIRED**
- Existing owner reports admitted `cliEvidence`: **YES / SOURCE_WIRED**
- Existing owner report schema: **v6 / SOURCE_WIRED**
- Authenticated owner readback: **YES**
- Tested: **NO**
- Runtime UI / TalkBack: **NO**
- Deployed / callable / executed / delivered / accepted: **NO**

## P0 / phone firewall
This skill owns no phone execution, Phone Hands queue, Home Center recovery, Nightcore, Pocket TTS, Chromium, Context Organ, or physical-acceptance action.
