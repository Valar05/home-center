import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {access, mkdtemp, readFile, readdir, rm} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {tmpdir} from 'node:os';
import path from 'node:path';
import test from 'node:test';

const require = createRequire(import.meta.url);
const ingress = require('../functions/host_file_ingress.js');
const {createHomeCenterMcpServer} = require('../functions/home_center_mcp.js');

const fixture = Buffer.from('home-center-host-file-fixture\n');
const publicDns = async () => [{address: '8.8.8.8', family: 4}];
function response(body = fixture, init = {}) {
  return new Response(body, {status: 200, headers: {'content-type': 'text/plain', 'content-length': String(body.length)}, ...init});
}
function descriptor(overrides = {}) {
  return {
    download_url: 'https://files.example.test/download/signed',
    file_id: 'file_fixture_001',
    mime_type: 'text/plain',
    file_name: 'fixture.txt',
    ...overrides,
  };
}

async function materialize(value, overrides = {}) {
  return ingress.materializeOpenAiHostFile(value, {
    maxBytes: 1024,
    resolveHostname: publicDns,
    fetchImpl: async () => response(),
    ...overrides,
  });
}

test('native ChatGPT attachment preserves bytes and metadata', async () => {
  const file = await materialize(descriptor());
  assert.equal(file.name, 'fixture.txt');
  assert.equal(file.type, 'text/plain');
  assert.equal(file.size, fixture.length);
  assert.deepEqual(Buffer.from(await file.arrayBuffer()), fixture);
});

test('generated Work Mode artifact uses the same typed boundary', async () => {
  const file = await materialize(descriptor({file_id: 'file_generated_001', file_name: 'generated.txt'}));
  assert.equal(file.fileId, 'file_generated_001');
  assert.deepEqual(Buffer.from(await file.arrayBuffer()), fixture);
});

test('Drive ingress spools fragmented bytes privately and deletes them on cleanup', async (t) => {
  const directory = await mkdtemp(path.join(tmpdir(), 'home-center-host-file-test-'));
  t.after(() => rm(directory, {recursive: true, force: true}));
  const streamed = await ingress.materializeOpenAiHostFileToTemp(descriptor({mime_type: 'application/octet-stream'}), {
    maxBytes: 1024,
    tempDir: directory,
    resolveHostname: publicDns,
    fetchImpl: async () => response(new Blob([fixture.subarray(0, 4), fixture.subarray(4)])),
  });
  assert.equal(streamed.size, fixture.length);
  assert.equal(streamed.sha256, createHash('sha256').update(fixture).digest('hex'));
  assert.deepEqual(await readFile(streamed.tempPath), fixture);
  assert.deepEqual(await new Promise((resolve, reject) => {
    const chunks = [];
    streamed.createReadStream().on('data', (chunk) => chunks.push(chunk)).on('end', () => resolve(Buffer.concat(chunks))).on('error', reject);
  }), fixture);
  await streamed.cleanup();
  await streamed.cleanup();
  await assert.rejects(() => access(streamed.tempPath), {code: 'ENOENT'});
});

test('streamed Drive ingress removes partial temporary bytes on overflow', async (t) => {
  const directory = await mkdtemp(path.join(tmpdir(), 'home-center-host-file-overflow-'));
  t.after(() => rm(directory, {recursive: true, force: true}));
  await assert.rejects(
    () => ingress.materializeOpenAiHostFileToTemp(descriptor(), {maxBytes: 4, tempDir: directory, resolveHostname: publicDns, fetchImpl: async () => response(fixture, {headers: {'content-type': 'text/plain'}})}),
    (error) => error.code === 'host_file_too_large',
  );
  assert.deepEqual(await readdir(directory), []);
});

test('plain paths and attachment handle strings fail closed', async () => {
  await assert.rejects(() => materialize('/workspace/fixture.txt'), (error) => error.code === 'host_file_required');
  await assert.rejects(() => materialize('file_fixture_001'), (error) => error.code === 'host_file_required');
});

test('malformed, expired, oversized, and unsafe files return bounded errors', async () => {
  await assert.rejects(() => materialize({download_url: 'https://files.example.test/x'}), (error) => error.code === 'host_file_schema_invalid' && !error.message.includes('https://'));
  await assert.rejects(() => materialize(descriptor(), {fetchImpl: async () => new Response('', {status: 410})}), (error) => error.code === 'host_file_expired' && /attach the file again/i.test(error.message));
  await assert.rejects(() => materialize(descriptor(), {fetchImpl: async () => new Response('x', {status: 200, headers: {'content-length': '2048'}})}), (error) => error.code === 'host_file_too_large');
  await assert.rejects(() => materialize(descriptor({download_url: 'http://files.example.test/x'})), (error) => error.code === 'host_file_url_forbidden');
  await assert.rejects(() => materialize(descriptor({download_url: 'https://127.0.0.1/x'})), (error) => error.code === 'host_file_url_forbidden');
  await assert.rejects(() => materialize(descriptor(), {fetchImpl: async () => new Response('', {status: 302, headers: {location: 'https://169.254.169.254/latest/meta-data'}})}), (error) => error.code === 'host_file_url_forbidden');
});

test('tool discovery advertises exact OpenAI file parameter contract', async () => {
  process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
  const server = createHomeCenterMcpServer({google: {}, admin: {firestore() { return {}; }}, googleClientId: () => 'configured', googleClientSecret: () => 'configured'});
  const handler = server.server._requestHandlers.get('tools/list');
  const listed = await handler({method: 'tools/list', params: {}}, {});
  for (const name of ['drive_ingest_file', 'storage_ingest_artifact']) {
    const tool = listed.tools.find((entry) => entry.name === name);
    assert.deepEqual(tool._meta['openai/fileParams'], ['file']);
    assert.deepEqual(tool.inputSchema.properties.file, {$ref: '#/$defs/OpenAIFile'});
    const fileSchema = tool.inputSchema.$defs.OpenAIFile;
    assert.equal(fileSchema.type, 'object');
    assert.deepEqual(fileSchema.required, ['download_url', 'file_id']);
    assert.deepEqual(Object.keys(fileSchema.properties).sort(), ['download_url', 'file_id', 'file_name', 'mime_type']);
    assert.equal(fileSchema.additionalProperties, false);
    assert.notEqual(tool.inputSchema.properties.file.type, 'string');
  }
});

test('cold module reload preserves file binding behavior', () => {
  const modulePath = require.resolve('../functions/host_file_ingress.js');
  delete require.cache[modulePath];
  const cold = require(modulePath);
  assert.deepEqual(cold.openAiFileParamJsonSchema().required, ['download_url', 'file_id']);
  assert.equal(cold.normalizeFileParam(descriptor()).fileId, 'file_fixture_001');
});
