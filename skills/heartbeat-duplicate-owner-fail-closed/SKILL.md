# Heartbeat Duplicate Owner Fail-Closed

Use this skill when the same semantic heartbeat light ID can arrive more than once through a source path that bypasses the canonical JSON parser.

## Contract

One material semantic light ID names exactly one current scene owner. Canonical `HeartbeatEnvelopeParser` already rejects case-insensitive duplicate IDs. Direct `HeartbeatSkillPolicy.Candidate` lists must not silently weaken that rule by relying on legacy first-wins deduplication.

`HeartbeatSkillPolicy.selectMaterialLights(...)` may keep its compatibility behavior for summaries and legacy callers. `HeartbeatSceneGraph.build(...)` is stricter: before display-ready filtering, two material candidates with the same case-insensitive semantic ID make the attempted scene ambiguous and must fail closed.

Do not pick a winner. Do not merge consequences. Do not rewrite IDs. Do not use source order as authority. An ambiguous owner must not become a native Button, selection target, viewport anchor, transition identity, or TalkBack detail source.

## Contact preservation

If a duplicate-owner pulse arrives after a last-good frame, preserve that frame, preserve the safe attempted pulse identity for diagnostics, expose a bounded trusted rejection boundary, and clamp both frame-level and node-level one-shot motion.

A duplicate non-material alias by itself does not create a second visible owner. The fail-closed duplicate check is about competing material ownership; canonical parsed candidates are all material after parser validation, so this preserves the parser/direct-scene ownership invariant without breaking legacy decorative filtering.

## Regression requirements

Keep source fixtures for:

- canonical parser rejection of case-insensitive duplicate semantic IDs;
- direct scene rejection of two material case-insensitive duplicate IDs;
- preservation of the exact last-good visible contact and zero transition motion after rejection;
- a non-material alias plus one material owner remaining one visible owner.

These fixtures are regression source until they execute. Do not call them tested merely because they exist.

## Capability membrane

Keep requested, implemented source, exact repository readback, regression source, tested, runtime consumed, UI rendered, TalkBack exercised, deployed, callable, executed, delivered, and accepted separate.

This skill owns no overlay controller, renderer, transport, phone execution surface, recovery daemon, P0 coordinator, or queue/relay mutation. Compose existing organs only.
