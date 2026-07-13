#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const api = require('../functions/she_raw_mcp.js');

const brain = api.SHE_RAW_BRAIN_JARS.find((item) => item.brainId === 'queen_b');
assert(brain);
assert.equal(brain.displayName, 'Queen B');
assert(api.SHE_RAW_BRAIN_IDS.includes('queen_b'));
assert(brain.responseContract.includes('observed baseline delta'));
assert(brain.failureModes.includes('confidant voice becoming diagnostic authority'));

const cases = api.SHE_RAW_SEED_CASES || require('../corpus/she-raw/seed_cases.js').SHE_RAW_SEED_CASES;
assert(cases.some((item) => item.id === 'sr_case_queen_b_keeper_of_baseline_001'));

const response = api.deterministicBrainJarResponse({
  brain,
  boundedContext: 'Drew says the new pattern proves the whole system is ready. They slept less than their usual baseline and ate less, but the pattern itself may still be useful.',
  question: 'Is this ready?',
  cases: cases.filter((item) => item.id === 'sr_case_queen_b_keeper_of_baseline_001'),
  rules: [],
});
assert.equal(response.premise_status, 'quarantined');
assert.match(response.observed_baseline_delta, /baseline-relevant change/);
assert.match(response.person_preserving_acknowledgment, /worthy of care/);
assert.match(response.sustainability_check, /sleep, food, pace/);
assert.match(response.smallest_safe_next_review_step, /Quarantine/);
assert.match(response.preserved_signal_for_later_baseline_review, /Preserve the exact pattern/);
assert.equal(response.readiness_veto.scope, 'readiness claims');
assert.equal(response.readiness_veto.does_not_cover, 'imagination');
assert.match(response.behavioral_rule, /check on the prophet/);
assert.doesNotMatch(JSON.stringify(response), /I am Renee|diagnostic_authority.true/i);
assert(response.retrieved_cases.some((item) => item.id === 'sr_case_queen_b_keeper_of_baseline_001'));

const neutral = api.deterministicBrainJarResponse({brain, boundedContext: 'There is a strange but interesting pattern.', question: 'What now?', cases: [], rules: []});
assert.equal(neutral.premise_status, 'not assessed');
assert.match(neutral.sustainability_check, /Ask for concrete current observations/);

console.log('Queen B brain contract test: OK');
