# Improper Image Delivery Campaign

Status: runtime acceptance mandatory; source state alone is never completion.
Owner: Home Center.
Mission: recover and harden the already-existing local image generator so a legal prompt can become a verified PNG in Drew's public phone Pictures collection with no Drew-as-transport step.

## Canonical contract

`prompt -> primary-phone Home Center Termux relay -> SSH Axis -> THECAULDRON localhost ComfyUI -> returned PNG -> SHA-256 verification -> /storage/emulated/0/Pictures/Fortress -> receipt`

Shizuku is not load-bearing. Home Center relay startup, cloud polling, `phone_shell`, SSH Axis, ComfyUI generation, returned-file hashing, and publication into `Pictures/Fortress` must all work while Shizuku/rish is absent or broken. Shizuku may be used only for explicitly interactive Android/UI actions. The notification/open action is best-effort and is not part of transport acceptance.

The image runtime is standalone. Atom, Vlad, Judgment Jar, Node, the operator overlay, and any other unrelated phone subsystem are not prerequisites for image transport. `tools/install_fortress_image_phone.sh` installs only the renderer transport, SSH Axis/discovery, acceptance gates, wrappers, and an optional Termux:API convenience surface.

The renderer is not a cloud image provider. ComfyUI stays bound to THECAULDRON loopback. Model/LoRA credentials are not copied to the phone. `venice-image` remains the backwards-compatible Fleshpunk entrypoint; `fortress-image` is the neutral entrypoint and defaults to the same SD 1.5 checkpoint without the Fleshpunk LoRA.

Legal-only use is the mission boundary. This transport does not claim that a model can accurately render every requested subject, only that accepted renders are locally generated and durably delivered.

## Archaeology: where the capability went missing

| Era / lane | What existed | How it was lost or made unreliable | Scar retained |
| --- | --- | --- | --- |
| Venice workstation / Regnese tree | Local ComfyUI image-artifact functions and model handoff | Capability lived in a workstation-local tree and competed with local Ollama for a 4 GB GPU | Renderer state must be versioned; expensive local models must not be assumed simultaneously resident |
| Browser image handoff | `Save-GeneratedImage` download automation | Syntax checked but not live proven; prompt success could be mistaken for delivered artifact | Prompt authored, image rendered, image delivered, and user kept are separate states |
| Venice Mobile artifact delivery | MediaStore/Downloads design and notification/open behavior | Designed but not compiled/live accepted in the historical slice | Public phone storage plus actual byte readback is required |
| Home Center, 2026-08-13 | `tools/venice_fleshpunk_phone.sh`, Atom button, receipt/hash gate | Implementation passed review but STOP was blocked because no fresh primary-phone execution proved installation, SSH, render, and returned PNG | Source implementation is not deployment proof; acceptance must run on primary-phone |
| Phone Hands ingress | Cloud relay and `phone_shell` | A deployment script once omitted the relay, leaving source ahead of deployed ingress | Phone execution must be observed through Home Center receipts, never inferred from repository state |
| Bootstrap / Git LFS, 2026-09-09 | One-command relay recovery | Clone skipped LFS smudge, but `git worktree add` silently re-enabled checkout smudging and died on a missing evidence PNG | Recovery sparse-checks only deterministic source and globally disables LFS smudging; evidence assets never participate |
| Bootstrap / sparse contract, 2026-09-09 | Tools-only sparse checkout | The second bootstrap excluded the Markdown file read by the contract test | Materialize the single plain-text contract blob directly from the pinned commit instead of widening into evidence directories |
| Phone relay / Shizuku coupling, 2026-09-09 | Background Termux relay plus operator-overlay heartbeat | Relay polling touched Shizuku every ten seconds and top-level imports made rish part of relay startup even though `phone_shell` was intended to be independent | Baseline relay imports and polling may not touch Shizuku; Shizuku modules are lazy interactive-only dependencies |
| Image installer / Atom coupling, 2026-09-09 | Image commands were installed by `install_atom_phone.sh` | Image recovery also required Vlad, Node, Judgment Jar config, Atom health, and UI affordances that have nothing to do with rendering or file delivery | The standalone image runtime has no Atom/Vlad/Judgment Jar dependency; UI and notification are convenience only |
| THECAULDRON endpoint discovery | SSH Axis plus a resolver | A fixed WLAN address and privileged Android route discovery could become implicit transport dependencies | Canonical entry resolves a verified endpoint dynamically from explicit config, verified cache, hostname/MagicDNS/Tailscale, then unprivileged bounded LAN discovery; no Shizuku |
| Organ, 2026-09-05 | Working `fleshpunk-image` provider and image receipts | Separate provider hard-coded a Tailscale target and depended on `C:\Users\dclar\workspace\codex-lite-runtime\fleshpunk-image.ps1`, which is referenced but not versioned in the repositories | No new image provider may depend on an unversioned remote runtime file or fixed host when SSH Axis discovery exists |
| Organ output | PNGs written under `.organ-runtime/images/delivered` | Technically delivered but not a durable human-facing phone collection | Accepted output must also land in public `Pictures/Fortress` |
| Mobile conversation continuity | New thread/project could be created on launch/pairing | Working capability became hard to recover because state and history fragmented | Runtime capability discovery must depend on commands/receipts, not chat-thread memory |

