import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  CASINGS_COLLECTION,
  RECEIPTS_COLLECTION,
  armoryReceiptOperation,
  armoryCasingOperation,
  armoryRecountOperation,
} = require('../functions/armory_range_service.js');

function fakeAdmin() {
  const stores = new Map();
  const store = (name) => {
    if (!stores.has(name)) stores.set(name, new Map());
    return stores.get(name);
  };
  const collection = (name) => ({
    doc: (id) => ({
      id,
      async get() {
        const value = store(name).get(id);
        return {exists: value !== undefined, data: () => value};
      },
      _name: name,
      _id: id,
    }),
    where: (field, operator, value) => {
      assert.equal(operator, '==');
      return {
        limit: (limit) => ({
          async get() {
            const docs = [...store(name).entries()]
              .filter(([, item]) => item[field] === value)
              .slice(0, limit)
              .map(([id, item]) => ({id, data: () => item}));
            return {docs, empty: docs.length === 0};
          },
        }),
      };
    },
  });
  return {
    firestore: () => ({
      collection,
      batch: () => {
        const writes = [];
        return {
          create(ref, value) {
            writes.push({ref, value});
          },
          async commit() {
            for (const {ref} of writes) {
              if (store(ref._name).has(ref._id)) throw new Error('already exists');
            }
            for (const {ref, value} of writes) store(ref._name).set(ref._id, value);
          },
        };
      },
    }),
    _store: store,
  };
}

const admin = fakeAdmin();
const user = {email: 'dclarke1005@gmail.com'};
const now = () => Date.parse('2026-07-26T18:30:00.000Z');

const receipt = await armoryReceiptOperation({
  admin,
  user,
  now,
  args: {ammunition: '9mm', count: 2, requestId: 'armory-contract-001'},
});
assert.equal(receipt.count, 2);
assert.deepEqual(receipt.timestamps, [
  '2026-07-26T18:30:00.000Z',
  '2026-07-26T18:30:00.000Z',
]);
assert.deepEqual(receipt.timestampSources, ['server_receipt', 'server_receipt']);
assert.equal(admin._store(CASINGS_COLLECTION).size, 2);
assert.equal(admin._store(RECEIPTS_COLLECTION).size, 1);
for (const casing of admin._store(CASINGS_COLLECTION).values()) {
  assert.ok(casing.occurredAt, 'timestamp is mandatory on every casing');
  assert.equal(casing.timestampSource, 'server_receipt');
  assert.equal(casing.quantity, 1);
}

const replay = await armoryReceiptOperation({
  admin,
  user,
  now,
  args: {ammunition: '9mm', count: 2, requestId: 'armory-contract-001'},
});
assert.equal(replay.idempotent, true);
assert.equal(admin._store(CASINGS_COLLECTION).size, 2);

await assert.rejects(
  () => armoryReceiptOperation({
    admin,
    user,
    now,
    args: {ammunition: '9mm', count: 3, requestId: 'armory-contract-001'},
  }),
  /reused with different/,
);

const explicit = await armoryReceiptOperation({
  admin,
  user,
  now: () => Date.parse('2026-07-26T19:00:00.000Z'),
  args: {
    ammunition: '12 gauge',
    count: 2,
    timestamps: ['2026-07-26T13:59:58-05:00', '2026-07-26T13:59:59-05:00'],
    requestId: 'armory-contract-002',
  },
});
assert.deepEqual(explicit.timestamps, [
  '2026-07-26T18:59:58.000Z',
  '2026-07-26T18:59:59.000Z',
]);
assert.deepEqual(explicit.timestampSources, ['explicit', 'explicit']);

const casing = await armoryCasingOperation({admin, user, args: {lastOnly: true, action: 'fired'}});
assert.equal(casing.count, 1);
assert.equal(casing.lastCasing.ammunition, '12 gauge');
assert.equal(casing.lastCasing.occurredAt, '2026-07-26T18:59:59.000Z');

const recount = await armoryRecountOperation({admin, user, args: {}});
assert.equal(recount.totalCasings, 4);
assert.deepEqual(
  recount.recount.map(({ammunition, count}) => ({ammunition, count})),
  [{ammunition: '12 gauge', count: 2}, {ammunition: '9mm', count: 2}],
);

await assert.rejects(
  () => armoryReceiptOperation({
    admin,
    user,
    now,
    args: {ammunition: '9mm', count: 2, timestamps: ['2026-07-26T18:30:00Z', 'bad'], requestId: 'armory-contract-003'},
  }),
  /timestamps\[1\]/,
);

console.log('Armory Range contract passed.');
