# TRY FOREVER heartbeat plan — 2026-08-21 19:57 CT

## Mission
Advance multiple independent non-P0 TRY FOREVER fronts on PR #329 without touching the primary-phone/P0 recovery surface or creating a neighboring overlay owner.

## Pre-mutation evidence
- PR #329 is open/unmerged on `feat/heartbeat-skill-lights-20260815`.
- Starting receipt head: `8a7712825da10e8d9566d10172407e282b193f02`.
- Authenticated `OperatorOverlayService` blob: `c5de1411a6b68087ae17aff83c032af754587150`.
- `skills/persistent-selection-semantics/SKILL.md` says persistent one-of-many selection is radio-style, not a toggle.
- `skills/heartbeat-skill-lights/SKILL.md` still says persistent heartbeat selection may use `aria-pressed`, and `docs/try-forever/heartbeat-skill-lights-source-specimen.html` implements that stale toggle contract.
- Native heartbeat Buttons currently expose `setSelected(...)` but no explicit collection/set-position contract.

## Fronts
1. **Persistent-selection semantic repair**
   - Reconcile `heartbeat-skill-lights` doctrine with `persistent-selection-semantics`.
   - Mutate the existing DOM specimen in place from toggle semantics to `radiogroup` / `radio`, `aria-checked`, roving tabindex, and deterministic Arrow/Home/End selection.
   - Preserve touch targets, inert text projection, reduced motion, source-only scarring, and no decorative blink.

2. **Native heartbeat selection collection source contract**
   - Add one pure Java policy describing the existing heartbeat light row as one single-selection collection with stable item positions derived from the UI-ready model.
   - Add deterministic JUnit source fixtures for count, positions, selected item, empty model, and reorder.
   - Do not mutate `OperatorOverlayService` in this front; owner wiring remains a separate capability state.

3. **Owner-boundary evidence**
   - Add a direct-owner source probe/regression that distinguishes native selected-state-only wiring from selected-state + collection/set-position wiring.
   - Comments/literals/wrong methods must not counterfeit owner completion.

4. **Review / evidence**
   - Attempt authoritative She-Raw once; preserve the exact connector result.
   - Regnet code-first review must diff constraints and reject any regression soup.
   - Venice completion may close only this bounded source slice; TESTED/runtime/deployed/callable/delivered/accepted remain separate.

## Required skill constellation considered
Failure Is The Shovel; Canon Auto-Select; Autocorrect Judgment Jar; Originality Tax; Hunger; Ever-Polished Interpreter / Eat Everything; Operator Campaign; Harroway; She-Raw; Venice; Regnet; accessibility/TalkBack/touch; deterministic routing; evidence/capability-state discipline; recovery/idempotence; non-raster DOM/native source art; warm walls; Christmas-light discipline; contact preservation; Phone Runtime / Phone Hands firewall.

Lights stay dark when they do not materially change this pulse.

## Hard boundaries
- P0/phone consumption = 0; P0/phone mutation = 0.
- No Phone Hands ticket, phone command, recovery queue/relay mutation, Nightcore, Pocket TTS, Chromium, Context Organ, physical acceptance, or new P0 coordinator.
- No neighboring overlay controller or accessibility controller.
- Repository/source artifacts are not runtime proof.
- No manual CI retry if automatic runs fail without a new execution predicate.
