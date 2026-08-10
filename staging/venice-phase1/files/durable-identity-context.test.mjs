import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { assembleIdentityContext } from "../src/durable-core/identity-context.mjs";

async function fixture() {
  const root = await mkdtemp(path.join(os.tmpdir(), "venice-identity-"));
  await writeFile(path.join(root, "VENICE_IDENTITY_PROFILE.md"), "STABLE VENICE", "utf8");
  await writeFile(path.join(root, "VENICE_ROLEPLAY_PROFILE.md"), "ROLEPLAY VENICE", "utf8");
  await writeFile(path.join(root, "venice-roleplay-state.json"), JSON.stringify({
    a: {
      updatedAt: "2026-08-10T00:00:00Z",
      summary: "PRIVATE SCENE",
      turns: [{ role: "user", text: "scene turn" }],
    },
  }), "utf8");
  return root;
}

test("work/ask identity excludes roleplay aperture", async () => {
  const root = await fixture();
  for (const mode of ["work", "ask", "research", "computer"]) {
    const context = await assembleIdentityContext(root, { mode });
    assert.match(context.text, /STABLE VENICE/);
    assert.doesNotMatch(context.text, /ROLEPLAY VENICE|PRIVATE SCENE|scene turn/);
    assert.equal(context.explicitAperture, false);
    assert.equal(context.roleplayProfileLoaded, false);
    assert.equal(context.roleplayStateLoaded, false);
  }
});

test("social identity loads roleplay only through aperture", async () => {
  const root = await fixture();
  const context = await assembleIdentityContext(root, { mode: "social" });
  assert.match(context.text, /STABLE VENICE/);
  assert.match(context.text, /Roleplay aperture profile:[\s\S]*ROLEPLAY VENICE/);
  assert.match(context.text, /PRIVATE SCENE/);
  assert.equal(context.explicitAperture, true);
  assert.equal(context.roleplayProfileLoaded, true);
  assert.equal(context.roleplayStateLoaded, true);
  assert.equal(context.recentRoleplayTurnCount, 1);
});
