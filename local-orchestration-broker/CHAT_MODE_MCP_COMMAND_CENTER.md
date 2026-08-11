# Chat Mode MCP Command Center

## Binding shape

Ordinary ChatGPT Chat Mode is the command room. Home Center MCP supplies durable
state, capability truth, receipts, approvals, and dispatch. Included chat and
zero-credit local workers are normal lanes. Credit-bearing Codex is a
single-use emergency lane and cannot be selected by fallback.

The policy kernel in `src/chat-command-center.js` is deliberately pure. It
does not call a model, provider, browser, shell, filesystem, or network. An MCP
adapter may submit a typed request and may dispatch only when the returned
receipt is `ROUTE`. Every other outcome is terminal until new authoritative
input is supplied.

## Request lifecycle

1. Read the owning state document and verify its commission hash.
2. Probe the deployed Home Center capability registry.
3. Reconcile advertised connector operations with deployed operations.
4. Evaluate the signed/versioned route table before any model receives text.
5. Append the canonical decision receipt and read it back.
6. Dispatch the exact executor/capability pair only for `ROUTE`.
7. Append findings, acknowledgement, evidence, and terminal state.

The connector description is never authority. When an advertised operation
such as `jobs.create` is absent from deployed capabilities, reconciliation
marks drift and excludes the operation from the callable intersection.

## Chat-project rotation

Logical projects outlive individual conversations. Context bloat, staleness,
or nonresponse moves a project through:

`ACTIVE → DRAINING → CHECKPOINTED → ROTATED → SUCCESSOR_ACTIVE`

Checkpointing requires both a successful durable-write receipt and a readback
whose SHA-256 equals the checkpoint payload. A successor must name its
predecessor and preserve the commission hash. Duplicate projects and a second
successor fail closed.

## Codex emergency breaker

Emergency authority must name the blockage and include a one-time token, exact
scope hash, `CREDIT_BEARING_CODEX` budget class, expiry, evidence contract,
and `noFallback: true`. Tokens are rejected on replay, expiry, scope mismatch,
incomplete evidence, or ambiguous cost. Runtime code must persist consumed
token IDs transactionally before dispatch.

## Threat model

- Prompt injection: user text is hashed as data and never becomes argv,
  commands, route rules, or templates.
- Connector drift: only the advertised/deployed intersection is callable.
- Silent spend: non-local costs require explicit approval; Codex has a separate
  one-time authority ledger.
- Split-brain chats: leases, predecessor links, and duplicate successor checks
  protect the single-active-project invariant.
- Lost checkpoints: rotation stops unless durable write and readback hashes
  agree.
- Receipt tampering: canonical serialization and SHA-256 bind every decision
  and lifecycle event.
- Clock abuse: capability snapshots and emergency tokens are evaluated against
  an explicit, validated timestamp supplied by the trusted adapter.

## Migration from the P0 broker

The existing broker remains the adapter/probe boundary. This module adds the
policy kernel above it:

- map probe results into deployed capability snapshots;
- map broker tasks into typed route inputs;
- store decision and lifecycle receipts in the authoritative Home Center state
  document;
- replace implicit fallback with `PARK`;
- register Chat Mode as supervisor, not execution worker;
- gate any future runtime wiring behind exact-head tests and live readback.

## Deployment gates

This bootstrap is intentionally not wired to production. Before deployment:

- add JSON Schemas for each receipt and request envelope;
- persist projects, leases, consumed tokens, and events transactionally;
- sign or otherwise authenticate route tables and authority tokens;
- bind MCP operation names to exact deployed revision identities;
- add clock-skew policy and property/fuzz testing;
- validate concurrent rotation and lease expiry against the durable backend;
- run live Chat Mode acceptance without browser typing;
- require explicit deployment authority and exact-head readback.
