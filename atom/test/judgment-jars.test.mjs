import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const atomRoot = dirname(here);

async function waitFor(url, timeoutMs = 8000) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return response;
      last = new Error(`HTTP ${response.status}`);
    } catch (error) {
      last = error;
    }
    await new Promise(resolve => setTimeout(resolve, 80));
  }
  throw last || new Error('Atom did not become ready');
}

async function stopChild(child) {
  if (child.exitCode !== null) return;
  const exited = new Promise(resolve => child.once('exit', resolve));
  child.kill();
  await Promise.race([exited, new Promise(resolve => setTimeout(resolve, 2000))]);
  if (child.exitCode === null) child.kill('SIGKILL');
}

function registryFixture() {
  const jars = [
    {
      id: 'mission-boundary',
      order: 0,
      title: 'Judgement Jar: Mission Boundary',
      status: 'active',
      scope: 'all work',
      judgment: 'Preserve the commissioned mission.',
      origin: 'repository-operational-core',
      sourceAuthority: 'repository',
      sourceCompleteness: 'full-body',
      sourcePath: '.continue/rules/00-judgement-jar-mission-boundary.md',
      sourceSha256: 'local-sha',
      aliases: ['judgment jar mission boundary'],
      body: '# Judgement Jar: Mission Boundary\n\nPreserve the mission.\n',
    },
    {
      id: 'vlad-the-adversary-keeps-the-edge',
      order: 10010,
      title: 'Vlad — The Adversary Keeps the Edge',
      status: 'active',
      judgment: 'Does this survive scarcity and process death?',
      compactLaw: 'Make it fit. Make it survive. Record the scar.',
      origin: 'home-center-cabinet',
      sourceAuthority: 'home-center-drive',
      sourceCompleteness: 'registry-summary',
      sourcePath: 'home-center://drive/vlad-sheet',
      sourceSha256: 'cabinet-sha',
      sourceFileId: 'vlad-sheet',
      sourceType: 'application/vnd.google-apps.spreadsheet',
      sourceUrl: 'https://docs.google.com/spreadsheets/d/vlad-sheet/edit',
      aliases: ['vlad judgment jar'],
      body: 'Vlad — The Adversary Keeps the Edge\nJudgment: Does this survive scarcity and process death?\n',
    },
    {
      id: 'android-67-judgment-jar-keep',
      order: 20010,
      title: 'ANDROID 67 — Judgment Jar — KEEP',
      status: 'unregistered',
      origin: 'home-center-discovery',
      sourceAuthority: 'home-center-drive-search',
      sourceCompleteness: 'metadata-only',
      sourcePath: 'home-center://drive/android67-sheet',
      sourceSha256: 'discovery-sha',
      sourceFileId: 'android67-sheet',
      sourceType: 'application/vnd.google-apps.spreadsheet',
      aliases: ['android 67 judgment jar keep'],
      body: '',
    },
  ];
  return {
    schema: 'home-center.judgment-jars.registry.v2',
    complete: true,
    jarCount: 3,
    localJarCount: 1,
    cabinetJarCount: 1,
    unregisteredJarCount: 1,
    activeJarIds: jars.filter(jar => jar.status === 'active').map(jar => jar.id),
    registryDigest: 'fixture-digest-v2',
    sourceCommit: 'fixture-commit',
    repositorySourcePattern: '.continue/rules/*judgement-jar*.md',
    aliasIndex: {
      'mission-boundary': 'mission-boundary',
      'judgment-jar-mission-boundary': 'mission-boundary',
      'vlad-judgment-jar': 'vlad-the-adversary-keeps-the-edge',
      'android-67-judgment-jar-keep': 'android-67-judgment-jar-keep',
    },
    homeCenter: {
      state: 'synced',
      registryFileId: 'registry-doc',
      registryTextSha256: 'registry-sha',
      lastSuccessEpoch: 1770000000,
      lastError: '',
      missingExecutableFunctions: ['Wardaddy', 'Quartermaster'],
    },
    jars,
  };
}

