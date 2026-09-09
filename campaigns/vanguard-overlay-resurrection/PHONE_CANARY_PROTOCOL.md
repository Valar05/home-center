# VANGUARD // OVERLAY RESURRECTION — phone canary protocol

This protocol exists so the durable phone campaign can test the real Android runtime without guessing UI internals. It does **not** create a remote-control backdoor for ARM LISTENING.

## State provider

`content://com.homecenter.operatoroverlay.state/state` must return compact machine-readable values containing at least:

- `overlay_mode` — `FULL`, `BUBBLE`, or `HIDDEN`
- `listening_state` — `OFF`, `ARMING`, `LISTENING`, or `ERROR`
- `mic_active` — `1` only while the app actually owns an active `AudioRecord`
- `ring_write_bytes` — monotonic logical bytes written in the current transient listening session
- `ring_capacity_bytes` — fixed physical raw-ring capacity
- `transcript_segment_count`
- `last_transcript_at_ms`
- `last_transcript_start_sample`
- `last_transcript_end_sample`
- `latest_transcript_text` — bounded recent segment text; escape delimiters safely
- `keep_count`
- `last_keep_id`
- `last_keep_bytes`
- `actual_sample_rate_hz`
- `latest_error`
- `opinion_speaker`
- `opinion_provider_state`

No field may claim a later capability state than it measures. `mic_active` is microphone-resource truth, not foreground-service-type truth.

## Visible MainActivity canary actions

The debug/recovery build must accept `vanguard_action` only through an explicit launch of the existing visible `MainActivity`. These actions are allowed because they do not acquire a while-in-use permission and are test/control operations on an already-installed app:

- `FULL` — set presentation FULL
- `BUBBLE` — set presentation BUBBLE
- `HIDE` — set presentation HIDDEN
- `RESTORE` — restore at least BUBBLE; this is a machine fallback, **not** evidence that notification-tap restore works
- `KEEP_LAST_60` — explicit durable promotion
- `STOP_LISTENING` — release microphone and clear unkept transient raw/text

Example transport used by the campaign:

```text
am start -n com.homecenter.operatoroverlay/.MainActivity --es vanguard_action FULL
```

## Deliberately forbidden machine ARM

There is **no** `vanguard_action=ARM_LISTENING` acceptance path. The first microphone ARM after install/reboot must come from a genuine visible user interaction inside the app/overlay (or another Android-qualified user interaction implemented with the same safety). The campaign may notify Drew and wait for `mic_active=1`; it may not manufacture the tap through shell input or a hidden intent.

## Notification restore proof

`RESTORE` machine action can repair presentation during tests, but it cannot prove the heartbeat notification works. To prove the commissioned recall surface:

1. campaign sets `HIDE` while listening;
2. verifies `overlay_mode=HIDDEN` and `mic_active=1`;
3. campaign posts a local instruction asking Drew to tap the Home Center heartbeat notification;
4. campaign waits for `overlay_mode=BUBBLE` or `FULL` while `mic_active` remains `1`.

No shell-generated restore may be counted for this acceptance item.

## Speech proof

The campaign asks Drew to speak one short phrase while listening. Acceptance does not depend on exact keyword recognition; it requires:

- transcript segment count increases;
- latest transcript text becomes non-empty;
- `last_transcript_end_sample > last_transcript_start_sample >= 0`;
- the segment's end sample does not exceed the current logical raw write position.

This proves live voice-to-text/sample mapping, not semantic accuracy or speaker identity.

## KEEP proof

While a live transcript/raw session exists:

1. record `keep_count`;
2. launch visible MainActivity with `vanguard_action=KEEP_LAST_60`;
3. require `keep_count` to increase by exactly 1;
4. require non-empty `last_keep_id` and `last_keep_bytes > 0`.

The durable bundle still requires implementation-level format/receipt tests; these provider fields are physical-phone readback.

## STOP/clear proof

1. record current logical raw position;
2. launch visible MainActivity with `vanguard_action=STOP_LISTENING`;
3. require `listening_state=OFF` and `mic_active=0`;
4. after at least five seconds require raw write position not to advance;
5. require rolling transcript segment count `0`;
6. require the unkept transient ring to report a cleared/new-session logical position according to implementation contract.

Previously created KEEP bundles must survive STOP.

## Live persona/exclusion proof

With FULL visible:

- provider must report `opinion_speaker=Ritsu` even if provider state is `offline`;
- deterministic capture/STOP/KEEP must not depend on `opinion_provider_state=ready`;
- a UI hierarchy dump of the package must not contain case-insensitive `Adam`.

## Reboot boundary

Reboot is a disruptive operator action and is not silently triggered by the main campaign. A separate explicit post-reboot canary must prove:

- listening is OFF;
- `mic_active=0`;
- no stale unkept raw/transcript session is restored;
- control shell can be recalled according to current Android boot policy.

Until that explicit test runs, `reboot-disarmed` remains unaccepted.
