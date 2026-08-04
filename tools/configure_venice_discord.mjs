#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const expectedNode = 'C:\\Program Files\\nodejs\\node.exe';
const expectedNodeSha256 = '77bdff912b1c569b3e693fe126f619337c3e9d73dafbc4d0bf1d4f1f6a145761';
const expectedEndpoint = 'https://us-central1-home-center-dclar.cloudfunctions.net/veniceDiscordInteractions';

function samePath(left, right) {
  return path.resolve(String(left || '')).toLowerCase() === path.resolve(String(right || '')).toLowerCase();
}

function assertTrustedLaunch() {
  if (
    process.platform !== 'win32'
    || process.env.VENICE_TRUSTED_ONE_SHOT_NODE !== '1'
    || !samePath(process.execPath, expectedNode)
    || !samePath(process.env.VENICE_TRUSTED_NODE, expectedNode)
    || process.env.VENICE_TRUSTED_NODE_SHA256 !== expectedNodeSha256
  ) {
    throw new Error('Use tools/configure_venice_discord.ps1 from clean origin/main.');
  }
  const stats = fs.lstatSync(expectedNode);
  if (stats.isSymbolicLink()) throw new Error('The governed Node runtime is a symbolic link.');
  const nodeHash = crypto.createHash('sha256').update(fs.readFileSync(expectedNode)).digest('hex');
  if (nodeHash !== expectedNodeSha256) throw new Error('The governed Node runtime hash changed.');
  const blocked = [
    'NODE_OPTIONS', 'NODE_PATH', 'NODE_DEBUG', 'NODE_DEBUG_NATIVE',
    'NODE_EXTRA_CA_CERTS', 'NODE_TLS_REJECT_UNAUTHORIZED', 'NODE_V8_COVERAGE',
    'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
    'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'SSL_CERT_FILE', 'SSL_CERT_DIR',
  ];
  for (const name of blocked) {
    if (process.env[name]) throw new Error(`Unsafe one-shot environment override is present: ${name}.`);
  }
}

assertTrustedLaunch();

const cli = process.argv.slice(-2);
if (cli.length !== 2 || cli[0] !== '--endpoint' || cli[1] !== expectedEndpoint) {
  throw new Error('The one-shot configuration requires the exact governed endpoint.');
}

const contractBytes = Buffer.from(process.env.VENICE_DISCORD_CONTRACT_BASE64 || '', 'base64');
const contractHash = crypto.createHash('sha256').update(contractBytes).digest('hex');
if (contractHash !== process.env.VENICE_DISCORD_CONTRACT_SHA256) {
  throw new Error('The governed Discord contract hash changed.');
}
const contract = JSON.parse(contractBytes.toString('utf8'));
const VENICE_APPLICATION_ID = String(contract.applicationId || '');
const VENICE_GUILD_ID = String(contract.guildId || '');
const VENICE_COMMANDS = contract.commands;
if (
  VENICE_APPLICATION_ID !== '1534113573708763196'
  || VENICE_GUILD_ID !== '1534104765796192356'
  || JSON.stringify(contract.allowedChannelIds) !== JSON.stringify(['1534104766643437620', '1534105192226623610'])
  || !Array.isArray(VENICE_COMMANDS)
) {
  throw new Error('The governed Discord contract is invalid.');
}

process.stdout.write('VENICE_ONE_SHOT_READY\n');
let botToken = fs.readFileSync(0, 'utf8').trim();
if (!/^[A-Za-z0-9._-]{30,200}$/.test(botToken)) throw new Error('Discord token input is invalid.');

async function discord(apiPath, init = {}) {
  const response = await fetch(`https://discord.com/api/v10${apiPath}`, {
    ...init,
    redirect: 'error',
    signal: AbortSignal.timeout(10_000),
    headers: {
      Authorization: `Bot ${botToken}`,
      'Content-Type': 'application/json',
      'User-Agent': 'DiscordBot (https://github.com/Valar05/home-center, 1.0)',
      ...(init.headers || {}),
    },
  });
  if (!response.ok) throw new Error(`Discord configuration failed with HTTP ${response.status}.`);
  return response.status === 204 ? null : response.json();
}

try {
  const application = await discord('/applications/@me');
  if (String(application.id || '') !== VENICE_APPLICATION_ID) {
    throw new Error('Discord token belongs to a different application.');
  }
  if (!/^[0-9a-f]{64}$/i.test(application.verify_key || '')) {
    throw new Error('Discord application public key is invalid.');
  }
  const registered = await discord(`/applications/${VENICE_APPLICATION_ID}/guilds/${VENICE_GUILD_ID}/commands`, {
    method: 'PUT',
    body: JSON.stringify(VENICE_COMMANDS),
  });
  const commandNames = registered.map((command) => command.name).sort();
  if (JSON.stringify(commandNames) !== JSON.stringify(['cut-the-cam', 'venice'])) {
    throw new Error('Discord did not return the exact governed command set.');
  }
  const updatedApplication = await discord('/applications/@me', {
    method: 'PATCH',
    body: JSON.stringify({interactions_endpoint_url: expectedEndpoint}),
  });
  if (updatedApplication.interactions_endpoint_url !== expectedEndpoint) {
    throw new Error('Discord did not accept the governed interactions endpoint.');
  }
  process.stdout.write(JSON.stringify({
    ok: true,
    applicationId: VENICE_APPLICATION_ID,
    guildId: VENICE_GUILD_ID,
    commands: commandNames,
    interactionsEndpointConfigured: true,
    publicKeyFingerprint: crypto.createHash('sha256').update(application.verify_key).digest('hex'),
    botTokenPersistedLocally: false,
    botTokenStillValidAtDiscord: true,
    revocationRequired: true,
  }) + '\n');
} finally {
  botToken = '';
}
