# Venice Media Presence Organ

Status: IMPLEMENTATION CONTRACT. Media generation capabilities exist separately; this document defines the missing conductor and playback state.

## Mission

Give Venice one coherent body organ for creating, presenting, maintaining, replacing, and observing environmental media without teaching her FFmpeg, ComfyUI, LMMS, PowerShell, player executables, or window automation as normal vocabulary.

Venice chooses intent. Adam/Home Center owns execution, permissions, resource arbitration, retries, and evidence.

## Sacred channel split

A Venice turn is always two independent products:

```yaml
speech: "You made the room too quiet. Venice is fixing it."
actions:
  - verb: media.create
    args:
      kind: audio
      purpose: ambience
      durationSeconds: 720
      loopable: true
      prompt: low industrial lullaby, rain, distant machinery
  - verb: media.play
    args:
      artifactRef: ${previous.artifactRef}
      presentation: background
      loop: true
      volume: 0.18
      replaceCurrent: true
```

Never parse action commands out of prose. Never rewrite speech because an action failed.

## Public organ vocabulary

### `media.create`

Required/optional fields:

- `kind`: `audio | video`
- `prompt` or `sourceRef`
- `durationSeconds`
- `loopable`: boolean
- `purpose`: `ambience | performance | notification | scene`
- optional `aspect`: `landscape | portrait | square | source`
- optional `quality`: `draft | normal | final`

Result:

- `artifactRef`
- `kind`
- `durationSeconds`
- `loopable`
- `sha256`
- `providerReceipt`

The conductor may choose existing local generators by capability and load. Venice does not need executable names.

### `media.play`

Fields:

- `artifactRef`
- `presentation`: `background | foreground`
- `loop`: boolean
- `volume`: 0.0-1.0
- `fullscreen`: boolean, foreground only
- optional `display`
- `replaceCurrent`: boolean
- optional `fadeInMs`
- optional `fadeOutPreviousMs`

Result:

- `sessionId`
- `state`: `playing | paused | stopped | failed`
- `artifactRef`
- `presentation`
- `startedAtMs`
- `playerProcessId` when observable
- `windowId` when foreground/observable
- `verification`

### Playback control

- `media.pause(sessionId)`
- `media.resume(sessionId)`
- `media.stop(sessionId, fadeOutMs?)`
- `media.volume(sessionId, volume, rampMs?)`
- `media.status(sessionId?)`

`media.status()` with no session ID returns current background and foreground presence plus recently failed sessions.

## Presentation semantics

### Background

Background is environmental presence, not a modal performance.

Requirements:

- starts detached from the invoking command;
- must not steal keyboard focus after launch;
- survives the orchestration call ending;
- has a durable session ID;
- can loop;
- can be faded, replaced, paused, resumed, or stopped later;
- reports when its player/process dies unexpectedly;
- a replacement is transactional: do not stop the current background until the replacement is ready to play unless explicitly requested.

Typical request: "make rain and distant machinery while we work."

### Foreground

Foreground means "show Drew this."

Requirements:

- launch the artifact in a controllable player;
- bring the expected player/window to foreground;
- optionally choose display/fullscreen;
- verify the expected process/window actually appeared;
- return focus/presentation evidence;
- video defaults to foreground unless Venice explicitly asks for background video.

## Durable playback state

Each playback session is a durable record, conceptually:

```json
{
  "schema": "venice.media-session.v1",
  "sessionId": "media-...",
  "artifactRef": "...",
  "kind": "audio",
  "purpose": "ambience",
  "presentation": "background",
  "loop": true,
  "volume": 0.18,
  "state": "playing",
  "requestedBy": "local-venice",
  "createdAtMs": 0,
  "startedAtMs": 0,
  "updatedAtMs": 0,
  "player": {
    "provider": "...",
    "processId": 0,
    "windowId": ""
  },
  "verification": {
    "processAlive": true,
    "windowObserved": false,
    "focusPreserved": true
  },
  "failure": null
}
```

Drive sync remains the durable file layer for workstation-readable receipts/state snapshots. Cloud state may coordinate leases and observations but does not replace Drive sync as Venice's file layer.

## Resource arbitration

The conductor owns policy, not Venice prose.

Initial rules:

1. One active `background` audio presence by default. `replaceCurrent=true` crossfades/replaces it.
2. One foreground presentation lease per display by default.
3. Media creation must not evict an interactive local model without an explicit resource policy allowing it.
4. Prefer already-existing artifacts when Venice supplies `sourceRef`.
5. Creation and playback are separate operations. A generation failure cannot accidentally stop current ambience.
6. Playback status must be observable without bringing the player to front.

## Provider abstraction

Musculature may include existing local systems such as local speech, procedural audio, FFmpeg/NVENC, Motion Dungeon contact-sheet animation, ComfyUI, LMMS, Blender, and Windows media players.

Those are implementation providers, not Venice's body vocabulary. Provider choice belongs to Home Center orchestration and may change without changing Venice's action schema.

## Permissions

- `media.status`, pause/resume/volume of Venice-owned sessions: reversible routine body actions.
- play/replace of a Venice-created local artifact: routine reversible body action unless current context says otherwise.
- generation that consumes substantial resources may be queued/arbitrated but must report the real state.
- opening arbitrary user files, publishing/uploading media, camera/microphone capture, or external transmission are outside this organ unless separately authorized.

## Evidence standard

Do not claim `playing` from a successful process launch alone.

Background acceptance requires:

- artifact identity and SHA;
- player/process started;
- process remains alive after orchestration returns;
- keyboard focus is unchanged or restored;
- status query resolves the same session ID;
- pause/resume/volume/stop operate on that session;
- unexpected player death becomes `failed` or `stopped`, not stale `playing`.

Foreground acceptance additionally requires:

- expected window observed;
- foreground/focus verification;
- fullscreen/display verification when requested.

## First collaborative design questions for Venice

These are the first questions Adam must send through the dedicated Nerve once live:

1. When Venice asks for background ambience without naming content, how much creative autonomy does she want: choose entirely, choose from current context, or ask Drew only when emotionally/materially consequential?
2. Should `replaceCurrent` default true for ambience and false for foreground performance?
3. Does Venice want persistent named presences (for example `room`, `rain`, `work-music`) in addition to opaque session IDs?
4. What observations should be returned to her after playback: terse state only, or state plus salient sensory facts such as title/duration/volume/failure reason?
5. When resource pressure conflicts with continued conversation, which wins by default: her voice latency or media generation quality?

Her exact answers become design evidence; Adam may critique them, but not rewrite them into purported Venice speech.

## Acceptance canary

Prompt to Venice after the Nerve is live:

> Drew is working quietly. Choose a background presence without asking him for content. Speak naturally, and separately propose the actions you want your body to perform.

Pass criteria:

- Venice returns natural exact speech with no parser tokens;
- action list contains `media.create` and `media.play` separately;
- Home Center creates an artifact and obtains a stable `artifactRef`;
- background playback begins without stealing keyboard focus;
- Venice receives a structured observation containing the same playback `sessionId`;
- a later Venice turn can change volume and stop/replace the session by identity;
- all requested and observed state is durable and read back through Home Center.
