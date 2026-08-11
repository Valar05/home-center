# Porchlight Internet Access Map

Porchlight is a living, community-reviewed map of how people and assistive tools can use the web. It maps public origins, reusable page archetypes, accessible landmarks and controls, task routes, deterministic postconditions, known accessibility failures, native/DOM boundaries, and freshness evidence.

The map is the product. The local paired-tab runtime is one discovery and verification worker.

Motivated Mode is a permanent runtime invariant: own the requested outcome, perform the obvious adjacent improvement (turn verified use into reusable map evidence), recover through bounded DOM refresh and sparse screenshot escalation, and stop instead of flailing or expanding authority.

## What a worker contributes

A successful worker observation can become a site-pack PR only after the same route has at least three verified successes across at least two document instances. A contribution contains the public HTTPS origin, page archetype, generic task, public accessible label when safe, role, locator strategy, expected postcondition, aggregate success/failure counts, and freshness timestamps.

It never contains accounts, URL paths or query strings, typed values, cookies, credentials, raw DOM, screenshots, claim or case numbers, or user identifiers. Authenticated pages may contribute reusable structure, never session content.

Contribution modes:

- `local-only`: learn without publishing;
- `approval`: prepare a site pack and require a person to approve the exact GitHub publication;
- `automatic`: open a branch and PR with `git` and `gh` after graduation and privacy validation.

Every PR is independently testable. CI validates schema, privacy boundaries, evidence thresholds, deterministic runtime behavior, and the generated accessible HTML/JSON index.

## Constant freshness

Public unauthenticated routes can be re-probed on a schedule. Authenticated or mutation-bearing routes are marked for human-worker verification during ordinary use. Packs expire after 30 days by default. A scheduled workflow opens a freshness issue when a pack is stale; it never invents a successful recheck.

## Local worker

```sh
node browser-porch/product/cli.mjs
```

Load `browser-porch/product/extension` as an unpacked Chrome extension. Its manifest public key fixes the extension ID at `dmfjnjkccebgbiepjbmbdmpffcaikaje`; the loopback daemon rejects every other extension origin before it discloses a pair intent, answers preflight, or accepts a token. In the CLI, run `pair https://example.com`, open that exact origin in an ordinary Chrome tab, and click the extension. The lease is tab-bound and memory-only. A second click revokes it.

The grammar is intentionally small: `look`, `click “Name”`, `read “Name”`, `type “value” into “Field”`, `choose “Option” in “Field”`, `scroll down`, `screenshot`, `submit “Button”`, `approve DIGEST`, `stats`, and `revoke`.

No model, embedding, OCR, or network inference is present. DOM actions remain separate from browser chrome and native file pickers. Commit actions require a separately approved digest. A verified click or submit never becomes proof that a remote institution received or indexed anything.
