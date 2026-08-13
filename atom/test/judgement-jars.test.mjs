import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
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

test('Atom gives Vlad fast exact Jar access and receipts every output kind', async t => {
  const stateDir = await mkdtemp(join(tmpdir(), 'atom-judgement-jars-test-'));
  const port = 19500 + (process.pid % 1000);
  const base = `http://127.0.0.1:${port}`;
  const child = spawn(process.execPath, [join(atomRoot, 'server.mjs')], {
    cwd: atomRoot,
    env: { ...process.env, ATOM_STATE_DIR: stateDir, ATOM_PORT: String(port) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stderr = '';
  child.stderr.on('data', chunk => { stderr += chunk; });
  t.after(async () => {
    await stopChild(child);
    await rm(stateDir, { recursive: true, force: true });
  });

  await waitFor(`${base}/v1/atom/status`);

  const listed = await (await fetch(`${base}/v1/atom/vlad/jars`)).json();
  assert.equal(listed.ok, true);
  assert.equal(listed.count, 8);
  assert.deepEqual(listed.jars.map(jar => jar.order), [0, 10, 20, 30, 40, 50, 70, 80]);
  assert.equal(listed.jars.some(jar => jar.path.includes('personality-gate')), false);
  assert.ok(listed.jars.every(jar => jar.sha256 && jar.path.startsWith('.continue/rules/')));

  const fetchedResponse = await fetch(`${base}/v1/atom/vlad/jars/mission-boundary`);
  assert.equal(fetchedResponse.status, 200);
  const fetched = await fetchedResponse.json();
  assert.equal(fetched.jar.id, 'mission-boundary');
  assert.match(fetched.jar.text, /Mission Boundary/i);
  assert.equal(fetched.usage.receipt.output.kind, 'context_packet');
  assert.equal(fetched.usage.state, 'DELIVERED');

  const invalidResponse = await fetch(`${base}/v1/atom/vlad/jars/receipts`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ schema: 'home-center.judgement-jar-usage-receipt.v1', receiptId: 'missing-output-kind' }),
  });
  assert.equal(invalidResponse.status, 400);

  const sourceJar = listed.jars.find(jar => jar.id === 'local-first');
  const validReceipt = {
    schema: 'home-center.judgement-jar-usage-receipt.v1',
    receiptId: 'atom-test-jar-usage-1',
    createdAt: new Date().toISOString(),
    createdAtEpochMs: Date.now(),
    captureState: 'CAPTURED',
    homeCenterDeliveryState: 'PENDING',
    jar: sourceJar,
    invocation: {
      source: 'atom.contract-test',
      requestId: 'atom-test-request-1',
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

  const syncResponse = await fetch(`${base}/v1/atom/vlad/jars/sync`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      schema: listed.schema,
      generatedAt: listed.generatedAt,
      source: listed.source,
      count: listed.count,
      jars: listed.jars,
      catalogSha256: listed.catalogSha256,
    }),
  });
  assert.equal(syncResponse.status, 200);
  assert.equal((await syncResponse.json()).state, 'DELIVERED');

  const status = await (await fetch(`${base}/v1/atom/status`)).json();
  assert.equal(status.vlad.judgementJars.jarCount, 8);
  assert.ok(status.vlad.judgementJars.usageReceiptCount >= 2);
  assert.ok(status.vlad.judgementJars.outputKinds.includes('review_verdict'));

  const receipts = await (await fetch(`${base}/v1/atom/receipts`)).json();
  assert.ok(receipts.receipts.some(value => value.kind === 'judgement.jar.usage' && value.outputKind === 'context_packet'));
  assert.ok(receipts.receipts.some(value => value.kind === 'judgement.jar.usage' && value.outputKind === 'plan'));

  const usageLines = (await readFile(join(stateDir, 'judgement-jar-usage.jsonl'), 'utf8')).trim().split('\n').map(JSON.parse);
  assert.equal(usageLines.filter(value => value.receiptId === 'atom-test-jar-usage-1').length, 1);
  assert.equal(stderr, '');
});
