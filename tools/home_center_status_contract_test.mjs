#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
process.env.HOME_CENTER_SOURCE_REPOSITORY = 'Valar05/home-center';
process.env.HOME_CENTER_SOURCE_COMMIT = '0123456789abcdef0123456789abcdef01234567';
process.env.HOME_CENTER_SOURCE_REF = 'refs/heads/main';
process.env.HOME_CENTER_PUBLIC_MANIFEST_SHA256 = 'a'.repeat(64);
process.env.K_REVISION = 'homecentermcp-test-revision';
const {
  HOME_CENTER_MCP_SERVER_VERSION,
  HOME_CENTER_CONNECTOR_SCHEMA_REVISION,
  createHomeCenterMcpApp,
  createHomeCenterMcpServer,
  homeCenterHealthPayload,
  homeCenterReleaseIdentity,
  homeCenterReadinessPayload,
  homeCenterCapabilitiesPayload,
  operationRegistrySummary,
} = require('../functions/home_center_mcp.js');
const {
  COMMAND_CENTER_MCP_SERVER_VERSION,
  createCommandCenterMcpApp,
  createCommandCenterMcpServer,
  commandCenterHealthPayload,
  commandCenterReadinessPayload,
  commandCenterCapabilitiesPayload,
} = require('../functions/command_center_mcp.js');

const admin = {firestore() { return {}; }};
const oauth = {
  googleClientId: () => 'client-id-is-configured',
  googleClientSecret: () => 'client-secret-is-configured',
};

function sha256(value) {
  return createHash('sha256').update(String(value || '')).digest('hex');
}

function oauthTokenAdmin(initialDocs = new Map()) {
  const docs = new Map(initialDocs);
  return {
    _docs: docs,
    firestore() {
      return {
        collection(name) {
          return {
            doc(id) {
              const key = `${name}/${id}`;
              return {
                async get() {
                  return {exists: docs.has(key), data: () => docs.get(key)};
                },
                async set(payload, options = {}) {
                  docs.set(key, options.merge && docs.has(key) ? {...docs.get(key), ...payload} : payload);
                },
              };
            },
          };
        },
      };
    },
  };
}

function textJson(result) {
  assert.equal(result.content?.length, 1);
  assert.equal(result.content[0].type, 'text');
  return JSON.parse(result.content[0].text);
}

function sortedUnique(values) {
  return [...new Set(values)].sort();
}

async function fetchApp(app, pathname, init) {
  const listener = app.listen(0, '127.0.0.1');
  await new Promise((resolve, reject) => {
    listener.once('listening', resolve);
    listener.once('error', reject);
  });
  try {
    const address = listener.address();
    return await fetch(`http://127.0.0.1:${address.port}${pathname}`, init);
  } finally {
    await new Promise((resolve) => listener.close(resolve));
  }
}

assert.deepEqual(homeCenterHealthPayload(), {
  ok: true,
  service: 'home-center-drive-bridge',
  version: HOME_CENTER_MCP_SERVER_VERSION,
});
assert.deepEqual(Object.keys(homeCenterHealthPayload()), ['ok', 'service', 'version']);
assert.deepEqual(homeCenterReleaseIdentity(), {sourceRepository: 'Valar05/home-center', sourceCommit: '0123456789abcdef0123456789abcdef01234567', sourceRef: 'refs/heads/main', registrySchemaRevision: HOME_CENTER_CONNECTOR_SCHEMA_REVISION, publicManifestSha256: 'a'.repeat(64), deployedServiceRevision: 'homecentermcp-test-revision'});

const homeReady = homeCenterReadinessPayload({admin, ...oauth});
assert.equal(homeReady.ready, true);
assert.equal(homeReady.status, 'ready');
assert.deepEqual(homeReady.releaseIdentity, homeCenterReleaseIdentity());
assert.deepEqual(homeReady.checks.map((check) => check.name), [
  'main_release_identity',
  'firebase_admin',
  'google_oauth_client_id',
  'google_oauth_client_secret',
  'command_center_endpoint',
  'artifact_bucket',
]);
assert(!JSON.stringify(homeReady).includes('client-secret-is-configured'));
const savedSourceCommit = process.env.HOME_CENTER_SOURCE_COMMIT;
delete process.env.HOME_CENTER_SOURCE_COMMIT;
assert.equal(homeCenterReadinessPayload({admin, ...oauth}).ready, false, 'missing immutable main identity must fail readiness');
process.env.HOME_CENTER_SOURCE_COMMIT = savedSourceCommit;
assert.equal(homeCenterReadinessPayload({admin: null, googleClientId: () => '', googleClientSecret: () => ''}).ready, false);

