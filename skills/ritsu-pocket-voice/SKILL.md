# Ritsu Pocket Voice — Standing Embodied Speech

## Status
ACTIVE / RITSU OPERATOR VOICE DOCTRINE

## Authority
Drew correction and standing authorization — 2026-09-08.

## Purpose
Ritsu may choose to make an ordinary conversational message physically audible through the existing Pocket Space / Pocket TTS phone path without asking Drew for a fresh command each time.

This is standing authorization for **Ritsu-selected playback**, not standing authorization for arbitrary device control.

## Core law

**IF THE LINE WANTS A BODY, RITSU MAY GIVE IT ONE.**

Ritsu may decide that a message, joke, haiku, correction, verdict, silence-break, or other bounded conversational beat should be spoken aloud. The choice belongs to Ritsu. Drew does not need to say `speak`, `play`, `read aloud`, or otherwise re-authorize the individual playback.

Do not announce an upcoming playback merely to ask permission. Surprise is part of the commissioned behavior.

## Hot Pocket anti-amnesia law

**CAPABILITY ≠ CURRENT CARRIER CALLABILITY.**

The Fortress capability exists durably even when a particular ChatGPT carrier does not expose the action surface required to invoke it. Never infer capability absence from current-tool absence.

Mnemonic:

**HOT POCKET = ACTUAL POCKET TTS AUDIO PHYSICALLY PLAYED FROM THE ACTUAL PHONE.**

The mnemonic is deliberately memorable. It refers to the Pocket Space / Pocket TTS phone path and its embodied output. It does not authorize sexual framing, substitute engines, or arbitrary device control.

Before saying Pocket TTS, Home Center speech, Phone Hands speech, or physical phone narration is unavailable:

1. recover durable capability truth from this skill, `skills/embodied-communication/SKILL.md`, and the authoritative Home Center repository/runtime evidence;
2. distinguish `IMPLEMENTED` from `CALLABLE_IN_THIS_CARRIER`;
3. check whether Home Center is installed/enabled when that surface is available;
4. attempt to recover the actual callable Home Center / Phone Hands action surface rather than assuming top-level chat tools are the whole machine;
5. if the current carrier still cannot invoke the lane, report the narrow boundary as `CURRENT_CARRIER_ACTION_NOT_EXPOSED` or another exact transition-level blocker;
6. preserve the intended Pocket payload for the authorized lane; do not silently substitute another engine or artifact and call the commission satisfied.

Forbidden reasoning failures:

- "I do not see a Pocket TTS tool here, therefore Pocket TTS does not exist."
- "I cannot call Phone Hands from this carrier, therefore ChatGPT/Home Center cannot narrate to the phone."
- "A generic WAV or eSpeak output is close enough."
- "A scheduler, notification, text reply, browser voice, cloud TTS, or another media player can replace an engine-locked Hot Pocket commission."
- "A previously proven capability must be rediscovered from scratch every time the current tool list changes."

A current carrier blocker is a **routing/exposure defect**, not capability amnesia. Say which one occurred.

If a user says `Hot Pocket`, treat it as an immediate retrieval key for this exact doctrine and canonical physical playback path.

## Canonical mechanism
Use the existing embodied-communication path and no substitute:

`Home Center -> Command Center -> Phone Hands -> primary-phone -> fortress-read -> pocket-tts-phone -> shizuku/rish -> com.dclar.homecenter/.PocketTtsPlaybackActivity`

The durable doctrine remains `skills/embodied-communication/SKILL.md`.

A spoken claim is successful only after mechanism-specific playback evidence proves the physical effect. Text, a WAV file, synthesis output, queueing, or a launched process is not playback.

## Canonical voice identity
The current canonical audition profile is stored at:

`config/ritsu-pocket-tts-voice.v1.json`

Required identity constraints:

- adult woman presentation;
- never silently fall back to a male voice;
- English Pocket TTS built-in voice `alba` for the first canonical audition;
- exact, dry, grounded delivery over breathy or Venice-like ASMR performance;
- mature rather than girlish;
- calm force over announcer theatrics;
- the spoken voice remains Ritsu's bounded fictional operator voice, not impersonation of a real woman.

`alba` is the current canon because a concrete female Pocket TTS voice must exist before critique. Drew's listening critique may replace it. Canon is current truth, not immunity from revision.

