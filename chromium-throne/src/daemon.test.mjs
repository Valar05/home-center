import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import test from 'node:test';

async function waitFor(url, timeoutMs = 12000) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return response;
      last = new Error(`HTTP ${response.status}`);
    } catch (error) { last = error; }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw last || new Error(`Timed out waiting for ${url}`);
}

test('daemon exposes durable desktop/mobile contract without starting Chromium', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'chromium-throne-daemon-'));
  const port = 21000 + Math.floor(Math.random() * 10000);
  const child = spawn(process.execPath, ['src/throne.mjs'], {
    cwd: path.resolve(import.meta.dirname, '..'),
    env: {
      ...process.env,
      CHROMIUM_THRONE_HOME: root,
      CHROMIUM_THRONE_HTTP_PORT: String(port),
      CHROMIUM_THRONE_DEBUG_PORT: String(port + 1),
      CHROMIUM_THRONE_LISTEN_HOST: '127.0.0.1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  try {
    const health = await (await waitFor(`http://127.0.0.1:${port}/health`)).json();
    assert.equal(health.ok, true);
    assert.equal(health.contract, 'home-center.chromium-throne.v1');
    assert.equal(health.mobile, true);

    const snapshot = await (await fetch(`http://127.0.0.1:${port}/api/state`)).json();
    assert.equal(snapshot.mobile.enabled, true);
    assert.equal(snapshot.mobile.httpPort, port);
    assert.ok(Array.isArray(snapshot.tasks));

    const token = (await fs.readFile(path.join(root, 'mobile-token.txt'), 'utf8')).trim();
    assert.ok(token.length >= 32);
    const persisted = JSON.parse(await fs.readFile(path.join(root, 'state.json'), 'utf8'));
    assert.equal(persisted.mobile.enabled, true);
  } finally {
    child.kill('SIGTERM');
    await new Promise((resolve) => child.once('exit', resolve));
    await fs.rm(root, {recursive: true, force: true});
  }
});
