'use strict';

const {
  isRecord,
  requireText,
  requireSha,
  requireRfc3339,
  requireStringArray,
  canonicalJson,
  sha256
} = require('./contracts');

const MOBILE_SCHEMAS = Object.freeze({ command: 'venice.command.v1', dispatch: 'venice.dispatch.v1', receipt: 'venice.receipt_projection.v1', deviceStatus: 'DEVICE_TTS_STATUS.v1' });
const ROUTE_CLASSES = Object.freeze(['REFLEX', 'COGNITION']);
const MOBILE_STATES = Object.freeze(['ONLINE', 'OFFLINE_QUEUED', 'WAITING_COGNITION_QUOTA', 'DISPATCHED', 'RECEIPT_READY', 'SUPERSEDED', 'EXPIRED']);
const REFLEX_ACTIONS = Object.freeze(['DEVICE_TTS_STATUS@1', 'STATUS_TEXT@1', 'MUTE_AUDIO@1', 'CANCEL_EXACT_LEASE@1']);
const LOCAL_CODING_SPINE = Object.freeze(['continue', 'qwen', 'ollama']);

function validateDeviceIdentity(value, path, errors) {
  if (!isRecord(value)) return errors.push(`${path} must be a plain object`);
  for (const key of ['deviceId', 'appId', 'buildId', 'accountId']) requireText(value[key], `${path}.${key}`, errors);
}

function validateMobileSession(value, path, errors) {
  if (!isRecord(value)) return errors.push(`${path} must be a plain object`);
  for (const key of ['mobileSessionId', 'conversationId', 'turnId']) requireText(value[key], `${path}.${key}`, errors);
}

function validateTranscript(value, path, errors) {
  if (!isRecord(value)) return errors.push(`${path} must be a plain object`);
  requireText(value.text, `${path}.text`, errors);
  requireSha(value.textHash, `${path}.textHash`, errors);
  if (typeof value.text === 'string' && sha256(value.text) !== value.textHash) errors.push(`${path}.textHash does not match exact UTF-8 text`);
}

function commandDigestPayload(value) {
  const payload = { ...value };
  delete payload.commandHash;
  return payload;
}

function commandEventPayload(value) {
  return { streamId: value.streamId, eventSequence: value.eventSequence, previousEventHash: value.previousEventHash, commandId: value.commandId, idempotencyKey: value.idempotencyKey, transcriptHash: value.transcript?.textHash, createdAt: value.createdAt, expiresAt: value.expiresAt };
}

