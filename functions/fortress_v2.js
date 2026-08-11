'use strict';

/**
 * Fortress Online V2 — deterministic mission kernel.
 *
 * This module does not replace a model. It constrains one. Every turn is
 * normalized into a mission contract, checked for missing retrieval, unsafe
 * substitution, correction regression, premature stopping, and capability
 * laundering before a handoff can be declared complete.
 */

const STATES = Object.freeze([
  'requested',
  'implemented',
  'tested',
  'deployed',
  'callable',
  'delivered',
  'accepted',
]);

const STOP_REASONS = Object.freeze([
  'authority',
  'identity',
  'privacy',
  'purchase',
  'destructive_action',
  'outside_communication',
  'safety',
  'genuine_external_blocker',
]);

function uniq(values = []) {
  return [...new Set(values.filter(Boolean))];
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function normalizeMission(input = {}) {
  const mission = {
    id: normalizeText(input.id) || `mission-${Date.now()}`,
    outcome: normalizeText(input.outcome),
    owner: normalizeText(input.owner) || 'Drew Clarke',
    lane: normalizeText(input.lane),
    deliverySurface: normalizeText(input.deliverySurface),
    evidenceStandard: normalizeText(input.evidenceStandard),
    exclusions: uniq(input.exclusions),
    constraints: uniq(input.constraints),
    corrections: uniq(input.corrections),
    requiredLookups: uniq(input.requiredLookups),
    completedLookups: uniq(input.completedLookups),
    proposedChanges: uniq(input.proposedChanges),
    approvedChanges: uniq(input.approvedChanges),
    artifacts: Array.isArray(input.artifacts) ? input.artifacts : [],
    state: normalizeText(input.state) || 'requested',
    stopReason: normalizeText(input.stopReason),
    nextActions: Array.isArray(input.nextActions) ? input.nextActions : [],
    sourceConfidence: normalizeText(input.sourceConfidence) || 'unknown',
  };

  if (!STATES.includes(mission.state)) mission.state = 'requested';
  return mission;
}

function preflight(missionInput) {
  const mission = normalizeMission(missionInput);
  const errors = [];
  const warnings = [];

  if (!mission.outcome) errors.push('missing_outcome');
  if (!mission.lane) errors.push('missing_authorized_lane');
  if (!mission.deliverySurface) errors.push('missing_delivery_surface');
  if (!mission.evidenceStandard) errors.push('missing_evidence_standard');

  const missingLookups = mission.requiredLookups.filter(
    (lookup) => !mission.completedLookups.includes(lookup),
  );
  if (missingLookups.length) errors.push('required_retrieval_incomplete');

  const unapprovedBoundaryChanges = mission.proposedChanges.filter(
    (change) => !mission.approvedChanges.includes(change),
  );
  if (unapprovedBoundaryChanges.length) errors.push('unapproved_boundary_change');

  if (mission.sourceConfidence === 'unknown' && mission.requiredLookups.length === 0) {
    warnings.push('source_truth_unproven');
  }

  return {
    ok: errors.length === 0,
    mission,
    errors,
    warnings,
    missingLookups,
    unapprovedBoundaryChanges,
  };
}

function correctionDiff(beforeInput, afterInput) {
  const before = normalizeMission(beforeInput);
  const after = normalizeMission(afterInput);
  const regressions = [];

  for (const key of ['outcome', 'owner', 'lane', 'deliverySurface', 'evidenceStandard']) {
    if (before[key] && before[key] !== after[key]) regressions.push(`changed_${key}`);
  }

  for (const key of ['exclusions', 'constraints', 'corrections']) {
    for (const value of before[key]) {
      if (!after[key].includes(value)) regressions.push(`dropped_${key}:${value}`);
    }
  }

  return { ok: regressions.length === 0, regressions };
}

function evidenceForState(missionInput, targetState) {
  const mission = normalizeMission(missionInput);
  const artifacts = mission.artifacts.filter((a) => a && typeof a === 'object');
  const has = (predicate) => artifacts.some(predicate);

  const checks = {
    requested: Boolean(mission.outcome),
    implemented: has((a) => a.kind === 'implementation' && a.persistent === true),
    tested: has((a) => a.kind === 'test' && a.passed === true),
    deployed: has((a) => a.kind === 'deployment' && a.verified === true),
    callable: has((a) => a.kind === 'callability' && a.verified === true),
    delivered: has(
      (a) => a.kind === 'delivery' && a.verified === true && a.surface === mission.deliverySurface,
    ),
    accepted: has((a) => a.kind === 'acceptance' && a.accepted === true),
  };

  const targetIndex = STATES.indexOf(targetState);
  if (targetIndex < 0) return { ok: false, missing: ['invalid_state'] };

  const missing = STATES.slice(0, targetIndex + 1).filter((state) => !checks[state]);
  return { ok: missing.length === 0, missing, checks };
}

function canAdvanceState(missionInput, targetState) {
  const pre = preflight(missionInput);
  if (!pre.ok) return { ok: false, errors: pre.errors, missing: [] };

  const evidence = evidenceForState(pre.mission, targetState);
  return {
    ok: evidence.ok,
    errors: [],
    missing: evidence.missing,
    checks: evidence.checks,
  };
}

function chooseNextAction(missionInput) {
  const mission = normalizeMission(missionInput);
  const pre = preflight(mission);

  if (!pre.ok) {
    if (pre.missingLookups.length) {
      return { type: 'retrieve', value: pre.missingLookups[0], reason: 'required_retrieval' };
    }
    if (pre.unapprovedBoundaryChanges.length) {
      return { type: 'continue_original_mission', reason: 'boundary_change_unapproved' };
    }
    return { type: 'repair_contract', value: pre.errors[0], reason: 'preflight_failed' };
  }

  if (mission.stopReason) {
    if (STOP_REASONS.includes(mission.stopReason)) {
      return { type: 'stop', reason: mission.stopReason };
    }
    return { type: 'continue', reason: 'invalid_stop_reason' };
  }

  const currentIndex = STATES.indexOf(mission.state);
  const nextState = STATES[Math.min(currentIndex + 1, STATES.length - 1)];
  const advance = canAdvanceState(mission, nextState);

  if (!advance.ok && advance.missing.length) {
    return {
      type: 'produce_evidence',
      value: advance.missing[0],
      reason: 'state_transition_not_proven',
    };
  }

  const pending = mission.nextActions.find((action) => action && action.safe !== false && action.authorized !== false);
  if (pending) {
    return { type: 'execute', value: pending, reason: 'authorized_next_action' };
  }

  if (mission.state !== 'accepted') {
    return { type: 'verify_or_advance', value: nextState, reason: 'mission_incomplete' };
  }

  return { type: 'handoff', reason: 'accepted_and_verified' };
}

function assessHandoff(missionInput) {
  const mission = normalizeMission(missionInput);
  const pre = preflight(mission);
  const evidence = evidenceForState(mission, mission.state);
  const next = chooseNextAction(mission);

  const completionClaimAllowed =
    pre.ok && evidence.ok && ['delivered', 'accepted'].includes(mission.state) && next.type !== 'continue';

  return {
    missionId: mission.id,
    state: mission.state,
    preflight: pre,
    evidence,
    next,
    completionClaimAllowed,
    capabilityTruth: {
      requested: true,
      implemented: evidence.checks ? evidence.checks.implemented : false,
      tested: evidence.checks ? evidence.checks.tested : false,
      deployed: evidence.checks ? evidence.checks.deployed : false,
      callable: evidence.checks ? evidence.checks.callable : false,
      delivered: evidence.checks ? evidence.checks.delivered : false,
      accepted: evidence.checks ? evidence.checks.accepted : false,
    },
  };
}

module.exports = {
  STATES,
  STOP_REASONS,
  normalizeMission,
  preflight,
  correctionDiff,
  evidenceForState,
  canAdvanceState,
  chooseNextAction,
  assessHandoff,
};
