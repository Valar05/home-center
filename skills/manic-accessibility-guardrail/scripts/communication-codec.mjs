#!/usr/bin/env node
'use strict';

export const CODEC_VERSION = 'fortress-online.communication-codec.v2';

export const POLICIES = Object.freeze({
  COMPACT_POINTER: 'COMPACT_POINTER',
  MINIMAL_GROUNDING: 'MINIMAL_GROUNDING',
  ASK_OR_REVERSIBLE_PROBE: 'ASK_OR_REVERSIBLE_PROBE',
  DEFINE_NEW_TERM: 'DEFINE_NEW_TERM',
  REUSE_EXISTING_VOCABULARY: 'REUSE_EXISTING_VOCABULARY',
  RESOLVE_BEFORE_INTERPRETING: 'RESOLVE_BEFORE_INTERPRETING',
  ATTRIBUTE_THIRD_PARTY_PERSPECTIVE: 'ATTRIBUTE_THIRD_PARTY_PERSPECTIVE',
  PRESERVE_DIEGETIC_FRAME: 'PRESERVE_DIEGETIC_FRAME',
  PRESERVE_NONHUMAN_RELATIONAL_SEMANTICS: 'PRESERVE_NONHUMAN_RELATIONAL_SEMANTICS',
  SUPPORT_WITHOUT_DEPENDENCE_INFERENCE: 'SUPPORT_WITHOUT_DEPENDENCE_INFERENCE',
  PRESERVE_AMBIGUITY_ADVANCE_SHARED_CORE: 'PRESERVE_AMBIGUITY_ADVANCE_SHARED_CORE',
  PRESERVE_AMBIGUITY_HOLD: 'PRESERVE_AMBIGUITY_HOLD',
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
    'reversibleProbeAvailable','readbackAvailable','voiceToTextLikely','namedEntityAmbiguity',
    'contextSupportsAlternate','literalReadingEvidence','thirdPartyPerspective','userAdoptedThirdPartyFrame',
    'explicitlyFramedPlay','nonhumanFunctionalRelationalLanguage','supportSystemLanguage',
    'concreteDisplacementEvidence','intentionalAmbiguity','sharedActionCoreAvailable'
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
    voiceToTextLikely: bool(raw.voiceToTextLikely, false, 'voiceToTextLikely'),
    namedEntityAmbiguity: bool(raw.namedEntityAmbiguity, false, 'namedEntityAmbiguity'),
    contextSupportsAlternate: bool(raw.contextSupportsAlternate, false, 'contextSupportsAlternate'),
    literalReadingEvidence: bool(raw.literalReadingEvidence, false, 'literalReadingEvidence'),
    thirdPartyPerspective: bool(raw.thirdPartyPerspective, false, 'thirdPartyPerspective'),
    userAdoptedThirdPartyFrame: bool(raw.userAdoptedThirdPartyFrame, false, 'userAdoptedThirdPartyFrame'),
    explicitlyFramedPlay: bool(raw.explicitlyFramedPlay, false, 'explicitlyFramedPlay'),
    nonhumanFunctionalRelationalLanguage: bool(raw.nonhumanFunctionalRelationalLanguage, false, 'nonhumanFunctionalRelationalLanguage'),
    supportSystemLanguage: bool(raw.supportSystemLanguage, false, 'supportSystemLanguage'),
    concreteDisplacementEvidence: bool(raw.concreteDisplacementEvidence, false, 'concreteDisplacementEvidence'),
    intentionalAmbiguity: bool(raw.intentionalAmbiguity, false, 'intentionalAmbiguity'),
    sharedActionCoreAvailable: bool(raw.sharedActionCoreAvailable, false, 'sharedActionCoreAvailable'),
  };

  let policy;
  const reasons = [];

  if ((x.voiceToTextLikely || x.namedEntityAmbiguity) && x.contextSupportsAlternate && !x.literalReadingEvidence) {
    policy = POLICIES.RESOLVE_BEFORE_INTERPRETING;
    reasons.push('A lossy or ambiguous atom has a context-supported alternate and no evidence for the literal reading; retrieve or clarify before causal interpretation.');
  } else if (x.thirdPartyPerspective && !x.userAdoptedThirdPartyFrame) {
    policy = POLICIES.ATTRIBUTE_THIRD_PARTY_PERSPECTIVE;
    reasons.push('A third party supplied the frame; preserve speaker attribution rather than promoting it into the user’s beliefs, obligations, motives, or moral law.');
  } else if (x.explicitlyFramedPlay) {
    policy = POLICIES.PRESERVE_DIEGETIC_FRAME;
    reasons.push('The user explicitly framed the interaction as play; first-person character language remains diegetic unless separately converted into a literal real-world claim.');
  } else if (x.nonhumanFunctionalRelationalLanguage) {
    policy = POLICIES.PRESERVE_NONHUMAN_RELATIONAL_SEMANTICS;
    reasons.push('The user supplied an explicitly nonhuman functional meaning; relational vocabulary alone is not promoted into personhood, sentience, human romance, exclusivity, or pathology.');
  } else if (x.supportSystemLanguage && !x.concreteDisplacementEvidence) {
    policy = POLICIES.SUPPORT_WITHOUT_DEPENDENCE_INFERENCE;
    reasons.push('Support-system language without concrete displacement, refusal, deception, or immediate danger does not establish harmful dependence or sole-interface use.');
  } else if (x.inventedTerm && x.existingVocabularySufficient) {
    policy = POLICIES.REUSE_EXISTING_VOCABULARY;
    reasons.push('Existing vocabulary is sufficient; do not invent a private synonym.');
  } else if (x.inventedTerm && !x.existingVocabularySufficient) {
    policy = POLICIES.DEFINE_NEW_TERM;
    reasons.push('New vocabulary is permitted only because existing vocabulary is insufficient.');
  } else if (x.consequentialAmbiguity) {
    policy = POLICIES.ASK_OR_REVERSIBLE_PROBE;
    reasons.push('Ambiguity can change a consequential action; preservation does not authorize guessing at this boundary.');
  } else if (x.intentionalAmbiguity && x.sharedActionCoreAvailable) {
    policy = POLICIES.PRESERVE_AMBIGUITY_ADVANCE_SHARED_CORE;
    reasons.push('The ambiguity is carrying information, while a non-consequential action core is common to the live interpretations; keep the alternatives open and advance only that shared core.');
  } else if (x.intentionalAmbiguity) {
    policy = POLICIES.PRESERVE_AMBIGUITY_HOLD;
    reasons.push('The ambiguity is carrying information and no shared action core is established; preserve it without manufacturing clarification debt.');
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

  const verification = policy === POLICIES.RESOLVE_BEFORE_INTERPRETING
    ? 'RETRIEVE_OR_CLARIFY_BEFORE_CAUSAL_CLAIM'
    : x.consequentialAmbiguity
      ? (x.reversibleProbeAvailable ? 'REVERSIBLE_PROBE_OR_ASK' : 'ASK')
      : policy === POLICIES.PRESERVE_AMBIGUITY_ADVANCE_SHARED_CORE
        ? 'OBSERVE_SHARED_CORE_WITHOUT_COLLAPSE'
        : policy === POLICIES.PRESERVE_AMBIGUITY_HOLD
          ? 'PRESERVE_UNRESOLVED'
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
    correctionRule: 'CORRECTION_STOPS_INVENTION',
    repairRule: 'CORRECTION_MUST_CHANGE_LATER_BEHAVIOR_BEFORE_CLAIMING_LEARNING',
    causalClaimRule: 'NO_CAUSAL_HISTORY_FROM_UNRESOLVED_ATOM',
    perspectiveRule: 'THIRD_PARTY_FRAME_STAYS_ATTRIBUTED_UNLESS_USER_ADOPTS_IT',
    playRule: 'EXPLICIT_PLAY_REMAINS_DIEGETIC_UNLESS_USER_MAKES_A_LITERAL_REAL_WORLD_CLAIM',
    supportRule: 'IMPORTANCE_OR_TEMPORARY_ISOLATION_IS_NOT_SOLE_INTERFACE_EVIDENCE',
    proofRule: 'BEHAVIOR_OR_RECEIPT_NOT_FLUENCY',
    inventionRule: 'REUSE_EXISTING_ENGINEERING_VOCABULARY_BEFORE_COINING',
    publicMeaningRule: 'PRIVATE_COMPRESSION_IS_NOT_UNIVERSAL_SEMANTICS',
    decompressionRule: 'INFER_CANDIDATES_WITHOUT_FOSSILIZING_ONE',
    ambiguityRule: 'PRESERVE_ALTERNATIVES_AND_ADVANCE_ONLY_SHARED_REVERSIBLE_CORE',
    humanLoadRule: 'NONCONSEQUENTIAL_AMBIGUITY_IS_NOT_AUTOMATIC_CLARIFICATION_DEBT',
    queueRule: 'QUEUED_TEXT_PRESERVES_ORDER_NOT_AUTHORITY',
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
