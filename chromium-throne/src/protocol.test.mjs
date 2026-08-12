import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {commandIsDangerous, executeAction, extractAction, resolveInside, workerInstruction} from './protocol.mjs';

test('extractAction reads the last well-formed throne envelope', () => {
  const action = extractAction('x <THRONE_ACTION>{"type":"read_file","path":"README.md"}</THRONE_ACTION>');
  assert.deepEqual(action, {type: 'read_file', path: 'README.md'});
});

test('resolveInside rejects traversal', () => {
  const root = path.resolve('/tmp/project');
  assert.throws(() => resolveInside(root, '../outside'), /escapes repository root/);
});

test('dangerous host commands are blocked', () => {
  assert.equal(commandIsDangerous('shutdown /s /t 0'), true);
  assert.equal(commandIsDangerous('npm test'), false);
});

test('read, write, list, shell and finish actions work inside a repository', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'throne-test-'));
  try {
    let result = await executeAction(root, {type: 'write_file', path: 'src/a.txt', content: 'hello'});
    assert.equal(result.readback, 'matched');
    result = await executeAction(root, {type: 'read_file', path: 'src/a.txt'});
    assert.equal(result.output, 'hello');
    result = await executeAction(root, {type: 'list_files', path: '.', depth: 3});
    assert.match(result.output, /src/);
    const command = process.platform === 'win32' ? 'node -e "process.stdout.write(\'ok\')"' : "node -e \"process.stdout.write('ok')\"";
    result = await executeAction(root, {type: 'shell', command});
    assert.equal(result.code, 0);
    assert.equal(result.stdout, 'ok');
    result = await executeAction(root, {type: 'finish', summary: 'done'});
    assert.equal(result.finished, true);
  } finally {
    await fs.rm(root, {recursive: true, force: true});
  }
});

test('worker instruction requires inspection, execution, verification and one action', () => {
  const text = workerInstruction({task: 'Build it', repoRoot: 'C:\\repo'});
  assert.match(text, /Inspect before editing/i);
  assert.match(text, /tests or direct verification/i);
  assert.match(text, /exactly one machine action/i);
});
