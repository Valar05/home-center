'use strict';

const {createHash} = require('node:crypto');

const MESSAGE_COLLECTION = 'agentMailMessages';
const EVENT_COLLECTION = 'agentMailEvents';
const MAX_BODY_CHARS = 12000;
const MAX_RECIPIENTS = 8;
const MAX_ATTACHMENTS = 12;
const MESSAGE_TYPES = new Set(['message', 'request', 'status', 'decision', 'correction']);
const PRIORITIES = new Set(['low', 'normal', 'high', 'urgent']);
const AUTHORITIES = new Set(['proposal', 'information', 'request', 'approval', 'rejection', 'correction']);
const PRIVACY_LABELS = new Set(['standard', 'private']);

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function fail(message, status = 400) {
  const err = new Error(message);
  err.status = status;
  throw err;
}

function stableRequestId(value) {
  const id = safeText(value, 160);
  if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(id)) {
    fail('requestId must be 6-160 characters using letters, numbers, dot, underscore, colon, or dash.');
  }
  return id;
}

function safeAgentId(value, label = 'agentId') {
  const id = safeText(value, 80).toLowerCase();
  if (!/^[a-z0-9][a-z0-9_.:-]{0,79}$/.test(id)) {
    fail(`${label} must be a lowercase agent address using letters, numbers, dot, underscore, colon, or dash.`);
  }
  return id;
}

function safeSpaceId(value) {
  return safeAgentId(value || 'home-center', 'spaceId');
}

function enumValue(value, allowed, fallback, label) {
  const clean = safeText(value, 40).toLowerCase() || fallback;
  if (!allowed.has(clean)) fail(`${label} must be one of: ${Array.from(allowed).join(', ')}.`);
  return clean;
}

function uniqueAgentIds(values, label = 'toAgents') {
  const raw = Array.isArray(values) ? values : [values];
  const ids = [...new Set(raw.filter(Boolean).map((value) => safeAgentId(value, label)))];
  if (!ids.length) fail(`${label} must contain at least one recipient.`);
  if (ids.length > MAX_RECIPIENTS) fail(`${label} supports at most ${MAX_RECIPIENTS} recipients.`);
  return ids;
}

function cleanAttachments(values) {
  if (!Array.isArray(values)) return [];
  return values.slice(0, MAX_ATTACHMENTS).map((item) => {
    const value = item && typeof item === 'object' && !Array.isArray(item) ? item : {};
    const driveFileId = safeText(value.driveFileId || value.fileId, 220);
    const url = safeText(value.url, 1200);
    const label = safeText(value.label || value.name, 240);
    if (!driveFileId && !url) fail('Each attachment requires driveFileId/fileId or url.');
    return {driveFileId, url, label};
  });
}

function actorIdentity(user = {}) {
  return {
    actorEmail: safeText(user.email, 320).toLowerCase(),
    actorUid: safeText(user.uid, 160),
    authKind: safeText(user.authKind, 80),
  };
}

function hashId(prefix, ...parts) {
  const digest = createHash('sha256').update(parts.map((part) => String(part || '')).join('\n')).digest('hex');
  return `${prefix}_${digest.slice(0, 32)}`;
}

function messageIdFor(user, requestId) {
  const actor = safeText(user && (user.email || user.uid), 320).toLowerCase() || 'unknown';
  return hashId('msg', actor, requestId);
}

function eventIdFor(user, requestId, kind) {
  const actor = safeText(user && (user.email || user.uid), 320).toLowerCase() || 'unknown';
  return hashId('evt', actor, kind, requestId);
}

function sanitizeAckMap(value) {
  const result = {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) return result;
  for (const [key, entry] of Object.entries(value)) {
    const agentId = safeAgentId(key);
    result[agentId] = {
      acknowledgedAtMs: Number(entry && entry.acknowledgedAtMs || 0),
      actorEmail: safeText(entry && entry.actorEmail, 320),
      note: safeText(entry && entry.note, 1000),
    };
  }
  return result;
}

