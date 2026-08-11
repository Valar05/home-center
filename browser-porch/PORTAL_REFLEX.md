# Portal Reflex

Status: implemented and fixture-tested on an isolated branch. Not integrated, installed, deployed, callable against Lincoln, or accepted.

Portal Reflex is deliberately not an AI agent. It is a local deterministic parser and state machine that accepts a small chat-like command grammar, resolves commands against a recent semantic DOM observation, chooses one allowlisted action, specifies the postcondition, and emits a deterministic receipt.

## Real replay case

The first replay case is Lincoln STD claim `19284100`. The case remains `submitted_unconfirmed`. Portal Reflex must never convert a click, form submission, upload attempt, screenshot, or outgoing message into insurer receipt or indexing proof.

The current administrative next actions remain:

- complete and verify the psychiatric provider's electronic-signature and transmission path;
- verify Lincoln received and indexed that submission;
- verify Lincoln received and indexed the August 11 corrective email and five-page appeal packet;
- verify Lawrence Family Medicine's fax receipt and indexing.

## Fixed grammar

- `look`, `status`, `where am I` → observe DOM
- `click "Accessible name"` → semantic click
- `type "value" into "Accessible name"` → set field; receipt stores only the value hash
- `choose "option" in "Accessible name"` → select option
- `scroll up|down` → scroll and re-observe
- `upload ...` → route the native file picker to Computer Hands
- `submit` / `send` / `file appeal` → stop for separately approved exact action
- unknown prose → ask; no guessing

## Screenshot policy

The normal path uses no screenshots. Portal Reflex requests one transient screenshot only when:

- the semantic DOM is effectively empty;
- the same target failed twice;
- the document changed unexpectedly;
- the page is primarily canvas or another visual surface;
- the observed postcondition disagrees with the action result; or
- Drew explicitly requests a screenshot.

Automatic screenshots are rate-limited per document fingerprint. A screenshot is reorientation evidence, not proof that an action, upload, filing, receipt, or insurer indexing succeeded.

## Boundary

Browser Nerve owns structured page actions. Computer Hands owns browser chrome, native dialogs, file pickers, and visual fallback. Browser Porch is the candidate bridge into Drew's already-authenticated ordinary Chrome tab. Portal Reflex changes none of those ownership boundaries.

No model call, prompt completion, embedding, OCR inference, or network inference is used. The machine is a reflex arc wearing a chat box as a hat.

## Verification

```sh
node --test browser-porch/portal-reflex.test.mjs
node --check browser-porch/portal-reflex.mjs
```

