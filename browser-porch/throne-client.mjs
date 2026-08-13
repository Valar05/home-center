#!/usr/bin/env node
import {readFile} from 'node:fs/promises';
import {join} from 'node:path';
import {homedir} from 'node:os';
import {spawn} from 'node:child_process';

const args = new Map();
for (let i = 2; i < process.argv.length; i += 2) args.set(process.argv[i], process.argv[i + 1] || '');
const root = args.get('--root') || process.env.HOME_CENTER_CHROMIUM_THRONE_ROOT || join(process.env.LOCALAPPDATA || join(homedir(), '.local', 'share'), 'HomeCenter', 'ChromiumThrone');
const capability = (await readFile(join(root, 'relay-capability.txt'), 'utf8')).trim();
const runtime = JSON.parse(await readFile(join(root, 'runtime-config.json'), 'utf8'));
const relayBase = runtime.relayBase || 'http://127.0.0.1:9234/v1/throne';
const commandB64 = args.get('--command-b64') || '';
if (!commandB64) throw new Error('--command-b64 is required');
const command = JSON.parse(Buffer.from(commandB64, 'base64url').toString('utf8'));
if (!command.commandId || !command.action) throw new Error('commandId and action are required');

const response = await fetch(`${relayBase}/command`, {
  method: 'POST',
  headers: {'content-type': 'application/json', authorization: `Bearer ${capability}`},
  body: JSON.stringify(command),
});
const text = await response.text();
if (!response.ok) throw new Error(`relay HTTP ${response.status}: ${text.slice(0, 1000)}`);
const accepted = text ? JSON.parse(text) : {};

let wakeRequested = false;
if (runtime.browserExe && runtime.profileDir && runtime.extensionDir && runtime.extensionId) {
  const wakeUrl = `chrome-extension://${runtime.extensionId}/wake.html`;
  const child = spawn(runtime.browserExe, [
    `--user-data-dir=${runtime.profileDir}`,
    `--load-extension=${runtime.extensionDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    wakeUrl,
  ], {detached: true, stdio: 'ignore'});
  child.unref();
  wakeRequested = true;
}

console.log(JSON.stringify({ok: true, commandId: command.commandId, action: command.action, relay: accepted, wakeRequested}));
