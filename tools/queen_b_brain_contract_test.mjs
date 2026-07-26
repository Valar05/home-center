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
const token = 'test-token-for-queen-b';
const tokenHash = require('node:crypto').createHash('sha256').update(token).digest('hex');
await admin.firestore().collection('mcpOAuthAccessTokens').doc(tokenHash).set({email: 'tester@example.com', expiresAtMs: Date.now() + 60000});
const extra = {requestInfo: {headers: {authorization: `Bearer ${token}`}}};

for (const seedCase of SHE_RAW_SEED_CASES) {
  await admin.firestore().collection(SHE_RAW_COLLECTIONS.corpusCases).doc(seedCase.id).set(seedCase);
}

assert(SHE_RAW_BRAIN_IDS.includes('queen_b'));
assert(listBrainJars().some((brain) => brain.brainId === 'queen_b' && brain.source === 'she-raw-corpus'));

const corpusHits = await retrieveCases(admin, 'Queen B QA confidant release confidence rehearsed green broad contract failure evidence receipts', {});
assert(corpusHits.some((caseRecord) => caseRecord.id === 'sr_case_queen_b_qa_confidant_001'));

const queenB = await handleBrainJar(admin, {
  brainId: 'queen_b',
  conversationKey: 'conv-queen-b-contract',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'A worker says the feature is done after a dedicated check passed, but the broad She-Raw contract failed and Home Center mirror evidence is missing. Need confidence without comfort.',
  question: 'Can we trust this release claim?',
}, extra);

assert.match(queenB.invocation_id, /^srbrain_/);
assert.equal(queenB.brain_id, 'queen_b');
assert.equal(queenB.source, 'she-raw-corpus');
assert(queenB.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_queen_b_qa_confidant_001'));
assert(!queenB.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_bikini_bottom_anti_agentism_001'));
assert(!queenB.retrieved_cases.some((caseRecord) => caseRecord.id === 'sr_case_tango_humane_mission_control_001'));
assert.match(queenB.release_judgment, /not releasable|blocked|red/i);
assert.match(queenB.confidence_read, /confidence|green|evidence|receipts/i);
assert(Array.isArray(queenB.receipts_required) && queenB.receipts_required.length >= 4);
assert(queenB.receipts_required.some((receipt) => /broad She-Raw contract/i.test(receipt)));
assert(queenB.receipts_required.some((receipt) => /mirror/i.test(receipt)));
assert.match(queenB.rehearsal_script, /dedicated check|broad contract|mirror/i);
assert.match(queenB.boundary, /comfort|approval|merge|deploy/i);
assert.equal(queenB.qa_checks.dedicated_contract_is_not_enough, true);
assert.equal(queenB.qa_checks.broad_contract_must_pass, true);
assert.equal(queenB.qa_checks.mirror_evidence_required, true);

const pumped = await runSheRawOperation(admin, extra, 'brain.invoke', {
  brainId: 'queen_b',
  conversationKey: 'conv-queen-b-pump',
  projectKey: 'home-center',
  commandState: 'idle',
  boundedContext: 'Dedicated Queen B test passed, but Tango and full She-Raw evidence have not been run.',
  question: 'Return the release confidence card.',
});
assert.equal(pumped.result.brain_id, 'queen_b');
assert.match(pumped.result.recommended_next_move, /run|contract|mirror|evidence/i);
assert((await health(admin)).available_brain_ids.includes('queen_b'));

console.log('Queen B brain contract test: OK');
