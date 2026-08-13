#!/usr/bin/env node
import {appendFile, mkdir, readFile} from 'node:fs/promises';
import {dirname, join} from 'node:path';
import {homedir} from 'node:os';
import {createRelay} from './relay.mjs';

const root = process.env.HOME_CENTER_CHROMIUM_THRONE_ROOT || join(process.env.LOCALAPPDATA || join(homedir(), '.local', 'share'), 'HomeCenter', 'ChromiumThrone');
const capabilityFile = process.env.HOME_CENTER_CHROMIUM_THRONE_CAPABILITY_FILE || join(root, 'relay-capability.txt');
const eventLog = process.env.HOME_CENTER_CHROMIUM_THRONE_EVENT_LOG || join(root, 'relay-events.jsonl');
const extensionId = process.env.HOME_CENTER_CHROMIUM_THRONE_EXTENSION_ID || 'lccnchjcenaomhnjjaomabpajagenkaf';
const extensionOrigin = `chrome-extension://${extensionId}`;
const port = Number(process.env.HOME_CENTER_CHROMIUM_THRONE_RELAY_PORT || 9234);
const host = '127.0.0.1';

const throneCapability = (await readFile(capabilityFile, 'utf8')).trim();
if (throneCapability.length < 32) throw new Error('Chromium Throne relay capability is missing or too short.');
await mkdir(dirname(eventLog), {recursive: true});
const eventSink = async (event) => appendFile(eventLog, JSON.stringify({at: new Date().toISOString(), ...event}) + '\n', 'utf8');

const server = createRelay({host, port, extensionOrigin, throneCapability, eventSink});
server.on('listening', () => console.log(JSON.stringify({ok: true, service: 'chromium-throne-relay', host, port, extensionOrigin, eventLog, capabilityStored: true})));
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.close(() => process.exit(0)));
