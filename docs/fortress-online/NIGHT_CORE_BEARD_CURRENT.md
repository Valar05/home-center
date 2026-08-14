# Night Core Beard — Active Integration State

Status: ACTIVE / NOT ACCEPTED

This is the single active integration surface for the phone-first Fortress overlay hardening campaign.

Current branch: `fortress/night-core-beard`

Merged upstream truth already consumed from `main`:
- Chromium deterministic Android controller/canary (PR #315 / merge `80efd21c288eb99c786006627b0bc82f15c39756`).
- Fail-closed phone ingress health checks (PR #314 / merge `d0348a84080416b88293d99135d512ea565bfdf0`).

Branch work in progress:
- battery-aware, cheap Night Core status policy;
- local-first `fortress_night_status.py` with Termux/sysfs first and bounded rish fallback;
- repaired Chromium-v2 overlay source contract;
- AUTO one-input request state while fixed phone operations compile to deterministic TERM commands;
- deterministic AUTO router for ordinary Beard speech.

Rejected regression:
- do NOT remove the active-only overlay touch guard while porting the one-input UI from stale PR #293.
- do NOT uninstall a working overlay to resolve signer mismatch.
- do NOT treat a queued Drive task, repository commit, scheduler run, or key dispatch as physical acceptance.

Physical ingress truth:
- raw Google Drive `.task` upload is callable from ChatGPT and consumed by the physical phone daemon.
- `$HOME/home-center` is the proven primary-phone repository path.
- device operations must have short inner timeouts; the daemon's broad timeout is only a last-resort ceiling.

Next gate:
1. finish visible one-input Beard UI while retaining active-only touch guard;
2. pass source contracts;
3. sync/test/build/install on primary phone;
4. prove Night Core status + Chromium death recovery/navigation + overlay restart through physical receipts;
5. only then consider merge/acceptance.
