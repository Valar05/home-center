import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import test from 'node:test';

const require = createRequire(import.meta.url);
const service = require('../functions/motion_to_docs_service.js');

test('execution id is deterministic and workflow-safe', () => {
  const first = service.executionIdFor('motion-docs-test-001');
  assert.equal(first, service.executionIdFor('motion-docs-test-001'));
  assert.match(first, /^scan-[a-f0-9]{24}$/);
});

test('source descriptor accepts the Work Mode file contract without exposing a path', () => {
  const value = service.sourceDescriptor([{download_url: 'https://files.oaiusercontent.com/video.mp4', file_id: 'file_1', file_name: 'scan.mp4', mime_type: 'video/mp4'}]);
  assert.equal(value.sourceUrl, 'https://files.oaiusercontent.com/video.mp4');
  assert.equal(value.name, 'scan.mp4');
});

test('workflow runner resumes an idempotent execution and returns parsed result', async () => {
  const calls = [];
  const client = {async request(request) {
    calls.push(request);
    if (request.method === 'POST') throw {response: {status: 409}};
    return {data: {name: 'projects/p/locations/us-central1/workflows/w/executions/scan-1', state: 'SUCCEEDED', result: JSON.stringify({document: {documentId: 'doc-1'}})}};
  }};
  const run = await service.runWorkflow({google: {}, workflowClient: client, projectId: 'p', workflow: 'w', idempotencyKey: 'motion-docs-test-001', argument: {sourceUrl: 'https://files.oaiusercontent.com/video.mp4'}, sleep: async () => {}});
  assert.equal(run.result.document.documentId, 'doc-1');
  assert.equal(calls.length, 2);
});
