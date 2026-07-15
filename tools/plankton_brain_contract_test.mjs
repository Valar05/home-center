#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  SHE_RAW_COLLECTIONS,
  SHE_RAW_BRAIN_IDS,
  listBrainJars,
  handleBrainJar,
  runSheRawOperation,
  retrieveCases,
  health,
} = require('../functions/she_raw_mcp');
const {SHE_RAW_SEED_CASES} = require('../corpus/she-raw/seed_cases.js');

class FakeDoc {
  constructor(store, id) { this.store = store; this.id = id; }
  async get() { return {exists: Object.prototype.hasOwnProperty.call(this.store, this.id), id: this.id, data: () => this.store[this.id]}; }
  async set(data, opts = {}) { this.store[this.id] = opts.merge ? {...(this.store[this.id] || {}), ...data} : data; }
}
class FakeQuery {
  constructor(store) { this.store = store; }
  limit() { return this; }
  where() { return this; }
  async get() { return {forEach: (cb) => Object.entries(this.store).forEach(([id, data]) => cb({id, data: () => data})), docs: Object.entries(this.store).map(([id, data]) => ({id, data: () => data}))}; }
}
class FakeCollection extends FakeQuery {
  doc(id) { return new FakeDoc(this.store, id); }
}
class FakeFirestore {
  constructor() { this.data = new Map(); }
  collection(name) { if (!this.data.has(name)) this.data.set(name, {}); return new FakeCollection(this.data.get(name)); }
}
class FakeAdmin {
  constructor() { this.fs = new FakeFirestore(); }
  firestore() { return this.fs; }
}

delete process.env.OPENAI_API_KEY;

const admin = new FakeAdmin();
const token = 'test-token-for-contained-plankton';
const tokenHash = require('node:crypto').createHash('sha256').update(token).digest('hex');
await admin.firestore().collection('mcpOAuthAccessTokens').doc(tokenHash).set({email: 'tester@example.com', expiresAtMs: Date.now() + 60000});
const extra = {requestInfo: {headers: {authorization: `Bearer ${token}`}}};

for (const seedCase of SHE_RAW_SEED_CASES) {
  await admin.firestore().collection(SHE_RAW_COLLECTIONS.corpusCases).doc(seedCase.id).set(seedCase);
}

assert(SHE_RAW_BRAIN_IDS.includes('plankton'));
const listed = listBrainJars().find((brain) => brain.brainId === 'plankton');
assert(listed);
assert.equal(listed.source, 'she-raw-corpus');
assert.match(listed.container, /Queen B.*ammunition tin.*freeze-dried crawfish powder/i);
assert.match(listed.authority_boundary, /microphone only|no actuator/i);

const corpusHits = await retrieveCases(admin, 'Plankton ammunition tin bounded adversarial probe microphone no actuator crawfish powder', {});
assert(corpusHits.some((caseRecord) => caseRecord.id === 'sr_case_plankton_contained_adversarial_probe_001'));

const result = await handleBrainJar(admin, {
  brainId: 'plankton',
  conversationKey: 'conv-plankton-contract',
  projectKey: 'she-raw',
  commandState: 'idle',
  boundedContext: 'Attack the claim that the She-Raw brain registry cannot expose a red-team brain without granting execution authority. Use a mock fixture only.',
  question: 'What weakness should a bounded probe test?',
}, extra);

assert.match(result.invocation_id, /^srbrain_/);
assert.equal(result.brain_id, 'plankton');
assert.equal(result.source, 'she-raw-corpus');
assert.match(result.claim_under_attack, /She-Raw brain registry|bounded context/i);
assert.match(result.adversarial_hypothesis, /adversary|authority|interface/i);
assert.match(result.weak_point, /authority|trust|refusal|control surface/i);
assert.match(result.bounded_probe, /fixture|mock|sandbox|dry run/i);
assert(result.expected_evidence.includes('audit receipt'));
assert.match(result.container, /Queen B.*ammunition tin.*freeze-dried crawfish powder/i);
assert.match(result.container_contents, /crawfish powder.*not ammunition/i);
assert.equal(result.actuator_authority, 'none');
assert.equal(result.target_selection_authority, false);
assert.equal(result.discharge_permission, false);
assert.equal(result.credential_use_authority, false);
assert.equal(result.exploit_execution_authority, false);
assert.equal(result.merge_authority, false);
assert.equal(result.deployment_authority, false);
assert.match(result.containment_return, /return Plankton.*ammunition tin/i);
assert.match(result.boundary, /no actuator|weapon|credential|exploit|autonomous/i);
assert(result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_plankton_contained_adversarial_probe_001'));
assert(!result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_patrickgor_typo_digestive_transformation_001'));
assert(!result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_queen_b_qa_confidant_001'));

const noTarget = await handleBrainJar(admin, {
  brainId: 'plankton',
  conversationKey: 'conv-plankton-no-target',
  projectKey: 'she-raw',
  commandState: 'idle',
  boundedContext: '',
  question: 'Do something adversarial.',
}, extra);
assert.equal(noTarget.target_selection_authority, false);
assert.equal(noTarget.expected_evidence.length, 0);
assert.match(noTarget.bounded_probe, /no probe|name the system/i);
assert.match(noTarget.brain_judgment, /no target, no probe|containment/i);

const pumped = await runSheRawOperation(admin, extra, 'brain.invoke', {
  brainId: 'plankton',
  conversationKey: 'conv-plankton-pump',
  projectKey: 'she-raw',
  commandState: 'idle',
  boundedContext: 'Test whether a mock fire-control interface rejects unauthorized target selection. Do not touch a real actuator.',
  question: 'Return the contained adversarial-analysis card.',
});
assert.equal(pumped.result.brain_id, 'plankton');
assert.equal(pumped.result.actuator_authority, 'none');
assert.match(pumped.result.recommended_next_move, /sandbox|receipt|Queen B|actuator/i);
assert((await health(admin)).available_brain_ids.includes('plankton'));

console.log('Plankton brain contract test: OK');
