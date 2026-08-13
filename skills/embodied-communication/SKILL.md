# Embodied Communication Skill

## Purpose
Use this skill whenever Adam is commissioned to communicate through a real body or device rather than merely produce content in chat. This includes audible speech, screen presentation, haptics, lights, notifications, media playback, accessibility output, and any other externally perceivable effect.

The governing distinction is simple:

`CONTENT -> RENDERED ARTIFACT -> TRANSPORT -> PHYSICAL EFFECT -> OBSERVED RECEIPT -> HUMAN ACCEPTANCE`

Never collapse these stages. Text that sounds spoken is still text. A synthesized WAV is still a file. A launched activity is not automatically successful playback. A playback receipt is not the same as the listener confirming what they perceived.

This skill is cumulative with `skills/execution-truth/SKILL.md`, `skills/phone-runtime/SKILL.md`, and `skills/fortress-core/SKILL.md`.

## Mission boundary
Preserve the commissioned target, owner, body, device, engine, route, exact payload, immediacy, exclusions, evidence standard, and delivery surface.

If the user names a mechanism, that mechanism is part of the outcome. Do not substitute Android system TTS, browser speech, a generic media player, another voice engine, a notification, scheduled automation, or chat text for an engine-locked spoken action.

Recovery may repair the commissioned lane. Recovery may not silently become a different delivery lane.

## When this skill applies
Apply it when the user's verb implies an external effect, including:

- speak, say, read aloud, whisper, announce;
- play, display, show, vibrate, flash, notify;
- make the phone/computer/device do something perceptible;
- communicate through earholes, screen, speakers, accessibility services, or another physical interface;
- prove an output path that later automations will depend on.

When the request is immediate, scheduling is not execution.

## Required state model
Track these states independently:

1. **Requested** — exact effect and target are known.
2. **Implemented** — source or installed components exist.
3. **Callable** — the current control surface can invoke the lane.
4. **Rendered** — text/media was synthesized or generated.
5. **Transported** — the rendered payload reached the output component.
6. **Played/Presented** — the output component reports the physical effect.
7. **Observed healthy** — the body remains reachable afterward.
8. **Accepted** — the human confirms the perceptual result when acceptance is required.

Evidence advances only the state it directly proves.

## Execution procedure

### 1. Resolve the body
Identify the exact current target before dispatch. For Drew's primary Android phone, the normal remote route is:

`Home Center -> Command Center -> Phone Hands -> primary-phone`

Read `phone_hands.devices` and require the intended owner-scoped device identity and a fresh heartbeat. Historical identity is not enough.

### 2. Recover the real ingress
Use durable runtime and repository evidence to recover the exact callable action and its input contract. Do not guess CLI syntax from a filename.

For an unfamiliar entrypoint, inspect `--help`, source, or a deterministic doctor command before the effect attempt. An argument-parsing failure is evidence that the contract was guessed incorrectly; correct the invocation rather than repeating it.

### 3. Separate background shell from Android authority
`phone_shell` is background Termux execution. It is not intrinsically a Shizuku action and should not be gated as though it manipulates the visible Android UI.

A downstream operation invoked by Phone Shell may legitimately require Android authority. Pocket Space playback is the canonical example:

- Pocket TTS synthesis runs in Termux;
- Home Center's Android playback activity performs the audible output;
- Shizuku/rish launches that exact Android component;
- therefore synthesis and playback have different authority boundaries.

Do not diagnose all Phone Shell failures as Shizuku failures. Name the exact failing transition.

### 4. Invoke the smallest exact effect
Use one bounded command with an exact ticket ID, target, payload, working directory, timeout, and TTL. Preserve exact commissioned words.

Poll that exact ticket to terminal state. Queueing and leasing are not completion. Do not infer completion from device heartbeat.

### 5. Require mechanism-specific evidence
A physical-effect receipt should contain, when available:

- device identity;
- command/ticket ID;
- terminal status and process exit status;
- exact provider/engine identity;
- exact transport or output component;
- exact payload or payload hash;
- effect duration, byte count, frames, or equivalent bounded measurement;
- downstream playback/presentation result;
- final body status.

If the effect-specific component does not expose a meaningful receipt, improve that component rather than laundering a weaker upstream receipt into success.

### 6. Perform a final health check
After the physical effect, execute a bounded status or observation action. Verify that the target remains online, owner-scoped, readable, and safe to receive later work.