function cleanMessage(data = {}) {
  const acknowledgedBy = sanitizeAckMap(data.acknowledgedBy);
  const toAgents = Array.isArray(data.toAgents) ? data.toAgents.map((value) => safeAgentId(value)) : [];
  return {
    messageId: safeText(data.messageId, 80),
    spaceId: safeSpaceId(data.spaceId),
    threadId: safeText(data.threadId, 80),
    replyTo: safeText(data.replyTo, 80),
    supersedesId: safeText(data.supersedesId, 80),
    fromAgent: safeAgentId(data.fromAgent, 'fromAgent'),
    toAgents,
    subject: safeText(data.subject, 240),
    body: safeText(data.body, MAX_BODY_CHARS),
    messageType: enumValue(data.messageType, MESSAGE_TYPES, 'message', 'messageType'),
    priority: enumValue(data.priority, PRIORITIES, 'normal', 'priority'),
    authority: enumValue(data.authority, AUTHORITIES, 'proposal', 'authority'),
    privacy: enumValue(data.privacy, PRIVACY_LABELS, 'standard', 'privacy'),
    requiresAck: data.requiresAck !== false,
    status: safeText(data.status, 40) || 'sent',
    attachments: cleanAttachments(data.attachments),
    tags: Array.isArray(data.tags) ? data.tags.map((tag) => safeText(tag, 80)).filter(Boolean).slice(0, 12) : [],
    createdAtMs: Number(data.createdAtMs || 0),
    updatedAtMs: Number(data.updatedAtMs || 0),
    expiresAtMs: Number(data.expiresAtMs || 0),
    acknowledgedBy,
    acknowledgedAgents: Object.keys(acknowledgedBy),
    actorEmail: safeText(data.actorEmail, 320),
  };
}

function messagePayload(user, args, messageId, now) {
  const fromAgent = safeAgentId(args.fromAgent, 'fromAgent');
  const toAgents = uniqueAgentIds(args.toAgents || args.toAgent);
  const body = safeText(args.body || args.text, MAX_BODY_CHARS);
  if (!body) fail('body is required.');
  const subject = safeText(args.subject, 240) || body.split(/\r?\n/, 1)[0].slice(0, 120);
  const threadId = safeText(args.threadId, 80) || messageId;
  const expiresAtMs = Math.max(0, Math.floor(Number(args.expiresAtMs || 0)) || 0);
  return {
    messageId,
    spaceId: safeSpaceId(args.spaceId),
    threadId,
    replyTo: safeText(args.replyTo, 80),
    supersedesId: safeText(args.supersedesId, 80),
    fromAgent,
    toAgents,
    subject,
    body,
    messageType: enumValue(args.messageType, MESSAGE_TYPES, 'message', 'messageType'),
    priority: enumValue(args.priority, PRIORITIES, 'normal', 'priority'),
    authority: enumValue(args.authority, AUTHORITIES, 'proposal', 'authority'),
    privacy: enumValue(args.privacy, PRIVACY_LABELS, 'standard', 'privacy'),
    requiresAck: args.requiresAck !== false,
    status: 'sent',
    attachments: cleanAttachments(args.attachments),
    tags: Array.isArray(args.tags) ? args.tags.map((tag) => safeText(tag, 80)).filter(Boolean).slice(0, 12) : [],
    createdAtMs: now,
    updatedAtMs: now,
    expiresAtMs,
    acknowledgedBy: {},
    ...actorIdentity(user),
  };
}

async function sendAgentMail({admin, user, args = {}}) {
  const requestId = stableRequestId(args.requestId);
  const messageId = messageIdFor(user, requestId);
  const db = admin.firestore();
  const messageRef = db.collection(MESSAGE_COLLECTION).doc(messageId);
  const eventRef = db.collection(EVENT_COLLECTION).doc(eventIdFor(user, requestId, 'sent'));
  const now = Date.now();
  const payload = messagePayload(user, args, messageId, now);
  const result = await db.runTransaction(async (tx) => {
    const existing = await tx.get(messageRef);
    if (existing.exists) return {message: cleanMessage(existing.data()), idempotent: true};
    tx.set(messageRef, payload, {merge: false});
    tx.set(eventRef, {
      eventId: eventRef.id,
      messageId,
      threadId: payload.threadId,
      spaceId: payload.spaceId,
      kind: 'sent',
      agentId: payload.fromAgent,
      createdAtMs: now,
      requestId,
      ...actorIdentity(user),
    }, {merge: false});
    return {message: cleanMessage(payload), idempotent: false};
  });
  return {...result, requestId};
}

