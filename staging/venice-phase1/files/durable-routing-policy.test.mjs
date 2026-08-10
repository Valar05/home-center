import test from "node:test";
import assert from "node:assert/strict";
import { resolveLocalCapabilities } from "../src/workstation-capabilities.mjs";

test("generic code inspection does not implicitly delegate to Copilot", () => {
  assert.deepEqual(resolveLocalCapabilities("Inspect the Venice codebase architecture and explain how routing works. Do not modify files."), []);
  assert.deepEqual(resolveLocalCapabilities("Review the repository structure and tell me what is fragile. Read-only analysis only."), []);
});

test("explicit Copilot requests still delegate", () => {
  assert.deepEqual(
    resolveLocalCapabilities("Use Copilot to inspect, patch, and test the source."),
    [{ capability: "copilot", mode: "edit" }],
  );
});

test("legacy implicit Copilot routing remains rollbackable", () => {
  assert.deepEqual(
    resolveLocalCapabilities("Inspect the codebase and explain it.", { allowImplicitCoding: true }),
    [{ capability: "copilot", mode: "plan" }],
  );
});