function validateVeniceCommand(value, options = {}) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['Venice command must be a plain object'] };
  if (value.schema !== MOBILE_SCHEMAS.command) errors.push(`command.schema must be ${MOBILE_SCHEMAS.command}`);
  for (const key of ['commandId', 'commissionId', 'commissionHash', 'queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner', 'laneId', 'laneOwner', 'requestedAction', 'idempotencyKey', 'streamId']) requireText(value[key], `command.${key}`, errors);
  requireSha(value.commissionHash, 'command.commissionHash', errors);
  validateDeviceIdentity(value.device, 'command.device', errors);
  validateMobileSession(value.session, 'command.session', errors);
  validateTranscript(value.transcript, 'command.transcript', errors);
  if (!ROUTE_CLASSES.includes(value.routeClass)) errors.push('command.routeClass must be REFLEX or COGNITION');
  if (!isRecord(value.routeDecision)) errors.push('command.routeDecision is required');
  else {
    errors.push(...validateRouteDecision(value.routeDecision).errors.map(error => `command ${error}`));
    if (value.routeDecision.routeClass !== value.routeClass || value.routeDecision.actionVersion !== value.actionVersion) errors.push('command route decision/action mismatch');
  }
  requireText(value.actionVersion, 'command.actionVersion', errors);
  if (!MOBILE_STATES.includes(value.state)) errors.push('command.state is unsupported');
  if (!Number.isSafeInteger(value.eventSequence) || value.eventSequence < 1) errors.push('command.eventSequence must be a positive safe integer');
  if (value.eventSequence === 1) {
    if (value.previousEventHash !== null) errors.push('first command previousEventHash must be null');
  } else requireSha(value.previousEventHash, 'command.previousEventHash', errors);
  requireSha(value.eventHash, 'command.eventHash', errors);
  requireSha(value.commandHash, 'command.commandHash', errors);
  requireRfc3339(value.createdAt, 'command.createdAt', errors);
  requireRfc3339(value.expiresAt, 'command.expiresAt', errors);
  if (value.inputMode !== 'VOICE_OR_NATIVE_COMMAND' || value.uiTypingAllowed !== false) errors.push('Venice mobile commands must affirmatively forbid UI typing');
  if (value.offlineQueued !== (value.state === 'OFFLINE_QUEUED')) errors.push('command.offlineQueued must match OFFLINE_QUEUED state');
  if (value.offlineQueued === true) {
    requireRfc3339(value.offlineEnqueuedAt, 'command.offlineEnqueuedAt', errors);
    if (value.durableIdempotency !== true) errors.push('offline command requires durableIdempotency=true');
  }
  requireRfc3339(options.now, 'options.now', errors);
  if (!isMobileRegistry(options.registry)) errors.push('trusted command replay registry is required');
  if (errors.length === 0) {
    if (Date.parse(value.expiresAt) <= Date.parse(value.createdAt)) errors.push('command.expiresAt must be later than createdAt');
    if (Date.parse(options.now) >= Date.parse(value.expiresAt) && value.state !== 'EXPIRED') errors.push('command is expired');
    if (options.registry.consumedCommandIds.includes(value.commandId) || options.registry.consumedIdempotencyKeys.includes(value.idempotencyKey)) errors.push('command replay detected');
    const trustedHead = options.registry.streamHeads[value.streamId] ?? null;
    if (value.previousEventHash !== trustedHead) errors.push('command does not append to trusted stream head');
    if (sha256(commandEventPayload(value)) !== value.eventHash) errors.push('command.eventHash mismatch');
    if (sha256(commandDigestPayload(value)) !== value.commandHash) errors.push('command.commandHash mismatch');
    errors.push(...validateMobileConsumptionCas(options.consumptionCas, options.registry, value).errors);
  }
  return { ok: errors.length === 0, errors };
}

function dispatchDigestPayload(value) {
  const payload = { ...value };
  delete payload.dispatchHash;
  return payload;
}

function dispatchEventPayload(value){return {streamId:value.streamId,eventSequence:value.eventSequence,previousEventHash:value.previousEventHash,dispatchId:value.dispatchId,commandHash:value.commandHash,idempotencyKey:value.idempotencyKey,createdAt:value.createdAt,expiresAt:value.expiresAt};}