test('Atom exposes Vlad fast access and receipts every Judgment Jar output', async t => {
  const stateDir = await mkdtemp(join(tmpdir(), 'atom-vlad-jars-test-'));
  const atomState = join(stateDir, 'atom');
  const cachePath = join(stateDir, 'judgment-jars.json');
  const fixture = registryFixture();
  await writeFile(cachePath, JSON.stringify(fixture, null, 2));
  const port = 19000 + (process.pid % 1000);
  const base = `http://127.0.0.1:${port}`;
  const child = spawn(process.execPath, [join(atomRoot, 'server.mjs')], {
    cwd: atomRoot,
    env: {
      ...process.env,
      ATOM_STATE_DIR: atomState,
      ATOM_PORT: String(port),
      HC_JUDGMENT_JARS_CACHE: cachePath,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stderr = '';
  child.stderr.on('data', chunk => { stderr += chunk; });
  t.after(async () => {
    await stopChild(child);
    await rm(stateDir, { recursive: true, force: true });
  });

  await waitFor(`${base}/v1/atom/status`);
  const status = await (await fetch(`${base}/v1/atom/status`)).json();
  assert.equal(status.vlad.judgmentJars.loaded, true);
  assert.equal(status.vlad.judgmentJars.complete, true);
  assert.equal(status.vlad.judgmentJars.state, 'synced');
  assert.equal(status.vlad.judgmentJars.jarCount, 3);
  assert.equal(status.vlad.judgmentJars.localJarCount, 1);
  assert.equal(status.vlad.judgmentJars.cabinetJarCount, 1);
  assert.equal(status.vlad.judgmentJars.unregisteredJarCount, 1);
  assert.equal(status.vlad.judgmentJars.homeCenterState, 'synced');
  assert.deepEqual(status.vlad.judgmentJars.missingExecutableFunctions, ['Wardaddy', 'Quartermaster']);
  assert.equal(status.vlad.judgmentJarReceipts.loaded, true);
  assert.ok(status.vlad.judgmentJarReceipts.outputKinds.includes('review_verdict'));

  const list = await (await fetch(`${base}/v1/atom/vlad/jars`)).json();
  assert.equal(list.ok, true);
  assert.equal(list.jars.length, 3);
  assert.equal(list.jars.find(jar => jar.id === 'vlad-the-adversary-keeps-the-edge').sourceCompleteness, 'registry-summary');
  assert.equal(list.jars.find(jar => jar.id === 'android-67-judgment-jar-keep').status, 'unregistered');

  const one = await (await fetch(`${base}/v1/atom/vlad/jars?id=judgement%20jar%20mission%20boundary`)).json();
  assert.equal(one.ok, true);
  assert.equal(one.jar.id, 'mission-boundary');
  assert.match(one.jar.body, /Preserve the mission/);
  assert.equal(one.usage.state, 'DELIVERED');
  assert.equal(one.usage.receipt.output.kind, 'context_packet');
  assert.equal(one.usage.receipt.jar.sourceSha256, 'local-sha');

  const search = await (await fetch(`${base}/v1/atom/vlad/jars?q=scarcity%20restart`)).json();
  assert.equal(search.ok, true);
  assert.equal(search.matches[0].id, 'vlad-the-adversary-keeps-the-edge');
  assert.equal(search.matches[0].sourceFileId, 'vlad-sheet');

  const invalid = await fetch(`${base}/v1/atom/vlad/jars/receipts`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ schema: 'home-center.judgment-jar-usage-receipt.v1', receiptId: 'missing-output-kind' }),
  });
  assert.equal(invalid.status, 400);

  const local = fixture.jars[0];
  const validReceipt = {
    schema: 'home-center.judgment-jar-usage-receipt.v1',
    receiptId: 'atom-test-jar-usage-1',
    createdAt: new Date().toISOString(),
    createdAtEpochMs: Date.now(),
    captureState: 'CAPTURED',
    homeCenterDeliveryState: 'PENDING',
    jar: {
      id: local.id,
      origin: local.origin,
      sourcePath: local.sourcePath,
      sourceSha256: local.sourceSha256,
      registryDigest: fixture.registryDigest,
    },
    invocation: {
      source: 'atom.contract-test',
      requestId: 'atom-test-request-1',
      groupId: 'atom-test-request-1',
      inputSha256: 'a'.repeat(64),
      inputBytes: 12,
    },
    output: {
      kind: 'plan',
      status: 'created',
      summary: 'Produced a bounded plan.',
      sha256: 'b'.repeat(64),
      bytes: 20,
      references: ['receipt://plan'],
    },
    nativeSource: null,
    metadata: {},
  };
  const acceptedResponse = await fetch(`${base}/v1/atom/vlad/jars/receipts`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(validReceipt),
  });
  assert.equal(acceptedResponse.status, 202);
  const accepted = await acceptedResponse.json();
  assert.equal(accepted.state, 'DELIVERED');
  assert.equal(accepted.receipt.output.kind, 'plan');
  assert.equal(accepted.receipt.homeCenterDeliveryState, 'DELIVERED');

  const duplicateResponse = await fetch(`${base}/v1/atom/vlad/jars/receipts`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(validReceipt),
  });
  assert.equal(duplicateResponse.status, 200);
  assert.equal((await duplicateResponse.json()).duplicate, true);

  const receiptStatus = await (await fetch(`${base}/v1/atom/vlad/jars/receipts/status`)).json();
  assert.equal(receiptStatus.ok, true);
  assert.equal(receiptStatus.usage.usageReceiptCount, 2);
  assert.ok(receiptStatus.usage.outputKinds.includes('plan'));

  const receipts = await (await fetch(`${base}/v1/atom/receipts`)).json();
  assert.ok(receipts.receipts.some(value => value.kind === 'judgment.jar.usage' && value.outputKind === 'context_packet'));
  assert.ok(receipts.receipts.some(value => value.kind === 'judgment.jar.usage' && value.outputKind === 'plan'));

  const usageLines = (await readFile(join(atomState, 'judgment-jar-usage.jsonl'), 'utf8')).trim().split('\n').map(JSON.parse);
  assert.equal(usageLines.filter(value => value.receiptId === 'atom-test-jar-usage-1').length, 1);
  assert.equal(stderr, '');
});
