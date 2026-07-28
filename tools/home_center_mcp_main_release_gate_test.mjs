#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const sourceGate = fileURLToPath(new URL('assert_home_center_mcp_main_release.sh', import.meta.url));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'home-center-main-gate-'));
const remote = path.join(tmp, 'remote.git');
const repo = path.join(tmp, 'repo');

function run(command, args, cwd = tmp, env = {}) {
  return spawnSync(command, args, {cwd, encoding: 'utf8', env: {...process.env, ...env}});
}
function ok(command, args, cwd = tmp) {
  const result = run(command, args, cwd);
  assert.equal(result.status, 0, result.stderr || result.stdout);
  return result;
}
function gate(env = {}) {
  return run('sh', ['tools/assert_home_center_mcp_main_release.sh', repo], repo, env);
}

ok('git', ['init', '--bare', remote]);
ok('git', ['clone', remote, repo]);
ok('git', ['config', 'user.name', 'Home Center Gate Test'], repo);
ok('git', ['config', 'user.email', 'gate@example.invalid'], repo);
fs.mkdirSync(path.join(repo, 'tools'), {recursive: true});
fs.copyFileSync(sourceGate, path.join(repo, 'tools/assert_home_center_mcp_main_release.sh'));
fs.writeFileSync(path.join(repo, 'tracked.txt'), 'main\n');
ok('git', ['add', '.'], repo);
ok('git', ['commit', '-m', 'main fixture'], repo);
ok('git', ['branch', '-M', 'main'], repo);
ok('git', ['push', '-u', 'origin', 'main'], repo);

let result = gate();
assert.equal(result.status, 0, result.stderr);
assert.match(result.stdout, /verified origin\/main/);

ok('git', ['switch', '-c', 'feature'], repo);
result = gate();
assert.equal(result.status, 23);
assert.match(result.stderr, /source must be branch main/);

ok('git', ['switch', 'main'], repo);
fs.writeFileSync(path.join(repo, 'untracked.txt'), 'dirty\n');
result = gate();
assert.equal(result.status, 23);
assert.match(result.stderr, /working tree is not clean/);
fs.rmSync(path.join(repo, 'untracked.txt'));

fs.writeFileSync(path.join(repo, 'tracked.txt'), 'ahead\n');
ok('git', ['add', 'tracked.txt'], repo);
ok('git', ['commit', '-m', 'local ahead'], repo);
result = gate();
assert.equal(result.status, 23);
assert.match(result.stderr, /is not the current origin\/main commit/);

ok('git', ['reset', '--hard', 'origin/main'], repo);
const head = ok('git', ['rev-parse', 'HEAD'], repo).stdout.trim();
ok('git', ['checkout', '--detach', head], repo);
result = gate({GITHUB_ACTIONS: 'true', GITHUB_REF: 'refs/heads/main', GITHUB_SHA: head});
assert.equal(result.status, 0, result.stderr);

result = gate({GITHUB_ACTIONS: 'true', GITHUB_REF: 'refs/pull/121/merge', GITHUB_SHA: head});
assert.equal(result.status, 23);
assert.match(result.stderr, /source must be branch main/);

fs.rmSync(tmp, {recursive: true, force: true});
console.log('Home Center main-only MCP release gate: OK');