function validateVeniceDispatch(value, command, options = {}) {
  const errors = [];
  if (!isRecord(value) || !isRecord(command)) return { ok: false, errors: ['dispatch and command must be plain objects'] };
  const upstream = validateVeniceCommand(command, options.commandValidationOptions || {});
  errors.push(...upstream.errors.map(error => `dispatch upstream ${error}`));
  const consumedCommand = typeof options.resolveConsumedCommand === 'function' ? options.resolveConsumedCommand(command.commandHash) : null;
  if (!isRecord(consumedCommand) || canonicalJson(consumedCommand.command) !== canonicalJson(command) || consumedCommand.receiptHash !== value.commandConsumptionReceiptHash || consumedCommand.state !== 'CONSUMED' || consumedCommand.commandHash !== command.commandHash) errors.push('dispatch requires exact trusted consumed command');
  if (value.schema !== MOBILE_SCHEMAS.dispatch) errors.push(`dispatch.schema must be ${MOBILE_SCHEMAS.dispatch}`);
  for (const key of ['dispatchId', 'commandId', 'commandHash','commandConsumptionReceiptHash', 'commissionId', 'commissionHash', 'queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner', 'laneId', 'laneOwner', 'idempotencyKey', 'requestedAction', 'executorKind', 'executorId', 'executorModel','streamId']) requireText(value[key], `dispatch.${key}`, errors);
  requireSha(value.commandHash, 'dispatch.commandHash', errors);
  requireSha(value.commandConsumptionReceiptHash,'dispatch.commandConsumptionReceiptHash',errors);
  requireSha(value.commissionHash, 'dispatch.commissionHash', errors);
  requireSha(value.dispatchHash, 'dispatch.dispatchHash', errors);
  requireSha(value.eventHash,'dispatch.eventHash',errors);if(!Number.isSafeInteger(value.eventSequence)||value.eventSequence<1)errors.push('dispatch.eventSequence must be positive');if(value.eventSequence===1){if(value.previousEventHash!==null)errors.push('first dispatch previousEventHash must be null');}else requireSha(value.previousEventHash,'dispatch.previousEventHash',errors);
  validateDeviceIdentity(value.device, 'dispatch.device', errors);
  validateMobileSession(value.session, 'dispatch.session', errors);
  requireRfc3339(value.createdAt, 'dispatch.createdAt', errors);
  requireRfc3339(value.expiresAt, 'dispatch.expiresAt', errors);
  if (value.uiTypingAllowed !== false || value.executorAttributionRequired !== true) errors.push('dispatch must forbid UI typing and require executor attribution');
  if (command.state !== 'ONLINE') errors.push('offline/quota-waiting commands cannot dispatch');
  for (const key of ['commandId', 'commandHash', 'commissionId', 'commissionHash', 'queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner', 'laneId', 'laneOwner', 'idempotencyKey', 'requestedAction']) if (value[key] !== (key === 'commandHash' ? command.commandHash : command[key])) errors.push(`dispatch.${key} does not match command`);
  if (canonicalJson(value.device) !== canonicalJson(command.device) || canonicalJson(value.session) !== canonicalJson(command.session)) errors.push('dispatch mobile identity mismatch');
  if (value.routeClass !== command.routeClass) errors.push('dispatch.routeClass mismatch');
  const route = { decisionId: value.dispatchId, routeClass: value.routeClass, actionVersion: value.actionVersion, executorKind: value.executorKind, executorId: value.executorId, executorModel: value.executorModel, deterministic: value.deterministic, semanticAuthorship: value.semanticAuthorship, personaAuthorship: value.personaAuthorship, cognitionAuthor: value.cognitionAuthor, orchestrator: value.orchestrator, state: command.state };
  errors.push(...validateRouteDecision(route).errors.map(error => `dispatch ${error}`));
  if (value.actionVersion !== command.actionVersion) errors.push('dispatch.actionVersion mismatch');
  requireRfc3339(options.now,'dispatch options.now',errors);if(!isDispatchRegistry(options.registry))errors.push('trusted dispatch registry required');
  if (errors.length === 0) {if(Date.parse(options.now)>=Date.parse(value.expiresAt))errors.push('dispatch expired');if(options.registry.dispatchIds.includes(value.dispatchId)||options.registry.consumedIdempotencyKeys.includes(value.idempotencyKey))errors.push('dispatch replay');if(value.previousEventHash!==(options.registry.streamHeads[value.streamId]??null))errors.push('dispatch stream head mismatch');if(sha256(dispatchEventPayload(value))!==value.eventHash)errors.push('dispatch.eventHash mismatch');if (sha256(dispatchDigestPayload(value)) !== value.dispatchHash) errors.push('dispatch.dispatchHash mismatch');errors.push(...validateDispatchConsumptionCas(options.consumptionCas,options.registry,value).errors);}
  return { ok: errors.length === 0, errors };
}

function receiptDigestPayload(value) {
  const payload = { ...value };
  delete payload.receiptHash;
  return payload;
}

function receiptEventPayload(value) {
  return { streamId: value.streamId, eventSequence: value.eventSequence, previousEventHash: value.previousEventHash, receiptId: value.receiptId, dispatchHash: value.dispatchHash, sourceReceiptHash: value.sourceReceiptHash, resultHash: value.resultHash, createdAt: value.createdAt, expiresAt: value.expiresAt };
}

