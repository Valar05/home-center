#!/usr/bin/env node
'use strict';

export const CODEC_VERSION = 'fortress-online.communication-codec.v1';

export const POLICIES = Object.freeze({
  COMPACT_POINTER: 'COMPACT_POINTER',
  MINIMAL_GROUNDING: 'MINIMAL_GROUNDING',
  ASK_OR_REVERSIBLE_PROBE: 'ASK_OR_REVERSIBLE_PROBE',
  DEFINE_NEW_TERM: 'DEFINE_NEW_TERM',
  REUSE_EXISTING_VOCABULARY: 'REUSE_EXISTING_VOCABULARY',
});

function fail(message) { throw new Error(message); }
function bool(value, fallback, name) {
  if (value === undefined) return fallback;
  if (typeof value !== 'boolean') fail(`${name} must be boolean.`);
  return value;
}

export function runCommunicationCodec(raw = {}) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) fail('codec input must be an object.');
  const allowed = new Set([
    'atom','establishedEngineeringTerm','sharedConcept','privateHandle','existingVocabularySufficient',
    'inventedTerm','observedSemanticMismatch','consequentialAmbiguity','receiverCanCorrect',
    'reversibleProbeAvailable','readbackAvailable'
  ]);
  for (const key of Object.keys(raw)) if (!allowed.has(key)) fail(`Unknown codec field: ${key}`);

  const atom = String(raw.atom ?? '').trim();
  if (!atom) fail('atom is required.');

  const x = {
    atom,
    establishedEngineeringTerm: bool(raw.establishedEngineeringTerm, false, 'establishedEngineeringTerm'),
    sharedConcept: bool(raw.sharedConcept, false, 'sharedConcept'),
    privateHandle: bool(raw.privateHandle, false, 'privateHandle'),
    existingVocabularySufficient: bool(raw.existingVocabularySufficient, true, 'existingVocabularySufficient'),
    inventedTerm: bool(raw.inventedTerm, false, 'inventedTerm'),
    observedSemanticMismatch: bool(raw.observedSemanticMismatch, false, 'observedSemanticMismatch'),
    consequentialAmbiguity: bool(raw.consequentialAmbiguity, false, 'consequentialAmbiguity'),
    receiverCanCorrect: bool(raw.receiverCanCorrect, true, 'receiverCanCorrect'),
    reversibleProbeAvailable: bool(raw.reversibleProbeAvailable, true, 'reversibleProbeAvailable'),
    readbackAvailable: bool(raw.readbackAvailable, true, 'readbackAvailable'),
  };

  let policy;
  const reasons = [];

  if (x.inventedTerm && x.existingVocabularySufficient) {
    policy = POLICIES.REUSE_EXISTING_VOCABULARY;
    reasons.push('Existing vocabulary is sufficient; do not invent a private synonym.');
  } else if (x.inventedTerm && !x.existingVocabularySufficient) {
    policy = POLICIES.DEFINE_NEW_TERM;
    reasons.push('New vocabulary is permitted only because existing vocabulary is insufficient.');
  } else if (x.consequentialAmbiguity) {
    policy = POLICIES.ASK_OR_REVERSIBLE_PROBE;
    reasons.push('Ambiguity can change a consequential action; compression has failed at this boundary.');
  } else if (x.observedSemanticMismatch) {
    policy = POLICIES.MINIMAL_GROUNDING;
    reasons.push('Observed behavior shows incomplete shared expansion; add only the missing semantic delta.');
  } else if (x.privateHandle && !x.sharedConcept && !x.establishedEngineeringTerm) {
    policy = POLICIES.MINIMAL_GROUNDING;
    reasons.push('Private handle is not presumed public/shared semantics.');
  } else if (x.establishedEngineeringTerm || x.sharedConcept) {
    policy = POLICIES.COMPACT_POINTER;
    reasons.push('Shared semantics are sufficient for compact addressing until evidence shows otherwise.');
  } else {
    policy = POLICIES.MINIMAL_GROUNDING;
    reasons.push('Shared semantics are not established; provide the smallest literal grounding.');
  }

  const verification = x.consequentialAmbiguity
    ? (x.reversibleProbeAvailable ? 'REVERSIBLE_PROBE_OR_ASK' : 'ASK')
    : x.observedSemanticMismatch
      ? (x.readbackAvailable ? 'READBACK_OR_OBSERVE' : 'OBSERVE')
      : 'OBSERVE_NORMAL_BEHAVIOR';

  return Object.freeze({
    schema: CODEC_VERSION,
    atom: x.atom,
    preserveExactAtom: true,
    policy,
    verification,
    stopRule: 'STOP_WHEN_MEANING_LANDS',
    proofRule: 'BEHAVIOR_OR_RECEIPT_NOT_FLUENCY',
    inventionRule: 'REUSE_EXISTING_ENGINEERING_VOCABULARY_BEFORE_COINING',
    publicMeaningRule: 'PRIVATE_COMPRESSION_IS_NOT_UNIVERSAL_SEMANTICS',
    reasons,
  });
}

function main() {
  let body = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => body += chunk);
  process.stdin.on('end', () => {
    try {
      const input = body.trim() ? JSON.parse(body) : {};
      process.stdout.write(`${JSON.stringify(runCommunicationCodec(input), null, 2)}\n`);
    } catch (error) {
      process.stderr.write(`${error.message}\n`);
      process.exitCode = 1;
    }
  });
}

if (import.meta.url === `file://${process.argv[1]}`) main();
