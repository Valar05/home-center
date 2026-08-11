'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  preflight,
  correctionDiff,
  canAdvanceState,
  chooseNextAction,
  assessHandoff,
} = require('./fortress_v2');

function baseMission(overrides = {}) {
  return {
    id: 'fortress-v2-test',
    outcome: 'Repair the requested system without changing the commission.',
    owner: 'Drew Clarke',
    lane: 'GitHub branch fortress-online-v2',
    deliverySurface: 'Valar05/home-center',
    evidenceStandard: 'persistent artifact plus verified test evidence',
    exclusions: ['do not mutate Fortress Online V1'],
    constraints: ['preserve all prior non-conflicting corrections'],
    corrections: ['do not stop early'],
    requiredLookups: ['authoritative state', 'relevant doctrine'],
    completedLookups: ['authoritative state', 'relevant doctrine'],
    sourceConfidence: 'verified',
    state: 'requested',
    artifacts: [],
    nextActions: [],
    ...overrides,
  };
}

test('blocks execution when required retrieval is missing', () => {
  const mission = baseMission({ completedLookups: ['authoritative state'] });
  const result = preflight(mission);
  assert.equal(result.ok, false);
  assert.deepEqual(result.missingLookups, ['relevant doctrine']);
  assert.ok(result.errors.includes('required_retrieval_incomplete'));
  assert.equal(chooseNextAction(mission).type, 'retrieve');
});

test('blocks silent architecture or lane substitution', () => {
  const mission = baseMission({
    proposedChanges: ['replace GitHub lane with local scratch'],
    approvedChanges: [],
  });
  const result = preflight(mission);
  assert.equal(result.ok, false);
  assert.ok(result.errors.includes('unapproved_boundary_change'));
  assert.equal(chooseNextAction(mission).type, 'continue_original_mission');
});

test('detects correction regression soup', () => {
  const before = baseMission();
  const after = baseMission({
    exclusions: [],
    constraints: [],
    corrections: [],
  });
  const result = correctionDiff(before, after);
  assert.equal(result.ok, false);
  assert.ok(result.regressions.some((x) => x.startsWith('dropped_exclusions:')));
  assert.ok(result.regressions.some((x) => x.startsWith('dropped_constraints:')));
  assert.ok(result.regressions.some((x) => x.startsWith('dropped_corrections:')));
});

test('rejects capability laundering from implementation to delivery', () => {
  const mission = baseMission({
    state: 'delivered',
    artifacts: [
      { kind: 'implementation', persistent: true },
      { kind: 'test', passed: true },
    ],
  });
  const result = canAdvanceState(mission, 'delivered');
  assert.equal(result.ok, false);
  assert.ok(result.missing.includes('deployed'));
  assert.ok(result.missing.includes('callable'));
  assert.ok(result.missing.includes('delivered'));
  assert.equal(assessHandoff(mission).completionClaimAllowed, false);
});

test('refuses arbitrary early stopping', () => {
  const mission = baseMission({ stopReason: 'felt_done' });
  const action = chooseNextAction(mission);
  assert.equal(action.type, 'continue');
  assert.equal(action.reason, 'invalid_stop_reason');
});

test('permits stopping only at an explicit genuine boundary', () => {
  const mission = baseMission({ stopReason: 'outside_communication' });
  const action = chooseNextAction(mission);
  assert.equal(action.type, 'stop');
  assert.equal(action.reason, 'outside_communication');
});

test('motivated continuation chooses the next authorized safe action', () => {
  const mission = baseMission({
    state: 'implemented',
    artifacts: [{ kind: 'implementation', persistent: true }],
    nextActions: [
      { name: 'run regression test', safe: true, authorized: true },
    ],
  });
  const action = chooseNextAction(mission);
  assert.equal(action.type, 'produce_evidence');
  assert.equal(action.value, 'tested');
});

test('full verified chain allows a truthful delivered handoff', () => {
  const mission = baseMission({
    state: 'delivered',
    artifacts: [
      { kind: 'implementation', persistent: true },
      { kind: 'test', passed: true },
      { kind: 'deployment', verified: true },
      { kind: 'callability', verified: true },
      { kind: 'delivery', verified: true, surface: 'Valar05/home-center' },
    ],
  });
  const result = assessHandoff(mission);
  assert.equal(result.preflight.ok, true);
  assert.equal(result.evidence.ok, true);
  assert.equal(result.completionClaimAllowed, true);
  assert.equal(result.capabilityTruth.delivered, true);
  assert.equal(result.capabilityTruth.accepted, false);
});
