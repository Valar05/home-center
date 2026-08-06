#!/usr/bin/env node
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');
const normalized = (relative) => read(relative).replaceAll('\r\n', '\n');
const hash = (relative) => crypto.createHash('sha256').update(normalized(relative)).digest('hex');
const outer = read('tools/configure_venice_discord.ps1');
const trustBody = read('tools/configure_venice_discord_trusted.ps1');
const inner = read('tools/configure_venice_discord_inner.ps1');
const nodeSource = read('tools/configure_venice_discord.mjs');
const discordContractSource = read('functions/venice_discord_contract.json');
const deploy = read('tools/deploy_venice_discord.sh');
const functionsIndex = read('functions/index.js');
const ci = read('tools/home_center_ci_validate.sh');

assert.match(outer, /configure_venice_discord_trusted\.ps1/);
assert.match(outer, /ExpectedPowerShellSha256/);
assert.match(outer, /ExpectedTrustBodySha256/);
assert.match(outer, /IO\.File\]::ReadAllBytes\(\$ExpectedPowerShell\)/);
assert.match(outer, /-NoLogo -NoProfile -ExecutionPolicy Bypass -OutputFormat Text -EncodedCommand/);
assert.match(outer, /EnvironmentVariables\.Clear\(\)/);
assert.match(outer, /VENICE_REPO_ROOT/);
assert.doesNotMatch(outer, /VENICE_TRUSTED_POWERSHELL_BOOTSTRAP/);
assert.doesNotMatch(outer, /-File /);
assert.doesNotMatch(outer, /Read-Host|Clipboard/i);

assert.match(trustBody, /https:\/\/github\.com\/Valar05\/home-center\.git/);
assert.match(trustBody, /MainModule\.FileName/);
assert.match(trustBody, /ExpectedRemoteHttpsSha256/);
assert.match(trustBody, /GIT_CONFIG_NOSYSTEM = '1'/);
assert.match(trustBody, /GIT_CONFIG_GLOBAL = 'NUL'/);
assert.match(trustBody, /GIT_TERMINAL_PROMPT = '0'/);
assert.match(trustBody, /core\.fsmonitor=false/);
assert.match(trustBody, /core\.hooksPath=NUL/);
assert.match(trustBody, /credential\.helper=/);
assert.match(trustBody, /credential\.helper=manager/);
assert.match(trustBody, /http\.sslBackend=schannel/);
assert.match(trustBody, /-C 'C:\\Windows\\System32' ls-remote --exit-code \$ExpectedOrigin/);
assert.match(trustBody, /HEAD to equal current origin\/main/);
assert.doesNotMatch(trustBody, /status --porcelain|remote get-url/);
assert.match(trustBody, /ExpectedInnerSha256/);
assert.match(trustBody, /ExpectedNodeSourceSha256/);
assert.match(trustBody, /ExpectedDiscordContractSha256/);
assert.match(trustBody, /-EncodedCommand/);
assert.match(trustBody, /secretProcessExited=\$true/);
assert.match(trustBody, /botTokenPersistedLocally=\$false/);
assert.match(trustBody, /botTokenStillValidAtDiscord=\$true/);
assert.match(trustBody, /revocationRequired=\$true/);
assert.doesNotMatch(trustBody, /Read-Host|Clipboard/i);

assert.match(inner, /Read-Host -AsSecureString/);
assert.match(inner, /clipboard use is prohibited/i);
assert.match(inner, /SecureStringToBSTR/);
assert.match(inner, /ZeroFreeBSTR/);
assert.match(inner, /StandardInput\.Write\(\$token\)/);
assert.match(inner, /StandardInput\.Close\(\)/);
assert.match(inner, /\$token = \$null/);
assert.match(inner, /EnvironmentVariables\.Clear\(\)/);
assert.match(inner, /VENICE_ONE_SHOT_READY/);
assert.ok(
  inner.indexOf('$ready = $process.StandardOutput.ReadLine()') < inner.indexOf('$secureToken = Read-Host'),
  'the reviewed Node process must be loaded and ready before Drew enters the token',
);
assert.doesNotMatch(inner, /Get-Clipboard|Set-Clipboard/i);
assert.doesNotMatch(inner, /gcloud|Secret Manager|secrets versions/i);

const guardIndex = nodeSource.indexOf('assertTrustedLaunch();');
const contractLoadIndex = nodeSource.indexOf("Buffer.from(process.env.VENICE_DISCORD_CONTRACT_BASE64");
const readyIndex = nodeSource.indexOf("process.stdout.write('VENICE_ONE_SHOT_READY\\n')");
const stdinIndex = nodeSource.indexOf("fs.readFileSync(0, 'utf8')");
assert.ok(guardIndex >= 0 && contractLoadIndex > guardIndex, 'launch guard must run before contract load');
assert.ok(contractLoadIndex < readyIndex && readyIndex < stdinIndex, 'all executable source must load before token input');
assert.doesNotMatch(
  nodeSource,
  /require\(['"]\.\.\/functions\/venice_discord\.js['"]\)/,
  'the isolated token process must not load repository runtime code',
);
assert.match(nodeSource, /fs\.readFileSync\(0, 'utf8'\)/);
assert.match(nodeSource, /https:\/\/discord\.com\/api\/v10/);
assert.match(nodeSource, /DiscordBot \(https:\/\/github\.com\/Valar05\/home-center, 1\.0\)/);
assert.match(nodeSource, /interactions_endpoint_url: expectedEndpoint/);
assert.match(nodeSource, /botTokenPersistedLocally: false/);
assert.match(nodeSource, /botTokenStillValidAtDiscord: true/);
assert.match(nodeSource, /revocationRequired: true/);
assert.match(nodeSource, /botToken = ''/);
assert.doesNotMatch(nodeSource, /gcloud|Secret Manager|secrets versions/i);

for (const source of [outer, trustBody, inner, nodeSource]) {
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

assert.ok(outer.includes(`$ExpectedTrustBodySha256 = '${hash('tools/configure_venice_discord_trusted.ps1')}'`));
assert.ok(trustBody.includes(`$ExpectedInnerSha256 = '${hash('tools/configure_venice_discord_inner.ps1')}'`));
assert.ok(trustBody.includes(`$ExpectedNodeSourceSha256 = '${hash('tools/configure_venice_discord.mjs')}'`));
assert.ok(trustBody.includes(`$ExpectedDiscordContractSha256 = '${hash('functions/venice_discord_contract.json')}'`));

const require = createRequire(import.meta.url);
const runtime = require('../functions/venice_discord.js');
const discordContract = JSON.parse(discordContractSource);
assert.equal(runtime.VENICE_APPLICATION_ID, discordContract.applicationId);
assert.equal(runtime.VENICE_GUILD_ID, discordContract.guildId);
assert.deepEqual(runtime.VENICE_ALLOWED_CHANNEL_IDS, discordContract.allowedChannelIds);
assert.deepEqual(runtime.VENICE_COMMANDS, discordContract.commands);

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
  immutableTrustBody: true,
  nonRepositoryRemoteCheck: true,
  clipboardProhibited: true,
  botTokenPersistedLocally: false,
  postRegistrationRevocationRequired: true,
  runtimeBindsPublicKeyOnly: true,
}));
