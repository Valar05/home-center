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

test('Atom owns the phone command surface and fails closed', async t => {
  const stateDir = await mkdtemp(join(tmpdir(), 'atom-command-center-test-'));
  const port = 18000 + (process.pid % 1000);
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

  const status = await (await fetch(`${base}/v1/atom/status`)).json();
  assert.equal(status.ok, true);
  assert.equal(status.service, 'Atom');
  assert.equal(status.offlinePrepared, true);
  assert.equal(status.terminalRequired, false);

  const acceptedResponse = await fetch(`${base}/v1/atom/commands`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      clientCommandId: 'test-command-1',
      text: 'Repair Phone Hands and return a receipt.',
      humanInitiated: true,
      source: 'atom.contract-test',
    }),
  });
  assert.equal(acceptedResponse.status, 202);
  const accepted = await acceptedResponse.json();
  assert.equal(accepted.mission.state, 'QUEUED');
  assert.equal(accepted.receipt.kind, 'command.accepted');

  const rejected = await fetch(`${base}/v1/atom/commands`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ text: 'Caller forgot the human initiation fence.' }),
  });
  assert.equal(rejected.status, 400);

  const receipts = await (await fetch(`${base}/v1/atom/receipts`)).json();
  assert.ok(receipts.receipts.some(r => r.kind === 'command.accepted' && r.missionId === 'test-command-1'));

  const diagnostic = await (await fetch(`${base}/v1/atom/diagnose`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: '{}',
  })).json();
  assert.equal(diagnostic.kind, 'diagnostic');
  assert.equal(diagnostic.state, 'blocked');

  const manifest = JSON.parse(await readFile(join(atomRoot, 'addons', 'chromium-throne', 'manifest.json'), 'utf8'));
  assert.equal(manifest.host, 'Atom');
  assert.equal(manifest.terminalRequired, false);
  assert.equal(manifest.directChatgptOrchestration, false);

  const addon = await readFile(join(atomRoot, 'addons', 'chromium-throne', 'addon.mjs'), 'utf8');
  assert.equal(addon.includes('chatgpt.com'), false);
  assert.equal(addon.includes('input.type'), false);
  assert.equal(addon.includes('shell.exec'), false);
  assert.equal(stderr, '');
});
