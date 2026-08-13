'use strict';

const { isRecord, requireText, requireSha, requireRfc3339, canonicalJson, sha256 } = require('./contracts');
const { authorizeApproval } = require('./guards');

const EXPERIMENT_PROVIDERS = Object.freeze(['groq', 'hugging_face']);
const EXPERIMENT_STATES = Object.freeze(['EXPERIMENT_DISABLED', 'SCOPED_ACTIVATION', 'RUNNING', 'RESULT_QUARANTINED', 'HARVESTED_LOCAL', 'EXPIRED', 'FAILED_NONBLOCKING']);

function experimentDigestPayload(value) {
  const payload = { ...value };
  delete payload.envelopeHash;
  return payload;
}

function validateExperimentEnvelope(value, options = {}) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['experiment envelope must be a plain object'] };
  if (value.schema !== 'provider.experiment.v1') errors.push('experiment.schema must be provider.experiment.v1');
  for (const key of ['experimentId', 'provider', 'model', 'purpose', 'inputClassification', 'dataPolicy', 'privacyPolicy', 'costAuthorityId', 'idempotencyKey', 'executorKind', 'executorId']) requireText(value[key], `experiment.${key}`, errors);
  if (!EXPERIMENT_PROVIDERS.includes(value.provider)) errors.push('experiment.provider is not allowlisted');
  if (!EXPERIMENT_STATES.includes(value.state)) errors.push('experiment.state is unsupported');
  for (const key of ['commissionHash', 'inputHash', 'resultHash', 'envelopeHash']) requireSha(value[key], `experiment.${key}`, errors);
  if (!Number.isSafeInteger(value.quotaCap) || value.quotaCap < 0) errors.push('experiment.quotaCap must be a non-negative safe integer');
  if (!['PUBLIC','NON_SENSITIVE_CODE','PRIVATE_LOCAL_ONLY'].includes(value.inputClassification)) errors.push('experiment input classification is not allowed');
  requireRfc3339(value.createdAt, 'experiment.createdAt', errors);
  requireRfc3339(value.expiresAt, 'experiment.expiresAt', errors);
  if (value.primaryDependency !== false || value.stateOwner !== false || value.silentFallback !== false || value.providerAbsenceStopsCore !== false) errors.push('experiment cannot be primary, state owner, silent fallback, or core dependency');
  if (value.harvestRequired !== true || value.useBeforeHarvestAllowed !== false) errors.push('experiment result must be harvested locally before use');
  if (!isRecord(value.harvestTarget)) errors.push('experiment.harvestTarget must be a plain object');
  else {
    if (!['artifact', 'test', 'jar', 'skill'].includes(value.harvestTarget.kind)) errors.push('experiment.harvestTarget.kind is unsupported');
    requireText(value.harvestTarget.ref, 'experiment.harvestTarget.ref', errors);
  }
  if (!Number.isSafeInteger(options.maxQuotaCap) || value.quotaCap > options.maxQuotaCap) errors.push('experiment quota exceeds trusted cap');
  if (value.state !== 'EXPERIMENT_DISABLED') {
    if (typeof options.resolveApproval !== 'function' || !isRecord(options.approvalRegistry)) errors.push('experiment activation requires trusted approval resolver/registry');
    else {
      const approval=options.resolveApproval(value.costAuthorityId);
      try { const out=authorizeApproval(approval,{actor:'Drew',action:`provider:${value.provider}`,target:value.model,artifactDigest:value.inputHash,environment:'EXPERIMENT',commissionHash:value.commissionHash,idempotencyKey:value.idempotencyKey},options.now,options.approvalRegistry); if(!out.cas) errors.push('experiment approval CAS missing'); } catch(error){ errors.push(`experiment approval invalid: ${error.code||error.message}`); }
    }
  }
  if (typeof options.resolvePrivacyPolicy !== 'function' || options.resolvePrivacyPolicy(value.privacyPolicy)?.classification !== value.inputClassification || options.resolvePrivacyPolicy(value.privacyPolicy)?.provider !== value.provider) errors.push('trusted privacy policy mismatch');
  if (value.provider === 'groq' && value.state !== 'EXPERIMENT_DISABLED' && options.groqPriorState !== 'EXPERIMENT_DISABLED') errors.push('Groq must transition from EXPERIMENT_DISABLED under scoped activation');
  requireRfc3339(options.now, 'options.now', errors);
  if (errors.length === 0) {
    if (Date.parse(value.expiresAt) <= Date.parse(value.createdAt) || Date.parse(options.now) >= Date.parse(value.expiresAt)) errors.push('experiment is expired or has invalid expiry');
    if (sha256(experimentDigestPayload(value)) !== value.envelopeHash) errors.push('experiment.envelopeHash mismatch');
  }
  return { ok: errors.length === 0, errors };
}

