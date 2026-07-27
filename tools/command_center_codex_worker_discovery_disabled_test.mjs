#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED,
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE,
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS,
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_TOOL_NAMES,
  assertCodexWorkerDiscoveryOperationEnabled,
  commandCenterHealthPayload,
  commandCenterCapabilitiesPayload,
  createCommandCenterMcpApp,
  createCommandCenterMcpServer,
} = require('../functions/command_center_mcp');
const {
  commandCenterOperationRegistry,
  supportedCommandCenterOperationTypes,
  commandCenterToolName,
} = require('../functions/home_center_mcp');

assert.equal(COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED, true);
assert.equal(COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE, 'command_center_codex_worker_discovery_permanently_disabled');
assert(COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS.length >= 25);
for (const required of [
  'system.health',
  'jobs.create',
  'jobs.dispatch_queued',
  'jobs.resume',
  'agents.create_activation',
  'workers.provision',
  'workers.register_oneshot',
  'workers.wake',
  'workers.list',
  'hosts.list',
  'machine_images.list',
  'codex_sessions.create',
  'routing.explain',
]) assert(COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS.includes(required), required);

for (const operation of COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS) {
  assert.throws(
    () => assertCodexWorkerDiscoveryOperationEnabled(operation),
    (err) => err && err.status === 410 && err.code === COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE && err.operation === operation,
    operation,
  );
  assert.throws(
    () => commandCenterToolName(operation),
    (err) => err && err.status === 410 && err.code === COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE,
    'Home Center stale dispatcher guard: ' + operation,
  );
}
assert.doesNotThrow(() => assertCodexWorkerDiscoveryOperationEnabled('render.blender_glb'));
assert.equal(commandCenterToolName('render.blender_glb'), 'command_center.render.blender_glb');

const server = createCommandCenterMcpServer({admin: null});
const toolNames = Object.keys(server._registeredTools).sort();
for (const toolName of COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_TOOL_NAMES) {
  assert(!toolNames.includes(toolName), 'disabled direct MCP tool leaked: ' + toolName);
}
for (const retained of [
  'command_center.health',
  'command_center.capabilities',
  'command_center_operation',
  'command_center.render.blender_glb',
  'command_center.projects.get',
  'command_center.bucket.get_layout',
]) assert(toolNames.includes(retained), 'retained tool missing: ' + retained);

const health = commandCenterHealthPayload();
assert.equal(health.codexWorkerDiscovery.state, 'permanently_disabled');
assert.equal(health.codexWorkerDiscovery.code, COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE);
const capabilities = commandCenterCapabilitiesPayload(server);
assert.equal(capabilities.diagnosticsOperation, 'health');
assert.equal(capabilities.codexWorkerDiscovery.state, 'permanently_disabled');
assert.deepEqual(capabilities.topLevelTools, toolNames);

const bridgeRegistry = commandCenterOperationRegistry();
const bridgeOperations = supportedCommandCenterOperationTypes();
assert.equal(bridgeRegistry.codexWorkerDiscovery.state, 'permanently_disabled');
for (const operation of COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS) {
  assert(!bridgeOperations.includes(operation), 'disabled Home Center operation leaked: ' + operation);
}
assert(bridgeOperations.includes('render.blender_glb'));
assert(bridgeOperations.includes('jobs.get'));

const app = createCommandCenterMcpApp({admin: null});
const listener = await new Promise((resolve) => {
  const instance = app.listen(0, '127.0.0.1', () => resolve(instance));
});
try {
  const address = listener.address();
  const base = 'http://127.0.0.1:' + address.port;
  for (const route of ['/agent/claim', '/agent/complete', '/worker/heartbeat', '/worker/lease', '/worker/complete']) {
    const response = await fetch(base + route, {method: 'POST', headers: {'content-type': 'application/json'}, body: '{}'});
    assert.equal(response.status, 410, route);
    const payload = await response.json();
    assert.equal(payload.error.code, COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE, route);
    assert.equal(payload.error.state, 'permanently_disabled', route);
  }
  const response = await fetch(base + '/');
  assert.equal(response.status, 200);
  assert.equal((await response.json()).codexWorkerDiscovery.state, 'permanently_disabled');
} finally {
  await new Promise((resolve, reject) => listener.close((err) => err ? reject(err) : resolve()));
  await server.close();
}

const deployScript = new URL('deploy_command_center_cloud_worker.sh', import.meta.url);
const deploy = spawnSync('sh', [deployScript.pathname], {encoding: 'utf8'});
assert.equal(deploy.status, 64);
assert.match(deploy.stderr, /command_center_codex_worker_discovery_permanently_disabled/);
assert(!deploy.stdout.includes('Cloud worker image deployed'));

const tombstone = fs.readFileSync(new URL('../docs/COMMAND_CENTER_CODEX_WORKER_DISCOVERY_TOMBSTONE.md', import.meta.url), 'utf8');
assert.match(tombstone, /There is no operational rollback/);
assert.match(tombstone, /render queues and specialized render workers/);

console.log('Command Center Codex worker discovery tombstone contract: OK');
