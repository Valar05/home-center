#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {createDriveFolderOperation, createGoogleDocOperation, driveWorkflowRunOperation, createHomeCenterMcpServer, normalizeRecoveryOperation, summarizeRecoveryOperations} = require('../functions/home_center_mcp.js');

function fakeAdmin() {
  const docs = new Map();
  const api = {
    _docs: docs,
    firestore() {
      return {
        collection(name) {
          return {
            doc(id) {
              const key = name + '/' + id;
              return {
                async get() {
                  return {exists: docs.has(key), data: () => docs.get(key)};
                },
                async set(payload, options = {}) {
                  docs.set(key, options && options.merge && docs.has(key) ? {...docs.get(key), ...payload} : payload);
                },
              };
            },
            async add(payload) {
              const id = 'auto-' + (docs.size + 1);
              docs.set(name + '/' + id, payload);
              return {id};
            },
            where(field, op, value) {
              return {
                limit() {
                  return {
                    async get() {
                      const found = [];
                      for (const [key, payload] of docs.entries()) {
                        if (key.startsWith(name + '/') && payload && payload[field] === value) found.push({data: () => payload});
                      }
                      return {empty: found.length === 0, docs: found};
                    },
                  };
                },
              };
            },
          };
        },
      };
    },
  };
  api.firestore.FieldValue = {serverTimestamp: () => 'SERVER_TIMESTAMP'};
  return api;
}

function fakeGoogle() {
  const calls = {driveCreate: [], driveUpdate: [], driveGet: [], docsCreate: [], docsGet: [], docsBatchUpdate: []};
  return {
    calls,
    drive() {
      return {
        files: {
          async create(params) {
            calls.driveCreate.push(params);
            return {data: {id: 'folder12345', name: params.requestBody.name, mimeType: params.requestBody.mimeType, webViewLink: 'https://drive/folder12345', parents: params.requestBody.parents || []}};
          },
          async update(params) {
            calls.driveUpdate.push(params);
            return {data: {id: params.fileId, parents: params.addParents ? [params.addParents] : []}};
          },
          async get(params) {
            calls.driveGet.push(params);
            if (params.fileId === 'folder12345') return {data: {id: 'folder12345', name: 'Workflow Project', mimeType: 'application/vnd.google-apps.folder', webViewLink: 'https://drive/folder12345', parents: []}};
            return {data: {id: params.fileId, name: 'Created Doc', mimeType: 'application/vnd.google-apps.document', webViewLink: `https://docs/${params.fileId}`, parents: ['folder12345']}};
          },
        },
      };
    },
    docs() {
      return {
        documents: {
          async create(params) {
            calls.docsCreate.push(params);
            return {data: {documentId: 'doc123456'}};
          },
          async get(params) {
            calls.docsGet.push(params);
            return {data: {body: {content: [{endIndex: 2}]}}};
          },
          async batchUpdate(params) {
            calls.docsBatchUpdate.push(params);
            return {data: {}};
          },
        },
      };
    },
  };
}

const user = {email: 'writer@example.com', authKind: 'test'};
const auth = {test: true};

async function testCreateFolder() {
  const admin = fakeAdmin();
  const google = fakeGoogle();
  const result = await createDriveFolderOperation({google, admin, auth, user, args: {name: 'Tanks for the Memories v2', parentFolderId: 'parent12345', requestId: 'folder-req-001', callerNote: 'Create project folder'}});
  assert.equal(result.folderId, 'folder12345');
  assert.equal(result.name, 'Tanks for the Memories v2');
  assert.equal(result.parentFolderId, 'parent12345');
  assert.equal(google.calls.driveCreate.length, 1);
  assert.equal(google.calls.driveCreate[0].requestBody.mimeType, 'application/vnd.google-apps.folder');
  assert.deepEqual(google.calls.driveCreate[0].requestBody.parents, ['parent12345']);
  assert.equal(admin._docs.get('driveBridgeAudit/folder-req-001').operation, 'drive.createFolder');

  const replay = await createDriveFolderOperation({google, admin, auth, user, args: {name: 'Should Not Duplicate', requestId: 'folder-req-001'}});
  assert.equal(replay.idempotent, true);
  assert.equal(google.calls.driveCreate.length, 1);
}

async function testCreateDoc() {
  const admin = fakeAdmin();
  const google = fakeGoogle();
  const result = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Tanks for the Memories v2 — Story Bible', parentFolderId: 'folder12345', initialText: '# Story Bible\n', requestId: 'doc-req-001'}});
  assert.equal(result.documentId, 'doc123456');
  assert.equal(result.parentFolderId, 'folder12345');
  assert.equal(google.calls.docsCreate.length, 1);
  assert.equal(google.calls.docsCreate[0].requestBody.title, 'Tanks for the Memories v2 — Story Bible');
  assert.equal(google.calls.docsBatchUpdate.length, 1);
  assert.equal(google.calls.docsBatchUpdate[0].requestBody.requests[0].insertText.text, '# Story Bible\n');
  assert.equal(google.calls.driveUpdate.length, 1);
  assert.equal(google.calls.driveUpdate[0].addParents, 'folder12345');
  assert.equal(admin._docs.get('driveBridgeAudit/doc-req-001').operation, 'docs.create');

  const replay = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Duplicate Doc', requestId: 'doc-req-001'}});
  assert.equal(replay.idempotent, true);
  assert.equal(google.calls.docsCreate.length, 1);
}

