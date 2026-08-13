import { appendFile, mkdir, readFile, readdir, rename, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join } from 'node:path';

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function titleOf(text, fallback) {
  for (const line of String(text || '').split('\n')) {
    if (line.startsWith('#')) {
      const title = line.replace(/^#+\s*/, '').trim();
      if (title) return title;
    }
  }
  return fallback;
}

function catalogSha256(jars) {
  return sha256([...jars]
    .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id))
    .map(jar => `${jar.path}:${jar.sha256}`)
    .join('\n'));
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
    .map(line => {
      try { return JSON.parse(line); } catch { return null; }
    })
    .filter(Boolean);
}

export async function createJudgementJarService({ repoRoot, stateDir, emitReceipt }) {
  const configPath = join(repoRoot, 'config', 'judgement-jar-runtime.v1.json');
  const config = JSON.parse(await readFile(configPath, 'utf8'));
  const outputKinds = new Set(config.outputKinds || []);
  const receiptSchema = config.receipt?.schema || 'home-center.judgement-jar-usage-receipt.v1';
  const ruleDir = join(repoRoot, '.continue', 'rules');
  const catalogPath = join(stateDir, 'judgement-jars.json');
  const usagePath = join(stateDir, 'judgement-jar-usage.jsonl');
  const lastUsagePath = join(stateDir, 'judgement-jar-last-usage.json');
  await mkdir(stateDir, { recursive: true });

  async function discover({ includeText = false } = {}) {
    const entries = await readdir(ruleDir, { withFileTypes: true });
    const jars = [];
    for (const entry of entries) {
      const match = /^(\d+)-judgement-jar-(.+)\.md$/.exec(entry.name);
      if (!entry.isFile() || !match) continue;
      const path = join(ruleDir, entry.name);
      const raw = await readFile(path);
      const text = raw.toString('utf8');
      const jar = {
        id: match[2],
        order: Number(match[1]),
        title: titleOf(text, entry.name),
        path: `.continue/rules/${entry.name}`,
        filename: entry.name,
        sha256: sha256(raw),
        bytes: raw.length,
      };
      if (includeText) jar.text = text;
      jars.push(jar);
    }
    jars.sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
    return {
      schema: 'home-center.judgement-jar-catalog.v1',
      generatedAt: new Date().toISOString(),
      source: 'repository:.continue/rules/*judgement-jar*.md',
      count: jars.length,
      jars,
      catalogSha256: catalogSha256(jars),
    };
  }

  function resolveFrom(catalog, reference) {
    const needle = String(reference || '').trim().toLowerCase();
    if (!needle) return null;
    const exact = catalog.jars.filter(jar => [
      jar.id,
      String(jar.order),
      String(jar.order).padStart(2, '0'),
      jar.path,
      jar.filename,
      jar.title,
    ].some(value => String(value).toLowerCase() === needle));
    if (exact.length === 1) return exact[0];
    const prefix = catalog.jars.filter(jar => jar.id.toLowerCase().startsWith(needle) || jar.filename.toLowerCase().startsWith(needle));
    return prefix.length === 1 ? prefix[0] : null;
  }

  async function syncRepositoryCatalog(input = null) {
    const repository = await discover();
    if (input) {
      if (input.schema !== repository.schema || input.catalogSha256 !== repository.catalogSha256 || Number(input.count) !== repository.count) {
        return { ok: false, status: 409, error: 'CATALOG_SOURCE_MISMATCH', repository };
      }
    }
    await atomicJson(catalogPath, repository);
    const daemonReceipt = await emitReceipt('judgement.jar.catalog.synced', `Vlad cataloged ${repository.count} Judgment Jars.`, {
      state: 'delivered',
      catalogSha256: repository.catalogSha256,
      jarCount: repository.count,
    });
    return { ok: true, status: 200, state: 'DELIVERED', catalog: repository, receipt: daemonReceipt };
  }

  async function list() {
    const repository = await discover();
    if (!existsSync(catalogPath)) await atomicJson(catalogPath, repository);
    return repository;
  }

  async function get(reference) {
    const repository = await discover({ includeText: true });
    return resolveFrom(repository, reference);
  }

  async function recordUsage(input) {
    if (!input || input.schema !== receiptSchema) {
      return { ok: false, status: 400, error: 'INVALID_RECEIPT_SCHEMA' };
    }
    const receiptId = String(input.receiptId || '').trim();
    const outputKind = String(input.output?.kind || '').trim();
    if (!receiptId || !outputKinds.has(outputKind)) {
      return { ok: false, status: 400, error: 'RECEIPT_ID_AND_OUTPUT_KIND_REQUIRED', outputKinds: [...outputKinds].sort() };
    }
    const repository = await discover();
    const jar = resolveFrom(repository, input.jar?.path || input.jar?.id);
    if (!jar || jar.sha256 !== input.jar?.sha256) {
      return { ok: false, status: 409, error: 'JAR_SOURCE_MISMATCH', repositoryJar: jar };
    }
    const existing = await jsonLines(usagePath);
    const duplicate = existing.find(value => value.receiptId === receiptId);
    if (duplicate) return { ok: true, status: 200, state: 'DELIVERED', duplicate: true, receipt: duplicate };
    const delivered = {
      ...input,
      homeCenterDeliveryState: 'DELIVERED',
      deliveredAt: new Date().toISOString(),
      daemon: 'Atom',
    };
    await appendFile(usagePath, `${JSON.stringify(delivered)}\n`, 'utf8');
    await atomicJson(lastUsagePath, delivered);
    const daemonReceipt = await emitReceipt('judgement.jar.usage', `${jar.id} produced ${outputKind}.`, {
      state: 'delivered',
      usageReceiptId: receiptId,
      jarId: jar.id,
      jarPath: jar.path,
      jarSha256: jar.sha256,
      outputKind,
      outputStatus: input.output?.status || 'created',
      requestId: input.invocation?.requestId || null,
    });
    return { ok: true, status: 202, state: 'DELIVERED', duplicate: false, receipt: delivered, daemonReceipt };
  }

  async function status() {
    const current = await discover();
    const usages = await jsonLines(usagePath);
    return {
      loaded: true,
      state: 'deterministic',
      jarCount: current.count,
      catalogSha256: current.catalogSha256,
      usageReceiptCount: usages.length,
      outputKinds: [...outputKinds].sort(),
      catalogPath,
      usagePath,
    };
  }

  return { discover, get, list, recordUsage, status, syncRepositoryCatalog };
}
