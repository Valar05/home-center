# Heartbeat Skill Title Source Hygiene

## Purpose
A missing H1 exposed a broader rule: H1 text and directory fallback both become the same human-facing `SkillRecord.title`, so they must share one canonical source-title admission contract.

## Contract
- Keep the existing provenance probe as sole owner.
- H1 and folder-name fallback share the owner's source title resource ceiling.
- Title admission is exact: reject over-budget text; never truncate it into plausible authority.
- Reject Cc control characters and explicit bidi-direction controls (ALM, LRM/RLM, embeddings/overrides, isolates/pops) from canonical skill titles.
- Do **not** ban Unicode Format characters as a class. ZWSP, ZWNJ, ZWJ, WORD JOINER, ordinary combining text and emoji composition may be legitimate.
- Structural source bounds and later human-facing projection/truncation are separate contracts; source admission is not permission to split grapheme clusters in speech/UI.

## Evidence discipline
Current source state:
- shared H1/fallback admission policy: **YES / SOURCE**
- hostile regression source: **YES / SOURCE / UNEXECUTED**
- existing `markdown_title` consumes the policy: **NO**
- tested/runtime/deployed/callable/delivered/accepted: **NO**

## Correction scar
The first supporting pass protected only the directory fallback. Review caught that this would create two semantic contracts for one title field; the policy was broadened before completion. Preserve this convergence.

## Ownership / firewall
No second title parser, provenance probe, registry, renderer, phone lane or P0 owner. Compose the existing `markdown_title` owner only. Phone/P0 surfaces are outside this skill.
