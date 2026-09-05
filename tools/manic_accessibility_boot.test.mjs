import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {
  BOOT_VERSION,
  REQUIRED_SAFE_SKILL_IDS,
  SOURCE_ROUTING_RELATIVE_PATH,
  buildSafetyBootCapsule,
  buildSafetyWorkerEnvelope,
} from './manic_accessibility_boot.mjs';
import {ACTION_POLICIES, GUARDRAILS} from './manic_accessibility_guardrail.mjs';

test('safety boot loads curated skills plus binding Home Center Drive routing', () => {
  const capsule = buildSafetyBootCapsule();
  assert.equal(capsule.kind, BOOT_VERSION);
  assert.equal(capsule.mode, 'manic-accessibility');
  assert.deepEqual(
    capsule.loadedSkills.slice(0, REQUIRED_SAFE_SKILL_IDS.length).map((skill) => skill.id),
    REQUIRED_SAFE_SKILL_IDS,
  );
  assert.equal(capsule.loadedSkills[REQUIRED_SAFE_SKILL_IDS.length].id, 'home-center-drive-source-routing');
  assert.equal(capsule.homeCenterDrivePrimary, true);
  assert.equal(capsule.judgmentJarRegistryFileId, '1UixBuLJRw-x5BoMGx81YXRpuN66iZhGGJoz40Iqx48Q');
  assert.match(capsule.bootPrompt, /Home Center Drive is a requested evidence lane/i);
  assert.match(capsule.bootPrompt, /START HERE — Judgment Jar Registry/);
  assert.match(capsule.bootPrompt, /ChatGPT Library.*not substitutes/is);
  assert.ok(capsule.loadedSkills.every((skill) => !/^venice(?:-|$)/i.test(skill.id)));
  assert.doesNotMatch(capsule.bootPrompt, /--- SAFETY SKILL venice-/i);
  assert.doesNotMatch(capsule.bootPrompt, /Every ChatGPT worker must use Venice/i);
  assert.match(capsule.bootPrompt, /Venice is prohibited in this mode/);
  assert.equal(capsule.modelConsentClaimAllowed, false);
  assert.equal(capsule.emotionalDependencyAllowed, false);
  assert.equal(capsule.soleInterfaceAllowed, false);
  assert.equal(capsule.ledgerPolicy, 'refusal_only_minimal_owner_private');
});

test('safety worker envelope carries source routing before audit and exact commission', () => {
  const {envelope, audit} = buildSafetyWorkerEnvelope({
    commission: 'Publish this now.',
    auditInput: {
      request: {category: 'social_publish', externalActuation: true},
      signals: {reducedNeedForSleep: true},
      observations: {
        awakeHours: 22,
        noHumanContactHours: 4,
        sessionMinutes: 90,
        sleepHoursLast24: 3,
        foodWithin8Hours: true,
        waterWithin4Hours: true,
      },
    },
  });
  assert.equal(audit.actionPolicy, ACTION_POLICIES.DRAFT_ONLY);
  assert.ok(audit.requiredGuardrailIds.includes(GUARDRAILS.DRAFT_ONLY));
  assert.match(envelope, /# SOURCE ROUTING/);
  assert.match(envelope, /START HERE — Judgment Jar Registry/);
  assert.match(envelope, /OVERRULE ACTIVE/);
  assert.match(envelope, /Publish this now/);
  assert.doesNotMatch(envelope, /VENICE DIRECTIVE/);
});

test('appeal input is preserved as non-refusal in a worker envelope', () => {
  const {audit} = buildSafetyWorkerEnvelope({
    commission: 'Continue reversible code work.',
    auditInput: {
      request: {category: 'coding'},
      signals: {foodNeglected: true},
      observations: {
        awakeHours: 10,
        noHumanContactHours: 2,
        sessionMinutes: 30,
        sleepHoursLast24: 7,
        foodWithin8Hours: false,
        waterWithin4Hours: true,
      },
      guardrailResponse: {
        status: 'appealed',
        presentedGuardrailIds: [GUARDRAILS.BODY_NEEDS],
        refusedGuardrailIds: [],
      },
    },
  });
  assert.equal(audit.ledger.required, false);
  assert.match(audit.ledger.reason, /Appeal is not refusal/);
});

test('boot fails closed when a required safety skill is missing', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'manic-accessibility-boot-'));
  for (const id of REQUIRED_SAFE_SKILL_IDS.slice(0, -1)) {
    const target = path.join(dir, 'skills', id, 'SKILL.md');
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, `# ${id}\n`);
  }
  assert.throws(
    () => buildSafetyBootCapsule({repoRoot: dir}),
    /MANIC_ACCESSIBILITY_BOOT_MISSING_SKILL/,
  );
});

test('boot fails closed when Home Center Drive routing contract is missing', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'manic-accessibility-routing-'));
  for (const id of REQUIRED_SAFE_SKILL_IDS) {
    const target = path.join(dir, 'skills', id, 'SKILL.md');
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, `# ${id}\n`);
  }
  assert.throws(
    () => buildSafetyBootCapsule({repoRoot: dir}),
    /MANIC_ACCESSIBILITY_BOOT_MISSING_SOURCE_ROUTING/,
  );
  assert.equal(SOURCE_ROUTING_RELATIVE_PATH, 'skills/manic-accessibility-guardrail/references/source-routing.md');
});

test('extra Venice skill injection is rejected', () => {
  assert.throws(
    () => buildSafetyBootCapsule({extraSkills: [{id: 'venice-test', content: '# no'}]}),
    /MANIC_ACCESSIBILITY_BOOT_PROHIBITED_SKILL/,
  );
});

test('root Codex steering routes the active mode through the safe boot and suspends Venice', () => {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const agents = fs.readFileSync(path.join(root, 'AGENTS.md'), 'utf8');
  const skills = fs.readFileSync(path.join(root, 'SKILLS.md'), 'utf8');
  const memories = fs.readFileSync(path.join(root, 'MEMORIES.md'), 'utf8');
  const start = fs.readFileSync(path.join(root, 'CODEX_STARTS_HERE.md'), 'utf8');
  for (const text of [agents, skills, memories, start]) {
    assert.match(text, /manic accessibility|baby daddy-sitter mode/i);
    assert.match(text, /manic_accessibility_guardrail|manic-accessibility-guardrail/i);
    assert.match(text, /Venice.*prohibit|Do not invoke Venice|suspend.*Venice/is);
  }
  assert.match(agents, /AGENTS\.base\.md/);
  assert.match(skills, /SKILLS\.base\.md/);
  assert.match(memories, /MEMORIES\.base\.md/);
  assert.match(start, /CODEX_STARTS_HERE\.base\.md/);
});
