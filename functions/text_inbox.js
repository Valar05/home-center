'use strict';

const {createHash} = require('node:crypto');

const REGISTRY_VERSION = '2026-08-13.text-inbox-owner-index-v1';
const MAX_SCAN = 200;
const OPERATIONS = Object.freeze({
  'text_inbox.status': {summary: 'Report the caller-owned Home Center text inbox capability.', write: false},
  'text_inbox.recent': {summary: 'List recent caller-owned text messages captured from Google Messages notifications.', write: false},
  'text_inbox.search': {summary: 'Search recent caller-owned captured text messages by sender or body.', write: false},
  'text_inbox.get': {summary: 'Read one caller-owned captured text message by Home Center message id.', write: false},
  'text_inbox.conversation': {summary: 'List recent captured messages sharing the same derived sender conversation key.', write: false},
});

function clean(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function statusError(status, message, code = '') {
  return Object.assign(new Error(message), {status, code});
}

function owner(user) {
  const uid = clean(user && user.uid, 160);
  const email = clean(user && user.email, 320).toLowerCase();
  if (!uid) throw statusError(401, 'A Firebase-backed Home Center identity is required.', 'TEXT_INBOX_UID_REQUIRED');
  return {uid, email};
}

function homeCenterMessageId(value) {
  const id = clean(value, 160);
  if (!/^sms_[a-f0-9]{32,64}$/.test(id)) throw statusError(400, 'A valid Home Center SMS messageId is required.');
  return id;
}

function sourcePath(value, expectedId = '') {
  const path = clean(value, 500);
  const match = path.match(/^households\/([a-z0-9_-]+)\/smsCalendarIntake\/(sms_[a-f0-9]{32,64})$/);
  if (!match) throw statusError(409, 'Text inbox index contains an invalid source path.', 'TEXT_INBOX_SOURCE_PATH_INVALID');
  if (expectedId && match[2] !== expectedId) throw statusError(409, 'Text inbox index source id does not match messageId.', 'TEXT_INBOX_SOURCE_ID_MISMATCH');
  return path;
}

function digest(value) {
  return createHash('sha256').update(String(value || '')).digest('hex');
}

function conversationKey(record) {
  const address = clean(record && record.senderAddress, 160).replace(/\D/g, '');
  const sender = clean(record && record.sender, 240).toLowerCase();
  const basis = address ? `tel:${address}` : `sender:${sender || 'unknown'}`;
  return `conversation_${digest(basis).slice(0, 24)}`;
}

function publicRecord(record) {
  const value = record || {};
  return {
    messageId: clean(value.messageId || value.id, 160),
    sender: clean(value.sender, 240),
    senderAddress: clean(value.senderAddress, 80),
    body: clean(value.body, 12000),
    receivedAtMs: Number(value.receivedAtMs || 0) || 0,
    conversationKey: conversationKey(value),
    sourceTransport: clean(value.sourceTransport, 120),
    sourceHash: clean(value.sourceHash, 128),
    classification: clean(value.classification && value.classification.classification, 80) || 'unclassified',
    calendarProposalReady: value.status === 'proposal_ready',
    privacyScope: 'owner_private_text_inbox',
  };
}

function registry() {
  return {
    version: REGISTRY_VERSION,
    authorityBoundary: 'Read-only caller-owned text evidence. Notification capture does not imply authoritative unread/thread state and this surface has no outbound send authority.',
    operations: OPERATIONS,
  };
}

function firestoreStore(admin, user) {
  const identity = owner(user);
  const db = admin.firestore();
  const index = db.collection('users').doc(identity.uid).collection('textInboxIndex');
  return {
    identity,
    async listPointers(limit = 50) {
      const snapshot = await index.orderBy('receivedAtMs', 'desc').limit(Math.max(1, Math.min(MAX_SCAN, Number(limit || 50)))).get();
      return (snapshot.docs || []).map((doc) => ({id: doc.id, ...doc.data()}));
    },
    async getPointer(id) {
      const snap = await index.doc(id).get();
      if (!snap.exists) throw statusError(404, 'Text message was not found in the caller-owned index.');
      return {id: snap.id, ...snap.data()};
    },
    async resolve(pointer) {
      const id = homeCenterMessageId(pointer.messageId || pointer.id);
      const path = sourcePath(pointer.sourcePath, id);
      const snap = await db.doc(path).get();
      if (!snap.exists) throw statusError(409, 'Indexed text source is missing.', 'TEXT_INBOX_SOURCE_MISSING');
      const record = {id: snap.id, ...snap.data()};
      if (clean(record.createdByUid, 160) !== identity.uid) {
        throw statusError(403, 'Indexed text source is not owned by the connected identity.', 'TEXT_INBOX_OWNER_MISMATCH');
      }
      if (homeCenterMessageId(record.messageId || record.id) !== id) {
        throw statusError(409, 'Indexed text source identity changed.', 'TEXT_INBOX_SOURCE_ID_MISMATCH');
      }
      if (clean(pointer.sourceHash, 128) && clean(pointer.sourceHash, 128) !== clean(record.sourceHash, 128)) {
        throw statusError(409, 'Indexed text source hash changed.', 'TEXT_INBOX_SOURCE_HASH_MISMATCH');
      }
      return record;
    },
  };
}

async function resolveMany(store, pointers) {
  const results = [];
  for (const pointer of pointers) {
    try {
      results.push(await store.resolve(pointer));
    } catch (error) {
      if (error && error.code === 'TEXT_INBOX_SOURCE_MISSING') continue;
      throw error;
    }
  }
  return results;
}

async function runOperation({admin, user, args = {}, store = null}) {
  const operation = clean(args.operation || args.type, 120);
  const input = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : args;
  if (!OPERATIONS[operation]) throw statusError(400, `Unsupported text inbox operation: ${operation}`);
  const dataStore = store || firestoreStore(admin, user);

  if (operation === 'text_inbox.status') {
    const pointers = await dataStore.listPointers(1);
    return {operation, registryVersion: REGISTRY_VERSION, result: {
      state: 'read_only',
      capture: 'android_google_messages_notification',
      indexed: pointers.length > 0,
      authoritativeUnreadState: false,
      authoritativeProviderThreadId: false,
      outboundAuthority: false,
    }};
  }

  if (operation === 'text_inbox.get') {
    const id = homeCenterMessageId(input.messageId);
    const record = await dataStore.resolve(await dataStore.getPointer(id));
    return {operation, registryVersion: REGISTRY_VERSION, result: publicRecord(record)};
  }

  const limit = Math.max(1, Math.min(100, Number(input.limit || 30)));
  const scan = Math.max(limit, Math.min(MAX_SCAN, Number(input.scanLimit || Math.max(100, limit))));
  const records = await resolveMany(dataStore, await dataStore.listPointers(scan));

  if (operation === 'text_inbox.recent') {
    return {operation, registryVersion: REGISTRY_VERSION, result: {count: Math.min(limit, records.length), messages: records.slice(0, limit).map(publicRecord)}};
  }

  if (operation === 'text_inbox.search') {
    const query = clean(input.query, 500).toLowerCase();
    if (!query) throw statusError(400, 'query is required.');
    const matches = records.filter((record) => `${clean(record.sender, 240)}\n${clean(record.senderAddress, 80)}\n${clean(record.body, 12000)}`.toLowerCase().includes(query)).slice(0, limit);
    return {operation, registryVersion: REGISTRY_VERSION, result: {query, count: matches.length, messages: matches.map(publicRecord)}};
  }

  if (operation === 'text_inbox.conversation') {
    const wanted = clean(input.conversationKey, 80);
    if (!/^conversation_[a-f0-9]{24}$/.test(wanted)) throw statusError(400, 'conversationKey is required.');
    const matches = records.filter((record) => conversationKey(record) === wanted).slice(0, limit);
    return {operation, registryVersion: REGISTRY_VERSION, result: {conversationKey: wanted, count: matches.length, messages: matches.map(publicRecord)}};
  }

  throw statusError(400, `Unsupported text inbox operation: ${operation}`);
}

module.exports = {REGISTRY_VERSION, conversationKey, firestoreStore, homeCenterMessageId, publicRecord, registry, runOperation, sourcePath};
