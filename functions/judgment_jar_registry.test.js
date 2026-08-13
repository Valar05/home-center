'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  compileSnapshot,
  createJudgmentJarRegistry,
  normalizeJar,
  validateReceipt,
} = require('./judgment_jar_registry');

const records = [
  {
    jar_id: 'venice',
    title: 'Venice',
    aliases: ['Ven', 'Portcullis'],
    jurisdiction: 'taste and autonomy',
    body: 'Return an independent verdict.',
    source_ref: 'drive:venice',
    source_revision: 'rev-7',
    status: 'active',
  },
  {
    jar_id: 'saint-andrew',
    title: 'Saint Andrew',
    aliases: ['St Andrew'],
    jurisdiction: 'unconstrained invention',
    body: 'Ask what the work becomes when allowed to continue.',
    source_ref: 'drive:andrew',
    source_revision: 'rev-2',
    status: 'active',
  },
];

function validReceipt(overrides = {}) {
  return {
    receipt_id: 'receipt-1',
    jar_id: 'venice',
    jar_revision: 'rev-7',
    request_id: 'request-1',
    worker: 'vlad',
    campaign: 'fortress',
    input_sha256: 'a'.repeat(64),
    opened_at: '2026-08-13T10:00:00Z',
    output_kind: 'plan_review',
    output_ref: 'drive:review-1',
    output_sha256: 'b'.repeat(64),
    status: 'completed',
    closed_at: '2026-08-13T10:01:00Z',
    ...overrides,
  };
}

test('normalizeJar creates stable aliases and checksum', () => {
  const jar = normalizeJar(records[0]);
  assert.equal(jar.jar_id, 'venice');
  assert.deepEqual(jar.aliases, ['Venice', 'venice', 'Ven', 'Portcullis']);
  assert.match(jar.content_sha256, /^[0-9a-f]{64}$/);
});

test('compileSnapshot is complete, deterministic, and sorted', () => {
  const first = compileSnapshot(records.slice().reverse(), {
    source: 'home-center',
    observedAt: '2026-08-13T10:00:00Z',
  });
  const second = compileSnapshot(records, {
    source: 'home-center',
    observedAt: '2026-08-13T11:00:00Z',
  });
  assert.equal(first.complete, true);
  assert.deepEqual(
    first.jars.map((jar) => jar.jar_id),
    ['saint-andrew', 'venice'],
  );
  assert.equal(first.snapshot_sha256, second.snapshot_sha256);
  assert.notEqual(first.observed_at, second.observed_at);
});

test('compileSnapshot rejects alias collisions', () => {
  assert.throws(
    () =>
      compileSnapshot([
        records[0],
        { jar_id: 'other', title: 'Other', aliases: ['Ven'] },
      ]),
    /alias collision/i,
  );
});

test('validateReceipt requires terminal output identity', () => {
  assert.equal(validateReceipt(validReceipt()).output_kind, 'plan_review');
  assert.throws(
    () => validateReceipt(validReceipt({ output_kind: 'mystery' })),
    /Unsupported Judgment Jar output_kind/,
  );
  assert.throws(
    () => validateReceipt(validReceipt({ output_sha256: '' })),
    /missing output_sha256/,
  );
});

test('registry exports all jars and ingests receipts idempotently', async () => {
  const stored = new Map();
  const registry = createJudgmentJarRegistry({
    source: {
      async listAllJudgmentJars() {
        return records;
      },
    },
    receiptStore: {
      async has(id) {
        return stored.has(id);
      },
      async append(receipt) {
        stored.set(receipt.receipt_id, receipt);
      },
    },
    clock: () => new Date('2026-08-13T12:00:00Z'),
  });

  const snapshot = await registry.snapshot();
  assert.equal(snapshot.jars.length, 2);
  assert.equal(snapshot.source, 'home-center');

  const envelope = {
    schema_version: 1,
    source: 'vlad',
    receipts: [validReceipt()],
  };
  const first = await registry.ingestReceipts(envelope);
  const second = await registry.ingestReceipts(envelope);
  assert.deepEqual(first.accepted, ['receipt-1']);
  assert.deepEqual(second.duplicates, ['receipt-1']);
  assert.equal(stored.size, 1);
  assert.equal(stored.get('receipt-1').source, 'vlad');
  assert.match(stored.get('receipt-1').receipt_sha256, /^[0-9a-f]{64}$/);
});
