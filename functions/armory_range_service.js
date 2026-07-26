'use strict';

const {createHash, randomUUID} = require('node:crypto');

const CASINGS_COLLECTION = 'armoryRangeCasingsV1';
const RECEIPTS_COLLECTION = 'armoryRangeReceiptsV1';
const DEFAULT_TIMEZONE = 'America/Chicago';
const MAX_RECEIPT_COUNT = 500;
const MAX_SCAN = 2000;

function fail(message, status = 400) {
  throw Object.assign(new Error(message), {status});
}

function cleanText(value, max = 240) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function canonicalJson(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + canonicalJson(value[key])).join(',') + '}';
  }
  return JSON.stringify(value);
}

function sha256(value) {
  return createHash('sha256').update(String(value), 'utf8').digest('hex');
}

function ownerEmail(user = {}) {
  const email = cleanText(user.email, 320).toLowerCase();
  if (!email) fail('Armory Range requires an authenticated owner.', 401);
  return email;
}

function positiveInt(value, fallback, max) {
  const number = Number(value == null ? fallback : value);
  if (!Number.isInteger(number) || number < 1 || number > max) {
    fail(`count must be an integer from 1 to ${max}.`);
  }
  return number;
}

function isoTimestamp(value, field = 'timestamp') {
  const parsed = new Date(value);
  if (!value || Number.isNaN(parsed.getTime())) fail(`${field} must be a valid timestamp.`);
  return parsed.toISOString();
}

function timestampInputs(args = {}) {
  if (Array.isArray(args.timestamps)) return args.timestamps;
  if (Array.isArray(args.firedAt)) return args.firedAt;
  if (Array.isArray(args.occurredAt)) return args.occurredAt;
  const one = args.timestamp || args.firedAt || args.occurredAt || '';
  return one ? [one] : [];
}

function safeAttributes(value) {
  if (value == null) return {};
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('attributes must be an object.');
  const encoded = canonicalJson(value);
  if (Buffer.byteLength(encoded, 'utf8') > 16 * 1024) fail('attributes must be 16 KiB or smaller.');
  return JSON.parse(encoded);
}

function normalizeReceiptInput(args = {}) {
  const item = cleanText(args.ammunition || args.item || args.subject, 240);
  if (!item) fail('ammunition or item is required.');
  const count = positiveInt(args.count, 1, MAX_RECEIPT_COUNT);
  const action = cleanText(args.action, 80) || 'fired';
  const unit = cleanText(args.unit, 80) || 'round';
  const timezone = cleanText(args.timezone, 120) || DEFAULT_TIMEZONE;
  const supplied = timestampInputs(args);
  if (supplied.length > 1 && supplied.length !== count) {
    fail('timestamps must contain exactly one timestamp or one timestamp per casing.');
  }
  const explicitTimestamps = supplied.map((value, index) => isoTimestamp(value, `timestamps[${index}]`));
  return {
    item,
    ammunition: item,
    action,
    count,
    unit,
    timezone,
    explicitTimestamps,
    attributes: safeAttributes(args.attributes),
    note: cleanText(args.note || args.callerNote, 2000),
  };
}

function receiptRequestId(args = {}, receivedAt, uuid = randomUUID) {
  const requested = cleanText(args.requestId || args.idempotencyKey, 160);
  if (requested) {
    if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(requested)) {
      fail('requestId must be 6-160 characters using letters, numbers, dot, underscore, colon, or dash.');
    }
    return requested;
  }
  return `armory-${receivedAt.replace(/[-:.TZ]/g, '').slice(0, 17)}-${uuid()}`;
}

function documentId(owner, requestId, suffix = '') {
  return sha256(`${owner}\n${requestId}\n${suffix}`);
}

function resolveCasingTimestamps(input, receivedAt) {
  if (!input.explicitTimestamps.length) {
    return Array.from({length: input.count}, () => ({occurredAt: receivedAt, timestampSource: 'server_receipt'}));
  }
  if (input.explicitTimestamps.length === 1) {
    return Array.from({length: input.count}, () => ({
      occurredAt: input.explicitTimestamps[0],
      timestampSource: input.count === 1 ? 'explicit' : 'explicit_shared',
    }));
  }
  return input.explicitTimestamps.map((occurredAt) => ({occurredAt, timestampSource: 'explicit'}));
}

