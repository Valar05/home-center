# Ritsu Warm v1: Home Center typed speech operation

**Status:** Source implemented on `feature/ritsu-typed-voice-v1`, CI integration pending, not yet deployed or commissioned on THECAULDRON.

## Mission

Replace chat → Computer Hands `shell.exec` with one narrow Home Center operation, `ritsu.voice.speak`.

    ChatGPT → Home Center typed voice ticket → dedicated outbound THECAULDRON voice worker
             → immutable Ritsu | Warm | v1 Qwen local API via ritsu_say.py
             → existing Windows relay → existing Tailscale Termux receiver

No direct SSH, PowerShell or arbitrary command is accepted through this voice operation. The Windows worker executes only a pinned script with a private temp `--text-file`, never injected shell text. It does not replace the approved voice profile, reference recording or relay.

## Chat-facing commands

`ritsu.voice.speak` with `{requestId, text, voice:"warm-v1", delivery:"phone"}`. Optional `chunks` constrains expected relay receipts. Max 5000 characters, no shell/action/engine fields, idempotent request IDs with immutable transcript hash.

`ritsu.voice.status` with `{requestId}` returns queued, leased, enqueued, failed or maintenance. Enqueued is **never** equivalent to Android ACK or HEARD.

`ritsu.voice.worker.register` with a unique requestId issues a single-use 10-minute bootstrap. Pass this secret directly to THECAULDRON using a private operator path, **never** paste it into ChatGPT. The Windows worker stores its bearer credential in a local ACL-protected file.

## Maintenance: Turbo ASMR

`C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\RITSU_WARM_ASMR_MAINTENANCE` prevents voice generation. The dedicated voice worker never starts or restarts Qwen, never loads a fallback model, and never competes with intentional Turbo ASMR GPU use. A separate relay watchdog is independent of model availability.

## Kokoro retirement and cleanup

The old `local_voice.ticket.create` operation is a separate **Kokoro** fixed `af_heart` pipeline. It is not, and must never be, a Ritsu Warm v1 fallback. This branch's deterministic integration removes old `local_voice` operations from Home Center's advertised/dispatchable MCP operation registry.

For safety, the legacy Kokoro HTTP endpoint, Firestore tickets, older worker files, and historical artifacts remain intact until a dependency audit proves nothing else relies on them. This is a *quarantine and deprecation*, not destructive blanket deletion. After Warm v1 ticket success, separately retire Kokoro startup/worker and deploy removal if confirmed unused.

## Deployment gates

1. CI validates source and integration patch. Review PR; merge only after green tests.
2. Deploy updated Home Center MCP dispatcher **and** HTTPS `ritsuVoice` function. Read back capabilities to confirm `ritsu.voice.speak` exists. No capability claim before deployment.
3. Bootstrap worker privately; install it as an outbound-only THECAULDRON supervisor only **after** a canary and explicit clearance of Turbo ASMR maintenance.
4. Verify fixed text, sequence, synth receipt, relay enqueue, Android download and ACK, and user-confirmed HEARD.
5. Test failure/retry/idempotency, simultaneous chats, lease expiry, reboot/login, paused model, worker downtime. Lease is 20 minutes; ambiguous crash after enqueue before cloud completion still needs a durable local receipt journal to prevent re-delivery. Do not claim exactly-once or fully hardened until tested.
6. Remove obsolete Kokoro assets only after dependency inventory and a backup/rollback receipt.

## Sources

- `docs/RITSU_PHONE_AUDIO_LAWS.md` governs the exact Warm v1 identity and current phone relay.
- `functions/ritsu_voice_api.js` is the narrow cloud dispatcher and outbound-worker ticket API.
- `workers/ritsu_warm_ticket_worker.py` is the fixed Windows voice worker.
- `tools/apply_ritsu_voice_patch.mjs` adds operation and HTTPS export, deprecates Kokoro MCP exposure.
- `.github/workflows/ritsu-typed-voice-integrate.yml` tests and stages integration wiring, no automatic production deployment.