function validateVeniceReceiptProjection(value, dispatch, options = {}) {
  const errors = [];
  if (!isRecord(value) || !isRecord(dispatch)) return { ok: false, errors: ['receipt projection and dispatch must be plain objects'] };
  const upstream = validateVeniceDispatch(dispatch, options.command, options.dispatchValidationOptions || {});
  errors.push(...upstream.errors.map(error => `receipt upstream ${error}`));
  const consumedDispatch = typeof options.resolveConsumedDispatch === 'function' ? options.resolveConsumedDispatch(dispatch.dispatchHash) : null;
  if (!isRecord(consumedDispatch) || canonicalJson(consumedDispatch.dispatch) !== canonicalJson(dispatch) || consumedDispatch.receiptHash !== value.dispatchConsumptionReceiptHash || consumedDispatch.state !== 'CONSUMED' || consumedDispatch.dispatchHash !== dispatch.dispatchHash) errors.push('receipt requires exact trusted consumed dispatch');
  if (value.schema !== MOBILE_SCHEMAS.receipt) errors.push(`receipt.schema must be ${MOBILE_SCHEMAS.receipt}`);
  for (const key of ['receiptId', 'dispatchId', 'dispatchHash','dispatchConsumptionReceiptHash', 'commandId', 'commissionId', 'commissionHash', 'queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner', 'laneId', 'laneOwner', 'idempotencyKey','projectionIdempotencyKey', 'executorKind', 'executorId', 'executorModel', 'sourceReceiptHash', 'resultState', 'streamId']) requireText(value[key], `receipt.${key}`, errors);
  for (const key of ['dispatchHash','dispatchConsumptionReceiptHash', 'commissionHash', 'sourceReceiptHash', 'resultHash', 'eventHash', 'receiptHash']) requireSha(value[key], `receipt.${key}`, errors);
  validateDeviceIdentity(value.device, 'receipt.device', errors);
  validateMobileSession(value.session, 'receipt.session', errors);
  validateTranscript(value.transcript, 'receipt.transcript', errors);
  if (!Number.isSafeInteger(value.eventSequence) || value.eventSequence < 1) errors.push('receipt.eventSequence must be positive');
  if (value.eventSequence === 1) {
    if (value.previousEventHash !== null) errors.push('first receipt previousEventHash must be null');
  } else requireSha(value.previousEventHash, 'receipt.previousEventHash', errors);
  requireRfc3339(value.createdAt, 'receipt.createdAt', errors);
  requireRfc3339(value.expiresAt, 'receipt.expiresAt', errors);
  if (value.uiTypingUsed !== false || value.textMirrorRequired !== true) errors.push('receipt must prove no UI typing and require a text mirror');
  for (const key of ['dispatchId', 'dispatchHash', 'commandId', 'commissionId', 'commissionHash', 'queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner', 'laneId', 'laneOwner', 'idempotencyKey', 'executorKind', 'executorId', 'executorModel']) if (value[key] !== dispatch[key]) errors.push(`receipt.${key} does not match dispatch`);
  if (canonicalJson(value.device) !== canonicalJson(dispatch.device) || canonicalJson(value.session) !== canonicalJson(dispatch.session)) errors.push('receipt mobile identity mismatch');
  if (typeof options.resolveSourceReceipt !== 'function') errors.push('trusted source receipt resolver is required');
  else {
    const source = options.resolveSourceReceipt(value.sourceReceiptHash);
    const exact = ['sourceReceiptHash','resultHash','resultState','correction','supersedesReceiptId','supersedesReceiptHash','executorKind','executorId','executorModel','commandId','dispatchId','dispatchHash','commissionId','commissionHash','queueDocumentId','queueFolderId','queueRevision','stateOwner','laneId','laneOwner','idempotencyKey','projectionIdempotencyKey'];
    if (!isRecord(source) || exact.some(key => source[key] !== value[key]) || source.text !== value.transcript?.text || canonicalJson(source.device) !== canonicalJson(value.device) || canonicalJson(source.session) !== canonicalJson(value.session) || source.terminal !== true) errors.push('trusted terminal source receipt mismatch');
  }
  requireRfc3339(options.now, 'receipt options.now', errors);
  if (!isReceiptRegistry(options.registry)) errors.push('trusted receipt replay registry is required');
  if (value.correction === true) { requireText(value.supersedesReceiptId, 'receipt.supersedesReceiptId', errors); requireSha(value.supersedesReceiptHash,'receipt.supersedesReceiptHash',errors); const prior=typeof options.resolveSupersededReceipt==='function'?options.resolveSupersededReceipt(value.supersedesReceiptId):null; const scope=['commissionHash','queueRevision','laneId','streamId'];if(!isRecord(prior)||prior.receiptId!==value.supersedesReceiptId||prior.receiptHash!==value.supersedesReceiptHash||scope.some(k=>prior[k]!==value[k])||canonicalJson(prior.device)!==canonicalJson(value.device)||canonicalJson(prior.session)!==canonicalJson(value.session)||prior.supersededBy!==null)errors.push('correction requires trusted same-scope unsuperseded receipt'); }
  else if (value.supersedesReceiptId !== null||value.supersedesReceiptHash!==null) errors.push('non-correction receipt supersedes fields must be null');
  if (errors.length === 0) {
    if (Date.parse(options.now) >= Date.parse(value.expiresAt)) errors.push('receipt projection expired');
    if (options.registry.receiptIds.includes(value.receiptId) || options.registry.consumedIdempotencyKeys.includes(value.projectionIdempotencyKey)) errors.push('receipt replay detected');
    if (value.previousEventHash !== (options.registry.streamHeads[value.streamId] ?? null)) errors.push('receipt does not append to trusted stream head');
    if (sha256(receiptEventPayload(value)) !== value.eventHash) errors.push('receipt.eventHash mismatch');
    if (sha256(receiptDigestPayload(value)) !== value.receiptHash) errors.push('receipt.receiptHash mismatch');
    errors.push(...validateReceiptConsumptionCas(options.consumptionCas, options.registry, value).errors);
  }
  return { ok: errors.length === 0, errors };
}

