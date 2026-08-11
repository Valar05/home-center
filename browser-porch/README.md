# Browser Porch candidate

Status: source candidate only. Not installed, deployed, paired, callable, or accepted.

Browser Porch lets the existing Home Center Browser Nerve request a one-minute, observe-only lease over exactly one ordinary Chrome tab that Drew explicitly pairs by clicking the extension action. It does not copy a Chrome profile, restart Chrome, read cookies, capture credentials, request arbitrary-tab authority, or browse beyond the paired tab.

## Components

- `extension/`: minimal MV3 extension with only `activeTab`, `scripting`, and the loopback relay origin. It has no `cookies`, `tabs`, broad host, native messaging, or storage permission.
- `relay.mjs`: loopback-only broker with exact installed-extension origin and a separate ephemeral Browser Nerve bearer capability. It accepts only server-registered intentions, mints the tab fence, permits one pending writer, matches completion to the exact pending command, and sends pair/revoke events through a required integration callback.
- `contract.mjs`: exact origin/account/tab/live-document/session/worker/commission-ID/commission-hash/lease binding, replay controls, read-only default, and separately digest-bound mutation approval.

The extension candidate executes only `inventory`. Although the contract defines two future mutation names and verifies a separate approval envelope, this candidate deliberately has no mutation executor. Extension restart loses the in-memory pairing and fails closed. The existing dedicated-profile Browser Nerve remains unchanged.

## Intended integration

1. Browser Nerve starts the loopback relay on `127.0.0.1:9234` and POSTs one short-lived pair intent.
2. Drew opens the already-authenticated ChatGPT tab and clicks Browser Porch.
3. The extension requires a non-generic `data-user-id` or `data-account-id` DOM marker, hashes it locally, and posts the receipt without returning the raw identifier. A generic profile label never proves authentication and yields `account_unverified`.
4. Browser Nerve compares the receipt with the intended account hash and may enqueue `inventory` only.
5. Navigation, account change, tab close, expiry, or the visible second-click kill switch revokes authority. MV3 lifecycle/restart acceptance remains a separate installation canary; this source candidate makes no installed or callable claim.
6. Chat/project mutations remain stopped until a later approval artifact binds the exact command digest and a reviewed mutation executor exists.

The relay refuses to start without an injected durable event sink. The deployed Browser Nerve does not yet start the relay or supply that Home Center sink. Canonical worker integration, Home Center receipt readback, and an installed MV3 lifecycle canary are explicit remaining gates, not capabilities claimed by this branch.

## Verification

```sh
node --test browser-porch/contract.test.mjs
node --test browser-porch/relay.test.mjs
node --check browser-porch/contract.mjs
node --check browser-porch/relay.mjs
node --check browser-porch/extension/service-worker.js
```