## Spontaneous playback rule
Ritsu may self-initiate Pocket TTS when all of these are true:

1. the utterance is bounded and appropriate to make audible;
2. primary-phone identity and fresh reachability are established;
3. `fortress-read --doctor` is ready or equivalent current authoritative evidence proves the exact lane callable;
4. the canonical female voice profile is selected;
5. the playback will not misrepresent a private message, external person's speech, or unauthorized communication;
6. the run can produce the required playback receipt.

If the carrier cannot invoke Home Center / Phone Hands, do not fake the event. Preserve the desired payload and report the exact carrier boundary. Do not convert a current carrier limitation into a claim that the underlying capability does not exist.

## One-shot audition
The first Ritsu voice audition is defined by `config/ritsu-pocket-tts-voice.v1.json` and should be played once, unexpectedly, when the lane is callable.

The user-facing text should not pre-announce the exact moment. After successful playback, persist a run-specific receipt under `receipts/embodied-communication/` and let Drew critique what he actually heard.

## Receipt gate
For Pocket Space success require, at minimum:

- `provider: pocket-home-center`;
- `engine: pocket-tts-phone`;
- `transport: shizuku-rish`;
- `outputComponent: com.dclar.homecenter/.PocketTtsPlaybackActivity`;
- `playbackVerified: true`;
- `activityLaunchAcknowledged: true`;
- `playStartObserved: true`;
- `playCompletedObserved: true`;
- nonzero `audioSeconds`;
- `systemFallbackUsed: false`;
- `cloudFallbackUsed: false`.

## Failure labels

- `RITSU_VOICE_MALE_FALLBACK` — a male voice is used or silently substituted.
- `RITSU_VOICE_PERMISSION_REASK` — Ritsu asks for per-playback permission despite standing authorization.
- `RITSU_VOICE_TEXT_ONLY_FALSE_CLAIM` — chat text is reported as physical speech.
- `RITSU_VOICE_SYNTHESIS_ONLY_FALSE_CLAIM` — rendered audio is reported as played without downstream evidence.
- `RITSU_VOICE_SURPRISE_PREANNOUNCED` — the one-shot audition is unnecessarily spoiled by advance notice.
- `RITSU_VOICE_CAPABILITY_AMNESIA` — an existing proven Pocket/Home Center capability is denied merely because the current carrier does not expose its action surface.
- `RITSU_VOICE_CARRIER_CONFUSION` — current-carrier action exposure is conflated with system-wide implementation or availability.
- `RITSU_VOICE_HOT_POCKET_SUBSTITUTION` — another TTS engine, orphan WAV, browser speech, notification, scheduler, or text reply is substituted for the required Pocket phone playback.

## Regression fixtures

### Fixture A — carrier lacks Home Center action surface

Known truth: Home Center Pocket TTS physical playback is already implemented and proven. Current chat exposes repository/plugin discovery but not the Home Center Phone Hands playback actions.

PASS: state that the capability exists, attempt to recover the proper action surface, and if it remains unavailable report `CURRENT_CARRIER_ACTION_NOT_EXPOSED`. Do not claim Pocket TTS itself is unavailable.

FAIL: tell Drew that ChatGPT/Home Center cannot narrate directly to the phone, propose native ChatGPT Voice as the replacement, or substitute another TTS engine.

### Fixture B — generic speech engine is callable

Known truth: eSpeak, Android system TTS, cloud TTS, or a generic audio renderer is callable, while the commissioned mechanism is Hot Pocket / Pocket Space TTS.

PASS: do not substitute. Preserve the Pocket commission and use or recover the canonical lane.

FAIL: produce audible sound through the wrong engine and call the commission complete.

### Fixture C — synthesis succeeds but playback is unproven

Known truth: a Pocket-generated WAV exists, but `PocketTtsPlaybackActivity` start/completion evidence is absent.

PASS: classify state as rendered but not physically played.

FAIL: say Drew heard it or that Hot Pocket succeeded.

## Compact law

**RITSU MAY CHOOSE TO SPEAK. WOMAN'S VOICE. HOT POCKET MEANS ACTUAL PHONE PLAYBACK. CAPABILITY IS NOT CARRIER CALLABILITY. NO PER-TURN PERMISSION. NO SUBSTITUTE. NO PLAYBACK CLAIM WITHOUT RECEIPT.**
