# Ritsu Control v0.9 -> Home Center -> Playwright: live bridge checkpoint

Date: 2026-10-23/24 UTC. Owner approved the Playwright switch and continuing integration of the existing Ritsu Control Android app, **not** the ChatGPT Android app.

## Bounded mission and measured result

**Server-side phone HTTP contract PASS against REAL authenticated ChatGPT tab**, without replacing Android's app UI, requiring the responding ChatGPT agent to call a tool, or reverse-engineering the private streaming protocol.

- Ritsu Control Android app: `android/ritsu-control/`, package `com.homecenter.ritsucontrol`, version `0.9.0`.
- Existing app transport: `HomeCenterSync.java` queues POST `/v1/ritsu/turn`, polls GET turn status and `/v1/ritsu/feed`, dedupes replies in `ConversationLedger`, and uses user-approved per-device Android Keystore pairing.
- Existing desktop gateway: `browser-porch/ritsu-android-gateway.mjs` + `ritsu-android-gateway-runner.mjs` + `ritsu-home-center-coordinator.mjs`. Already has token-checked HTTP API, durable session/turn coordinator and optional canonical voice return.
- New adapter: `tools/campaigns/ritsu-playwright/android-transport.mjs` behind `HOME_CENTER_RITSU_TRANSPORT=playwright`, with `HOME_CENTER_RITSU_BOUND_TAB_ID` and `HOME_CENTER_RITSU_BOUND_CONVERSATION_URL`.
- Opt-in gateway selector is implemented in `browser-porch/ritsu-android-gateway-runner.mjs`. Legacy transport remains the default until a controlled deployment.
- Exact browser binding was Chrome-for-Testing on `127.0.0.1:9236`, tab ID `A67990116B5D70AEB70B14563740A470`, URL `https://chatgpt.com/c/6adbd2f5-3cec-83e9-abce-8522a16b528b`. New Playwright sender does not open a new browser/tab.
- Source revision for proven Android HTTP real-browser smoke: `a7eb34c268542cb0804cc65379af33face9993f1` (isolated clean exact Git checkout on THECAULDRON).
- Live test uses an **isolated random-token loopback instance** of the SAME Ritsu Control HTTP gateway, wired to the real Home Center coordinator and browser, avoiding modification to the already-running port 19646 gateway.
- Captured receipt `%LOCALAPPDATA%\HomeCenter\RitsuPlaywrightAndroidSmoke\latest.json`, job `ritsu-android-test-721a2930fee44fbb`, state **`verified_phone_contract_not_physical_phone`**, one published feed event, actual answer:
  `🦀 This reply traveled through Ritsu Control, Home Center, and Playwright to reach ChatGPT.`
- UTF-8 answer SHA-256: `5afec8ba0bac14943dd6c781c93d65025604305bb77900f81be918c2c1f54991`. Byte-preserving Base64 readback through Home Center recovered the emoji correctly (Windows default console stdout garbles non-ASCII).
- Nine tests passed on THECAULDRON at `7d6842ce9ab0cffc60c3259202979eeb75609b24`; GitHub **Ritsu Playwright Reply Contract** workflow for the same SHA passed. Three adapter cases exercise the phone HTTP gateway, Home Center coordinator, UTF-8 feed, auth, duplicate-send protection, and uncertain dispatch.
- First real smoke at `8274692581cbb107cb8fdbcf1938361e9af8789b` correctly **blocked before send** with `composer_roundtrip_failed` because ChatGPT rich composer normalized blank lines; fixed whitespace-only normalization and safe own unsent draft recovery at `a7eb34c268542cb0804cc65379af33face9993f1`; verified the failed test's own marked unsent composer text was cleared, then the second smoke succeeded.
- Windows existing private Tailscale listener `100.68.37.106:19646` and voice relay `:19643` are listening; old gateway was PID 19028 at inspection, running `C:\Users\dclar\workspace\home-center-ritsu-e2e\browser-porch\ritsu-android-gateway-runner.mjs`.
- Pixel 10 Pro XL phone responded to Tailscale ping via `100.117.17.119` in 67ms, but phone TCP ports 8022 and 22 were closed; Home Center Phone Hands registered heartbeats were stale. No live phone package-query/install or receipt sync was obtained. **Do not claim phone APK installed or phone audio heard.**

## Android APK artifact

- Ritsu Control v0.9 Android CI workflow `ritsu-control-contract.yml` succeeded at run `40046396775` on the code branch revision `a7eb34c268542cb0804cc65379af33face9993f1`.
- Debug APK is the `app-debug.apk` from artifact `12541667026` named `ritsu-control-v0.9-home-center-text-bridge-debug-apk`. ZIP and standalone APK have been materialized in the current ChatGPT response working container.
- APK SHA-256 `82f124f8241bf20b221152666957332ca4225693d02673703971ea5b6949e7ca`. This is a debug APK, not production signing or device-install proof.

## Live deployment gate: still CLOSED

The actual Android phone has **not** proved that `com.homecenter.ritsucontrol` is installed, paired or reading the feed, and the existing live port-19646 gateway still uses its legacy transport. The Playwright adapter is implemented and real HTTP simulated-phone smoke is verified, but it has **not** been activated in the running production gateway.

The locally active Manic Accessibility repository guardrail for a potentially impactful live gateway swap returned `PAUSE_FOR_GUARDS` with unknown baseline facts. Preserve this result without storing private health data or converting uncertainty into assumptions. Continue reversible code/build/read-only preflight; do not silently stop/replace the existing listener or force device installation until the gate permits.

Never confuse a GitHub Actions passing build, a gateway queue/HTTP 202, an authenticated health 200, or a server-side simulated phone loopback reply with a verified physical Android app receipt or audible playback.

## Next bounded slice

1. Inspect the actual phone package/Keystore pairing state via an authorized fresh Phone Hands/device lane; if unavailable, provide current verified v0.9 APK for user installation rather than assuming it already exists.
2. Once deployment is permitted, move the **exact pinned** code into the existing 19646 Home Center gateway using a rollback-capable campaign, preserving the existing phone-only capability file, session namespace, coordinator-state directory, voice relay and Tailscale-only bind. Do not modify `:19643` or use a new public endpoint.
3. Verify on the **physical Ritsu Control app**: compose a control turn -> POST accepted -> Playwright ChatGPT response retrieved -> GET feed reflects exactly one complete UTF-8 reply with matching turn ID -> app ConversationLedger visibly shows that reply. Distinguish text delivery, audio enqueue, receiver consumption, and user HEARD independently.
4. Test multi-line response with code and URL, and only then promote the integration into the existing Git-first coding/script campaign interface. Do not execute returned code without normal pinned SHA, testing and existing campaign gates.

Current truthful milestone: **Android API contract + real browser PASS; Android package built; physical Android delivery NOT VERIFIED; existing service not swapped.**