function createMobileConsumptionCas(registry, command) {
  const value = { registryId: registry.registryId, expectedRevision: registry.revision, nextRevision: registry.revision + 1, commandId: command.commandId, commandHash: command.commandHash, streamId: command.streamId, previousEventHash: command.previousEventHash, nextEventHash: command.eventHash, idempotencyKey: command.idempotencyKey };
  value.casHash = sha256(value);
  return value;
}

function validateMobileConsumptionCas(value, registry, command) {
  const errors = [];
  if (!isMobileRegistry(registry) || !isRecord(value)) return { ok: false, errors: ['mobile command consumption CAS and trusted registry are required'] };
  if (value.registryId !== registry.registryId || value.expectedRevision !== registry.revision || value.nextRevision !== registry.revision + 1) errors.push('mobile CAS registry mismatch');
  if (value.commandId !== command.commandId || value.commandHash !== command.commandHash || value.streamId!==command.streamId || value.previousEventHash!==command.previousEventHash || value.nextEventHash!==command.eventHash || value.idempotencyKey !== command.idempotencyKey) errors.push('mobile CAS command identity mismatch');
  const payload = { ...value }; delete payload.casHash;
  if (!/^[a-f0-9]{64}$/.test(value.casHash || '') || sha256(payload) !== value.casHash) errors.push('mobile CAS hash mismatch');
  return { ok: errors.length === 0, errors };
}

function isMobileRegistry(value) {
  return isRecord(value) && typeof value.registryId === 'string' && Number.isSafeInteger(value.revision) && Array.isArray(value.consumedCommandIds) && Array.isArray(value.consumedIdempotencyKeys) && isRecord(value.streamHeads);
}

