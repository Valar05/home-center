import { appendFile, mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { dirname, join } from 'node:path';

function sha256(value) {
  return createHash('sha256').update(String(value ?? '')).digest('hex');
}

async function atomicJson(path, value) {
  await mkdir(dirname(path), { recursive: true });
  const temp = `${path}.tmp`;
  await writeFile(temp, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  await rename(temp, path);
}

async function jsonLines(path) {
  if (!existsSync(path)) return [];
  return (await readFile(path, 'utf8'))
    .split('\n')
    .filter(Boolean)
    .map(line => { try { return JSON.parse(line); } catch { return null; } })
    .filter(Boolean);
}

function normalize(value) {
  return String(value || '').trim().toLowerCase().replaceAll('judgement', 'judgment')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

function resolveJar(registry, reference) {
  const key = normalize(reference);
  const id = registry?.aliasIndex?.[key] || key;
  return (registry?.jars || []).find(jar => jar.id === id) || null;
}

function jarIdentity(registry, jar) {
  const keys = [
    'id', 'order', 'title', 'status', 'origin', 'sourceAuthority', 'sourceCompleteness',
    'sourcePath', 'sourceSha256', 'sourceFileId', 'sourceType', 'sourceUrl',
    'registryFileId', 'registrySection',
  ];
  const value = {};
  for (const key of keys) if (jar?.[key] !== undefined && jar?.[key] !== null && jar?.[key] !== '') value[key] = jar[key];
  return {
    ...value,
    registryDigest: registry?.registryDigest || '',
    registrySchema: registry?.schema || '',
    registrySourceCommit: registry?.sourceCommit || 'unknown',
  };
}

export async function createJudgmentJarReceiptService({ configPath, cachePath, stateDir, emitReceipt }) {
  const config = JSON.parse(await readFile(configPath, 'utf8'));
  const receiptConfig = config.receipts || {};
  const schema = receiptConfig.schema || 'home-center.judgment-jar-usage-receipt.v1';
  const outputKinds = new Set(receiptConfig.outputKinds || []);
  const usagePath = join(stateDir, 'judgment-jar-usage.jsonl');
  const lastUsagePath = join(stateDir, 'judgment-jar-last-usage.json');
  await mkdir(stateDir, { recursive: true });

  async function registry() {
    try {
      const value = JSON.parse(await readFile(cachePath, 'utf8'));
      return value?.schema === 'home-center.judgment-jars.registry.v2' ? value : null;
    } catch {
      return null;
    }
  }

  async function validate(input) {
    if (!input || input.schema !== schema) return { ok: false, status: 400, error: 'INVALID_RECEIPT_SCHEMA' };
    const receiptId = String(input.receiptId || '').trim();
    const outputKind = String(input.output?.kind || '').trim();
    if (!receiptId || !outputKinds.has(outputKind)) {
      return { ok: false, status: 400, error: 'RECEIPT_ID_AND_OUTPUT_KIND_REQUIRED', outputKinds: [...outputKinds].sort() };
    }
    const current = await registry();
    if (!current) return { ok: false, status: 503, error: 'JUDGMENT_JAR_CACHE_UNAVAILABLE', cachePath };
    const jar = resolveJar(current, input.jar?.id || input.jar?.sourcePath);
    if (!jar) return { ok: false, status: 409, error: 'JAR_NO_LONGER_RESOLVES' };
    const expected = jarIdentity(current, jar);
    const received = input.jar || {};
    for (const key of ['id', 'origin', 'sourcePath', 'sourceSha256', 'registryDigest']) {
      if (String(received[key] || '') !== String(expected[key] || '')) {
        return { ok: false, status: 409, error: 'JAR_SOURCE_MISMATCH', field: key, expected: expected[key], received: received[key] };
      }
    }
    return { ok: true, current, jar, expected, receiptId, outputKind };
  }

  async function record(input) {
    const checked = await validate(input);
    if (!checked.ok) return checked;
    const existing = (await jsonLines(usagePath)).find(value => value.receiptId === checked.receiptId);
    if (existing) return { ok: true, status: 200, state: 'DELIVERED', duplicate: true, receipt: existing };
    const delivered = {
      ...input,
      homeCenterDeliveryState: 'DELIVERED',
      deliveredAt: new Date().toISOString(),
      daemon: 'Atom',
    };
    await appendFile(usagePath, `${JSON.stringify(delivered)}\n`, 'utf8');
    await atomicJson(lastUsagePath, delivered);
    const daemonReceipt = await emitReceipt('judgment.jar.usage', `${checked.jar.id} produced ${checked.outputKind}.`, {
      state: 'delivered',
      usageReceiptId: checked.receiptId,
      jarId: checked.jar.id,
      jarOrigin: checked.jar.origin,
      jarSourcePath: checked.jar.sourcePath,
      jarSourceSha256: checked.jar.sourceSha256,
      registryDigest: checked.current.registryDigest,
      outputKind: checked.outputKind,
      outputStatus: input.output?.status || 'created',
      requestId: input.invocation?.requestId || null,
    });
    return { ok: true, status: 202, state: 'DELIVERED', duplicate: false, receipt: delivered, daemonReceipt };
  }

  async function recordContextAccess(current, jar, source, inputText, outputText) {
    const now = Date.now();
    return record({
      schema,
      receiptId: randomUUID(),
      createdAt: new Date(now).toISOString(),
      createdAtEpochMs: now,
      captureState: 'CAPTURED',
      homeCenterDeliveryState: 'PENDING',
      jar: jarIdentity(current, jar),
      invocation: {
        source,
        requestId: randomUUID(),
        groupId: randomUUID(),
        inputSha256: sha256(inputText),
        inputBytes: Buffer.byteLength(String(inputText || '')),
      },
      output: {
        kind: 'context_packet',
        status: 'created',
        summary: `Atom loaded Judgment Jar context: ${jar.title}`,
        sha256: sha256(outputText),
        bytes: Buffer.byteLength(String(outputText || '')),
        references: [jar.sourcePath].filter(Boolean),
      },
      nativeSource: null,
      metadata: { access: 'atom-fast-path' },
    });
  }

  async function status() {
    const current = await registry();
    const values = await jsonLines(usagePath);
    return {
      loaded: true,
      state: 'deterministic',
      schema,
      outputKinds: [...outputKinds].sort(),
      usageReceiptCount: values.length,
      lastUsageReceiptId: values.at(-1)?.receiptId || null,
      registryDigest: current?.registryDigest || null,
      cachePath,
      usagePath,
    };
  }

  return { jarIdentity, record, recordContextAccess, registry, resolveJar, status };
}
