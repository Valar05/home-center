import test from "node:test";
import assert from "node:assert/strict";
import { ThroneState } from "../src/state.mjs";

test("thread lifecycle is visible and evented", () => {
  const state = new ThroneState();
  state.create({ threadId: "thread:alpha", title: "Alpha", costClass: "INCLUDED_CHAT", owner: "Chat", tasteOwner: "Venice" });
  state.update("thread:alpha", { state: "RUNNING", summary: "Working" });
  assert.equal(state.get("thread:alpha").summary, "Working");
  assert.deepEqual(state.events().map(x => x.type), ["THREAD_CREATED", "THREAD_UPDATED"]);
});

test("conversation and command coexist in each parallel nerve", () => {
  const state = new ThroneState();
  state.create({ threadId: "thread:venice", costClass: "INCLUDED_CHAT", conversationEngine: "Venice" });
  state.addMessage("thread:venice", { speaker: "Drew", kind: "SOCIAL", text: "Stay with me." });
  state.addMessage("thread:venice", { speaker: "Drew", kind: "COMMAND", text: "Inspect the build." });
  assert.deepEqual(state.messages("thread:venice").map(x => x.kind), ["SOCIAL", "COMMAND"]);
});

test("credit-bearing work is not mislabeled local", () => {
  const state = new ThroneState();
  assert.throws(() => state.create({ threadId: "thread:bad", costClass: "FREE_MAGIC" }), /INVALID_COST_CLASS/);
});
