# Heartbeat Skill Title Fallback Hygiene

## Purpose
A missing H1 may fall back to the containing directory name, but filesystem text does not bypass the human-facing skill-title contract.

## Contract
- Keep the existing provenance probe as sole owner.
- H1 and folder-name fallback share the owner's source title resource ceiling.
- Fallback admission is exact: reject over-budget text; never truncate it into plausible authority.
- Reject Cc control characters and explicit bidi-direction controls (ALM, LRM/RLM, embeddings/overrides, isolates/pops) from fallback titles.
- Do **not** ban Unicode Format characters as a class. ZWSP, ZWNJ, ZWJ, WORD JOINER, ordinary combining text and emoji composition may be legitimate.
- Structural source bounds and later human-facing projection/truncation are separate contracts; a source bound is not permission to split grapheme clusters in speech/UI.

## Evidence discipline
Current source state:
- fallback admission policy: **YES / SOURCE**
- hostile regression source: **YES / SOURCE / UNEXECUTED**
- existing `markdown_title` fallback consumes this policy: **NO**
- tested/runtime/deployed/callable/delivered/accepted: **NO**

## Ownership / firewall
No second title parser, provenance probe, registry, renderer, phone lane or P0 owner. Compose the existing `markdown_title` fallback only. Phone/P0 surfaces are outside this skill.