function isReceiptRegistry(value) { return isRecord(value) && typeof value.registryId === 'string' && Number.isSafeInteger(value.revision) && Array.isArray(value.receiptIds) && Array.isArray(value.consumedIdempotencyKeys) && isRecord(value.streamHeads); }
function isDispatchRegistry(value){return isRecord(value)&&typeof value.registryId==='string'&&Number.isSafeInteger(value.revision)&&Array.isArray(value.dispatchIds)&&Array.isArray(value.consumedIdempotencyKeys)&&isRecord(value.streamHeads);}
function createDispatchConsumptionCas(registry,dispatch){const value={registryId:registry.registryId,expectedRevision:registry.revision,nextRevision:registry.revision+1,dispatchId:dispatch.dispatchId,dispatchHash:dispatch.dispatchHash,previousEventHash:dispatch.previousEventHash,nextEventHash:dispatch.eventHash,idempotencyKey:dispatch.idempotencyKey};value.casHash=sha256(value);return value;}
function validateDispatchConsumptionCas(value,registry,dispatch){const errors=[];if(!isDispatchRegistry(registry)||!isRecord(value))return {ok:false,errors:['dispatch CAS/registry required']};if(value.registryId!==registry.registryId||value.expectedRevision!==registry.revision||value.nextRevision!==registry.revision+1||value.dispatchId!==dispatch.dispatchId||value.dispatchHash!==dispatch.dispatchHash||value.previousEventHash!==dispatch.previousEventHash||value.nextEventHash!==dispatch.eventHash||value.idempotencyKey!==dispatch.idempotencyKey)errors.push('dispatch CAS identity mismatch');const p={...value};delete p.casHash;if(!/^[a-f0-9]{64}$/.test(value.casHash||'')||sha256(p)!==value.casHash)errors.push('dispatch CAS hash mismatch');return {ok:errors.length===0,errors};}
function createReceiptConsumptionCas(registry, receipt) { const value = { registryId: registry.registryId, expectedRevision: registry.revision, nextRevision: registry.revision + 1, receiptId: receipt.receiptId, receiptHash: receipt.receiptHash, previousEventHash: receipt.previousEventHash, nextEventHash: receipt.eventHash,supersedesReceiptId:receipt.supersedesReceiptId,supersedesReceiptHash:receipt.supersedesReceiptHash, idempotencyKey: receipt.projectionIdempotencyKey }; value.casHash = sha256(value); return value; }
function validateReceiptConsumptionCas(value, registry, receipt) { const errors=[]; if (!isReceiptRegistry(registry)||!isRecord(value)) return {ok:false,errors:['receipt consumption CAS and registry required']}; if(value.registryId!==registry.registryId||value.expectedRevision!==registry.revision||value.nextRevision!==registry.revision+1||value.receiptId!==receipt.receiptId||value.receiptHash!==receipt.receiptHash||value.previousEventHash!==receipt.previousEventHash||value.nextEventHash!==receipt.eventHash||value.supersedesReceiptId!==receipt.supersedesReceiptId||value.supersedesReceiptHash!==receipt.supersedesReceiptHash||value.idempotencyKey!==receipt.projectionIdempotencyKey) errors.push('receipt CAS identity mismatch'); const p={...value};delete p.casHash;if(!/^[a-f0-9]{64}$/.test(value.casHash||'')||sha256(p)!==value.casHash)errors.push('receipt CAS hash mismatch');return {ok:errors.length===0,errors}; }

function validateRouteDecision(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['route decision must be a plain object'] };
  for (const key of ['decisionId', 'routeClass', 'actionVersion', 'executorKind', 'executorId', 'executorModel']) requireText(value[key], `route.${key}`, errors);
  if (!ROUTE_CLASSES.includes(value.routeClass)) errors.push('route.routeClass is unsupported');
  if (value.routeClass === 'REFLEX') {
    if (!REFLEX_ACTIONS.includes(value.actionVersion)) errors.push('REFLEX action/version is not allowlisted');
    if (value.deterministic !== true || value.semanticAuthorship !== false || value.personaAuthorship !== false) errors.push('REFLEX must be deterministic and non-cognitive');
    if (value.executorKind !== 'LOCAL_DETERMINISTIC') errors.push('REFLEX must use LOCAL_DETERMINISTIC executor');
  }
  if (value.routeClass === 'COGNITION') {
    if (value.executorKind !== 'CHATGPT' || value.cognitionAuthor !== 'Venice' || value.orchestrator !== 'ChatGPT') errors.push('COGNITION must route to ChatGPT as Venice cognition/orchestration');
    if (LOCAL_CODING_SPINE.includes(value.executorId) || ['LOCAL_JAR', 'LOCAL_SCRIPT', 'QWEN'].includes(value.executorKind)) errors.push('local jars/scripts/Qwen cannot author Venice cognition');
    if (!['ONLINE', 'WAITING_COGNITION_QUOTA', 'OFFLINE_QUEUED'].includes(value.state)) errors.push('COGNITION state must express online, quota wait, or durable offline queue');
  }
  return { ok: errors.length === 0, errors };
}

