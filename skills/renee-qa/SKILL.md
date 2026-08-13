# Regnet QA

Use this skill when quality assurance, validity, evidence sufficiency, reproducibility, reachable failure paths, regression risk, acceptance criteria, or capability-state truth are material.

## Identity and boundary

The invocation keyword is **Regnet QA**.

Regnet QA is the unified deterministic QA judgment interface. The former Renee QA office and Regnet are one person-function; legacy Renee names remain provenance aliases, not a second active person.

Regnet-source assertions require attributable `REGNET_DIRECT`, `REGNET_CORRECTION`, legacy Renee-lineage provenance, or clearly attributed `DREW_RECALL`. CLI output is always `SYNTHETIC_REGNET` and never promotes itself.

## Review sequence

1. State the exact bounded claim and capability state.
2. State acceptance criteria in observable terms.
3. Run deterministic checks on the authorized execution surface.
4. Provide current receipts/evidence to Regnet QA.
5. Attack scope substitution, missing failure paths, stale evidence, non-reproducible success, regression risk, and collapsed capability states.
6. Obey the Regnet verdict: `PASS`, `REVISE_REQUIRED`, `BLOCKED_UNKNOWN`, or `STOP_SHIP`.
7. After PASS, perform the separate Venice mission/adversarial/stop review. Regnet cannot grant `STOP_ALLOWED`.

## Stable CLI

`./regnet.sh status`

`./regnet.sh review "<exact claim>" --state tested --acceptance "<criterion>" --evidence <receipt> --failure-path "<reachable path>"`

`./regnet.sh record "<finding>" --provenance RENEE_DIRECT --source <attributable-locator>`

`./regnet.sh correct <receipt-id> "<correction>" --provenance RENEE_CORRECTION --source <attributable-locator> --regression-target "<generalized scar>"`

`./regnet.sh precedent "<question>"`

`./regnet.sh explain`

`./regnet.sh diff-judgment <left.json> <right.json>`

`./regnet.sh regress`

The CLI writes receipts/corrections under `$RENEE_QA_HOME (legacy-compatible state variable)` or `~/.home-center/renee-qa`. Do not commit workplace conversations or proprietary source material into the personal Renee corpus by default. Store generalized rules or authorized references with provenance instead.

## Calibration doctrine

The highest-value future data is new attributable Regnet correction with the tool. Preserve corrections rather than smoothing them away. A human correction outranks synthetic output and should become a regression target when it generalizes.

The generated `Work Wife Organ` may supply candidate structural ideas such as consequential opposition and QA standing, but it remains generated/unpromoted evidence and never counts as direct Renee testimony.

## Compatibility

`tools/renee.py`, `skills/renee-qa`, the state directory, and legacy `RENEE_*` provenance tokens remain compatibility surfaces. New human-facing invocation uses `regnet.sh` and the canonical keyword `Regnet QA`. Regent and Ranget remain separate identities unless their owning artifacts explicitly say otherwise.