const bounded = operationRegistrySummary({version: 'v1', invocationTool: 'dispatch', operations: {z: {write: true}, a: {write: false}, m: {readOnly: false}}}, 2);
assert.deepEqual(bounded, {
  version: 'v1',
  invocationTool: 'dispatch',
  operationCount: 3,
  operations: ['a', 'm'],
  writeOperations: ['m'],
  truncated: true,
});

const homeServer = createHomeCenterMcpServer({google: {}, admin, ...oauth});
const health = textJson(await homeServer._registeredTools.health.handler({}, {}));
const readiness = textJson(await homeServer._registeredTools.readiness.handler({}, {}));
const capabilities = textJson(await homeServer._registeredTools.capabilities.handler({}, {}));
assert.deepEqual(health, homeCenterHealthPayload());
assert.deepEqual(readiness, homeReady);
assert.deepEqual(capabilities, homeCenterCapabilitiesPayload(homeServer));
assert.deepEqual(capabilities, textJson(await homeServer._registeredTools.capabilities.handler({}, {})), 'capabilities must be deterministic');
assert.equal(capabilities.registryVersion, HOME_CENTER_CONNECTOR_SCHEMA_REVISION);
assert.deepEqual(capabilities.releaseIdentity, homeCenterReleaseIdentity());
assert.equal(capabilities.summaryKind, 'names_only');
assert.deepEqual(capabilities.topLevelTools, sortedUnique(capabilities.topLevelTools));
for (const summary of Object.values(capabilities.operationSurfaces)) {
  assert.deepEqual(summary.operations, sortedUnique(summary.operations));
  assert.deepEqual(summary.writeOperations, sortedUnique(summary.writeOperations));
  assert(summary.operationCount >= summary.operations.length);
  assert(summary.operations.length <= 200);
}
for (const operation of ['sfx.analyze_source', 'sfx.transcribe_slate', 'sfx.segment', 'sfx.render', 'sfx.status', 'sfx.artifacts']) {
  assert(capabilities.operationSurfaces.drive.operations.includes(operation), `live Drive registry must expose ${operation}`);
}
for (const operation of ['projects.resolve', 'projects.upsert', 'bucket.put_object', 'bucket.promote_skill', 'app_control.record_run', 'browser_sessions.create']) {
  assert(capabilities.operationSurfaces.commandCenter.writeOperations.includes(operation), `Command Center mutation must be advertised as a write: ${operation}`);
}
for (const operation of ['health', 'projects.get', 'bucket.get_object', 'bucket.list_objects', 'browser_sessions.observe']) {
  assert(!capabilities.operationSurfaces.commandCenter.writeOperations.includes(operation), `Command Center read must not be advertised as a write: ${operation}`);
}
assert.deepEqual(capabilities.fileUploadTools, [
  {
    name: 'drive_ingest_file',
    required: ['requestId', 'file'],
    inputs: {
      file: {format: 'binary', contentMediaType: 'application/octet-stream'},
    },
    maxBytes: 256 * 1024 * 1024,
    verification: ['expectedSha256', 'Drive readback byte count', 'Drive readback SHA-256'],
  },
  {
    name: 'storage_ingest_artifact',
    required: ['requestId', 'file', 'artifactId', 'artifactKind', 'project', 'expectedSha256'],
    inputs: {
      file: {format: 'binary', contentMediaType: 'application/octet-stream'},
    },
    maxBytes: 256 * 1024 * 1024,
    verification: ['expectedSha256', 'GCS readback byte count', 'GCS readback SHA-256', 'immutable indexes', 'Command Center artifact receipt'],
  },
]);
const homeCapabilitiesText = JSON.stringify(capabilities);
assert(homeCapabilitiesText.length < 20000, `capabilities payload grew to ${homeCapabilitiesText.length} bytes`);
for (const forbidden of ['commandCenterManual', 'simulationManual', 'homeDriveManual', 'discoverability', 'recipes', 'reconnectAdvice', 'client-secret-is-configured']) {
  assert(!homeCapabilitiesText.includes(forbidden), `capabilities leaked clutter: ${forbidden}`);
}

