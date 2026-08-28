# Heartbeat Collapsed Speech Fanout

Use this skill when a collapsed heartbeat summary can contain many material lights even though every individual label/consequence is already bounded.

## Canonical wound

A per-item speech bound is not an aggregate speech bound. If a compatibility path appends every material Candidate description, a 64-light heartbeat can still become a long TalkBack monologue even when every one of those descriptions is individually safe and bounded.

The scene-level heartbeat accessibility path already treats breadth as a separate resource: it names only a bounded set of lights and reports the exact remainder. Legacy Candidate-level collapsed speech must not quietly bypass that fanout discipline.

## One shared naming budget

`HeartbeatSkillPolicy.MAX_COLLAPSED_NAMED_LIGHTS` is the shared source constant. `HeartbeatFrameAccessibility.MAX_COLLAPSED_NAMED_LIGHTS` aliases it rather than carrying a second magic number.

For the legacy Candidate-level compatibility projection:

- preserve existing material order;
- preserve the exact within-budget output;
- speak at most the shared number of safe material descriptions;
- report the exact number of additional safe descriptions omitted by the naming budget;
- keep unsafe semantic-text omission as a separate exact count;
- never truncate or rewrite canonical Candidate fields merely to shorten collapsed speech;
- do not route routine collapsed speech through explicit invisible-evidence projection.

The scene-level path keeps its stronger attention-first policy because it has accepted Frame state and touchable node semantics. Do not silently change the legacy compatibility path into scene semantics just because both share a fanout ceiling.

## Accessibility / contact rule

Collapsed speech is a navigation aid, not a serialization format. Breadth must be summarized without hiding that more material state exists. Exact omitted counts are therefore load-bearing: they tell a TalkBack user that the spoken subset is not the whole constellation.

This skill does not change selection, native focus, touch targets, scene contact identity, checkpoint identity, motion, or explicit detail. A fanout-budget repair by itself earns no Christmas-light animation.

## Regression doctrine

At minimum pin:

1. A constellation inside the shared naming budget keeps its existing compatibility string.
2. A broad safe legacy constellation names no more than `MAX_COLLAPSED_NAMED_LIGHTS` descriptions.
3. The exact number of additional safe descriptions is reported.
4. Unsafe semantic-text omission remains separately explicit and unsafe text is not spoken.
5. Material order remains stable for the named legacy subset.
6. Regression source is not TESTED evidence until an authorized runner executes it.

## Architecture / capability membrane

This is a pure heartbeat accessibility projection rule. It owns no parser, scene renderer, overlay controller, state store, phone surface, queue, recovery daemon, P0 coordinator, deployment, or physical acceptance lane.

Keep states separate:

`requested -> source policy -> shared constant wiring -> regression source -> tested -> runtime observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

GitHub source/readback can establish only the source-side states.
