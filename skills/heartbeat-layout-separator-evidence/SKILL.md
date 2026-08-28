# Heartbeat Layout Separator Evidence

## Purpose

Use this skill when operator-facing provenance paths or explicit heartbeat detail can contain Unicode line/paragraph separators whose source semantics are legitimate but whose raw rendering silently changes layout.

## Canonical wound

`U+2028 LINE SEPARATOR` and `U+2029 PARAGRAPH SEPARATOR` are not ISO controls and are not directional-bidi attacks. Rejecting them merely because they alter layout would repeat the old blanket-invisible-character failure. Emitting them raw in an evidence surface is also wrong: a decoded report or detail view can split the evidence without visibly naming the source character.

The repair is **REVEAL, DO NOT REWRITE**.

- Canonical source text remains exact.
- Routine/compact speech is unchanged unless a separate accessibility contract says otherwise.
- Explicit evidence projection renders deterministic markers (`\\u{2028}`, `\\u{2029}` in provenance paths; `\\u{2028 LS}`, `\\u{2029 PS}` in heartbeat detail).
- Literal backslashes are escaped first so marker-looking source text cannot alias an actual separator.
- Hard display/speech bounds apply after projection and may never cut a marker in half.

## Existing organs

Compose existing owners only:

- `tools/try_forever_provenance_report_path.py` owns operator-facing provenance path projection.
- `HeartbeatInvisibleSemanticControlPolicy` owns explicit heartbeat evidence marker projection.
- `HeartbeatEvidenceDetailProjection` already consumes the heartbeat evidence projection for selected-light detail.

Do not create a second path serializer, heartbeat formatter, renderer, overlay controller, phone lane, or P0 coordinator.

## Java source scar

Java processes Unicode-escape syntax before normal tokenization, including inside comments. A comment/Javadoc example that literally spells a backslash followed by `u{...}` is therefore compile-hostile rather than harmless documentation. Keep Java comments in `U+2028`, `U+2029`, or neutral `marker[...]` notation. Actual marker strings remain escaped Java string literals.

This scar was found by code-first review after the separator source change and repaired in `HeartbeatInvisibleSemanticControlPolicy`. Do not reintroduce raw malformed Unicode-escape examples into Java comments under the excuse that they are only prose.

## Regression doctrine

Pin these independently:

1. U+2028 and U+2029 never appear raw in projected provenance path evidence.
2. Provenance projection retains collision resistance against literal `\\u{2028}` / `\\u{2029}` source spelling.
3. Over-budget repository paths collapse from exact repository-relative identity rather than exposing a partial layout-control prefix.
4. Heartbeat explicit evidence projects U+2028/U+2029 as complete named marker units.
5. Literal heartbeat marker text remains distinct from an actual separator.
6. Typed explicit detail uses the same marker projection while exact Candidate source text remains unchanged.
7. Routine compact speech is not silently redesigned by this source repair.
8. Java comments/Javadocs use `U+...` or neutral marker notation rather than malformed raw Unicode-escape syntax.
9. Regression source is not TESTED evidence until an authorized execution lane runs it.

## Capability membrane

Current source state for this scar:

- provenance path separator projection: **YES / SOURCE_WIRED through existing report projection consumers**
- heartbeat explicit-detail separator projection: **YES / SOURCE_WIRED through existing evidence-detail consumer**
- compile-hostile Java comment examples in the changed policy: **REPAIRED / SOURCE**
- provenance hostile regression source: **YES / UNEXECUTED**
- Android hostile regression source: **YES / UNEXECUTED**
- Android test execution: **NO**
- provenance test execution: **NO**
- runtime UI/TalkBack observation: **NO**
- deployed/callable/executed/delivered/accepted: **NO**

## P0 / phone firewall

This skill owns no Phone Hands action, primary-phone command, queue/relay work, Home Center P0 recovery mutation, Nightcore, Pocket TTS, Chromium, Context Organs, physical acceptance, or duplicate recovery architecture. Phone/P0 consumption and mutation remain zero.