async function armoryReceiptOperation({admin, user, args = {}, now = Date.now, uuid = randomUUID}) {
  const owner = ownerEmail(user);
  const input = normalizeReceiptInput(args);
  const receivedAt = new Date(now()).toISOString();
  const requestId = receiptRequestId(args, receivedAt, uuid);
  const inputSha256 = sha256(canonicalJson(input));
  const receiptId = documentId(owner, requestId);
  const receiptRef = admin.firestore().collection(RECEIPTS_COLLECTION).doc(receiptId);
  const existing = await receiptRef.get();
  if (existing.exists) {
    const prior = existing.data();
    if (prior.inputSha256 !== inputSha256) fail('requestId was reused with different Armory Range input.', 409);
    return {...prior, ok: true, idempotent: true};
  }

  const resolved = resolveCasingTimestamps(input, receivedAt);
  const casings = resolved.map((time, index) => ({
    casingId: documentId(owner, requestId, String(index)),
    receiptId,
    requestId,
    ownerEmail: owner,
    sequence: index + 1,
    item: input.item,
    ammunition: input.ammunition,
    action: input.action,
    quantity: 1,
    unit: input.unit,
    occurredAt: time.occurredAt,
    timestampSource: time.timestampSource,
    recordedAt: receivedAt,
    timezone: input.timezone,
    attributes: input.attributes,
    note: input.note,
    immutable: true,
    schemaVersion: 'armory-range.casing.v1',
  }));

  const receipt = {
    ok: true,
    idempotent: false,
    receiptId,
    requestId,
    ownerEmail: owner,
    item: input.item,
    ammunition: input.ammunition,
    action: input.action,
    count: input.count,
    unit: input.unit,
    timestamps: casings.map((casing) => casing.occurredAt),
    timestampSources: casings.map((casing) => casing.timestampSource),
    recordedAt: receivedAt,
    timezone: input.timezone,
    casingIds: casings.map((casing) => casing.casingId),
    inputSha256,
    schemaVersion: 'armory-range.receipt.v1',
  };

  const batch = admin.firestore().batch();
  batch.create(receiptRef, receipt);
  for (const casing of casings) {
    batch.create(admin.firestore().collection(CASINGS_COLLECTION).doc(casing.casingId), casing);
  }
  await batch.commit();
  return receipt;
}

function queryBounds(args = {}) {
  return {
    item: cleanText(args.ammunition || args.item || args.subject, 240).toLowerCase(),
    action: cleanText(args.action, 80).toLowerCase(),
    since: args.since ? isoTimestamp(args.since, 'since') : '',
    until: args.until ? isoTimestamp(args.until, 'until') : '',
  };
}

function matches(casing, bounds) {
  if (bounds.item && String(casing.item || casing.ammunition || '').toLowerCase() !== bounds.item) return false;
  if (bounds.action && String(casing.action || '').toLowerCase() !== bounds.action) return false;
  if (bounds.since && casing.occurredAt < bounds.since) return false;
  if (bounds.until && casing.occurredAt > bounds.until) return false;
  return true;
}

async function ownerCasings({admin, user, args = {}}) {
  const owner = ownerEmail(user);
  const snapshot = await admin.firestore().collection(CASINGS_COLLECTION)
    .where('ownerEmail', '==', owner)
    .limit(MAX_SCAN)
    .get();
  const bounds = queryBounds(args);
  return snapshot.docs
    .map((doc) => doc.data())
    .filter((casing) => matches(casing, bounds))
    .sort((a, b) => String(b.occurredAt).localeCompare(String(a.occurredAt)) || b.sequence - a.sequence);
}

async function armoryCasingOperation(context) {
  const casings = await ownerCasings(context);
  const rawLimit = context.args && context.args.limit;
  const limit = context.args && context.args.lastOnly === true ? 1 : positiveInt(rawLimit, 10, 100);
  const selected = casings.slice(0, limit);
  return {
    ok: true,
    count: selected.length,
    lastCasing: selected[0] || null,
    casings: selected,
    scannedLimit: MAX_SCAN,
    schemaVersion: 'armory-range.casing-query.v1',
  };
}

async function armoryRecountOperation(context) {
  const casings = await ownerCasings(context);
  const groups = new Map();
  for (const casing of casings) {
    const key = canonicalJson({item: casing.item, action: casing.action, unit: casing.unit});
    const group = groups.get(key) || {item: casing.item, ammunition: casing.ammunition, action: casing.action, unit: casing.unit, count: 0, lastOccurredAt: ''};
    group.count += 1;
    if (!group.lastOccurredAt || casing.occurredAt > group.lastOccurredAt) group.lastOccurredAt = casing.occurredAt;
    groups.set(key, group);
  }
  const recount = [...groups.values()].sort((a, b) => b.count - a.count || a.item.localeCompare(b.item));
  return {
    ok: true,
    totalCasings: casings.length,
    recount,
    lastCasing: casings[0] || null,
    scannedLimit: MAX_SCAN,
    schemaVersion: 'armory-range.recount.v1',
  };
}

module.exports = {
  CASINGS_COLLECTION,
  RECEIPTS_COLLECTION,
  armoryReceiptOperation,
  armoryCasingOperation,
  armoryRecountOperation,
  normalizeReceiptInput,
  resolveCasingTimestamps,
};
