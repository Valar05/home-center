# Heartbeat Generated Index Alias Contract

## Purpose

Prevent supported generated-index metadata aliases from becoming a silent first-wins provenance channel. Generated indexes remain discovery aids; conflicting aliases, unsafe scalar shapes, non-finite numbers, or unbounded scalar text must become bounded `UNRESOLVED` evidence rather than whichever key happens to be read first.

## Existing owner

`tools/try_forever_skill_provenance_probe.py::inspect_generated_index` remains the sole generated-index owner. `tools/try_forever_generated_index_alias_policy.py` is a pure policy helper only. Do not create another provenance probe, index daemon, registry, controller, scheduler, phone lane, or P0 owner.

## Alias law

1. Run the existing byte/UTF-8/JSON ingress gates first once that owner patch is applied.
2. Treat each supported metadata alias family as one typed declaration: source HEAD, generated timestamp, and dirty-source truth.
3. If multiple aliases are present, they must carry the same value **and the same scalar type**.
4. `bool` is not admitted as an integer timestamp merely because Python subclasses it from `int`.
5. Floating timestamps must be finite.
6. String scalar evidence is hard-bounded before it reaches operator/report projection.
7. Conflicting aliases never use first-wins, last-wins, key order, or coercion as a resolver.
8. A contract rejection is `UNRESOLVED`; generated-index evidence never substitutes for direct current-tree `skills/**/SKILL.md` authority.

## Accessibility / operator truth

Operator-facing detail should distinguish `ALIAS CONSISTENT`, `ALIAS CONFLICT`, `TYPE BLOCKED`, and `SCALAR BUDGET BLOCKED` without color alone. Routine speech remains compact and must not dump hostile scalar text. Alias bookkeeping earns no automatic focus movement or decorative Christmas motion.

## Evidence membrane

A pure helper, hostile regression source, patch artifact, GitHub commit, or review is source evidence only. Preserve `requested → implemented source → owner source wired → tested → runtime → deployed → callable → executed → delivered → accepted` separately.

## P0 / phone firewall

This skill owns no Phone Hands, primary-phone execution, queue/relay recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance work. P0 remains read-only evidence here.

## Current capability state

- Pure alias-contract policy source: **YES**
- Hostile policy regression source: **YES**
- Exact existing-owner patch provenance: **YES / PROPOSED_NOT_APPLIED**
- Existing generated-index owner consumes alias contract: **NO**
- Existing generated-index byte/UTF-8 ingress patch: **YES / PROPOSED_NOT_APPLIED**
- TESTED: **NO**
- Runtime UI/TalkBack: **NO**
- Deployed/callable/executed/delivered/accepted: **NO**