async function getMessageSnapshot(admin, messageId) {
  const id = safeText(messageId, 80);
  if (!/^msg_[a-f0-9]{32}$/.test(id)) fail('A valid messageId is required.');
  const snap = await admin.firestore().collection(MESSAGE_COLLECTION).doc(id).get();
  if (!snap.exists) fail('Message not found.', 404);
  return snap;
}

async function getAgentMail({admin, args = {}}) {
  const snap = await getMessageSnapshot(admin, args.messageId);
  return {message: cleanMessage(snap.data())};
}

async function inboxAgentMail({admin, args = {}}) {
  const agentId = safeAgentId(args.agentId || args.toAgent, 'agentId');
  const spaceId = safeSpaceId(args.spaceId);
  const limit = Math.max(1, Math.min(50, Math.floor(Number(args.limit || 20)) || 20));
  const includeAcknowledged = args.includeAcknowledged === true;
  const now = Date.now();
  const snap = await admin.firestore()
    .collection(MESSAGE_COLLECTION)
    .where('toAgents', 'array-contains', agentId)
    .limit(200)
    .get();
  const messages = snap.docs
    .map((doc) => cleanMessage(doc.data()))
    .filter((message) => message.spaceId === spaceId)
    .filter((message) => !message.expiresAtMs || message.expiresAtMs > now)
    .filter((message) => includeAcknowledged || !message.acknowledgedBy[agentId])
    .sort((a, b) => b.createdAtMs - a.createdAtMs)
    .slice(0, limit);
  return {
    spaceId,
    agentId,
    count: messages.length,
    messages,
    nextAction: messages.length ? `Read or acknowledge ${messages[0].messageId}.` : 'No pending messages.',
  };
}

async function threadAgentMail({admin, args = {}}) {
  const threadId = safeText(args.threadId, 80);
  if (!threadId) fail('threadId is required.');
  const spaceId = safeSpaceId(args.spaceId);
  const limit = Math.max(1, Math.min(100, Math.floor(Number(args.limit || 50)) || 50));
  const snap = await admin.firestore()
    .collection(MESSAGE_COLLECTION)
    .where('threadId', '==', threadId)
    .limit(200)
    .get();
  const messages = snap.docs
    .map((doc) => cleanMessage(doc.data()))
    .filter((message) => message.spaceId === spaceId)
    .sort((a, b) => a.createdAtMs - b.createdAtMs)
    .slice(-limit);
  return {spaceId, threadId, count: messages.length, messages};
}

async function acknowledgeAgentMail({admin, user, args = {}}) {
  const requestId = stableRequestId(args.requestId);
  const agentId = safeAgentId(args.agentId, 'agentId');
  const messageId = safeText(args.messageId, 80);
  if (!/^msg_[a-f0-9]{32}$/.test(messageId)) fail('A valid messageId is required.');
  const db = admin.firestore();
  const messageRef = db.collection(MESSAGE_COLLECTION).doc(messageId);
  const eventRef = db.collection(EVENT_COLLECTION).doc(eventIdFor(user, requestId, 'acknowledged'));
  const now = Date.now();
  const result = await db.runTransaction(async (tx) => {
    const [messageSnap, eventSnap] = await Promise.all([tx.get(messageRef), tx.get(eventRef)]);
    if (!messageSnap.exists) fail('Message not found.', 404);
    const current = cleanMessage(messageSnap.data());
    if (!current.toAgents.includes(agentId)) fail(`${agentId} is not a recipient of this message.`, 403);
    if (eventSnap.exists) return {message: current, idempotent: true};
    const acknowledgedBy = {...current.acknowledgedBy, [agentId]: {
      acknowledgedAtMs: now,
      actorEmail: safeText(user && user.email, 320).toLowerCase(),
      note: safeText(args.note, 1000),
    }};
    const allAcknowledged = current.toAgents.every((recipient) => acknowledgedBy[recipient]);
    const updated = {
      ...messageSnap.data(),
      acknowledgedBy,
      status: allAcknowledged ? 'acknowledged' : 'sent',
      updatedAtMs: now,
    };
    tx.set(messageRef, updated, {merge: false});
    tx.set(eventRef, {
      eventId: eventRef.id,
      messageId,
      threadId: current.threadId,
      spaceId: current.spaceId,
      kind: 'acknowledged',
      agentId,
      note: safeText(args.note, 1000),
      createdAtMs: now,
      requestId,
      ...actorIdentity(user),
    }, {merge: false});
    return {message: cleanMessage(updated), idempotent: false};
  });
  return {...result, requestId};
}

