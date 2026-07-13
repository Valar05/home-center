#!/usr/bin/env node
import assert from 'node:assert/strict';
import {copyFileSync, existsSync, chmodSync, mkdirSync, mkdtempSync, readFileSync, readdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {spawnSync} from 'node:child_process';

const ROOT = resolve(new URL('..', import.meta.url).pathname);
const PROBE = join(ROOT, 'tools/home_center_shizuku_setup_probe.sh');
const FAKES = join(ROOT, 'tools/install-harness/fakes/bin');

function stageFakes(name) {
  const bin = mkdtempSync(join(tmpdir(), `hc-install-${name}-fake-bin-`));
  for (const entry of readdirSync(FAKES)) {
    const src = join(FAKES, entry);
    const dst = join(bin, entry);
    copyFileSync(src, dst);
    chmodSync(dst, 0o755);
  }
  return bin;
}

function runProbe(name, args = [], extraEnv = {}) {
  const home = mkdtempSync(join(tmpdir(), `hc-install-${name}-home-`));
  const outDir = mkdtempSync(join(tmpdir(), `hc-install-${name}-out-`));
  const fakeBin = stageFakes(name);
  const report = join(outDir, 'readiness.json');
  const env = {
    ...process.env,
    HOME: home,
    PATH: `${fakeBin}:${process.env.PATH}`,
    RISH: join(fakeBin, 'rish'),
    HOME_CENTER_SHIZUKU_REPORT: report,
    HOME_CENTER_PAIRING_FAKE: '1',
    HOME_CENTER_CODEX_CONFIG: join(home, '.config/home-center/codex-hub.json'),
    HC_FAKE_MISSING_CODEX: '0',
    HC_FAKE_MISSING_TERMUX: '0',
    HC_FAKE_MISSING_SHIZUKU: '0',
    HC_FAKE_MISSING_RISH: '0',
    HC_FAKE_RISH_FAIL: '0',
    HC_FAKE_AM_FAIL: '0',
    ...extraEnv,
  };
  const result = spawnSync('sh', [PROBE, '--no-network-install', ...args], {
    cwd: ROOT,
    env,
    encoding: 'utf8',
    timeout: 30000,
  });
  assert.equal(result.status, 0, `${name} probe exited ${result.status}\nSTDOUT:\n${result.stdout}\nSTDERR:\n${result.stderr}`);
  assert.equal(existsSync(report), true, `${name} did not write ${report}`);
  const json = JSON.parse(readFileSync(report, 'utf8'));
  return {json, stdout: result.stdout, stderr: result.stderr, home};
}

function textArray(value) {
  assert.equal(Array.isArray(value), true);
  return value.join(' | ');
}

{
  const {json} = runProbe('ready', ['--report-only']);
  assert.equal(json.status, 'ready');
  assert.equal(json.termux.installed, true);
  assert.equal(json.termux.packages_ok, true);
  assert.equal(json.codex.installed, true);
  assert.equal(json.codex.package, '@mmmbuto/codex-cli-termux');
  assert.equal(json.shizuku.installed, true);
  assert.equal(json.rish.probe_ok, true);
  assert.equal(json.automation_probe.package_inspection_ok, true);
  assert.equal(json.pairing.attempted, false);
  assert.equal(json.human_actions_required.length, 0);
}

{
  const {json} = runProbe('missing-shizuku', ['--report-only'], {HC_FAKE_MISSING_SHIZUKU: '1'});
  assert.equal(json.status, 'partial');
  assert.equal(json.shizuku.installed, false);
  assert.match(textArray(json.human_actions_required), /Install Shizuku/);
}

{
  const {json} = runProbe('missing-rish', ['--report-only'], {HC_FAKE_MISSING_RISH: '1'});
  assert.equal(json.status, 'partial');
  assert.equal(json.rish.installed, false);
  assert.match(textArray(json.human_actions_required), /Export rish/);
}

{
  const {json} = runProbe('rish-fail', ['--report-only'], {HC_FAKE_RISH_FAIL: '1'});
  assert.equal(json.status, 'blocked');
  assert.equal(json.rish.installed, true);
  assert.equal(json.rish.probe_ok, false);
  assert.match(textArray(json.blockers), /rish exists but the harmless probe failed/);
}

{
  const {json} = runProbe('missing-codex', ['--report-only'], {HC_FAKE_MISSING_CODEX: '1'});
  assert.equal(json.status, 'partial');
  assert.equal(json.codex.installed, false);
  assert.match(textArray(json.human_actions_required), /Install Codex|Run Home Center Termux pairing/);
}

{
  const {json, home} = runProbe('auto-pair', ['--auto-pair']);
  assert.equal(json.status, 'ready');
  assert.equal(json.pairing.attempted, true);
  assert.equal(json.pairing.paired, true);
  assert.match(json.diagnostics.pair_log, /Paired Home Center through Shizuku/);
  assert.equal(existsSync(join(home, '.config/home-center/codex-hub.json')), true);
  assert.doesNotMatch(JSON.stringify(json), /123456|fakePairingIdForHarness|fake@example\.invalid|fake-access-token|fake-refresh-token/);
}

{
  const {json} = runProbe('auto-pair-am-fail', ['--auto-pair'], {HC_FAKE_AM_FAIL: '1'});
  assert.equal(json.status, 'ready');
  assert.equal(json.pairing.attempted, true);
  assert.equal(json.pairing.paired, false);
  assert.match(json.diagnostics.pair_log, /Shizuku launch failed|launch failed/);
  assert.doesNotMatch(JSON.stringify(json), /123456|fakePairingIdForHarness|fake@example\.invalid|fake-access-token|fake-refresh-token/);
}

console.log('Home Center install contract test: OK');
