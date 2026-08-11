import { createHash } from "node:crypto";

export const OUTCOMES = Object.freeze(["ROUTE", "PARK", "ASK_APPROVAL", "DENY"]);
export const EXECUTORS = Object.freeze([
  "CHAT_MCP_SUPERVISOR", "DETERMINISTIC_LOCAL", "CONTINUE_LOCAL",
  "QWEN_LOCAL", "OLLAMA_LOCAL", "COMPUTER_HANDS", "BROWSER_NERVE",
  "PHONE_HANDS", "CODEX_EMERGENCY",
]);
export const COST_CLASSES = Object.freeze([
  "INCLUDED_CHAT", "ZERO_CREDIT_LOCAL", "CREDIT_BEARING_CODEX", "PAID_PROVIDER",
]);
export const ROTATION_STATES = Object.freeze([
  "ACTIVE", "DRAINING", "CHECKPOINTED", "ROTATED", "SUCCESSOR_ACTIVE",
]);

const LOCAL_COSTS = new Set(["INCLUDED_CHAT", "ZERO_CREDIT_LOCAL"]);
const id = /^[A-Za-z0-9][A-Za-z0-9._:-]{2,159}$/;

export function canonical(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(",")}}`;
}

export function sha256(value) {
  return createHash("sha256").update(typeof value === "string" ? value : canonical(value)).digest("hex");
}

function receipt(body) {
  const frozen = structuredClone(body);
  frozen.receiptSha256 = sha256(frozen);
  return Object.freeze(frozen);
}

function decision(outcome, code, input, rule = null, extra = {}) {
  return receipt({
    schema: "fortress.chat-mcp-route.v1",
    outcome,
    reasonCode: code,
    requestSha256: sha256(input),
    tableSha256: extra.tableSha256 ?? null,
    ruleId: rule?.ruleId ?? null,
    executor: outcome === "ROUTE" ? rule?.executor ?? null : null,
    capability: outcome === "ROUTE" ? rule?.capability ?? null : null,
    costClass: rule?.costClass ?? null,
    fallback: "NONE",
    ...extra,
  });
}

export function validateRouteTable(table) {
  if (!table || table.schema !== "fortress.chat-mcp-routes.v1" || !Array.isArray(table.rules)) {
    throw new TypeError("INVALID_ROUTE_TABLE");
  }
  const seen = new Set();
  const rules = table.rules.map(raw => {
    const rule = structuredClone(raw);
    if (!id.test(rule.ruleId ?? "") || seen.has(rule.ruleId)) throw new TypeError("INVALID_OR_DUPLICATE_RULE_ID");
    seen.add(rule.ruleId);
    if (!Number.isSafeInteger(rule.priority)) throw new TypeError("INVALID_PRIORITY");
    if (!OUTCOMES.includes(rule.outcome)) throw new TypeError("INVALID_OUTCOME");
    if (rule.outcome === "ROUTE" && !EXECUTORS.includes(rule.executor)) throw new TypeError("INVALID_EXECUTOR");
    if (!COST_CLASSES.includes(rule.costClass)) throw new TypeError("INVALID_COST_CLASS");
    if (!id.test(rule.capability ?? "")) throw new TypeError("INVALID_CAPABILITY");
    if (!Array.isArray(rule.allTags) || !rule.allTags.every(x => id.test(x))) throw new TypeError("INVALID_TAGS");
    if ("command" in rule || "argv" in rule || "prompt" in rule) throw new TypeError("EXECUTABLE_MATERIAL_FORBIDDEN");
    return Object.freeze(rule);
  });
  return Object.freeze({ schema: table.schema, version: String(table.version), rules, sha256: sha256({ ...table, rules }) });
}

export function reconcileCapabilities(advertised, deployed, now) {
  const instant = Date.parse(now);
  const observed = Date.parse(deployed?.observedAt);
  const expires = Date.parse(deployed?.expiresAt);
  if (![instant, observed, expires].every(Number.isFinite) || instant < observed || instant > expires) {
    return receipt({ schema: "fortress.capability-reconciliation.v1", status: "STALE", callable: [] });
  }
  const runtime = new Set(deployed.operations ?? []);
  const ads = new Set(advertised.operations ?? []);
  const callable = [...runtime].filter(x => ads.has(x)).sort();
  const advertisedOnly = [...ads].filter(x => !runtime.has(x)).sort();
  return receipt({
    schema: "fortress.capability-reconciliation.v1",
    status: advertisedOnly.length ? "DRIFT" : "CURRENT",
    deployedRevision: deployed.revision ?? null,
    callable,
    advertisedOnly,
  });
}

function requiredContext(input) {
  const names = ["requestId", "commissionId", "projectId", "sessionId", "now", "approvalPolicy", "costPolicy"];
  return names.filter(k => !id.test(input[k] ?? "") && k !== "now")
    .concat(Number.isFinite(Date.parse(input.now)) ? [] : ["now"]);
}

function matches(rule, input) {
  const tags = new Set(input.tags ?? []);
  return rule.allTags.every(tag => tags.has(tag));
}

export function evaluateRoute(input, table, capabilityReceipt) {
  const validated = table.sha256 ? table : validateRouteTable(table);
  const missing = requiredContext(input);
  if (missing.length) return decision("PARK", "MISSING_CONTEXT", input, null, { tableSha256: validated.sha256, missing: missing.sort() });
  if (!capabilityReceipt || !["CURRENT", "DRIFT"].includes(capabilityReceipt.status)) {
    return decision("PARK", "CAPABILITY_TRUTH_UNAVAILABLE", input, null, { tableSha256: validated.sha256 });
  }
  const matchesList = validated.rules.filter(r => matches(r, input));
  if (!matchesList.length) return decision("PARK", "NO_MATCH", input, null, { tableSha256: validated.sha256 });
  const priority = Math.min(...matchesList.map(r => r.priority));
  const winners = matchesList.filter(r => r.priority === priority);
  if (winners.length !== 1) return decision("PARK", "AMBIGUOUS_ROUTE", input, null, { tableSha256: validated.sha256 });
  const rule = winners[0];
  if (rule.outcome === "DENY") return decision("DENY", rule.reasonCode ?? "RULE_DENY", input, rule, { tableSha256: validated.sha256 });
  if (rule.outcome === "ASK_APPROVAL" || rule.requiresApproval) {
    return decision("ASK_APPROVAL", "EXPLICIT_APPROVAL_REQUIRED", input, rule, { tableSha256: validated.sha256 });
  }
  if (!capabilityReceipt.callable.includes(rule.capability)) {
    return decision("PARK", "CAPABILITY_NOT_DEPLOYED", input, rule, { tableSha256: validated.sha256 });
  }
  if (rule.executor === "CODEX_EMERGENCY") {
    return decision("ASK_APPROVAL", "CODEX_EMERGENCY_TOKEN_REQUIRED", input, rule, { tableSha256: validated.sha256 });
  }
  if (!LOCAL_COSTS.has(rule.costClass)) {
    return decision("ASK_APPROVAL", "COST_AUTHORITY_REQUIRED", input, rule, { tableSha256: validated.sha256 });
  }
  if (input.costPolicy === "LOCAL_ONLY" && !LOCAL_COSTS.has(rule.costClass)) {
    return decision("DENY", "COST_POLICY_DENIED", input, rule, { tableSha256: validated.sha256 });
  }
  return decision("ROUTE", rule.reasonCode ?? "EXACT_ROUTE", input, rule, { tableSha256: validated.sha256 });
}

export class EmergencyAuthorityLedger {
  #consumed = new Set();
  authorize(token, request, now) {
    const required = ["tokenId", "blockage", "scopeSha256", "budgetClass", "expiresAt", "evidenceContract"];
    const missing = required.filter(k => !token?.[k]);
    if (missing.length) return receipt({ schema: "fortress.codex-emergency.v1", outcome: "DENY", reasonCode: "INCOMPLETE_TOKEN", missing });
    if (this.#consumed.has(token.tokenId)) return receipt({ schema: "fortress.codex-emergency.v1", outcome: "DENY", reasonCode: "TOKEN_REPLAY" });
    if (Date.parse(now) > Date.parse(token.expiresAt)) return receipt({ schema: "fortress.codex-emergency.v1", outcome: "DENY", reasonCode: "TOKEN_EXPIRED" });
    if (token.scopeSha256 !== sha256(request.scope)) return receipt({ schema: "fortress.codex-emergency.v1", outcome: "DENY", reasonCode: "SCOPE_MISMATCH" });
    if (token.budgetClass !== "CREDIT_BEARING_CODEX" || token.noFallback !== true) {
      return receipt({ schema: "fortress.codex-emergency.v1", outcome: "DENY", reasonCode: "AMBIGUOUS_COST_OR_FALLBACK" });
    }
    this.#consumed.add(token.tokenId);
    return receipt({ schema: "fortress.codex-emergency.v1", outcome: "ROUTE", reasonCode: "ONE_TIME_AUTHORITY_ACCEPTED", tokenId: token.tokenId, scopeSha256: token.scopeSha256 });
  }
}

export class ChatProjectRegistry {
  #projects = new Map();
  #events = [];
  create(project) {
    const required = ["projectId", "stateDocumentId", "commissionSha256", "conversationId", "leaseId"];
    if (required.some(k => !id.test(project[k] ?? ""))) throw new TypeError("INVALID_PROJECT");
    if (this.#projects.has(project.projectId)) throw new Error("DUPLICATE_PROJECT");
    const value = { ...structuredClone(project), state: "ACTIVE", successorId: null, checkpointSha256: null, readbackSha256: null, compactionWatermark: project.compactionWatermark ?? 0 };
    this.#projects.set(project.projectId, value);
    this.#record("PROJECT_CREATED", value);
    return structuredClone(value);
  }
  get(projectId) { return structuredClone(this.#projects.get(projectId) ?? null); }
  events() { return structuredClone(this.#events); }
  markDraining(projectId, signals) {
    const p = this.#must(projectId, "ACTIVE");
    if (!signals?.stale && !signals?.nonresponsive && !signals?.contextBloat) throw new Error("ROTATION_SIGNAL_REQUIRED");
    p.state = "DRAINING"; p.rotationSignals = structuredClone(signals); this.#record("PROJECT_DRAINING", p); return this.get(projectId);
  }
  checkpoint(projectId, payload, durableWriteReceipt, readback) {
    const p = this.#must(projectId, "DRAINING");
    const hash = sha256(payload);
    if (durableWriteReceipt?.status !== "success" || durableWriteReceipt.sha256 !== hash || readback?.sha256 !== hash) {
      throw new Error("CHECKPOINT_READBACK_MISMATCH");
    }
    p.state = "CHECKPOINTED"; p.checkpointSha256 = hash; p.readbackSha256 = readback.sha256; p.compactionWatermark += 1;
    this.#record("PROJECT_CHECKPOINTED", p); return this.get(projectId);
  }
  rotate(projectId, successor) {
    const p = this.#must(projectId, "CHECKPOINTED");
    if (p.successorId || this.#projects.has(successor.projectId)) throw new Error("DUPLICATE_SUCCESSOR");
    if (successor.predecessorId !== projectId || successor.commissionSha256 !== p.commissionSha256) throw new Error("SUCCESSOR_LINEAGE_MISMATCH");
    p.state = "ROTATED"; p.successorId = successor.projectId; this.#record("PROJECT_ROTATED", p);
    const next = { ...structuredClone(successor), state: "SUCCESSOR_ACTIVE", successorId: null, checkpointSha256: p.checkpointSha256, readbackSha256: p.readbackSha256, compactionWatermark: p.compactionWatermark };
    this.#projects.set(next.projectId, next); this.#record("SUCCESSOR_ACTIVE", next); return this.get(next.projectId);
  }
  #must(projectId, state) {
    const p = this.#projects.get(projectId);
    if (!p) throw new Error("PROJECT_NOT_FOUND");
    if (p.state !== state) throw new Error(`INVALID_TRANSITION_${p.state}_TO_${state}`);
    return p;
  }
  #record(type, body) { this.#events.push(receipt({ schema: "fortress.chat-project-event.v1", sequence: this.#events.length + 1, type, projectId: body.projectId, state: body.state })); }
}

export function planOnly(request, table, capabilities) {
  const result = evaluateRoute(request, table, capabilities);
  return Object.freeze({ ...result, dispatchPerformed: false, modelCalled: false, networkUsed: false, commandSynthesized: false });
}