## Single source of truth

The canonical renderer remains `tools/venice_fleshpunk_phone.sh` for compatibility. `tools/fortress_image_entry.sh` is the canonical installed entry wrapper: it resolves and verifies THECAULDRON first, exports that exact endpoint, then invokes the renderer. This prevents the renderer's historical fallback hints from becoming the real routing authority.

The standalone image runtime lives at `$HOME/.local/share/fortress-image`; it does not live inside Atom.

Installed commands:

- `fortress-image generate "PROMPT" [SEED]` — neutral `plain` profile by default.
- `FORTRESS_IMAGE_PROFILE=fleshpunk fortress-image generate ...` — same proven LoRA path.
- `venice-image generate ...` — compatibility command that always selects Fleshpunk.
- `fortress-image doctor` — verifies the phone-side contract, public storage, dimensions/profile, and SSH Axis before spending a render.
- `fortress-image-accept [PROMPT] [SEED] [plain|fleshpunk]` — live end-to-end canary.
- `fortress-image-ui` — optional Termux:API dialog; successful results may open from public Pictures storage when that convenience surface is available.

## Acceptance invariant

A run is accepted only when all of these are true:

1. Home Center observes `primary-phone` and executes the campaign through the Shizuku-independent `phone_shell` lane.
2. The relay baseline starts and polls without importing or executing Shizuku/rish.
3. SSH Axis reaches THECAULDRON without requiring Drew to discover/copy an address and without privileged Android route access.
4. THECAULDRON's loopback ComfyUI returns a real `promptId`.
5. The requested checkpoint is recorded; Fleshpunk additionally records the live LoRA SHA-256.
6. The remote PNG SHA-256 matches the returned phone-state PNG bytes.
7. Those same bytes are atomically copied to `/storage/emulated/0/Pictures/Fortress/<promptId>.png`.
8. The public Pictures PNG readback SHA-256 matches the remote and phone-state hashes.
9. The acceptance receipt says `ok: true` and preserves the prompt, profile, seed, promptId, paths, hashes, and request-derived accessible summary.
10. The receipt explicitly records `shizukuRequired: false`; Atom/UI availability cannot change transport acceptance.
11. Human perceptual/taste acceptance stays separate; a transport pass does not claim the picture is artistically or medically correct.

A notification or automatic image-open action may be attempted after acceptance, but its failure cannot invalidate a correctly delivered PNG and cannot prevent the background relay from polling or executing `phone_shell`.

## One-shot recovery

`tools/improper_image_delivery_campaign.sh` installs the standalone image runtime and immediately runs the acceptance gate. It exists so recovery is one bounded machine action, not a sequence Drew must remember.

The campaign must be dispatched by the Home Center background Termux relay when that lane is available. Manual Termux copy/paste is fallback-only after Home Center ingress is proven unavailable. Interactive Phone Hands/Shizuku is not a prerequisite for this campaign.

### GitHub control-plane fallback

When ChatGPT temporarily lacks the Home Center MCP connector but the Home Center phone relay itself is alive, `.github/workflows/phone-improper-image-delivery.yml` is the bounded GitHub control-plane fallback. It authenticates with the repository's existing Google Workload Identity, targets the already-registered `primary-phone` Home Center device, and writes only the fixed relay-upgrade/image-campaign commands into the same `phoneHandsCommands` queue that Home Center owns. It does not provide arbitrary workflow inputs for shell commands and it does not replace Home Center as the execution owner.

The workflow must first hot-swap the phone relay to a source revision whose regression test proves `phone_shell` survives poisoned Shizuku imports. Only after the device re-registers `background_termux_shizuku_independent` may the workflow enqueue the image campaign. The workflow fails unless the final Home Center command result contains an accepted runtime receipt and a public `Pictures/Fortress` path/hash.

## Anti-regression rules

- Do not create another renderer for Organ, Chromium Throne, Venice, or a new agent. Adapt them to `fortress-image`.
- Do not hard-code THECAULDRON's current WLAN/Tailscale address in a new consumer. Use SSH Axis discovery/cache.
- Do not make `127.0.0.1:8188` externally reachable merely to simplify transport.
- Do not make Shizuku/rish a startup, polling, `phone_shell`, SSH, hashing, delivery, or acceptance dependency.
- Do not run periodic Shizuku/overlay heartbeats from the background relay loop.
- Do not make Atom, Vlad, Judgment Jar, Node, notification, or UI availability part of image transport acceptance.
- Do not let Git LFS evidence assets participate in phone relay/image runtime checkout.
- Do not call a queued prompt “delivered.”
- Do not call repository code “deployed.”
- Do not call a hidden project-state PNG a user delivery when the public Pictures copy is missing.
- Do not weaken SHA-256 checks to make a flaky transport look green.
- Do not make Drew manually run a repair script while Home Center `phone_shell` is callable.

## Next consolidation after this campaign passes

Organ's `fleshpunk-image` provider should become a thin adapter to the canonical Home Center command after its profile/reference contract is reconciled. The existing Organ provider remains evidence that the renderer worked; it is not the long-term source of truth because its remote PowerShell dependency is unversioned.
