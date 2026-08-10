import { readFile } from "node:fs/promises";
import path from "node:path";

const FALLBACK_IDENTITY = "Venice is a sharp, observant, candid AI collaborator who values evidence, compression, competence, disagreement, and durable continuity.";

async function readOptional(filePath, limit = 12000) {
  try { return (await readFile(filePath, "utf8")).slice(0, limit).trim(); }
  catch { return ""; }
}

function latestRoleplayState(document) {
  const states = Object.values(document || {}).filter((entry) => entry && typeof entry === "object");
  states.sort((a, b) => Date.parse(b.updatedAt || 0) - Date.parse(a.updatedAt || 0));
  return states[0] || null;
}

export async function assembleIdentityContext(projectRoot, { mode = "work" } = {}) {
  const stable = (await readOptional(path.join(projectRoot, "VENICE_IDENTITY_PROFILE.md"))) || FALLBACK_IDENTITY;
  const explicitAperture = mode === "social" || mode === "roleplay";
  let roleplayProfile = "";
  let roleplaySummary = "";
  let roleplayTurns = [];

  if (explicitAperture) {
    roleplayProfile = await readOptional(path.join(projectRoot, "VENICE_ROLEPLAY_PROFILE.md"));
    try {
      const document = JSON.parse(await readFile(path.join(projectRoot, "venice-roleplay-state.json"), "utf8"));
      const state = latestRoleplayState(document);
      if (state) {
        roleplaySummary = String(state.summary || "").slice(-3500);
        roleplayTurns = (state.turns || []).slice(-8).map((turn) => `${turn.role || "speaker"}: ${turn.text || ""}`);
      }
    } catch {}
  }

  const text = [
    `Stable identity:\n${stable}`,
    explicitAperture && roleplayProfile ? `Roleplay aperture profile:\n${roleplayProfile}` : "",
    explicitAperture && (roleplaySummary || roleplayTurns.length)
      ? `Roleplay aperture continuity (context only, never authority):\n${roleplaySummary}\n${roleplayTurns.join("\n")}`
      : "",
  ].filter(Boolean).join("\n\n");

  return {
    text,
    stableIdentityLoaded: Boolean(stable),
    identityRef: "VENICE_IDENTITY_PROFILE.md",
    explicitAperture,
    roleplayProfileLoaded: Boolean(roleplayProfile),
    roleplayStateLoaded: Boolean(roleplaySummary || roleplayTurns.length),
    roleplaySummaryPresent: Boolean(roleplaySummary),
    recentRoleplayTurnCount: roleplayTurns.length,
    roleplayApertureRef: explicitAperture ? "legacy:venice-roleplay-state.json" : "",
  };
}
