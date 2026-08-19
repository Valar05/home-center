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
- Markdown structural normalization must not erase forbidden title controls before semantic admission. Remove only structural CR/LF line endings and ordinary ASCII-space margin before admitting an H1; if broad whitespace stripping would create an H1 that the narrow parser would not, reject rather than launder hidden control state.

## Evidence discipline
Current source state:
- shared H1/fallback admission policy: **YES / SOURCE**
- pre-normalization H1 admission policy: **YES / SOURCE**
- hostile regression source: **YES / SOURCE / UNEXECUTED**
- corrected existing-owner delta: **YES / PROPOSED_NOT_APPLIED**
- existing `markdown_title` consumes the policy: **NO**
- tested/runtime/deployed/callable/delivered/accepted: **NO**

## Correction scars
1. The first supporting pass protected only the directory fallback. Review caught that this would create two semantic contracts for one title field; the policy was broadened before completion.
2. The second pass proposed applying semantic admission only after the owner's existing `line.strip()`. Review caught that Python broad stripping can remove edge Cc whitespace such as U+0085 before the policy sees it. Preserve the corrected raw-line H1 admission boundary.

## Ownership / firewall
No second title parser, provenance probe, registry, renderer, phone lane or P0 owner. Compose the existing `markdown_title` owner only. Phone/P0 surfaces are outside this skill.