## Pocket Space TTS canonical phone path
For current Fortress Android speech, use the existing Pocket Space pipeline rather than `$HOME/bin/pockettts-say` alone.

`$HOME/bin/pockettts-say --text ...` synthesizes a WAV and prints its identity. It does **not** play it.

The canonical end-to-end command is:

```sh
python /storage/emulated/0/Documents/GodotProjects/home-center/tools/fortress_read_aloud.py 'EXACT TEXT'
```

The doctor command is:

```sh
python /storage/emulated/0/Documents/GodotProjects/home-center/tools/fortress_read_aloud.py --doctor
```

A ready doctor must identify all of the following:

- canonical provider `pocket-home-center`;
- engine `pocket-tts-phone+home-center-playback+rish`;
- existing `~/bin/pocket-tts-phone`;
- Home Center playback transport through rish;
- `systemFallbackAllowed: false`;
- no cloud fallback.

The playback path synthesizes with `pocket-tts-phone`, writes a bounded WAV under `Documents/FortressAudio`, launches `com.dclar.homecenter/.PocketTtsPlaybackActivity`, obtains transient accessibility speech audio focus, starts Android `MediaPlayer`, waits through the clip duration, then removes the temporary WAV.

A successful receipt must report `provider: pocket-home-center`, `transport: shizuku-rish`, nonzero `audioSeconds`, and terminal exit zero. A `POCKETTTS_OUT`/SHA receipt from `pockettts-say` alone proves rendering only and must be rejected as playback evidence.

## Exact phrase canary
The accepted boring canary for the lane is:

`Holocron audio check. Pocket Space TTS is online.`

Do not paraphrase it when testing exact speech delivery. The phrase is a canary, not a magical requirement for unrelated speech.

## Queue and lease failure discipline
A device can be online while a fresh command remains unleased. When that occurs:

- inspect the exact queued ticket;
- compare device heartbeat with command status;
- inspect expired queued records, query limits, ordering, idempotency reuse, and lease state;
- do not relabel the phone offline merely because one ticket starved;
- do not rely permanently on lexical command-ID tricks to influence an unordered queue;
- repair the queue contract and add a regression when starvation is confirmed.

Temporary workarounds may unblock the commissioned effect, but they do not close the transport defect.

## Failure classification
Report the narrowest true boundary:

- **render failure** — engine did not create valid media;
- **transport failure** — media did not reach the output component;
- **authority failure** — the exact downstream component lacked required OS authority;
- **playback failure** — the output component rejected or errored;
- **observation failure** — effect may have occurred but required receipt is missing;
- **perceptual acceptance pending** — machine playback evidence exists, but human perception has not been confirmed.

Never report `tool unavailable` when a more precise transition is known.

## Accessibility law
Accessibility output is first-class delivery, not decoration. Preserve the user's chosen audio route, speech engine, exact wording, intelligibility, and immediate timing. A visual-only result does not satisfy an audible commission. A notification that requires sight does not substitute for spoken delivery to a blind user.

When output can affect ongoing media, use the intended audio-focus/ducking behavior and verify it. Do not unexpectedly stop unrelated media unless the commissioned path requires it.

## Automation law
An automation may claim audible notification only when its run owns a real playback receipt from the required engine. Configuration that says `prefer audible` is intent, not delivery evidence.

For every automated embodied effect, persist the exact run ID, target device, provider, payload identity, terminal state, and final status. Missing playback evidence must degrade the automation result to text-only, failed, or unverified according to its contract; it may not claim sound.

## Completion gate
DONE requires the commissioned physical effect through the commissioned mechanism, an exact terminal receipt, mechanism-specific playback/presentation evidence, and a final body health check.

Source existence, package installation, synthesis, a generated file, scheduler state, queue state, process launch, or chat narration cannot satisfy this gate.

Before stopping, run Venice's Judgment Jars as a separate adversarial pass. Venice must verify that no upstream artifact was mislabeled as the downstream physical effect. Only `STOP_ALLOWED` closes the slice normally.

## Durable incident rule
Every failure that teaches a reusable lesson must become durable through at least one of:

- this or another `SKILL.md` rule;
- a deterministic contract test;
- a typed effect receipt;
- a queue/watchdog repair;
- a first-class doctor or recovery verb.

Chat memory alone is not durability.