async function replyAgentMail({admin, user, args = {}}) {
  const parentSnap = await getMessageSnapshot(admin, args.replyTo || args.messageId);
  const parent = cleanMessage(parentSnap.data());
  const fromAgent = safeAgentId(args.fromAgent, 'fromAgent');
  const recipients = args.toAgents || args.toAgent || [parent.fromAgent];
  return sendAgentMail({
    admin,
    user,
    args: {
      ...args,
      fromAgent,
      toAgents: recipients,
      replyTo: parent.messageId,
      threadId: parent.threadId,
      spaceId: args.spaceId || parent.spaceId,
      subject: args.subject || `Re: ${parent.subject}`,
    },
  });
}

function agentMailOperationRegistry() {
  return {
    version: '2026-07-25.firestore-agent-mail-v1',
    authorityBoundary: 'Messages are durable contributions, not Holocron canon. Receiving or acknowledging a message never promotes it.',
    operations: {
      'agent_mail.send': {
        summary: 'Send an authenticated, idempotent agent message through the Home Center Firestore mailbox.',
        write: true,
        requiresRequestId: true,
        input: {spaceId: 'optional string', fromAgent: 'string', toAgents: 'string[]', subject: 'optional string', body: 'string', messageType: 'optional message|request|status|decision|correction', priority: 'optional low|normal|high|urgent', authority: 'optional proposal|information|request|approval|rejection|correction', privacy: 'optional standard|private', requiresAck: 'optional boolean', attachments: 'optional array', requestId: 'string'},
      },
      'agent_mail.inbox': {
        summary: 'Read pending messages for an agent address, newest first.',
        write: false,
        input: {spaceId: 'optional string', agentId: 'string', includeAcknowledged: 'optional boolean', limit: 'optional number 1-50'},
      },
      'agent_mail.get': {
        summary: 'Read one agent message by stable message ID.',
        write: false,
        input: {messageId: 'string'},
      },
      'agent_mail.thread': {
        summary: 'Read a complete agent conversation thread in chronological order.',
        write: false,
        input: {spaceId: 'optional string', threadId: 'string', limit: 'optional number 1-100'},
      },
      'agent_mail.ack': {
        summary: 'Acknowledge receipt of one message for one recipient agent, idempotently.',
        write: true,
        requiresRequestId: true,
        input: {messageId: 'string', agentId: 'string', note: 'optional string', requestId: 'string'},
      },
      'agent_mail.reply': {
        summary: 'Reply in an existing thread; defaults the recipient to the original sender.',
        write: true,
        requiresRequestId: true,
        input: {replyTo: 'messageId string', fromAgent: 'string', toAgents: 'optional string[]', subject: 'optional string', body: 'string', priority: 'optional string', authority: 'optional string', requestId: 'string'},
      },
    },
  };
}

async function agentMailOperationRunOperation({admin, user, args = {}}) {
  const operation = safeText(args.operation, 120);
  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : {};
  const registry = agentMailOperationRegistry();
  if (!registry.operations[operation]) fail(`Unsupported agent mail operation: ${operation}.`);
  let result;
  if (operation === 'agent_mail.send') result = await sendAgentMail({admin, user, args: operationArgs});
  else if (operation === 'agent_mail.inbox') result = await inboxAgentMail({admin, args: operationArgs});
  else if (operation === 'agent_mail.get') result = await getAgentMail({admin, args: operationArgs});
  else if (operation === 'agent_mail.thread') result = await threadAgentMail({admin, args: operationArgs});
  else if (operation === 'agent_mail.ack') result = await acknowledgeAgentMail({admin, user, args: operationArgs});
  else if (operation === 'agent_mail.reply') result = await replyAgentMail({admin, user, args: operationArgs});
  return {operation, registryVersion: registry.version, result};
}

module.exports = {
  agentMailOperationRegistry,
  agentMailOperationRunOperation,
  sendAgentMail,
  inboxAgentMail,
  getAgentMail,
  threadAgentMail,
  acknowledgeAgentMail,
  replyAgentMail,
  cleanMessage,
  messageIdFor,
};
