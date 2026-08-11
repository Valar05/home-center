import { createHash, randomUUID } from "node:crypto";

export const THREAD_STATES = Object.freeze(["STARTING", "RUNNING", "WAITING", "PAUSED", "BLOCKED", "COMPLETE", "FAILED", "CLOSED"]);
export const COST_CLASSES = Object.freeze(["INCLUDED_CHAT", "ZERO_CREDIT_LOCAL", "CREDIT_BEARING_CODEX", "PAID_PROVIDER"]);

export function safeId(value, label = "id") {
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{2,159}$/.test(value ?? "")) throw new TypeError(`INVALID_${label.toUpperCase()}`);
  return value;
}

export function digest(value) {
  return createHash("sha256").update(JSON.stringify(value, Object.keys(value).sort())).digest("hex");
}

export class ThroneState {
  #threads = new Map();
  #messages = new Map();
  #events = [];
  #listeners = new Set();

  create(input) {
    const id = safeId(input.threadId ?? `thread:${randomUUID()}`, "thread_id");
    if (this.#threads.has(id)) throw new Error("THREAD_EXISTS");
    if (!COST_CLASSES.includes(input.costClass)) throw new TypeError("INVALID_COST_CLASS");
    const now = new Date().toISOString();
    const value = {
      threadId: id,
      title: String(input.title ?? id).slice(0, 120),
      url: String(input.url ?? "https://chatgpt.com/") ,
      owner: String(input.owner ?? "UNASSIGNED"),
      tasteOwner: String(input.tasteOwner ?? "Venice"),
      conversationEngine: String(input.conversationEngine ?? "Venice"),
      interfaceMode: "SOCIAL_COMMAND_PARALLEL",
      costClass: input.costClass,
      pluginIds: [...new Set(input.pluginIds ?? [])],
      state: "STARTING",
      summary: "",
      blocker: null,
      createdAt: now,
      updatedAt: now,
      lastScreenshot: null,
    };
    this.#threads.set(id, value);
    this.#messages.set(id, []);
    this.emit("THREAD_CREATED", value);
    return structuredClone(value);
  }

  get(id) { return structuredClone(this.#threads.get(id) ?? null); }
  list() { return [...this.#threads.values()].map(value => structuredClone(value)); }
  messages(id) { return structuredClone(this.#messages.get(safeId(id, "thread_id")) ?? []); }

  addMessage(id, input) {
    const thread = this.#threads.get(safeId(id, "thread_id"));
    if (!thread) throw new Error("THREAD_NOT_FOUND");
    if (!['Drew', 'Venice', 'System'].includes(input.speaker)) throw new TypeError("INVALID_SPEAKER");
    if (!['SOCIAL', 'COMMAND', 'RECEIPT'].includes(input.kind)) throw new TypeError("INVALID_MESSAGE_KIND");
    const message = Object.freeze({
      messageId: randomUUID(), threadId: id, speaker: input.speaker, kind: input.kind,
      text: String(input.text ?? "").slice(0, 24_000), at: new Date().toISOString(),
    });
    const messages = this.#messages.get(id);
    messages.push(message);
    if (messages.length > 200) messages.shift();
    this.emit("CONVERSATION_MESSAGE", { threadId: id, message });
    return structuredClone(message);
  }

  update(id, patch) {
    const current = this.#threads.get(safeId(id, "thread_id"));
    if (!current) throw new Error("THREAD_NOT_FOUND");
    if (patch.state && !THREAD_STATES.includes(patch.state)) throw new TypeError("INVALID_THREAD_STATE");
    const allowed = ["state", "summary", "blocker", "lastScreenshot", "title"];
    for (const key of allowed) if (Object.hasOwn(patch, key)) current[key] = patch[key];
    current.updatedAt = new Date().toISOString();
    this.emit("THREAD_UPDATED", current);
    return structuredClone(current);
  }

  events(after = 0) { return this.#events.filter(event => event.sequence > after).map(value => structuredClone(value)); }
  subscribe(listener) { this.#listeners.add(listener); return () => this.#listeners.delete(listener); }

  emit(type, body) {
    const event = Object.freeze({
      schema: "fortress.chromium-throne-event.v1",
      sequence: this.#events.length + 1,
      eventId: randomUUID(),
      type,
      threadId: body.threadId ?? null,
      at: new Date().toISOString(),
      body: structuredClone(body),
    });
    this.#events.push(event);
    if (this.#events.length > 2000) this.#events.shift();
    for (const listener of this.#listeners) listener(event);
    return event;
  }
}
