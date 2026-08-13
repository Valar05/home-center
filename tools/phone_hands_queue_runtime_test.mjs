#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const {devicePull, hashText, COLLECTIONS} = require('../functions/phone_hands_relay');

const copy = (value) => value === undefined ? undefined : JSON.parse(JSON.stringify(value));

class Snapshot {
  constructor(id, value) {
    this.id = id;
    this.exists = value !== undefined;
    this.value = copy(value);
  }
  data() { return copy(this.value); }
}

class DocumentReference {
  constructor(store, collectionName, id) {
    this.store = store;
    this.collectionName = collectionName;
    this.id = id;
  }
  async get() { return new Snapshot(this.id, this.store.directGet(this.collectionName, this.id)); }
  async set(value, options = {}) { this.store.directSet(this.collectionName, this.id, value, options); }
}

class Query {
  constructor(store, collectionName, filters = [], maximum = Infinity) {
    this.store = store;
    this.collectionName = collectionName;
    this.filters = filters;
    this.maximum = maximum;
  }
  where(field, operator, value) {
    assert.equal(operator, '==');
    return new Query(this.store, this.collectionName, [...this.filters, {field, value}], this.maximum);
  }
  limit(maximum) { return new Query(this.store, this.collectionName, this.filters, maximum); }
  async get() {
    const rows = [...this.store.collectionMap(this.collectionName).entries()]
      .filter(([, value]) => this.filters.every((filter) => value[filter.field] === filter.value))
      .sort(([left], [right]) => left.localeCompare(right))
      .slice(0, this.maximum)
      .map(([id, value]) => new Snapshot(id, value));
    return {docs: rows, empty: rows.length === 0};
  }
}

class CollectionReference {
  constructor(store, name) { this.store = store; this.name = name; }
  doc(id) { return new DocumentReference(this.store, this.name, id); }
  where(field, operator, value) { return new Query(this.store, this.name).where(field, operator, value); }
}

class Transaction {
  constructor(store) { this.store = store; this.writes = []; }
  async get(reference) {
    if (this.store.transactionGetHook) await this.store.transactionGetHook(reference, this.store);
    return reference.get();
  }
  set(reference, value, options = {}) { this.writes.push({reference, value: copy(value), options}); }
  commit() {
    for (const write of this.writes) {
      this.store.directSet(write.reference.collectionName, write.reference.id, write.value, write.options);
    }
  }
}

class FakeFirestore {
  constructor() {
    this.collections = new Map();
    this.transactionGetHook = null;
  }
  collectionMap(name) {
    if (!this.collections.has(name)) this.collections.set(name, new Map());
    return this.collections.get(name);
  }
  collection(name) { return new CollectionReference(this, name); }
  directGet(name, id) { return copy(this.collectionMap(name).get(id)); }
  directSet(name, id, value, options = {}) {
    const map = this.collectionMap(name);
    const current = map.get(id) || {};
    map.set(id, options.merge ? {...copy(current), ...copy(value)} : copy(value));
  }
  async runTransaction(callback) {
    const transaction = new Transaction(this);
    const result = await callback(transaction);
    transaction.commit();
    return result;
  }
}

const firestore = new FakeFirestore();
const admin = {firestore: () => firestore};
const deviceId = 'primary-phone';
const ownerKey = 'owner_test';
const deviceToken = 'test-device-token-with-at-least-thirty-two-characters';
const now = Date.now();
firestore.directSet(COLLECTIONS.devices, deviceId, {
  deviceId,
  ownerKey,
  tokenHash: hashText(deviceToken),
  status: 'registered',
});

for (let index = 0; index < 12; index += 1) {
  const commandId = `expired-${String(index).padStart(2, '0')}`;
  firestore.directSet(COLLECTIONS.commands, commandId, {
    commandId,
    deviceId,
    ownerKey,
    status: 'queued',
    createdAtMs: now - 20_000 + index,
    expiresAtMs: now - 1_000,
    action: {action: 'observe'},
  });
}
firestore.directSet(COLLECTIONS.commands, 'fresh-command', {
  commandId: 'fresh-command',
  deviceId,
  ownerKey,
  status: 'queued',
  createdAtMs: now,
  expiresAtMs: now + 60_000,
  action: {action: 'observe'},
});

const pulled = await devicePull(admin, {deviceId, deviceToken, leaseMs: 30_000});
assert.equal(pulled.ok, true);
assert.equal(pulled.command.commandId, 'fresh-command');
assert.equal(pulled.command.status, 'leased');
assert.equal(pulled.command.leaseOwner, 'device:primary-phone');
for (let index = 0; index < 12; index += 1) {
  const commandId = `expired-${String(index).padStart(2, '0')}`;
  const record = firestore.directGet(COLLECTIONS.commands, commandId);
  assert.equal(record.status, 'failed');
  assert.equal(record.error, 'expired_before_lease');
  assert.ok(record.completedAtMs > 0);
}
assert.equal(firestore.directGet(COLLECTIONS.commands, 'fresh-command').status, 'leased');
assert.equal(firestore.directGet(COLLECTIONS.devices, deviceId).status, 'online');

const empty = await devicePull(admin, {deviceId, deviceToken, leaseMs: 30_000});
assert.equal(empty.ok, true);
assert.equal(empty.command, null);

firestore.directSet(COLLECTIONS.commands, 'raced-command', {
  commandId: 'raced-command',
  deviceId,
  ownerKey,
  status: 'queued',
  createdAtMs: now + 1,
  expiresAtMs: now + 60_000,
  action: {action: 'observe'},
});
let raced = false;
firestore.transactionGetHook = async (reference, store) => {
  if (!raced && reference.collectionName === COLLECTIONS.commands && reference.id === 'raced-command') {
    raced = true;
    store.directSet(COLLECTIONS.commands, 'raced-command', {status: 'completed', completedAtMs: Date.now()}, {merge: true});
  }
};
const racedPull = await devicePull(admin, {deviceId, deviceToken, leaseMs: 30_000});
assert.equal(racedPull.ok, true);
assert.equal(racedPull.command, null);
assert.equal(firestore.directGet(COLLECTIONS.commands, 'raced-command').status, 'completed');

console.log('Phone Hands queue runtime tests passed');
