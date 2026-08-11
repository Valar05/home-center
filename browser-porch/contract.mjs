import {createHash, timingSafeEqual} from 'node:crypto';

export const CONTRACT_VERSION = 'home-center.browser-porch.v1';
export const CHATGPT_ORIGIN = 'https://chatgpt.com';
export const OBSERVE_ACTIONS = Object.freeze(['inventory']);
export const MUTATION_ACTIONS = Object.freeze(['project.create', 'conversation.move']);
const ID = /^[A-Za-z0-9_.:-]{6,180}$/;

export function sha256(value) {
  return createHash('sha256').update(String(value), 'utf8').digest('hex');
}

export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

function fail(code, message) {
  const error = new Error(message);
  error.code = code;
  throw error;
}

function id(value, label) {
  const text = String(value || '');
  if (!ID.test(text)) fail('INVALID_BINDING', `${label} is invalid`);
  return text;
}

function hex(value, label) {
  const text = String(value || '').toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(text)) fail('INVALID_BINDING', `${label} must be a SHA-256 digest`);
  return text;
}

function exactOrigin(url) {
  try { return new URL(url).origin; } catch { return ''; }
}

export function validatePairIntent(input, nowMs = Date.now()) {
  const intent = {
    contractVersion: input?.contractVersion,
    pairingId: id(input?.pairingId, 'pairingId'),
    sessionId: id(input?.sessionId, 'sessionId'),
    workerId: id(input?.workerId, 'workerId'),
    commissionId: id(input?.commissionId, 'commissionId'),
    expectedOrigin: String(input?.expectedOrigin || ''),
    expectedAccountHash: hex(input?.expectedAccountHash, 'expectedAccountHash'),
    nonce: id(input?.nonce, 'nonce'),
    issuedAtMs: Number(input?.issuedAtMs),
    expiresAtMs: Number(input?.expiresAtMs),
    mode: String(input?.mode || ''),
  };
  if (intent.contractVersion !== CONTRACT_VERSION) fail('CONTRACT_MISMATCH', 'contract version mismatch');
  if (intent.expectedOrigin !== CHATGPT_ORIGIN) fail('ORIGIN_MISMATCH', 'only the exact ChatGPT origin may be paired');
  if (intent.mode !== 'observe') fail('MUTATION_NOT_APPROVED', 'pairing starts observe-only');
  if (!Number.isSafeInteger(intent.issuedAtMs) || !Number.isSafeInteger(intent.expiresAtMs)) fail('INVALID_TIME', 'intent timestamps are required');
  if (intent.issuedAtMs > nowMs + 5_000 || intent.expiresAtMs <= nowMs || intent.expiresAtMs - intent.issuedAtMs > 60_000) fail('STALE_PAIRING', 'pair intent is stale or exceeds one minute');
  return Object.freeze(intent);
}

export function createPairReceipt(intentInput, observation, state, nowMs = Date.now()) {
  const intent = validatePairIntent(intentInput, nowMs);
  if (state.usedNonces.has(intent.nonce) || state.receipts.has(intent.pairingId)) fail('PAIRING_REPLAY', 'pair intent was already consumed');
  if (observation?.gesture !== 'extension_action_click') fail('USER_GESTURE_REQUIRED', 'pairing requires the extension action click');
  if (!Number.isSafeInteger(observation?.tabId)) fail('TAB_MISMATCH', 'numeric active tabId is required');
  if (exactOrigin(observation?.url) !== intent.expectedOrigin) fail('ORIGIN_MISMATCH', 'active tab origin differs from intent');
  if (observation?.authenticationState !== 'dom_verified') fail('AUTHENTICATION_UNVERIFIED', 'authentication cannot be claimed without current DOM evidence');
  const accountHash = hex(observation?.accountHash, 'accountHash');
  if (!constantEqual(accountHash, intent.expectedAccountHash)) fail('ACCOUNT_MISMATCH', 'active account differs from intent');
  const receipt = {
    contractVersion: CONTRACT_VERSION,
    receiptType: 'pairing',
    pairingId: intent.pairingId,
    sessionId: intent.sessionId,
    workerId: intent.workerId,
    commissionId: intent.commissionId,
    origin: intent.expectedOrigin,
    accountHash,
    tabId: observation.tabId,
    tabSessionId: id(observation?.tabSessionId, 'tabSessionId'),
    leaseId: id(observation?.leaseId, 'leaseId'),
    mode: 'observe',
    issuedAtMs: intent.issuedAtMs,
    pairedAtMs: nowMs,
    expiresAtMs: Math.min(intent.expiresAtMs, nowMs + 60_000),
    nonceHash: sha256(intent.nonce),
    secretsPersisted: false,
    cookiesRead: false,
    credentialsRead: false,
  };
  receipt.receiptHash = sha256(canonical(receipt));
  state.usedNonces.add(intent.nonce);
  state.receipts.set(receipt.pairingId, Object.freeze({...receipt}));
  state.events.push(Object.freeze({sequence: state.events.length + 1, type: 'paired', pairingId: receipt.pairingId, receiptHash: receipt.receiptHash, atMs: nowMs}));
  return Object.freeze(receipt);
}

