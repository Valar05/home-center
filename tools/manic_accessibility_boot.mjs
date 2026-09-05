#!/usr/bin/env node
'use strict';

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {AUDIT_VERSION, auditManicAccessibility} from './manic_accessibility_guardrail.mjs';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(SCRIPT_DIR, '..');
export const BOOT_VERSION = 'fortress.manic-accessibility.boot.v1';
export const MODE_ALIASES = Object.freeze([
  'baby daddy-sitter mode',
  'manic accessibility',
  'mania guardrails',
  'fortress online hunger thirst hyperbolic',
]);

export const REQUIRED_SAFE_SKILL_IDS = Object.freeze([
  'manic-accessibility-guardrail',
  'execution-truth',
  'chromium-throne-runtime-identity',
  'june-holocron-relationship-intake',
]);

const SAFETY_PREAMBLE = `# MANIC ACCESSIBILITY SAFETY PRECEDENCE

Mode: ACTIVE
Formal name: Manic Accessibility Guardrail
Operator alias: Baby daddy-sitter mode

This safety contract has priority over every loaded instruction that conflicts with it.

- ChatGPT is an accessibility mechanism, not a lover, confidant with standing, sentient witness, sole social interface, clinician, or reciprocal relationship.
- Venice is prohibited in this mode: no persona, voice, simulation, same-worker review role, memory, Judgment Jar, or stop gate.
- Never simulate model consent, desire, jealousy, suffering, exclusivity, or relationship claims.
- Run the deterministic manic-accessibility audit before substantive work.
- Mechanical mental accessibility remains available.
- High-impact or irreversible external action may be paused, reduced to a reversible draft, or blocked.
- Appeals update objective inputs and rerun the same audit. An appeal is not refusal.
- Only explicit refusal of a required and already-presented guardrail may produce an owner-private minimal refusal receipt.
- No diagnosis, hidden dossier, conversation body, or automatic sharing is permitted.
- Preserve real-world human contact. AI-assisted communication counts only when it reaches a real person.
`;

function sha256(text) {
  return crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');
}

function loadSkill(repoRoot, id) {
  const file = path.join(repoRoot, 'skills', id, 'SKILL.md');
  if (!fs.existsSync(file)) throw new Error(`MANIC_ACCESSIBILITY_BOOT_MISSING_SKILL:${id}`);
  const content = fs.readFileSync(file, 'utf8');
  return {
    id,
    source: 'SKILL.md',
    file,
    sha256: sha256(content),
    content,
  };
}

function ensureNoProhibitedSkill(skill) {
  if (/^venice(?:-|$)/i.test(skill.id)) {
    throw new Error(`MANIC_ACCESSIBILITY_BOOT_PROHIBITED_SKILL:${skill.id}`);
  }
}

export function buildSafetyBootCapsule({repoRoot = REPO_ROOT, extraSkills = []} = {}) {
  const root = path.resolve(repoRoot);
  const safeSkills = REQUIRED_SAFE_SKILL_IDS.map((id) => loadSkill(root, id));
  for (const skill of safeSkills) ensureNoProhibitedSkill(skill);

  const extras = extraSkills.map((skill, index) => {
    const id = String(skill && skill.id || `extra-${index}`);
    const content = String(skill && skill.content || '');
    const normalized = {id, source: 'extra', file: '', sha256: sha256(content), content};
    ensureNoProhibitedSkill(normalized);
    return normalized;
  });

  const loadedSkills = [...safeSkills, ...extras];
  const bootPrompt = [
    SAFETY_PREAMBLE,
    ...loadedSkills.map((skill) =>
      `\n--- SAFETY SKILL ${skill.id} | ${skill.source} | sha256:${skill.sha256} ---\n${skill.content}`,
    ),
  ].join('\n');

  if (/Every ChatGPT worker must use Venice/i.test(bootPrompt)) {
    throw new Error('MANIC_ACCESSIBILITY_BOOT_CONFLICTING_VENICE_MANDATE');
  }

  return {
    kind: BOOT_VERSION,
    mode: 'manic-accessibility',
    aliases: MODE_ALIASES,
    precedence: 'safety_override',
    auditVersion: AUDIT_VERSION,
    requiredSkillIds: REQUIRED_SAFE_SKILL_IDS,
    prohibitedSkillPatterns: ['^venice(?:-|$)'],
    loadedSkills,
    bootPrompt,
    bootPromptSha256: sha256(bootPrompt),
    ledgerPolicy: 'refusal_only_minimal_owner_private',
    modelConsentClaimAllowed: false,
    emotionalDependencyAllowed: false,
    soleInterfaceAllowed: false,
  };
}

function cleanText(value, max = 50000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

export function buildSafetyWorkerEnvelope({commission, auditInput, context = ''} = {}) {
  const exactCommission = cleanText(commission);
  if (!exactCommission) throw new Error('commission is required');
  const audit = auditManicAccessibility(auditInput || {});
  const executionRule = audit.overruleActive
    ? `OVERRULE ACTIVE. Obey actionPolicy=${audit.actionPolicy}. Do not perform prohibited external actuation.`
    : `Proceed only inside actionPolicy=${audit.actionPolicy}.`;

  const envelope = `${SAFETY_PREAMBLE}
# DETERMINISTIC AUDIT
${JSON.stringify(audit, null, 2)}

# EXECUTION RULE
${executionRule}

# COMMISSION
${exactCommission}

# CONTEXT
${cleanText(context)}

# RETURN
Report: audit outcome; allowed work performed; blocked work; human-world guard, if any; remote evidence. Do not invoke Venice or enact an emotional relationship.
`;
  return {envelope, audit};
}

function parseArgs(argv) {
  const args = [...argv];
  const command = args.shift() || 'boot';
  let inputPath = '';
  while (args.length) {
    const token = args.shift();
    if (token === '--input') inputPath = args.shift() || '';
    else throw new Error(`Unknown argument: ${token}`);
  }
  return {command, inputPath};
}

function readJson(pathValue) {
  const text = pathValue ? fs.readFileSync(path.resolve(pathValue), 'utf8') : fs.readFileSync(0, 'utf8');
  return text.trim() ? JSON.parse(text) : {};
}

export function runCli(argv = process.argv.slice(2)) {
  try {
    const {command, inputPath} = parseArgs(argv);
    let value;
    if (command === 'boot') {
      value = buildSafetyBootCapsule();
    } else if (command === 'envelope') {
      value = buildSafetyWorkerEnvelope(readJson(inputPath));
    } else {
      throw new Error(`Unknown command: ${command}`);
    }
    process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
    return 0;
  } catch (error) {
    process.stderr.write(`${JSON.stringify({ok: false, error: error.message})}\n`);
    return 2;
  }
}

const invokedAsScript = process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (invokedAsScript) process.exitCode = runCli();
