# Android Phone Hands

## Mission

Give Home Center a phone body using the same observation/action/readback pattern as desktop Computer Hands.

Authorized lane:

`Home Center -> Tailscale -> Termux bridge -> Shizuku/rish -> Android`

Tailscale is transport only. Shizuku provides Android-shell authority. Termux hosts the bridge. Home Center remains the orchestrator and policy boundary.

## Existing evidence

`generated/shizuku_setup/home_center_shizuku_readiness.json` already records a green Termux/Shizuku/rish setup and successful Home Center pairing. Phone Hands extends that proven substrate; it does not replace it.

## Security boundary

The bridge:

- listens on TCP port `8787` by default;
- rejects peers unless their source address is in Tailscale IPv4 `100.64.0.0/10` or Tailscale IPv6 `fd7a:115c:a1e0::/48`;
- also requires `Authorization: Bearer <secret>`;
- stores the secret only in `~/.config/home-center/phone-hands.env` with mode `0600`;
- never writes that secret into GitHub, Drive, Home Center bucket objects, logs, or response bodies;
- exposes a fixed action vocabulary by default;
- keeps arbitrary Android shell disabled until `HC_PHONE_HANDS_ALLOW_SHELL=1` or the launcher is invoked with `--shell`.

Tailscale's own access policy should additionally restrict which tailnet identities may connect to the phone's Phone Hands port.

## Start on the phone

From the Home Center checkout inside Termux:

```sh
chmod +x tools/start_android_phone_hands.sh
./tools/start_android_phone_hands.sh --background
```

To deliberately expose arbitrary Android-shell execution to authenticated Home Center callers:

```sh
./tools/start_android_phone_hands.sh --background --shell
```

The launcher refuses to start if `rish` cannot prove Shizuku authority or if the Tailscale Android package is absent. It warns when it cannot prove that the Tailscale VPN is currently active.

## API

All calls require the bearer token.

### Health

`GET /v1/health`

Proves the Termux HTTP service is alive and `rish` can reach the Shizuku service.

### Observe

`GET /v1/observe`

Returns foreground window/app information, display size, battery state, and capability names.

`GET /v1/observe?ui=1`

Also returns an Android UIAutomator XML hierarchy.

`GET /v1/observe?screen=1`

Also returns a PNG screenshot as base64.

Both flags may be combined.

### Act

`POST /v1/act` with JSON.

Supported actions:

```json
{"action":"tap","x":500,"y":1200}
{"action":"swipe","x1":500,"y1":1500,"x2":500,"y2":400,"duration_ms":350}
{"action":"text","text":"hello world"}
{"action":"keyevent","key":"KEYCODE_ENTER"}
{"action":"home"}
{"action":"back"}
{"action":"recents"}
{"action":"launch","package":"com.android.settings"}
{"action":"launch","component":"com.android.settings/.Settings"}
{"action":"force_stop","package":"com.example.app"}
```

When shell is explicitly enabled:

```json
{"action":"shell","command":"dumpsys activity activities | head -40"}
```

Every successful action returns a fresh foreground-window readback so Home Center can verify that the requested mutation had an observable effect.

## Acceptance criteria

Phone Hands is **implemented** when the repository contains the bridge, launcher, and contract.

Phone Hands is **deployed** only when all of the following have been observed through the authorized lane on the actual phone:

1. Tailscale reports the phone connected to the expected tailnet.
2. `start_android_phone_hands.sh --background` remains alive after startup.
3. A different tailnet device receives HTTP 200 from `/v1/health` using the local bearer secret.
4. `/v1/observe?ui=1&screen=1` returns current foreground state, UI hierarchy, and a decodable screenshot from the phone.
5. Home Center performs `home`, `launch`, `tap`, `swipe`, `text`, and `back`, with foreground/UI/screenshot readback after each relevant action.
6. A non-tailnet connection attempt is rejected.
7. A tailnet request without the bearer secret is rejected.
8. Arbitrary shell is rejected by default and succeeds only after explicit enablement.
9. The phone worker is registered in Home Center with a stable device alias and capability map so callers do not need to know Termux/Shizuku implementation details.
10. Reboot/recovery behavior is exercised and documented; no success claim is made merely because files exist in GitHub.

## Next integration seam

The Home Center control plane should represent this as a Computer Hands worker/body, not as a new planning system. Suggested normalized capabilities:

- `screen.capture`
- `ui.inspect`
- `window.foreground`
- `input.tap`
- `input.swipe`
- `input.text`
- `input.keyevent`
- `app.launch`
- `app.stop`
- `nav.home`
- `nav.back`
- `nav.recents`
- `shell.android` when explicitly authorized

Desktop Hands and Phone Hands should then differ only in their adapter implementation, not in the orchestration contract.