assert.deepEqual(commandCenterHealthPayload(), {
  ok: true,
  service: 'command-center-mcp',
  version: COMMAND_CENTER_MCP_SERVER_VERSION,
  hasFrontend: false,
});
const commandReady = commandCenterReadinessPayload({admin});
assert.equal(commandReady.ready, true);
assert.equal(commandCenterReadinessPayload({admin: null}).ready, false);
const commandServer = createCommandCenterMcpServer({admin});
const commandHealth = textJson(await commandServer._registeredTools['command_center.health'].handler({}, {}));
const commandReadiness = textJson(await commandServer._registeredTools['command_center.readiness'].handler({}, {}));
const commandCapabilities = textJson(await commandServer._registeredTools['command_center.capabilities'].handler({}, {}));
assert.deepEqual(commandHealth, commandCenterHealthPayload());
assert.deepEqual(commandReadiness, commandReady);
assert.deepEqual(commandCapabilities, commandCenterCapabilitiesPayload(commandServer));
assert.deepEqual(commandCapabilities.topLevelTools, sortedUnique(commandCapabilities.topLevelTools));
assert.equal(commandCapabilities.diagnosticsOperation, 'system.health');
assert(JSON.stringify(commandCapabilities).length < 10000);

const homeRoot = await fetchApp(createHomeCenterMcpApp({google: {}, admin, ...oauth}), '/');
assert.equal(homeRoot.status, 200);
assert.deepEqual(await homeRoot.json(), homeCenterHealthPayload());
const homeApp = createHomeCenterMcpApp({google: {}, admin, ...oauth});
const oauthResourceMetadata = await fetchApp(homeApp, '/.well-known/oauth-protected-resource');
assert.equal(oauthResourceMetadata.status, 200);
assert.equal(oauthResourceMetadata.headers.get('cache-control'), 'no-store');
const oauthResourceMetadataBody = await oauthResourceMetadata.json();
assert.equal(oauthResourceMetadataBody.resource, 'https://homecentermcp-vxybsaualq-uc.a.run.app/mcp');
assert.deepEqual(oauthResourceMetadataBody.authorization_servers, ['https://homecentermcp-vxybsaualq-uc.a.run.app']);
assert(oauthResourceMetadataBody.metadata_aliases.includes('https://homecentermcp-vxybsaualq-uc.a.run.app/.well-known/oauth-protected-resource/mcp'));
assert(oauthResourceMetadataBody.metadata_aliases.includes('https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/.well-known/oauth-protected-resource'));
const oauthAuthorizationMetadata = await fetchApp(homeApp, '/.well-known/oauth-authorization-server');
assert.equal(oauthAuthorizationMetadata.status, 200);
const oauthAuthorizationMetadataBody = await oauthAuthorizationMetadata.json();
assert.equal(oauthAuthorizationMetadataBody.issuer, 'https://homecentermcp-vxybsaualq-uc.a.run.app');
assert.equal(oauthAuthorizationMetadataBody.authorization_endpoint, 'https://homecentermcp-vxybsaualq-uc.a.run.app/oauth/authorize');
assert.equal(oauthAuthorizationMetadataBody.token_endpoint, 'https://homecentermcp-vxybsaualq-uc.a.run.app/oauth/token');
assert.equal(oauthAuthorizationMetadataBody.registration_endpoint, 'https://homecentermcp-vxybsaualq-uc.a.run.app/oauth/register');

