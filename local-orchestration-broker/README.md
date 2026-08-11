# Local Orchestration Broker — P0 Contracts

This isolated package defines data contracts and fail-closed policy for a future Home Center local orchestration broker. It does not start a server, open a browser, invoke an adapter, dispatch work, or mutate Home Center.

## Boundary

- Browser Chat is supervisory only: it may select a bounded queue item and interpret receipts.
- Home Center or a future local broker owns local identity, process, repository, session, and receipt state.
- Zero-credit means local models, deterministic local tools, or access already included by the product. It never means quota bypass, unlimited compute, credential reuse, or API-key Agents SDK work.
- This P0 package creates only schemas, pure validation, and read-only `health` / `identity` probe envelopes.

Every request is rejected when queue revision, state owner, lane owner, worker identity, or commission digest differs from current trusted state. Any request marked mutating or naming an operation outside `health` and `identity` is rejected.

## Verification

```sh
npm test
npm run check
```

The package uses Node built-ins only and intentionally has no lockfile, network client, executable entry point, production route, adapter implementation, or deployment configuration.
