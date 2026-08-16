# Heartbeat Ingress Separation

## Purpose
Keep the Home Center Operator heartbeat's independent liveness update separate from optional heartbeat skill-light telemetry. A bad optional light envelope must not become a liveness outage, and a real storage/runtime failure must not be painted green.

## Canonical existing owner
Compose the existing `ACTION_HEARTBEAT -> OverlayUpdateReceiver -> OperatorState` organ. Do not create a neighboring receiver, overlay controller, recovery daemon, phone ingress path, or P0 coordinator.

## Optional-payload rule
`heartbeatLightsJson` is optional telemetry. When it is absent or blank, invoke the existing heartbeat sink normally.

When the optional payload reaches `OperatorState.updateHeartbeatLights(...)`:

- caller-invalid input rejected with `HeartbeatIngressPolicy.CallerInvalidPayloadException` (for example malformed Unicode or the bounded payload ceiling) rejects only that optional payload;
- the previously stored heartbeat-light identity remains untouched because validation fails before the state write;
- the independent heartbeat sink is still invoked;
- the rejection boundary may be logged/reviewed, but it must not be promoted into a new visible light payload that overwrites last-good contact.

## Failure-class boundary
Catch only the dedicated `HeartbeatIngressPolicy.CallerInvalidPayloadException` that the existing ingress owner explicitly uses for caller-invalid optional telemetry. Do **not** catch every `IllegalArgumentException`, `RuntimeException`, or every failure emitted by the persistence sink.

A generic/unrelated `IllegalArgumentException` from persistence is an internal/programmer-contract wound unless an explicit typed boundary says otherwise. It propagates and the heartbeat sink is not invoked. This prevents a future implementation mistake from being silently relabeled as bad caller data merely because it shares a Java base exception type.

An internal/storage failure such as `IllegalStateException` from a failed heartbeat-light commit also propagates. The heartbeat sink is not invoked after that failure, because claiming a healthy liveness update would conceal an implementation/storage wound.

If the heartbeat sink itself fails, that failure also propagates. No returned source result may claim heartbeat success.

## Human-facing boundary hygiene
The bounded rejection string is a human-facing/loggable projection of the typed failure. It is **not** the raw exception identity and must not become a substitute payload.

`HeartbeatIngressPolicy.cleanBoundary(...)` therefore:

- collapses ISO control characters, recognized whitespace/space, and invisible Unicode `FORMAT` code points such as bidirectional overrides/isolates to one ordinary space;
- replaces malformed lone UTF-16 surrogate code units with U+FFFD rather than preserving an ill-formed Java string;
- truncates by Unicode code point, never by raw UTF-16 code unit, so a valid surrogate pair is not split;
- keeps the final result within `MAX_BOUNDARY_CODE_POINTS`;
- leaves the typed exception object/cause untouched and never promotes the sanitized text into semantic payload state.

This is accessibility/evidence hygiene, not an execution filter. Command-looking text remains inert text. Sanitizing a boundary does not validate the rejected payload, prove persistence, or overwrite last-good contact. Ordinary visible right-to-left script letters remain text; only invisible `FORMAT` controls are normalized.

## Evidence language
A pure source policy may say the heartbeat sink was **invoked** only when that call returned normally. Do not rename this to `accepted`, `persisted`, `durable`, `live`, or `healthy` unless evidence proves that later state.

The current `OperatorState.heartbeat(...)` uses `SharedPreferences.apply()`. A normal return therefore does not prove synchronous disk durability, deployment, on-device observation, connector egress, callability, delivery, or acceptance.

Keep the capability membrane explicit:

`requested -> implemented -> tested -> deployed -> callable -> executed -> delivered -> accepted`

Source ordering and regression source prove only source implementation until the relevant test/runtime evidence exists.

## Contact preservation
Caller-invalid optional telemetry must not overwrite the previously stored skill-light payload. This is the ingress-side complement to `HeartbeatSceneGraph`/`HeartbeatPersistedEnvelopeProjection` fail-closed contact preservation after stored bytes exist.

Do not manufacture a replacement fault payload merely to make the rejection visible; doing so would destroy the last-good telemetry the rule exists to preserve.

## Accessibility and art
Source specimens may visualize the split between optional payload acceptance and heartbeat-sink invocation using DOM/SVG/native/vector primitives. They must:

- use semantic controls with at least 48px/dp target intent;
- expose state with text/non-color tokens;
- use one bounded live-status surface;
- respect reduced motion;
- avoid autoplay/decorative blinking;
- carry an explicit `SOURCE ONLY` / `NOT RUNTIME PROOF` scar.

A source specimen never proves Android rendering, TalkBack runtime behavior, deployment, phone callability, delivery, or acceptance.

For TalkBack speech projections, keep complete typed source/evidence fields in the semantic model but independently bound long spoken fields by Unicode code point and mark truncation. Accessibility is not permission to discard evidence, and evidence richness is not permission to make one focus action speak several kilobytes.

Human-facing ingress rejection boundaries follow the same Unicode discipline: single-line, code-point bounded, control/format-normalized, and safe against surrogate splitting. This does not make them canonical semantic evidence; it only keeps the review/log surface sane.

## P0 Fortress firewall
This skill owns no Phone Hands, queue, P0 recovery, Nightcore, Pocket TTS, Chromium, Context Organs, or physical acceptance work. Those surfaces remain under their canonical owners. A source-side ingress defect may be repaired without consuming the shared phone surface; physical proof waits for the authorized owner lane.

## Regression doctrine
Lock at least these cases in pure regression source:

1. blank optional payload -> heartbeat sink invoked;
2. valid optional payload -> payload sink returns, then heartbeat sink invoked;
3. dedicated caller-invalid optional payload -> payload rejected, heartbeat sink still invoked, bounded exact rejection reason retained;
4. unrelated/generic `IllegalArgumentException` -> failure propagates, heartbeat sink not invoked;
5. internal/storage payload failure -> failure propagates, heartbeat sink not invoked;
6. heartbeat-sink failure -> failure propagates and no success result is returned;
7. expanded TalkBack detail -> long Unicode fields are speech-bounded without changing the exact Candidate data or splitting surrogate pairs;
8. hostile caller-invalid boundary text -> controls/whitespace/Unicode FORMAT controls normalize to one line, lone surrogate code units are repaired, truncation is code-point safe, the optional payload remains rejected, and heartbeat invocation semantics remain unchanged.

Blind CI retries do not count as progress. When deterministic CI cannot start for an unchanged external reason, preserve `TESTED = NO/BLOCKED_UNKNOWN` and advance a materially different authorized front instead.
