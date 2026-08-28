# Heartbeat Pre-Decode Resource Budget

## Purpose
Keep corrupt or directly supplied heartbeat text from consuming unbounded repeated comparison, encode, decode, allocation, or parser work before the existing integrity/semantic pipeline can reject it.

The canonical writer caps the UTF-8 payload at `OperatorState.MAX_HEARTBEAT_LIGHTS_BYTES`. Standard padded Base64 can therefore require at most:

`4 * ceil(MAX_HEARTBEAT_LIGHTS_BYTES / 3)` characters.

`HeartbeatPersistedSnapshotReader.MAX_PAYLOAD_BASE64_CHARS` derives that ceiling from the existing byte constant. The coherent reader rejects a longer stored declaration before `OperatorOverlayService` calls Android Base64 decode.

The same resource law also applies to direct/source-only entrypoints that do not necessarily inherit coherent-reader custody:

- `HeartbeatPersistedPollPolicy.Snapshot` has finite dedup eligibility: Base64 text is bounded by the canonical maximum and SHA metadata by a finite diagnostic/integrity source ceiling before repeated `String.equals` work. Oversized exact evidence is **not** truncated or normalized; it becomes `PROJECT` so the existing verification path can reject it while last-good contact semantics remain available.
- `HeartbeatPersistedEnvelopeProjection.project(String, ...)` has a finite early Java source-code-unit throat **before UTF-8 encoding**. The throat aliases the canonical payload-byte ceiling rather than inventing a neighboring resource constant. Exact-at-ceiling text still reaches existing byte/SHA/update and semantic custody; over-ceiling text fails before encode/allocation work. This is **SOURCE_WIRED / APPLIED_SOURCE**, not regression execution or runtime proof.
- `HeartbeatEnvelopeParser.parse(String)` now has its distinct direct preparse source-work throat **before `trim()` and `JsonCursor` traversal**. `MAX_ENVELOPE_SOURCE_CODE_UNITS = 32768`; above-ceiling text fails before blank normalization or JSON allocation, while at/below-ceiling text continues through the existing strict parser. This is **SOURCE_WIRED / APPLIED_SOURCE / regression source UNEXECUTED**.

## Ownership
This skill owns source-level resource-bound doctrine only. It does not own a decoder, poll loop, cache, parser twin, renderer, overlay controller, transport, Phone Hands ticket, primary-phone command, P0 recovery action, deployment, or acceptance lane. The sole runtime owner remains the existing `OperatorOverlayService`; the canonical writer remains `OperatorState.updateHeartbeatLights(...)`.

Compose existing organs. Do not create a second decoder, heartbeat reader, poll controller, parser, or projection owner to enforce these rules.

## Evidence separation
A finite source-work ceiling is not Base64 canonicality, payload integrity, semantic acceptance, or runtime proof.

- coherent-reader declaration length within the Base64 ceiling: merely eligible for the existing decode/canonicality/integrity/parser chain;
- declaration length above the coherent-reader ceiling: storage read failure before owner decode;
- poll snapshot text within the dedup ceilings: merely eligible to compare with the previous processed observation;
- poll snapshot text above a dedup ceiling: never `SKIP_UNCHANGED`; route through `PROJECT` without rewriting exact evidence;
- direct String projection above its source ceiling: source rejection before UTF-8 encoding;
- direct String projection at/below its source ceiling: merely eligible for existing byte/SHA/update and semantic custody;
- direct parser text above `MAX_ENVELOPE_SOURCE_CODE_UNITS`: source rejection before trim/JSON traversal;
- direct parser text at/below its source ceiling: merely eligible for existing strict JSON/semantic custody;
- exact Base64 writer representation: separate `HeartbeatPersistedBase64Canonicality` concern;
- decoded byte count/SHA/UTF-8/semantic acceptance: existing downstream concerns.

Never report `length <= max` as valid Base64, accepted payload, rendered UI, or runtime delivery.

## Accessibility and contact preservation
An oversized declaration is a storage/evidence wound, not operator prose. Existing fail-closed paths must expose bounded boundaries rather than raw hostile text through TalkBack.

Poll dedup resource rejection must not erase contact or convert hostile evidence into a false equality. Returning `PROJECT` for oversized exact snapshots keeps verification failure distinct from `SKIP_UNCHANGED` and preserves the existing last-good/contact-preservation path.

The existing `docs/try-forever/heartbeat-predecode-throat-source.html` Warm Wall exposes coherent-reader, poll-dedup, direct-String, and direct-parser SOURCE_WIRED states in one non-raster source specimen. Its native buttons are at least 56px, keyboard focus is visible, state is available through non-color `role=status` live text, SVG has title/description semantics, and reduced-motion/no-timer behavior is pinned by a source-only fixture. That is repository-source accessibility evidence only: runtime TalkBack, deployment, phone delivery, and acceptance remain **NO**.

If last-good heartbeat contact exists, preserve it through the existing fail-closed scene organ and clamp one-shot motion. Before first contact, do not invent `CONTACT HELD`.

## Regression source
Pin at least:

- exact canonical maximum persisted Base64 declaration length is accepted by the coherent reader;
- maximum + 1 persisted declaration is rejected before owner decode;
- exact poll-dedup Base64 ceiling may compare equal while max + 1 cannot become dedup authority;
- oversized SHA metadata cannot become dedup authority;
- an oversized previous poll observation cannot make a finite changed observation skip;
- exact SHA metadata text remains byte-for-character unchanged by the reader/poll snapshot;
- direct String projection max + 1 fails before encode, while exact-at-ceiling text still reaches existing byte-integrity semantics;
- the direct String public source ceiling equals the canonical payload-byte ceiling rather than drifting independently;
- multibyte text exactly at the String code-unit ceiling still reaches and may fail the canonical byte ceiling rather than being falsely accepted;
- direct envelope parser max + 1 fails before blank normalization / JSON traversal, while exact-at-ceiling text still reaches existing parser semantics;
- the Warm Wall retains >=56px native controls, visible focus, non-color live state, SVG semantics, reduced-motion handling, source/runtime membrane text, and no timer/autoplay motion;
- wrong stored types remain read failures rather than fake absence;
- regression source existence is not TESTED evidence.

## Capability membrane
Keep these states distinct:

`requested -> coherent-reader bound source -> poll-dedup bound source -> direct-string preencode source -> direct-parser preparse source -> regression source -> exact GitHub readback -> tested -> runtime work avoided -> runtime UI observed -> TalkBack exercised -> deployed -> callable -> executed -> delivered -> accepted`

Current source state:

- coherent reader Base64 bound: **SOURCE_WIRED**;
- persisted poll dedup source-work bound: **SOURCE_WIRED**;
- direct persisted String pre-encode throat: **SOURCE_WIRED / APPLIED_SOURCE**;
- direct envelope parser preparse throat: **SOURCE_WIRED / APPLIED_SOURCE**;
- Warm Wall accessibility contract: **SOURCE_WIRED / SOURCE ONLY**;
- regression source: **YES / UNEXECUTED**;
- tested/runtime/runtime TalkBack/deployed/callable/executed/delivered/accepted: **NO** until separate evidence exists.

## P0 firewall
This skill must never wake, queue, retask, probe, or consume Phone Ingress, Phone Hands, Nightcore, Pocket TTS, Chromium Control, Context Organs, or their physical acceptance chain. A repository-source resource bound is independent of P0 recovery.