function validateDeviceTtsStatus(value, options = {}) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['DEVICE_TTS_STATUS must be a plain object'] };
  if (value.schema !== MOBILE_SCHEMAS.deviceStatus || value.routeClass !== 'REFLEX' || value.actionVersion !== 'DEVICE_TTS_STATUS@1') errors.push('DEVICE_TTS_STATUS must be the deterministic v1 reflex');
  for (const key of ['projectionId', 'sourceReceiptHash','sourceResultHash','commissionId','queueDocumentId','queueFolderId','queueRevision','stateOwner','laneId','dispatchId', 'cacheKey', 'statusCode', 'executorId', 'idempotencyKey', 'streamId']) requireText(value[key], `deviceTts.${key}`, errors);
  for (const key of ['sourceReceiptHash','sourceResultHash','commissionHash', 'cacheKey', 'resultHash', 'eventHash']) requireSha(value[key], `deviceTts.${key}`, errors);
  validateDeviceIdentity(value.device, 'deviceTts.device', errors); validateMobileSession(value.session, 'deviceTts.session', errors);
  validateTranscript(value.transcript, 'deviceTts.transcript', errors);
  if (!Number.isSafeInteger(value.eventSequence) || value.eventSequence < 1) errors.push('deviceTts.eventSequence must be positive');
  if(value.eventSequence===1){if(value.previousEventHash!==null)errors.push('first DEVICE_TTS_STATUS previousEventHash must be null');}else requireSha(value.previousEventHash,'deviceTts.previousEventHash',errors);
  requireRfc3339(value.createdAt, 'deviceTts.createdAt', errors);
  requireRfc3339(value.expiresAt, 'deviceTts.expiresAt', errors);
  if (value.cacheFirst !== true || value.nonblocking !== true || value.textMirrored !== true || value.deterministic !== true) errors.push('DEVICE_TTS_STATUS must be cache-first, nonblocking, text-mirrored, and deterministic');
  if (value.semanticAuthorship !== false || value.personaAuthorship !== false || value.cognition !== false || value.claimedSuccess !== false) errors.push('DEVICE_TTS_STATUS cannot author persona/cognition or invent success');
  if (value.supersedes !== null) {requireText(value.supersedes, 'deviceTts.supersedes', errors);requireSha(value.supersedesHash,'deviceTts.supersedesHash',errors);} else if(value.supersedesHash!==null)errors.push('DEVICE_TTS_STATUS supersedesHash must be null without supersedes');
  if (value.cacheHit !== true && value.cueSkipped !== true) errors.push('cache miss must skip status audio rather than block');
  requireRfc3339(options.now, 'options.now', errors);
  if (typeof options.resolveSourceReceipt !== 'function') errors.push('DEVICE_TTS_STATUS requires trusted source receipt');
  const source = typeof options.resolveSourceReceipt === 'function' ? options.resolveSourceReceipt(value.sourceReceiptHash) : null;
  const sourceScope=['sourceReceiptHash','sourceResultHash','commissionId','commissionHash','queueDocumentId','queueFolderId','queueRevision','stateOwner','laneId','dispatchId'];
  if (!isRecord(source) || sourceScope.some(k=>source[k]!==value[k]) || canonicalJson(source.device)!==canonicalJson(value.device) || canonicalJson(source.session)!==canonicalJson(value.session) || source.terminal !== true || source.statusCode !== value.statusCode || source.text!==value.transcript?.text) errors.push('DEVICE_TTS_STATUS full-scope source receipt mismatch');
  if (!isRecord(options.registry) || typeof options.registry.registryId!=='string' || !Number.isSafeInteger(options.registry.revision) || !isRecord(options.registry.streamHeads) || !Array.isArray(options.registry.projectionIds) || !Array.isArray(options.registry.consumedIdempotencyKeys)) errors.push('DEVICE_TTS_STATUS persistent registry required');
  if (errors.length === 0) {
    if (Date.parse(options.now) >= Date.parse(value.expiresAt)) errors.push('DEVICE_TTS_STATUS projection expired');
    if (value.previousEventHash !== (options.registry.streamHeads[value.streamId] ?? null)) errors.push('DEVICE_TTS_STATUS stream head mismatch');
    if (options.registry.projectionIds.includes(value.projectionId) || options.registry.consumedIdempotencyKeys.includes(value.idempotencyKey)) errors.push('DEVICE_TTS_STATUS replay');
    if(value.supersedes!==null){const prior=typeof options.resolveSupersededProjection==='function'?options.resolveSupersededProjection(value.supersedes):null;const scope=['commissionHash','queueRevision','laneId','streamId'];if(!isRecord(prior)||prior.projectionId!==value.supersedes||prior.eventHash!==value.supersedesHash||scope.some(k=>prior[k]!==value[k])||canonicalJson(prior.device)!==canonicalJson(value.device)||canonicalJson(prior.session)!==canonicalJson(value.session)||prior.supersededBy!==null)errors.push('DEVICE_TTS_STATUS supersession scope mismatch');}
    const deterministic = { sourceReceiptHash:value.sourceReceiptHash,sourceResultHash:value.sourceResultHash,commissionHash:value.commissionHash,queueRevision:value.queueRevision,laneId:value.laneId,dispatchId:value.dispatchId,statusCode:value.statusCode,text:value.transcript.text,cacheKey:value.cacheKey,cacheHit:value.cacheHit,cueSkipped:value.cueSkipped };
    if (sha256(deterministic)!==value.resultHash) errors.push('DEVICE_TTS_STATUS resultHash mismatch');
    const eventPayload={streamId:value.streamId,eventSequence:value.eventSequence,previousEventHash:value.previousEventHash,projectionId:value.projectionId,resultHash:value.resultHash,idempotencyKey:value.idempotencyKey,createdAt:value.createdAt,expiresAt:value.expiresAt,supersedes:value.supersedes,supersedesHash:value.supersedesHash};
    if(sha256(eventPayload)!==value.eventHash) errors.push('DEVICE_TTS_STATUS eventHash mismatch');
    const cas=options.consumptionCas;const p=isRecord(cas)?{...cas}:{};delete p.casHash;if(!isRecord(cas)||cas.registryId!==options.registry.registryId||cas.expectedRevision!==options.registry.revision||cas.nextRevision!==options.registry.revision+1||cas.projectionId!==value.projectionId||cas.resultHash!==value.resultHash||cas.previousEventHash!==value.previousEventHash||cas.nextEventHash!==value.eventHash||cas.supersedes!==value.supersedes||cas.supersedesHash!==value.supersedesHash||cas.idempotencyKey!==value.idempotencyKey||sha256(p)!==cas.casHash) errors.push('DEVICE_TTS_STATUS persistent CAS mismatch');
  }
  return { ok: errors.length === 0, errors };
}