export function authorizeCommand(pairing, command, state, nowMs = Date.now()) {
  const stored = state.receipts.get(pairing?.pairingId);
  if (!stored || stored.receiptHash !== pairing.receiptHash) fail('PAIRING_UNKNOWN', 'pairing receipt is unknown');
  if (state.revoked.has(stored.pairingId)) fail('PAIRING_REVOKED', 'pairing was revoked');
  if (stored.expiresAtMs <= nowMs) fail('STALE_PAIRING', 'pairing expired');
  for (const key of ['sessionId', 'workerId', 'commissionId', 'origin', 'accountHash', 'tabId', 'tabSessionId', 'leaseId']) {
    if (command?.[key] !== stored[key]) fail(`${key.replace(/[A-Z]/g, (c) => `_${c}`).toUpperCase()}_MISMATCH`, `${key} differs from pairing`);
  }
  if (exactOrigin(command?.currentUrl) !== stored.origin) fail('TAB_NAVIGATED', 'paired tab left the exact origin');
  if (command?.authenticationState !== 'dom_verified') fail('AUTHENTICATION_UNVERIFIED', 'current authentication is not verified');
  if (!constantEqual(String(command?.currentAccountHash || ''), stored.accountHash)) fail('ACCOUNT_MISMATCH', 'current account differs from pairing');
  const commandId = id(command?.commandId, 'commandId');
  if (state.commands.has(commandId)) fail('COMMAND_REPLAY', 'command was already consumed');
  const action = String(command?.action || '');
  if (OBSERVE_ACTIONS.includes(action)) {
    state.commands.add(commandId);
    return Object.freeze({allowed: true, mode: 'observe', action, commandId, pairingId: stored.pairingId});
  }
  if (!MUTATION_ACTIONS.includes(action)) fail('ACTION_UNSUPPORTED', 'action is outside Browser Porch vocabulary');
  validateMutationApproval(stored, command, state, nowMs);
  state.commands.add(commandId);
  return Object.freeze({allowed: true, mode: 'mutation', action, commandId, pairingId: stored.pairingId});
}

export function validateMutationApproval(pairing, command, state, nowMs = Date.now()) {
  const approval = command?.mutationApproval;
  if (!approval) fail('MUTATION_NOT_APPROVED', 'mutation requires a separate scoped approval');
  const approvalId = id(approval.approvalId, 'approvalId');
  if (state.approvals.has(approvalId)) fail('APPROVAL_REPLAY', 'mutation approval was already consumed');
  if (approval.pairingId !== pairing.pairingId || approval.sessionId !== pairing.sessionId || approval.workerId !== pairing.workerId || approval.commissionId !== pairing.commissionId) fail('APPROVAL_SCOPE_MISMATCH', 'approval binding differs from pairing');
  if (approval.tabId !== pairing.tabId || approval.tabSessionId !== pairing.tabSessionId || approval.accountHash !== pairing.accountHash || approval.origin !== pairing.origin) fail('APPROVAL_SCOPE_MISMATCH', 'approval tab/account/origin differs from pairing');
  if (Number(approval.expiresAtMs) <= nowMs) fail('APPROVAL_EXPIRED', 'mutation approval expired');
  const digest = sha256(canonical({action: command.action, target: command.target || {}, valueHash: sha256(command.value || '')}));
  if (!constantEqual(String(approval.commandDigest || ''), digest)) fail('APPROVAL_DIGEST_MISMATCH', 'approval does not bind this exact command');
  state.approvals.add(approvalId);
}

export function revokePairing(pairingId, state, nowMs = Date.now()) {
  if (!state.receipts.has(pairingId)) fail('PAIRING_UNKNOWN', 'pairing receipt is unknown');
  if (!state.revoked.has(pairingId)) {
    state.revoked.add(pairingId);
    state.events.push(Object.freeze({sequence: state.events.length + 1, type: 'revoked', pairingId, atMs: nowMs}));
  }
  return Object.freeze({pairingId, revoked: true, atMs: nowMs});
}

export function createEphemeralState() {
  return {usedNonces: new Set(), receipts: new Map(), revoked: new Set(), commands: new Set(), approvals: new Set(), events: []};
}

function constantEqual(a, b) {
  const left = Buffer.from(String(a));
  const right = Buffer.from(String(b));
  return left.length === right.length && timingSafeEqual(left, right);
}