// Regression: OAuth refresh grants issued before resource binding have no resource field.
// After the path-free issuer migration, old clients still submit the legacy resource while
// the server's fallback is canonical. Both identifiers name this same Home Center install.
const refreshToken = 'fixture-refresh-token-never-log';
const refreshClientId = 'home_center_mcp_fixture_client';
const legacyResource = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const canonicalResource = 'https://homecentermcp-vxybsaualq-uc.a.run.app/mcp';
const refreshAdmin = oauthTokenAdmin(new Map([
  [`mcpOAuthRefreshTokens/${sha256(refreshToken)}`, {
    clientId: refreshClientId,
    email: 'fixture@example.invalid',
    googleTokens: {refresh_token: 'fixture-google-refresh-token'},
    scopes: ['https://www.googleapis.com/auth/drive'],
    createdAtMs: Date.now() - 60_000,
  }],
]));
const refreshApp = createHomeCenterMcpApp({google: {}, admin: refreshAdmin, ...oauth});
const legacyRefreshResponse = await fetchApp(refreshApp, '/oauth/token', {
  method: 'POST',
  headers: {'content-type': 'application/x-www-form-urlencoded'},
  body: new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    client_id: refreshClientId,
    resource: legacyResource,
  }),
});
assert.equal(legacyRefreshResponse.status, 200, 'pre-resource refresh grants must survive the issuer migration');
const legacyRefreshBody = await legacyRefreshResponse.json();
assert.equal(legacyRefreshBody.token_type, 'Bearer');
assert.equal(typeof legacyRefreshBody.access_token, 'string');
const refreshedAccessRecords = [...refreshAdmin._docs.entries()].filter(([key]) => key.startsWith('mcpOAuthAccessTokens/'));
assert.equal(refreshedAccessRecords.length, 1);
assert.equal(refreshedAccessRecords[0][1].resource, canonicalResource, 'successful refresh migrates the access token to the canonical resource');

const unrelatedRefreshResponse = await fetchApp(refreshApp, '/oauth/token', {
  method: 'POST',
  headers: {'content-type': 'application/x-www-form-urlencoded'},
  body: new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    client_id: refreshClientId,
    resource: 'https://unrelated.example/mcp',
  }),
});
assert.equal(unrelatedRefreshResponse.status, 400);
assert.deepEqual(await unrelatedRefreshResponse.json(), {
  error: 'invalid_target',
  error_description: 'resource_not_bound_to_refresh_grant',
});

const unauthenticatedMcp = await fetchApp(homeApp, '/mcp', {
  method: 'POST',
  headers: {'content-type': 'application/json', accept: 'application/json, text/event-stream'},
  body: JSON.stringify({jsonrpc: '2.0', id: 1, method: 'tools/list', params: {}}),
});
assert.equal(unauthenticatedMcp.status, 401);
assert.match(unauthenticatedMcp.headers.get('www-authenticate') || '', /resource_metadata="https:\/\/homecentermcp-vxybsaualq-uc\.a\.run\.app\/\.well-known\/oauth-protected-resource"/);
const oauthPathResourceMetadata = await fetchApp(homeApp, '/.well-known/oauth-protected-resource/mcp');
assert.equal(oauthPathResourceMetadata.status, 200);
assert.equal(oauthPathResourceMetadata.headers.get('cache-control'), 'no-store');
assert.deepEqual(await oauthPathResourceMetadata.json(), oauthResourceMetadataBody);
const homeReadyResponse = await fetchApp(homeApp, '/ready');
assert.equal(homeReadyResponse.status, 200);
assert.deepEqual(await homeReadyResponse.json(), homeReady);
const homeNotReadyResponse = await fetchApp(createHomeCenterMcpApp({google: {}, admin: null}), '/ready');
assert.equal(homeNotReadyResponse.status, 503);
assert.equal((await homeNotReadyResponse.json()).ready, false);

const commandRoot = await fetchApp(createCommandCenterMcpApp({admin}), '/');
assert.equal(commandRoot.status, 200);
assert.deepEqual(await commandRoot.json(), commandCenterHealthPayload());
const commandReadyResponse = await fetchApp(createCommandCenterMcpApp({admin}), '/ready');
assert.equal(commandReadyResponse.status, 200);
assert.deepEqual(await commandReadyResponse.json(), commandReady);
const commandNotReadyResponse = await fetchApp(createCommandCenterMcpApp({admin: null}), '/ready');
assert.equal(commandNotReadyResponse.status, 503);
assert.equal((await commandNotReadyResponse.json()).ready, false);

delete process.env.HOME_CENTER_MCP_EXTENDED_TOOLS;
console.log('Home Center status contract test: OK');

