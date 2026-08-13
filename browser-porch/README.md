# Chromium Throne / Browser Porch

Status: **parallel worker source implemented; not yet deployed or acceptance-proven on Drew's desktop.**

Chromium Throne is the visible desktop ChatGPT worker organ behind Atom/Vlad. **Atom on the phone is the command room.** ChatGPT tabs are disposable worker bodies and must not require Drew to code through ChatGPT or babysit threads.

## Current contract

- One Atom/Vlad operator surface on the phone.
- One Chromium Throne extension on the desktop.
- Up to 8 visible ChatGPT worker tabs in one bounded parallel wave.
- One bounded `PORTCULLIS LOCKED` commission per worker.
- Every worker has a job ID and tab ID.
- Worker checkpoints and handoffs are captured per tab.
- Choked threads rotate through the strict six-field handoff packet.
- ChatGPT cannot self-certify completion; Vlad + Venice review remain required and Tetsuya owns final release.
- No API-token compute, hidden headless farm, account rotation, cookie scraping, or substitute agent framework.

## Parallel worker behavior

`extension/swarm-core.mjs` defines `MAX_PARALLEL_WORKERS = 8` and selects only queued independent jobs for a wave. `extension/throne-panel.mjs` dispatches that wave concurrently. `extension/service-worker.js` creates a separate inactive `chatgpt.com` tab for each fresh worker, tags it with the job ID, records the tab ID in receipts, and can inspect/capture that specific worker without activating it.

Parallelism remains intentionally bounded. A tightly coupled write must still be one worker. Independent archaeology, diagnosis, review preparation, test authoring, documentation, and other non-conflicting slices may fan out.

## Worker boot contract: `PORTCULLIS LOCKED`

Every worker receives a fixed envelope that preserves outcome, owner, execution lane, exclusions, evidence standard, and delivery surface; separates capability truth states; forbids ChatGPT-local scratch as hardware proof; limits the worker to one bounded slice; and requires a strict handoff on context choke.

The phrase is a boot marker, not magic. Enforcement comes from extension behavior, bounded queues, receipts, and external review gates.

## Important architecture boundary

Chromium Throne is not the phone command surface. The Atom Chromium-Throne add-on already exposes commands, missions, browser-tab inventory, receipts, and diagnostics on the phone. The remaining integration seam is routing Atom/Vlad mission commands through the existing Home Center/Browser Nerve/Computer Hands transport into this extension without creating a second control plane.

## Capability truth

Implemented in repository source:

- bounded parallel wave selection;
- independent visible worker-tab creation;
- per-worker job/tab identity;
- per-tab inspection and checkpoint capture;
- strict handoff rotation;
- explicit Vlad/Venice/Tetsuya review metadata;
- Atom/Vlad operator-surface doctrine.

Not yet claimed:

- tests executed on authoritative desktop runtime;
- extension reloaded on THECAULDRON;
- multiple real ChatGPT workers concurrently commissioned;
- Atom phone command routed end-to-end into the swarm;
- live worker roster visible in Atom from actual desktop state;
- accepted desktop swarm behavior.

Those states require real Computer Hands / desktop / phone receipts. Repository commits are implementation evidence only.