function validateExperimentHarvest(value, envelope, options = {}) {
  const errors = [];
  if (!isRecord(value) || !isRecord(envelope)) return { ok: false, errors: ['harvest and envelope must be plain objects'] };
  for (const key of ['harvestId', 'experimentId', 'resultHash', 'localArtifactHash', 'localArtifactRef', 'verifierId']) requireText(value[key], `harvest.${key}`, errors);
  for (const key of ['resultHash', 'localArtifactHash', 'harvestHash']) requireSha(value[key], `harvest.${key}`, errors);
  requireRfc3339(value.verifiedAt, 'harvest.verifiedAt', errors);
  const envelopeValidation=validateExperimentEnvelope(envelope,options.envelopeOptions||{}); errors.push(...envelopeValidation.errors.map(error=>`harvest envelope ${error}`));
  if(envelope.state!=='RESULT_QUARANTINED') errors.push('harvest requires RESULT_QUARANTINED envelope');
  if (value.experimentId !== envelope.experimentId || value.resultHash !== envelope.resultHash) errors.push('harvest does not match experiment result');
  if (!['artifact', 'test', 'jar', 'skill'].includes(value.targetKind) || value.targetKind !== envelope.harvestTarget.kind || value.localArtifactRef !== envelope.harvestTarget.ref) errors.push('harvest target mismatch');
  if (value.testsPassed !== true || value.availableForUse !== true) errors.push('harvest requires verified local tests before use');
  if (typeof options.resolveArtifact !== 'function') errors.push('trusted local artifact resolver is required');
  else {
    const resolved = options.resolveArtifact(value.localArtifactRef);
    if (!isRecord(resolved) || resolved.sha256 !== value.localArtifactHash || resolved.verifierId !== value.verifierId) errors.push('trusted local artifact resolution failed');
  }
  if (errors.length === 0) {
    const payload = { ...value };
    delete payload.harvestHash;
    if (sha256(payload) !== value.harvestHash) errors.push('harvest.harvestHash mismatch');
  }
  return { ok: errors.length === 0, errors };
}

function validateAdditionalQuotesToken(value) {
  const expected = { exactToken: 'additional quotes', state: 'UNRESOLVED_SUGGESTED_CORRECTION', suggestedCorrection: 'additional quotas', correctionApplied: false };
  return { ok: isRecord(value) && canonicalJson(value) === canonicalJson(expected), errors: isRecord(value) && canonicalJson(value) === canonicalJson(expected) ? [] : ['`additional quotes` must remain exact and unresolved; suggested correction may not be applied'] };
}

function validateCodexAppServerCompanion(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['Codex app-server companion must be a plain object'] };
  if (value.kind !== 'CODEX_APP_SERVER_COMPANION' || value.mode !== 'DESCRIPTOR_ONLY') errors.push('companion must be a descriptor-only Codex app-server companion');
  if (value.scope !== 'CODEX_ONLY' || value.wiringState !== 'NOT_WIRED' || value.setupState !== 'HUMAN_SETUP_REQUIRED') errors.push('companion remains CODEX_ONLY, NOT_WIRED, HUMAN_SETUP_REQUIRED');
  if (value.transport !== 'JSON_RPC_THREADS_TURNS_EVENTS' || value.authentication !== 'CHATGPT_MANAGED_OAUTH_OR_DEVICE_CODE') errors.push('companion transport/authentication contract mismatch');
  if (value.humanSetupGate !== 'REQUIRED' || value.uiTypingAllowed !== false || value.apiKeyRequired !== false) errors.push('companion requires human setup and forbids UI typing/API-key assumptions');
  if (value.generalChatgptResponseTransport !== false || value.homeCenterExecutorAvailable !== false || value.includedQuotaCandidate !== true) errors.push('companion must not claim General ChatGPT or Home Center executor transport');
  if (value.primaryStateOwner !== false || value.coreDependency !== false) errors.push('companion cannot own state or become a core dependency');
  if(value.loopbackOnly!==true||value.outboundCompanionOnly!==true||value.noTokenEgress!==true||value.exactThreadSessionResume!==true||value.unlimitedClaim!==false||value.quotaBypass!==false) errors.push('companion loopback/resume/no-egress/no-bypass law mismatch');
  if(value.humanLoginStatus!=='UNVERIFIED'||value.humanLoginEvidence!==null||value.apiKeyEnvironmentStatus!=='UNVERIFIED_ABSENT'||value.apiKeyAbsenceEvidence!==null||value.planQuotaState!=='UNVERIFIED') errors.push('companion cannot claim unprobed login/key/quota evidence');
  return { ok: errors.length === 0, errors };
}

module.exports = { EXPERIMENT_PROVIDERS, EXPERIMENT_STATES, experimentDigestPayload, validateExperimentEnvelope, validateExperimentHarvest, validateAdditionalQuotesToken, validateCodexAppServerCompanion };

