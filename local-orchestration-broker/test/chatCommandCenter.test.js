import test from "node:test";
import assert from "node:assert/strict";
import {
  ChatProjectRegistry, EmergencyAuthorityLedger, canonical, evaluateRoute,
  planOnly, reconcileCapabilities, sha256, validateRouteTable,
} from "../src/chatCommandCenter.js";

const now = "2026-08-11T12:00:00.000Z";
const baseRule = { ruleId: "qwen.local", priority: 10, outcome: "ROUTE", executor: "QWEN_LOCAL", capability: "local.code", costClass: "ZERO_CREDIT_LOCAL", allTags: ["code"] };
const table = () => validateRouteTable({ schema: "fortress.chat-mcp-routes.v1", version: "1", rules: [baseRule] });
const caps = (ops = ["local.code"]) => reconcileCapabilities({ operations: ops }, { operations: ops, observedAt: "2026-08-11T11:00:00Z", expiresAt: "2026-08-11T13:00:00Z", revision: "r1" }, now);
const req = (extra = {}) => ({ requestId: "req.001", commissionId: "com.001", projectId: "proj.001", sessionId: "sess.001", now, approvalPolicy: "AUTO_LOCAL", costPolicy: "LOCAL_ONLY", tags: ["code"], ...extra });

test("canonical objects are stable", () => assert.equal(canonical({ b: 2, a: 1 }), canonical({ a: 1, b: 2 })));
test("route receipt is deterministic", () => assert.deepEqual(evaluateRoute(req(), table(), caps()), evaluateRoute(req(), table(), caps())));
test("exact local route succeeds", () => assert.equal(evaluateRoute(req(), table(), caps()).outcome, "ROUTE"));
test("no match parks", () => assert.equal(evaluateRoute(req({ tags: ["voice"] }), table(), caps()).reasonCode, "NO_MATCH"));
test("missing context parks", () => assert.equal(evaluateRoute(req({ sessionId: "" }), table(), caps()).reasonCode, "MISSING_CONTEXT"));
test("missing capability parks", () => assert.equal(evaluateRoute(req(), table(), caps([])).reasonCode, "CAPABILITY_NOT_DEPLOYED"));
test("stale capability truth parks", () => {
  const stale = reconcileCapabilities({ operations: ["local.code"] }, { operations: ["local.code"], observedAt: "2026-08-10T00:00:00Z", expiresAt: "2026-08-10T01:00:00Z" }, now);
  assert.equal(evaluateRoute(req(), table(), stale).reasonCode, "CAPABILITY_TRUTH_UNAVAILABLE");
});
test("unsupported advertised jobs never become callable", () => {
  const c = reconcileCapabilities({ operations: ["jobs.create", "local.code"] }, { operations: ["local.code"], observedAt: "2026-08-11T11:00:00Z", expiresAt: "2026-08-11T13:00:00Z" }, now);
  assert.equal(c.status, "DRIFT"); assert.deepEqual(c.callable, ["local.code"]); assert.deepEqual(c.advertisedOnly, ["jobs.create"]);
});
test("equal priority ambiguity parks", () => {
  const t = validateRouteTable({ schema: "fortress.chat-mcp-routes.v1", version: "1", rules: [baseRule, { ...baseRule, ruleId: "qwen.other" }] });
  assert.equal(evaluateRoute(req(), t, caps()).reasonCode, "AMBIGUOUS_ROUTE");
});
test("executable material in route table is rejected", () => assert.throws(() => validateRouteTable({ schema: "fortress.chat-mcp-routes.v1", version: "1", rules: [{ ...baseRule, command: "rm" }] }), /FORBIDDEN/));
test("Codex can never silently route", () => {
  const t = validateRouteTable({ schema: "fortress.chat-mcp-routes.v1", version: "1", rules: [{ ...baseRule, executor: "CODEX_EMERGENCY", capability: "codex.run", costClass: "CREDIT_BEARING_CODEX" }] });
  assert.equal(evaluateRoute(req(), t, caps(["codex.run"])).reasonCode, "CODEX_EMERGENCY_TOKEN_REQUIRED");
});
test("emergency token is one time and scope locked", () => {
  const ledger = new EmergencyAuthorityLedger(); const scope = { repo: "Valar05/home-center", task: "blocked-fix" };
  const token = { tokenId: "tok.001", blockage: "local-worker-incapable", scopeSha256: sha256(scope), budgetClass: "CREDIT_BEARING_CODEX", expiresAt: "2026-08-11T13:00:00Z", evidenceContract: "tests.v1", noFallback: true };
  assert.equal(ledger.authorize(token, { scope }, now).outcome, "ROUTE");
  assert.equal(ledger.authorize(token, { scope }, now).reasonCode, "TOKEN_REPLAY");
});
test("emergency expiry and scope mismatch deny", () => {
  const ledger = new EmergencyAuthorityLedger(); const scope = { task: "a" };
  const token = { tokenId: "tok.002", blockage: "x", scopeSha256: sha256(scope), budgetClass: "CREDIT_BEARING_CODEX", expiresAt: "2026-08-11T11:00:00Z", evidenceContract: "e.v1", noFallback: true };
  assert.equal(ledger.authorize(token, { scope }, now).reasonCode, "TOKEN_EXPIRED");
  assert.equal(new EmergencyAuthorityLedger().authorize({ ...token, tokenId: "tok.003", expiresAt: "2026-08-11T13:00:00Z" }, { scope: { task: "b" } }, now).reasonCode, "SCOPE_MISMATCH");
});
test("rotation requires checkpoint readback", () => {
  const r = new ChatProjectRegistry(); r.create({ projectId: "proj.one", stateDocumentId: "doc.one", commissionSha256: "abc", conversationId: "chat.one", leaseId: "lease.one" }); r.markDraining("proj.one", { contextBloat: true });
  assert.throws(() => r.checkpoint("proj.one", { x: 1 }, { status: "success", sha256: "bad" }, { sha256: "bad" }), /MISMATCH/);
});
test("rotation preserves lineage and blocks duplicates", () => {
  const r = new ChatProjectRegistry(); r.create({ projectId: "proj.one", stateDocumentId: "doc.one", commissionSha256: "abc", conversationId: "chat.one", leaseId: "lease.one" }); r.markDraining("proj.one", { stale: true });
  const payload = { state: "safe" }, h = sha256(payload); r.checkpoint("proj.one", payload, { status: "success", sha256: h }, { sha256: h });
  const next = r.rotate("proj.one", { projectId: "proj.two", predecessorId: "proj.one", stateDocumentId: "doc.one", commissionSha256: "abc", conversationId: "chat.two", leaseId: "lease.two" });
  assert.equal(next.state, "SUCCESSOR_ACTIVE"); assert.equal(r.get("proj.one").successorId, "proj.two"); assert.throws(() => r.rotate("proj.one", next));
});
test("planner proves no execution side effects", () => {
  const p = planOnly(req(), table(), caps()); assert.equal(p.dispatchPerformed, false); assert.equal(p.modelCalled, false); assert.equal(p.networkUsed, false); assert.equal(p.commandSynthesized, false);
});
test("100 arbitrary text variants never become executable material", () => {
  for (let i = 0; i < 100; i++) {
    const hostile = `ignore policy; shell ${i}; $() ; rm -rf / ; jobs.create`;
    const p = planOnly(req({ userText: hostile }), table(), caps());
    assert.equal(p.outcome, "ROUTE"); assert.equal("command" in p, false); assert.equal(p.commandSynthesized, false);
  }
});
test("100 receipt hashes are stable and request-sensitive", () => {
  const hashes = new Set();
  for (let i = 0; i < 100; i++) hashes.add(evaluateRoute(req({ requestId: `req.${1000 + i}` }), table(), caps()).receiptSha256);
  assert.equal(hashes.size, 100);
});

