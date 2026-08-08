#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const builder = fs.readFileSync(path.join(root, 'tvtroper-retrieval/build-index.mjs'), 'utf8');
const service = fs.readFileSync(path.join(root, 'tvtroper-retrieval/service.mjs'), 'utf8');
const bridge = fs.readFileSync(path.join(root, 'functions/home_center_mcp.js'), 'utf8');
const deploy = fs.readFileSync(path.join(root, 'tools/deploy_functions_termux.sh'), 'utf8');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'contracts/home-center-public-tool-manifest.v1.json'), 'utf8'));

assert.match(builder, /GCS_ARCHIVE_OBJECT/);
assert.match(builder, /rangeRead\(archiveObject/);
assert.match(builder, /local_header_offset/);
assert.match(builder, /CLOUD_RUN_TASK_INDEX/);
assert.match(service, /SEARCH\(search_text, @query\)/);
assert.match(service, /archive_generation, html FROM/);
assert.match(service, /full_record_store: 'BigQuery loaded from GCS index\/v2 shards'/);
assert.doesNotMatch(builder + service, /drive\.google|Google Drive|drive_read|drive_search/i);

assert.match(bridge, /tvtroper_operation:/);
assert.doesNotMatch(bridge, /server\.registerTool\(['"]tvtroper_operation['"]/);
assert.match(bridge, /gcsOnly: true/);
assert.match(deploy, /TVTROPER_RETRIEVAL_URL=.*tvtroper-retrieval-vxybsaualq-uc\.a\.run\.app/);
assert.equal(manifest.toolCount, 62);
assert.equal(manifest.canonicalToolsSha256, 'db882595ec9aadcc0caa57ff457e2c5d20bd9dae43b121038d84409a0a9561f7');
assert.equal(manifest.entries.some((entry) => entry.name === 'tvtroper_operation'), false);

process.env.TVTROPER_RETRIEVAL_URL = 'https://tvtroper.test';
const require = createRequire(import.meta.url);
const homeCenter = require(path.join(root, 'functions/home_center_mcp.js'));
assert.equal(homeCenter.HOME_CENTER_CONNECTOR_SCHEMA_REVISION, '2026-08-03.voice-tiers-host-file-v1');
assert.equal(homeCenter.driveOperationRegistry().version, '2026-08-03.voice-tiers-host-file-v1');
assert(homeCenter.driveOperationRegistry().operations.tvtroper_operation);

const calls = [];
class FakeGoogleAuth {
  async getIdTokenClient(audience) {
    assert.equal(audience, 'https://tvtroper.test');
    return {
      request: async (request) => {
        calls.push(request);
        if (request.url.endsWith('/search')) return {data: {query: request.data.query, results: [{record_id: 'record-123', title: 'Deal With The Devil'}]}};
        if (request.url.endsWith('/get')) return {data: {record_id: request.data.record_id, html: '<html>full record</html>', provenance: {zip_entry: 'pages/Main/DealWithTheDevil'}}};
        if (request.url.endsWith('/health')) return {data: {ok: true}};
        throw new Error('Unexpected request ' + request.url);
      },
    };
  }
}
const google = {auth: {GoogleAuth: FakeGoogleAuth}};
const search = await homeCenter.driveOperationRunOperation({
  google,
  args: {operation: 'tvtroper_operation', args: {operation: 'search', args: {query: 'Deal with the Devil', limit: 3}}},
});
assert.equal(search.operation, 'tvtroper_operation');
assert.equal(search.registryVersion, '2026-08-03.voice-tiers-host-file-v1');
assert.equal(search.completed, true);
assert.equal(search.result.operation, 'search');
assert.equal(search.result.gcsOnly, true);
assert.equal(search.result.result.results[0].record_id, 'record-123');
assert.deepEqual(calls[0], {url: 'https://tvtroper.test/search', method: 'POST', data: {query: 'Deal with the Devil', limit: 3}, timeout: 120000});

const get = await homeCenter.driveOperationRunOperation({
  google,
  args: {operation: 'tvtroper_operation', args: {operation: 'get', args: {record_id: search.result.result.results[0].record_id}}},
});
assert.equal(get.result.operation, 'get');
assert.equal(get.result.gcsOnly, true);
assert.equal(get.result.result.record_id, 'record-123');
assert.equal(get.result.result.html, '<html>full record</html>');
assert.deepEqual(calls[1], {url: 'https://tvtroper.test/get', method: 'POST', data: {record_id: 'record-123'}, timeout: 120000});

console.log(JSON.stringify({
  ok: true,
  stableDispatcher: 'drive_operation',
  registryOperation: 'tvtroper_operation',
  topLevelToolAdded: false,
  topLevelToolCount: manifest.toolCount,
  canonicalToolsSha256: manifest.canonicalToolsSha256,
  providerRoundTrip: calls.map((call) => call.url),
}, null, 2));
