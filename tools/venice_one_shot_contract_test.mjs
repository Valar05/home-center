#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');
const outer = read('tools/configure_venice_discord.ps1');
const inner = read('tools/configure_venice_discord_inner.ps1');
const nodeSource = read('tools/configure_venice_discord.mjs');
const deploy = read('tools/deploy_venice_discord.sh');
const functionsIndex = read('functions/index.js');
const ci = read('tools/home_center_ci_validate.sh');

assert.match(outer, /https:\/\/github\.com\/Valar05\/home-center\.git/);
assert.match(outer, /ls-remote --exit-code origin refs\/heads\/main/);
assert.match(outer, /HEAD to equal current origin\/main/);
assert.match(outer, /status --porcelain --untracked-files=all/);
assert.match(outer, /Get-FileHash[^\n]+SHA256/);
assert.match(outer, /EnvironmentVariables\.Clear\(\)/);
assert.match(outer, /configure_venice_discord_inner\.ps1/);
assert.match(outer, /secretProcessExited=\$true/);
assert.match(outer, /botTokenPersisted=\$false/);
assert.doesNotMatch(outer, /Read-Host/);
assert.doesNotMatch(outer, /Clipboard/i);

assert.match(inner, /Read-Host -AsSecureString/);
assert.match(inner, /clipboard use is prohibited/i);
assert.match(inner, /SecureStringToBSTR/);
assert.match(inner, /ZeroFreeBSTR/);
assert.match(inner, /StandardInput\.Write\(\$token\)/);
assert.match(inner, /StandardInput\.Close\(\)/);
assert.match(inner, /\$token = \$null/);
assert.match(inner, /EnvironmentVariables\.Clear\(\)/);
assert.doesNotMatch(inner, /Get-Clipboard|Set-Clipboard/i);
assert.doesNotMatch(inner, /gcloud|Secret Manager|secrets versions/i);

const guardIndex = nodeSource.indexOf('assertTrustedLaunch();');
const requireIndex = nodeSource.indexOf("require('../functions/venice_discord.js')");
assert.ok(guardIndex >= 0 && requireIndex > guardIndex, 'trusted-launch guard must run before repository code loads');
assert.match(nodeSource, /fs\.readFileSync\(0, 'utf8'\)/);
assert.match(nodeSource, /https:\/\/discord\.com\/api\/v10/);
assert.match(nodeSource, /DiscordBot \(https:\/\/github\.com\/Valar05\/home-center, 1\.0\)/);
assert.match(nodeSource, /interactions_endpoint_url: expectedEndpoint/);
assert.match(nodeSource, /botTokenPersisted: false/);
assert.match(nodeSource, /botToken = ''/);
assert.doesNotMatch(nodeSource, /gcloud|Secret Manager|secrets versions/i);

for (const source of [outer, inner, nodeSource]) {
  assert.doesNotMatch(source, /DISCORD_BOT_TOKEN/);
  assert.doesNotMatch(source, /secrets versions (?:access|add)/i);
}
assert.doesNotMatch(deploy, /DISCORD_BOT_TOKEN/);
assert.match(deploy, /gcloud secrets describe DISCORD_PUBLIC_KEY/);
assert.match(deploy, /roles\/datastore\.user/);
assert.match(functionsIndex, /defineSecret\('DISCORD_PUBLIC_KEY'\)/);
assert.doesNotMatch(functionsIndex, /defineSecret\('DISCORD_BOT_TOKEN'\)/);
assert.ok(ci.includes('node tools/venice_one_shot_contract_test.mjs'));
assert.ok(!ci.includes('venice_custody_contract_test.mjs'));

const refused = spawnSync(process.execPath, [path.join(root, 'tools/configure_venice_discord.mjs')], {
  cwd: root,
  encoding: 'utf8',
  timeout: 10_000,
});
assert.notEqual(refused.status, 0, 'direct Node launch must fail closed');
assert.match(refused.stderr, /Use tools\/configure_venice_discord\.ps1 from clean origin\/main/);
assert.doesNotMatch(refused.stdout + refused.stderr, /Authorization|Bot [A-Za-z0-9._-]{30,}/);

console.log(JSON.stringify({
  ok: true,
  flow: 'one-shot-stdin-only',
  cleanOriginMainRequired: true,
  clipboardProhibited: true,
  botTokenPersisted: false,
  runtimeBindsPublicKeyOnly: true,
}));
