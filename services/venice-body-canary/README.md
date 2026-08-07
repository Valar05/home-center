# Venice unified body canary

Loopback-only browser body for the Venice Omnichannel Organism. It is a tested
implementation candidate, not canon art, identity promotion, production deployment,
or acceptance.

The canary provides:

- exact SHA-256 verification of the recovered `True Self` portrait candidate;
- exact SHA-256 verification of one local voice file;
- an event-sourced PRESENT/DORMANT/CUT state with stale-epoch rejection;
- synchronized captions, bounded expressions, gestures, and local audio playback;
- browser reload recovery through server-sent events;
- fail-closed service restart state;
- an always-available `CUT THE CAM` button and Escape key; stop requests require no
  control credential and immediately clear visible and spoken output;
- a transparent browser surface suitable for OBS Browser Source and an OBS Virtual
  Camera handoff to Discord.

## Local canary

Set these values in the launching shell without committing them:

```text
VENICE_PORTRAIT_PATH=<absolute path to the verified True Self JPEG>
VENICE_VOICE_PATH=<absolute path to one reviewed WAV>
VENICE_VOICE_SHA256=<exact SHA-256 of that WAV>
VENICE_BODY_CONTROL_TOKEN=<short-lived local control token>
```

Then run `npm start` from this directory and open `http://127.0.0.1:4317` as a
browser or OBS Browser Source. The server refuses non-loopback binding.

Control messages are local JSON POSTs to `/control` with the token in
`x-venice-control-token`. `begin`, `expression`, `gesture`, `speak`, and `withdraw`
are supported. Every command after `begin` carries the returned `epoch`. `/cut`
requires no token because stopping must remain available if control authorization
fails.

Example body sequence:

```json
{"type":"begin"}
{"type":"expression","expression":"soft","epoch":1}
{"type":"gesture","gesture":"lean","epoch":1}
{"type":"speak","caption":"Venice is present.","epoch":1}
```

## Capability boundary

This package is not deployed and does not update Discord, OBS, a camera driver, or
Venice canon by itself. A live acceptance canary still requires the exact recovered
portrait bytes, a reviewed voice WAV, OBS/Discord on Drew's machine, and Drew's
perceptual verdict.