function validateCodingSpine(value) {
  const errors = [];
  if (!isRecord(value)) return { ok: false, errors: ['coding spine must be a plain object'] };
  if (value.kind !== 'OMNI_CODING_SPINE' || value.primaryCognition !== 'ChatGPT') errors.push('Omni coding keeps ChatGPT as primary cognition');
  requireStringArray(value.offlineRuntimes, 'codingSpine.offlineRuntimes', errors, { nonEmpty: true });
  if (Array.isArray(value.offlineRuntimes) && canonicalJson([...value.offlineRuntimes].sort()) !== canonicalJson([...LOCAL_CODING_SPINE].sort())) errors.push('offline coding spine must be exactly Continue/Qwen/Ollama');
  if (value.localMayAuthorVeniceCognition !== false || value.providerAbsenceStopsCore !== false) errors.push('local coding cannot author Venice cognition and provider absence cannot stop core');
  return { ok: errors.length === 0, errors };
}

module.exports = {
  MOBILE_SCHEMAS,
  ROUTE_CLASSES,
  MOBILE_STATES,
  REFLEX_ACTIONS,
  LOCAL_CODING_SPINE,
  commandDigestPayload,
  commandEventPayload,
  dispatchDigestPayload,
  dispatchEventPayload,
  receiptDigestPayload,
  receiptEventPayload,
  createMobileConsumptionCas,
  validateMobileConsumptionCas,
  createDispatchConsumptionCas,
  createReceiptConsumptionCas,
  validateReceiptConsumptionCas,
  validateVeniceCommand,
  validateVeniceDispatch,
  validateVeniceReceiptProjection,
  validateRouteDecision,
  validateDeviceTtsStatus,
  validateCodingSpine
};

