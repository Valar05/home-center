'use strict';

/**
 * Home Center side of the Judgment Jar contract.
 *
 * The service is deliberately adapter-driven. Home Center remains the only source
 * owner; Vlad receives a complete, checksum-bound snapshot and may return closed
 * invocation receipts. No caller may mutate jar source truth through this module.
 */

const crypto = require('node:crypto');

const SCHEMA_VERSION = 1;
const OUTPUT_KINDS = new Set([
  'verdict',
  'plan_review',
  'completion_review',
  'canon_review',
  'rewrite',
  'research_review',
  'risk_review',
  'routing_decision',
  'other',
]);

function canonicalJson(value) {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(',')}]`;
  }
  if (value && typeof value === 'object') {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`)
      .join(',')}}`;
  }
  return JSON.stringify(value);
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function normalizeAlias(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function firstText(record, keys) {
  for (const key of keys) {
    const value = record[key];
    if (value !== undefined && value !== null && String(value).trim()) {
      return String(value).trim();
    }
  }
  return '';
}

function normalizeJar(record) {
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    throw new TypeError('Judgment Jar source record must be an object');
  }
  const title = firstText(record, ['title', 'name', 'display_name']);
  let jarId = firstText(record, ['jar_id', 'id', 'canonical_id', 'slug']);
  if (!jarId && title) {
    jarId = normalizeAlias(title).replace(/ /g, '-');
  }
  if (!jarId) {
    throw new Error('Judgment Jar source record requires jar_id/id or title/name');
  }

  const rawAliases = record.aliases === undefined ? [] : record.aliases;
  const aliases = Array.isArray(rawAliases) ? rawAliases : [rawAliases];
  const aliasMap = new Map();
  for (const alias of [title || jarId, jarId, ...aliases]) {
    const display = String(alias || '').trim();
    const normalized = normalizeAlias(display);
    if (normalized && !aliasMap.has(normalized)) {
      aliasMap.set(normalized, display);
    }
  }

  const normalized = {
    jar_id: jarId,
    title: title || jarId,
    aliases: [...aliasMap.values()],
    jurisdiction: firstText(record, ['jurisdiction', 'criterion', 'purpose', 'role']),
    body: firstText(record, ['body', 'prompt', 'content', 'material', 'text']),
    source_ref: firstText(record, ['source_ref', 'source_url', 'document_id', 'file_id']),
    source_revision: firstText(record, [
      'source_revision',
      'revision',
      'revision_id',
      'version',
    ]),
    status: firstText(record, ['status']) || 'active',
    source_updated_at: firstText(record, [
      'source_updated_at',
      'updated_at',
      'modified_at',
      'observed_at',
    ]),
  };
  normalized.content_sha256 =
    firstText(record, ['content_sha256', 'sha256']) || sha256(canonicalJson(normalized));
  return normalized;
}

function validateAliasUniqueness(jars) {
  const aliases = new Map();
  for (const jar of jars) {
    for (const alias of jar.aliases) {
      const normalized = normalizeAlias(alias);
      const existing = aliases.get(normalized);
      if (existing && existing !== jar.jar_id) {
        throw new Error(
          `Judgment Jar alias collision: ${JSON.stringify(alias)} belongs to ${existing} and ${jar.jar_id}`,
        );
      }
      aliases.set(normalized, jar.jar_id);
    }
  }
}

function compileSnapshot(sourceRecords, options = {}) {
  if (!Array.isArray(sourceRecords)) {
    throw new TypeError('sourceRecords must be an array');
  }
  const jars = sourceRecords.map(normalizeJar).sort((a, b) =>
    a.jar_id.localeCompare(b.jar_id),
  );
  const ids = new Set();
  for (const jar of jars) {
    if (ids.has(jar.jar_id)) {
      throw new Error(`Duplicate Judgment Jar id: ${jar.jar_id}`);
    }
    ids.add(jar.jar_id);
  }
  validateAliasUniqueness(jars);

  const stableMaterial = {
    schema_version: SCHEMA_VERSION,
    source: options.source || 'home-center',
    complete: options.complete !== false,
    jars,
  };
  return {
    ...stableMaterial,
    observed_at: options.observedAt || new Date().toISOString(),
    snapshot_sha256: sha256(canonicalJson(stableMaterial)),
  };
}

function validateReceipt(receipt) {
  if (!receipt || typeof receipt !== 'object' || Array.isArray(receipt)) {
    throw new TypeError('Receipt must be an object');
  }
  const required = [
    'receipt_id',
    'jar_id',
    'jar_revision',
    'request_id',
    'worker',
    'input_sha256',
    'opened_at',
    'output_kind',
    'output_sha256',
    'status',
    'closed_at',
  ];
  for (const field of required) {
    if (receipt[field] === undefined || receipt[field] === null || String(receipt[field]) === '') {
      throw new Error(`Receipt is missing ${field}`);
    }
  }
  if (!OUTPUT_KINDS.has(receipt.output_kind)) {
    throw new Error(`Unsupported Judgment Jar output_kind: ${receipt.output_kind}`);
  }
  if (!['completed', 'failed', 'rejected', 'blocked'].includes(receipt.status)) {
    throw new Error(`Unsupported Judgment Jar receipt status: ${receipt.status}`);
  }
  for (const field of ['input_sha256', 'output_sha256']) {
    if (!/^[0-9a-f]{64}$/i.test(receipt[field])) {
      throw new Error(`${field} must be a SHA-256 hex digest`);
    }
  }
  return {
    schema_version: SCHEMA_VERSION,
    receipt_id: String(receipt.receipt_id),
    jar_id: String(receipt.jar_id),
    jar_revision: String(receipt.jar_revision),
    request_id: String(receipt.request_id),
    worker: String(receipt.worker),
    campaign: String(receipt.campaign || ''),
    input_sha256: String(receipt.input_sha256).toLowerCase(),
    opened_at: String(receipt.opened_at),
    output_kind: String(receipt.output_kind),
    output_ref: String(receipt.output_ref || ''),
    output_sha256: String(receipt.output_sha256).toLowerCase(),
    status: String(receipt.status),
    closed_at: String(receipt.closed_at),
  };
}

/**
 * Create the two daemon operations from explicit Home Center adapters.
 *
 * source.listAllJudgmentJars() must return every active/non-deleted source record.
 * receiptStore.has(id), receiptStore.append(record), and optionally
 * receiptStore.read(id) provide append-only idempotent storage.
 */
function createJudgmentJarRegistry({ source, receiptStore, clock = () => new Date() }) {
  if (!source || typeof source.listAllJudgmentJars !== 'function') {
    throw new TypeError('source.listAllJudgmentJars adapter is required');
  }
  if (
    !receiptStore ||
    typeof receiptStore.has !== 'function' ||
    typeof receiptStore.append !== 'function'
  ) {
    throw new TypeError('append-only receiptStore adapter is required');
  }

  return {
    async snapshot() {
      const records = await source.listAllJudgmentJars();
      return compileSnapshot(records, {
        source: 'home-center',
        complete: true,
        observedAt: clock().toISOString(),
      });
    },

    async ingestReceipts(envelope) {
      if (!envelope || envelope.schema_version !== SCHEMA_VERSION) {
        throw new Error(`Receipt envelope schema_version must be ${SCHEMA_VERSION}`);
      }
      if (!Array.isArray(envelope.receipts)) {
        throw new Error('Receipt envelope requires receipts array');
      }
      const accepted = [];
      const duplicates = [];
      for (const rawReceipt of envelope.receipts) {
        const receipt = validateReceipt(rawReceipt);
        if (await receiptStore.has(receipt.receipt_id)) {
          duplicates.push(receipt.receipt_id);
          continue;
        }
        const stored = {
          ...receipt,
          source: envelope.source || 'vlad',
          ingested_at: clock().toISOString(),
          receipt_sha256: sha256(canonicalJson(receipt)),
        };
        await receiptStore.append(stored);
        accepted.push(receipt.receipt_id);
      }
      return {
        schema_version: SCHEMA_VERSION,
        accepted,
        duplicates,
        received: envelope.receipts.length,
      };
    },
  };
}

module.exports = {
  OUTPUT_KINDS,
  SCHEMA_VERSION,
  canonicalJson,
  compileSnapshot,
  createJudgmentJarRegistry,
  normalizeAlias,
  normalizeJar,
  sha256,
  validateReceipt,
};