async function testWorkflowRun() {
  const admin = fakeAdmin();
  const google = fakeGoogle();
  const result = await driveWorkflowRunOperation({google, admin, auth, user, args: {
    workflowId: 'workflow-test-001',
    objective: 'Create project folder, story doc, and seed text in one durable bridge call.',
    approved: true,
    operations: [
      {type: 'drive_create_folder', name: 'Workflow Project', saveAs: 'project', requestId: 'workflow-test-001:folder'},
      {type: 'docs_create', title: 'Workflow Story Bible', parentFolderKey: 'project', saveAs: 'story', requestId: 'workflow-test-001:story'},
      {type: 'docs_append', documentKey: 'story', heading: 'Seed', text: 'Bridge-owned workflow text.', requestId: 'workflow-test-001:append'},
    ],
  }});
  assert.equal(result.completed, true);
  assert.equal(result.outputs.project, 'folder12345');
  assert.equal(result.outputs.story, 'doc123456');
  assert.equal(result.results.length, 3);
  assert.equal(admin._docs.get('driveBridgeAudit/workflow-test-001:folder').operation, 'drive.createFolder');
  assert.equal(admin._docs.get('driveBridgeAudit/workflow-test-001:story').operation, 'docs.create');
  assert.equal(admin._docs.get('driveBridgeAudit/workflow-test-001:append').operation, 'docs.append');
  assert.equal(admin._docs.get('driveBridgeRecoveryCheckpoints/workflow-test-001').status, 'completed');
  assert.equal(google.calls.driveCreate.length, 1);
  assert.equal(google.calls.docsCreate.length, 1);
  assert.equal(google.calls.docsBatchUpdate.length, 1);

  const replay = await driveWorkflowRunOperation({google, admin, auth, user, args: {workflowId: 'workflow-test-001', approved: true, operations: [{type: 'drive_create_folder', name: 'Duplicate'}]}});
  assert.equal(replay.idempotent, true);
  assert.equal(google.calls.driveCreate.length, 1);
}

async function testValidation() {
  await assert.rejects(() => createDriveFolderOperation({google: fakeGoogle(), admin: fakeAdmin(), auth, user, args: {}}), /name is required/);
  await assert.rejects(() => createGoogleDocOperation({google: fakeGoogle(), admin: fakeAdmin(), auth, user, args: {}}), /title is required/);
  await assert.rejects(() => createDriveFolderOperation({google: fakeGoogle(), admin: fakeAdmin(), auth, user, args: {name: 'x', parentFolderId: 'bad'}}), /valid Google Drive fileId/);
  await assert.rejects(() => createGoogleDocOperation({google: fakeGoogle(), admin: fakeAdmin(), auth, user, args: {title: 'x', parentFolderId: 'bad'}}), /valid Google Drive fileId/);
}

function testMcpToolSurface() {
  delete process.env.HOME_CENTER_MCP_EXTENDED_TOOLS;
  const minimal = createHomeCenterMcpServer({google: {}, admin: {}, googleClientId: () => '', googleClientSecret: () => ''});
  assert.deepEqual(Object.keys(minimal._registeredTools), [
    'health',
    'drive_search',
    'drive_read',
    'docs_append',
    'drive_create_folder',
    'docs_create',
  ]);

  process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
  const extended = createHomeCenterMcpServer({google: {}, admin: {}, googleClientId: () => '', googleClientSecret: () => ''});
  const extendedTools = Object.keys(extended._registeredTools);
  assert(extendedTools.includes('drive_move'));
  assert(extendedTools.includes('drive_workflow_run'));
  assert(extendedTools.includes('recovery_checkpoint'));
  assert(extendedTools.includes('recovery_status'));
  assert(extendedTools.includes('audit_log'));
  for (const toolName of [
    'github_get_repo',
    'github_read_file',
    'github_list_branches',
    'github_list_issues',
    'github_get_issue',
    'github_create_issue',
    'github_comment_issue',
    'github_list_pull_requests',
    'github_get_pull_request',
    'github_list_pull_request_files',
    'github_comment_pull_request',
    'github_list_workflow_runs',
    'github_get_workflow_run',
  ]) {
    assert(extendedTools.includes(toolName), `expected ${toolName}`);
  }
  assert(!extendedTools.includes('github_merge_pull_request'));
  assert(!extendedTools.includes('github_dispatch_workflow'));
  delete process.env.HOME_CENTER_MCP_EXTENDED_TOOLS;
}

await testCreateFolder();
await testCreateDoc();
function testRecoveryClassification() {
  const normalized = normalizeRecoveryOperation({tool: 'docs_create', requestId: 'doc-req-002', title: 'Recovered Doc', intent: 'Create recovered doc'}, 0);
  assert.equal(normalized.toolName, 'docs_create');
  assert.equal(normalized.targetName, 'Recovered Doc');
  assert.equal(normalized.summary, 'Create recovered doc');

  const status = summarizeRecoveryOperations([
    {toolName: 'docs_append', requestId: 'append-req-001', targetName: 'Skill Index'},
    {toolName: 'docs_create', requestId: 'doc-req-002', targetName: 'Recovered Doc'},
  ], {
    'append-req-001': {actionAudit: {requestId: 'append-req-001', operation: 'docs.append'}},
  });
  assert.equal(status.complete, false);
  assert.equal(status.completed.length, 1);
  assert.equal(status.missing.length, 1);
  assert.equal(status.nextOperation.requestId, 'doc-req-002');
}

await testValidation();
await testWorkflowRun();
testMcpToolSurface();
testRecoveryClassification();
console.log('Drive Bridge create tools mock tests: OK');
