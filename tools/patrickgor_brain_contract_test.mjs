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
const token = 'test-token-for-patrickgor';
const tokenHash = require('node:crypto').createHash('sha256').update(token).digest('hex');
await admin.firestore().collection('mcpOAuthAccessTokens').doc(tokenHash).set({email: 'tester@example.com', expiresAtMs: Date.now() + 60000});
const extra = {requestInfo: {headers: {authorization: `Bearer ${token}`}}};

for (const seedCase of SHE_RAW_SEED_CASES) {
  await admin.firestore().collection(SHE_RAW_COLLECTIONS.corpusCases).doc(seedCase.id).set(seedCase);
}

assert(SHE_RAW_BRAIN_IDS.includes('patrickgor'));
assert(listBrainJars().some((brain) => brain.brainId === 'patrickgor' && brain.source === 'she-raw-corpus'));

const corpusHits = await retrieveCases(admin, 'Patrickgor PatrickGPT autocorrect typo creature digest the mutation convert it into honey', {});
assert(corpusHits.some((caseRecord) => caseRecord.id === 'sr_case_patrickgor_typo_digestive_transformation_001'));

const result = await handleBrainJar(admin, {
  brainId: 'patrickgor',
  conversationKey: 'conv-patrickgor-contract',
  projectKey: 'she-raw',
  commandState: 'idle',
  boundedContext: 'Patrickgor was supposed to be PatrickGPT, but autocorrect created a monster. Patrickgor it is. Digest the mutation carefully.',
  question: 'What did the mistake create that the intended input could not?',
}, extra);

assert.match(result.invocation_id, /^srbrain_/);
assert.equal(result.brain_id, 'patrickgor');
assert.equal(result.source, 'she-raw-corpus');
assert.equal(result.intended_input, 'PatrickGPT');
assert.equal(result.mutation, 'Patrickgor');
assert.match(result.provenance_status, /correction preserved/i);
assert.match(result.edible_signal, /mass|appetite|provenance|artifact/i);
assert.match(result.honey_artifact, /explicit-only|digest|labeled artifact/i);
assert.match(result.damp_artifact, /humor|canon|generativity/i);
assert.match(result.larva_candidate, /test|transfer|hijack/i);
assert.match(result.jar_label, /PATRICKGOR|EXPLICIT INVOCATION ONLY/i);
assert.match(result.boundary, /exact identifiers|code symbols|living people|medical|legal|safety instructions|standalone agent/i);
assert(result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_patrickgor_typo_digestive_transformation_001'));
assert(!result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_bikini_bottom_anti_agentism_001'));
assert(!result.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_queen_b_qa_confidant_001'));

const unproven = await handleBrainJar(admin, {
  brainId: 'patrickgor',
  conversationKey: 'conv-patrickgor-unproven',
  projectKey: 'she-raw',
  commandState: 'idle',
  boundedContext: 'Digest this ordinary sentence.',
  question: 'Make a creature.',
}, extra);
assert.equal(unproven.intended_input, 'unproven');
assert.equal(unproven.mutation, 'unproven');
assert.match(unproven.brain_judgment, /do not promote/i);

const pumped = await runSheRawOperation(admin, extra, 'brain.invoke', {
  brainId: 'patrickgor',
  conversationKey: 'conv-patrickgor-pump',
  projectKey: 'she-raw',
  commandState: 'idle',
  boundedContext: 'Patrickgor was meant to be PatrickGPT. Preserve the correction and test the monster.',
  question: 'Return the labeled digestion card.',
});
assert.equal(pumped.result.brain_id, 'patrickgor');
assert.equal(pumped.result.intended_input, 'PatrickGPT');
assert.match(pumped.result.recommended_next_move, /preserve|bounded mutation|label/i);
assert((await health(admin)).available_brain_ids.includes('patrickgor'));

console.log('Patrickgor brain contract test: OK');
