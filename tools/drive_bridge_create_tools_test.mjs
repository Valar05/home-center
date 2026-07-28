#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {createDriveFolderOperation, createGoogleDocOperation, publishContextSnapshotOperation, createSheetOperation, updateSheetValuesOperation, importXlsxWorkbookOperation, driveOperationRunOperation, driveWorkflowRunOperation, simulationOperationRunOperation, createHomeCenterMcpServer, normalizeRecoveryOperation, summarizeRecoveryOperations, loadMcpAccessContext} = require('../functions/home_center_mcp.js');

function tokenHash(value) {
  return createHash('sha256').update(String(value || '')).digest('hex');
}

function fakeAdmin(options = {}) {
  const docs = new Map();
  const fail = options.fail || {};
  const maybeFail = (name, op) => {
    if (fail[`${name}.${op}`] || fail[op] || fail[name]) throw new Error(`Injected Firestore failure: ${name}.${op}`);
  };
  const api = {
    _docs: docs,
    firestore() {
      return {
        batch() {
          const writes = [];
          return {
            set(ref, payload, options = {}) {
              writes.push({ref, payload, options});
            },
            async commit() {
              for (const write of writes) await write.ref.set(write.payload, write.options);
            },
          };
        },
        collection(name) {
          return {
            doc(id) {
              const key = name + '/' + id;
              return {
                async get() {
                  maybeFail(name, 'get');
                  return {exists: docs.has(key), data: () => docs.get(key)};
                },
                async set(payload, options = {}) {
                  maybeFail(name, 'set');
                  docs.set(key, options && options.merge && docs.has(key) ? {...docs.get(key), ...payload} : payload);
                },
              };
            },
            async add(payload) {
              maybeFail(name, 'add');
              const id = 'auto-' + (docs.size + 1);
              docs.set(name + '/' + id, payload);
              return {id};
            },
            where(field, op, value) {
              const run = async () => {
                maybeFail(name, 'whereGet');
                const found = [];
                for (const [key, payload] of docs.entries()) {
                  if (key.startsWith(name + '/') && payload && payload[field] === value) found.push({data: () => payload});
                }
                return {empty: found.length === 0, docs: found};
              };
              return {
                async get() {
                  return run();
                },
                limit() {
                  return {async get() { return run(); }};
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


async function collectFakeMediaBody(body) {
  if (!body) return Buffer.alloc(0);
  if (Buffer.isBuffer(body)) return body;
  if (typeof body === 'string') return Buffer.from(body, 'utf8');
  if (body instanceof ArrayBuffer) return Buffer.from(body);
  if (ArrayBuffer.isView(body)) return Buffer.from(body.buffer, body.byteOffset, body.byteLength);
  const chunks = [];
  if (typeof body[Symbol.asyncIterator] === 'function') {
    for await (const chunk of body) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk), 'utf8'));
    return Buffer.concat(chunks);
  }
  if (typeof body[Symbol.iterator] === 'function') {
    for (const chunk of body) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk), 'utf8'));
    return Buffer.concat(chunks);
  }
  return Buffer.from(String(body || ''), 'utf8');
}

function fakeGoogle(options = {}) {
  const calls = {driveCreate: [], driveUpdate: [], driveGet: [], driveList: [], docsCreate: [], docsGet: [], docsBatchUpdate: [], sheetsCreate: [], sheetsValuesGet: [], sheetsValuesUpdate: [], sheetsGet: []};
  const mediaById = options.mediaById || {};
  let docCounter = 0;
  const fail = options.fail || {};
  const maybeFail = (op) => {
    if (fail[op]) {
      const err = new Error(fail[op].message || `Injected Google failure: ${op}`);
      err.status = fail[op].status || 500;
      err.response = fail[op].response;
      throw err;
    }
  };
  return {
    calls,
    drive() {
      return {
        files: {
          async list(params) {
            maybeFail('driveList');
            calls.driveList.push(params);
            return {data: {files: options.driveListFiles || []}};
          },
          async create(params) {
            maybeFail('driveCreate');
            calls.driveCreate.push(params);
            if (params.requestBody && params.requestBody.mimeType === 'application/vnd.google-apps.spreadsheet') {
              return {data: {id: options.fixedImportedSpreadsheetId || 'importedSheet123', name: params.requestBody.name, mimeType: params.requestBody.mimeType, webViewLink: 'https://sheets/importedSheet123', parents: params.requestBody.parents || []}};
            }
            if (params.media) {
              const id = options.fixedFileId || 'snapshotFile123';
              mediaById[id] = await collectFakeMediaBody(params.media.body);
              return {data: {id, name: params.requestBody.name, mimeType: params.requestBody.mimeType, webViewLink: `https://drive/${id}`, parents: params.requestBody.parents || []}};
            }
            return {data: {id: 'folder12345', name: params.requestBody.name, mimeType: params.requestBody.mimeType, webViewLink: 'https://drive/folder12345', parents: params.requestBody.parents || []}};
          },
          async update(params) {
            maybeFail('driveUpdate');
            calls.driveUpdate.push(params);
            if (params.media) mediaById[params.fileId] = await collectFakeMediaBody(params.media.body);
            return {data: {id: params.fileId, name: params.requestBody && params.requestBody.name || options.titleById && options.titleById[params.fileId] || 'Updated File', mimeType: params.requestBody && params.requestBody.mimeType || 'text/markdown', webViewLink: `https://drive/${params.fileId}`, parents: params.addParents ? [params.addParents] : ['folder12345']}};
          },
          async get(params) {
            maybeFail('driveGet');
            calls.driveGet.push(params);
            if (params.alt === 'media') return {data: mediaById[params.fileId] || Buffer.from('xlsx')};
            if (params.fileId === 'folder12345') return {data: {id: 'folder12345', name: 'Workflow Project', mimeType: 'application/vnd.google-apps.folder', webViewLink: 'https://drive/folder12345', parents: []}};
            if (params.fileId === (options.fixedImportedSpreadsheetId || 'importedSheet123')) return {data: {id: params.fileId, name: 'Imported Workbook', mimeType: 'application/vnd.google-apps.spreadsheet', webViewLink: `https://sheets/${params.fileId}`, parents: ['folder12345']}};
            if (mediaById[params.fileId]) return {data: {id: params.fileId, name: options.titleById && options.titleById[params.fileId] || 'Snapshot File', mimeType: 'text/markdown', webViewLink: `https://drive/${params.fileId}`, parents: ['folder12345']}};
            return {data: {id: params.fileId, name: options.titleById && options.titleById[params.fileId] || 'Created Doc', mimeType: 'application/vnd.google-apps.document', webViewLink: `https://docs/${params.fileId}`, parents: ['folder12345']}};
          },
        },
      };
    },
    docs() {
      return {
        documents: {
          async create(params) {
            maybeFail('docsCreate');
            calls.docsCreate.push(params);
            docCounter += 1;
            const documentId = options.fixedDocumentId || `doc123456${docCounter}`;
            if (options.titleById) options.titleById[documentId] = params.requestBody.title;
            return {data: {documentId}};
          },
          async get(params) {
            maybeFail('docsGet');
            calls.docsGet.push(params);
            return {data: {body: {content: [{endIndex: 2}]}}};
          },
          async batchUpdate(params) {
            maybeFail('docsBatchUpdate');
            calls.docsBatchUpdate.push(params);
            return {data: {}};
          },
        },
      };
    },
    sheets() {
      return {
        spreadsheets: {
          async create(params) {
            maybeFail('sheetsCreate');
            calls.sheetsCreate.push(params);
            return {data: {spreadsheetId: options.fixedSpreadsheetId || 'sheet123456', spreadsheetUrl: 'https://sheets/sheet123456', properties: {title: params.requestBody.properties.title}, sheets: [{properties: {sheetId: 1, title: params.requestBody.sheets[0].properties.title, index: 0, gridProperties: {rowCount: 1000, columnCount: 26}}}]}};
          },
          async get(params) {
            maybeFail('sheetsGet');
            calls.sheetsGet.push(params);
            if (params.spreadsheetId === (options.fixedImportedSpreadsheetId || 'importedSheet123')) {
              const sheets = options.importedSheetNames || ['README', 'CANON'];
              return {data: {spreadsheetId: params.spreadsheetId, spreadsheetUrl: `https://sheets/${params.spreadsheetId}`, properties: {title: 'Imported Workbook'}, sheets: sheets.map((title, index) => ({properties: {sheetId: index + 1, title, index, gridProperties: {rowCount: 1000, columnCount: 26, frozenRowCount: index === 0 ? 1 : 0, frozenColumnCount: 0}}}))}};
            }
            return {data: {spreadsheetId: params.spreadsheetId, spreadsheetUrl: `https://sheets/${params.spreadsheetId}`, properties: {title: 'Budget'}, sheets: [{properties: {sheetId: 1, title: 'Sheet1', index: 0, gridProperties: {rowCount: 1000, columnCount: 26}}}]}};
          },
          values: {
            async get(params) {
              maybeFail('sheetsValuesGet');
              calls.sheetsValuesGet.push(params);
              const name = String(params.range || '').replace(/^'/, '').replace(/'$/, '').replace(/''/g, "'");
              const importedValues = options.valuesBySheet || {};
              if (Object.prototype.hasOwnProperty.call(importedValues, name)) {
                return {data: {range: params.range, majorDimension: 'ROWS', values: importedValues[name]}};
              }
              return {data: {range: params.range, majorDimension: 'ROWS', values: [['Name', 'Amount'], ['Coffee', '5']]}};
            },
            async update(params) {
              maybeFail('sheetsValuesUpdate');
              calls.sheetsValuesUpdate.push(params);
              return {data: {spreadsheetId: params.spreadsheetId, updatedRange: params.range, updatedRows: (params.requestBody.values || []).length}};
            },
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
  const google = fakeGoogle({fixedDocumentId: 'doc123456'});
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

async function testDocsCreateIncidentPayloads() {
  const admin = fakeAdmin();
  const titleById = {};
  const google = fakeGoogle({titleById});

  const minimal = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Test Document'}});
  assert.equal(minimal.documentId, 'doc1234561');
  assert.equal(google.calls.docsCreate.length, 1);

  const withRequestId = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Test Document', requestId: 'docs-create-test-001'}});
  assert.equal(withRequestId.documentId, 'doc1234562');
  const replay = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Test Document Replay', requestId: 'docs-create-test-001'}});
  assert.equal(replay.idempotent, true);
  assert.equal(replay.documentId, 'doc1234562');
  assert.equal(google.calls.docsCreate.length, 2);

  const withParent = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Parented Document', parentFolderId: '1YGQNw22f_WXe52SqPv9oMqHLK6DK-p_K', requestId: 'docs-create-parent-001'}});
  assert.equal(withParent.parentFolderId, 'folder12345');
  assert.equal(google.calls.driveUpdate.at(-1).addParents, '1YGQNw22f_WXe52SqPv9oMqHLK6DK-p_K');

  const unicode = await createGoogleDocOperation({google, admin, auth, user, args: {
    title: 'Research Organ 04 — Second Commandment of Human Simulation: Explanation Is Evidence, Not Verdict',
    parentFolderId: '1YGQNw22f_WXe52SqPv9oMqHLK6DK-p_K',
    initialText: 'Research Organ 04 — Second Commandment\n\nA PERSON’S EXPLANATION IS EVIDENCE, NOT VERDICT.',
    requestId: 'docs-create-unicode-001',
  }});
  assert.equal(unicode.documentId, 'doc1234564');
  assert.equal(google.calls.docsBatchUpdate.at(-1).requestBody.requests[0].insertText.text.includes('PERSON’S'), true);

  const longBody = 'Long body.\n'.repeat(701);
  assert(longBody.length > 6000);
  const long = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Long Body Document', initialText: longBody, requestId: 'docs-create-long-001'}});
  assert.equal(long.documentId, 'doc1234565');
  assert.equal(google.calls.docsBatchUpdate.at(-1).requestBody.requests[0].insertText.text.length, longBody.length);

  const next = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Different Request After Success', requestId: 'docs-create-next-001'}});
  assert.equal(next.documentId, 'doc1234566');
  assert.equal(google.calls.docsCreate.length, 6);
}

async function testDocsCreateSchemaMatchesRuntime() {
  delete process.env.HOME_CENTER_MCP_EXTENDED_TOOLS;
  const server = createHomeCenterMcpServer({google: {}, admin: {}, googleClientId: () => '', googleClientSecret: () => ''});
  const schema = server._registeredTools.docs_create.inputSchema;
  const payload = {
    title: 'Schema Accepted Runtime Accepted',
    parentFolderId: '1YGQNw22f_WXe52SqPv9oMqHLK6DK-p_K',
    initialText: 'Published schema fields are runtime accepted.',
    requestId: 'docs-create-schema-runtime-001',
    callerNote: 'Schema/runtime contract test',
  };
  assert.equal(schema.safeParse(payload).success, true, 'published docs_create schema accepts all documented fields');
  assert.equal(schema.safeParse({...payload, approved: true}).success, true, 'docs_create schema does not require approved=true');
  const admin = fakeAdmin();
  const google = fakeGoogle({fixedDocumentId: 'schemaDoc123'});
  const result = await createGoogleDocOperation({google, admin, auth, user, args: payload});
  assert.equal(result.documentId, 'schemaDoc123');
}

async function testDocsCreateFailureRecovery() {
  {
    const result = await createGoogleDocOperation({google: fakeGoogle(), admin: fakeAdmin({fail: {'driveBridgeAudit.get': true}}), auth, user, args: {title: 'Audit Store Unavailable', requestId: 'docs-create-audit-read-fail'}});
    assert.equal(result.ok, false);
    assert.equal(result.error.code, 'DOCS_CREATE_AUDIT_FAILED');
    assert.equal(result.error.stage, 'idempotency_state_read');
  }
  {
    const admin = fakeAdmin();
    const google = fakeGoogle({fixedDocumentId: 'partialTextDoc', fail: {docsBatchUpdate: {status: 400, message: 'bad insert'}}});
    const result = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Text Insert Fails', initialText: 'body', requestId: 'docs-create-text-fail'}});
    assert.equal(result.ok, false);
    assert.equal(result.error.code, 'DOCS_CREATE_TEXT_INSERT_FAILED');
    assert.equal(result.partial.documentId, 'partialTextDoc');
    assert.equal(admin._docs.get('driveBridgeOperationState/docs-create-text-fail').status, 'text_insert_failed');
  }
  {
    const admin = fakeAdmin();
    const google = fakeGoogle({fixedDocumentId: 'partialAuditDoc'});
    const original = admin.firestore;
    admin.firestore = function wrappedFirestore() {
      const db = original.call(admin);
      const originalCollection = db.collection;
      db.collection = function wrappedCollection(name) {
        const col = originalCollection.call(db, name);
        if (name !== 'driveBridgeAudit') return col;
        const originalDoc = col.doc;
        col.doc = function wrappedDoc(id) {
          const doc = originalDoc.call(col, id);
          return {...doc, async set() { throw new Error('audit write down'); }};
        };
        return col;
      };
      return db;
    };
    const result = await createGoogleDocOperation({google, admin, auth, user, args: {title: 'Audit Write Fails', requestId: 'docs-create-audit-write-fail'}});
    assert.equal(result.ok, false);
    assert.equal(result.error.code, 'DOCS_CREATE_AUDIT_FAILED');
    assert.equal(result.error.stage, 'audit_write');
    assert.equal(result.partial.documentId, 'partialAuditDoc');
  }
}

async function testMcpOAuthRefreshUsesSecretValues() {
  const accessToken = 'bridge-access-token-for-oauth-client-test';
  const admin = fakeAdmin();
  admin._docs.set('mcpOAuthAccessTokens/' + tokenHash(accessToken), {
    email: 'writer@example.com',
    expiresAtMs: Date.now() + 60000,
    googleTokens: {refresh_token: 'stored-refresh-token'},
  });
  const constructed = [];
  const google = {
    auth: {
      OAuth2: class FakeOAuth2 {
        constructor(clientId, clientSecret, redirectUri) {
          constructed.push({clientId, clientSecret, redirectUri});
        }
        setCredentials(credentials) {
          this.credentials = credentials;
        }
        on() {}
      },
    },
  };
  const context = await loadMcpAccessContext(admin, google, () => 'actual-client-id', () => 'actual-client-secret', accessToken);
  assert.equal(context.user.email, 'writer@example.com');
  assert.equal(constructed[0].clientId, 'actual-client-id');
  assert.equal(constructed[0].clientSecret, 'actual-client-secret');
  assert.notEqual(typeof constructed[0].clientId, 'function');
}

async function testWorkflowRun() {
  const admin = fakeAdmin();
  const google = fakeGoogle({fixedDocumentId: 'doc123456'});
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


async function testContextSyncPublishSnapshot() {
  const admin = fakeAdmin();
  const google = fakeGoogle({fixedFileId: 'snapshotFile123'});
  const content = `# Snapshot\n\nDurable content.\n`;
  const sha256 = createHash('sha256').update(content).digest('hex');
  const result = await publishContextSnapshotOperation({google, admin, auth, user, args: {
    name: 'AGENTS.md',
    parentFolderId: 'folder12345',
    content,
    byteCount: Buffer.byteLength(content),
    sha256,
    requestId: 'context-sync-publish-001',
    callerNote: 'Publish AGENTS snapshot',
  }});
  assert.equal(result.fileId, 'snapshotFile123');
  assert.equal(result.byteCount, Buffer.byteLength(content));
  assert.equal(result.sha256, sha256);
  assert.equal(result.readbackSha256, sha256);
  assert.equal(result.verified, true);
  assert.equal(google.calls.driveCreate.length, 1);
  assert.equal(google.calls.driveCreate[0].media.mimeType, 'text/markdown');
  assert.equal(admin._docs.get('driveBridgeAudit/context-sync-publish-001').operation, 'contextSync.publishSnapshot');

  const replay = await publishContextSnapshotOperation({google, admin, auth, user, args: {name: 'AGENTS.md', content: 'changed', requestId: 'context-sync-publish-001'}});
  assert.equal(replay.idempotent, true);
  assert.equal(google.calls.driveCreate.length, 1);

  await assert.rejects(() => publishContextSnapshotOperation({google: fakeGoogle(), admin: fakeAdmin(), auth, user, args: {name: 'Bad Hash', content, sha256: '0'.repeat(64), requestId: 'context-sync-bad-hash'}}), /sha256 mismatch/);
}

async function testDriveOperationContextSyncPublishSnapshot() {
  const admin = fakeAdmin();
  const google = fakeGoogle({fixedFileId: 'snapshotFile456'});
  const content = `Skills snapshot\n`;
  const sha256 = createHash('sha256').update(content).digest('hex');
  const result = await driveOperationRunOperation({google, admin, auth, user, args: {
    operation: 'context_sync.publish_snapshot',
    operationBatchId: 'context-sync-operation-001',
    args: {
      name: 'SKILLS.md',
      parentFolderId: 'folder12345',
      content,
      byteCount: Buffer.byteLength(content),
      sha256,
      requestId: 'context-sync-operation-001:skills',
      callerNote: 'Registry publish',
    },
  }});
  assert.equal(result.operation, 'context_sync.publish_snapshot');
  assert.equal(result.completed, true);
  assert.equal(result.result.fileId, 'snapshotFile456');
  assert.equal(result.result.verified, true);
  assert.equal(admin._docs.get('driveBridgeAudit/context-sync-operation-001:skills').operation, 'contextSync.publishSnapshot');
}

async function testSheetsCreateAndUpdate() {
  const admin = fakeAdmin();
  const google = fakeGoogle({fixedSpreadsheetId: 'sheet123456'});
  const created = await createSheetOperation({google, admin, auth, user, args: {
    title: 'Household Budget',
    sheetTitle: 'Ledger',
    parentFolderId: 'folder12345',
    values: [['Item', 'Amount'], ['Coffee', 5]],
    requestId: 'sheet-create-001',
    callerNote: 'Create household budget sheet',
  }});
  assert.equal(created.spreadsheetId, 'sheet123456');
  assert.equal(created.sheetTitle, 'Ledger');
  assert.equal(google.calls.sheetsCreate.length, 1);
  assert.equal(google.calls.sheetsValuesUpdate.length, 1);
  assert.equal(google.calls.sheetsValuesUpdate[0].range, 'Ledger!A1');
  assert.equal(google.calls.driveUpdate.at(-1).addParents, 'folder12345');
  assert.equal(admin._docs.get('driveBridgeAudit/sheet-create-001').operation, 'sheets.create');

  const replay = await createSheetOperation({google, admin, auth, user, args: {title: 'Duplicate Budget', requestId: 'sheet-create-001'}});
  assert.equal(replay.idempotent, true);
  assert.equal(google.calls.sheetsCreate.length, 1);

  const updated = await updateSheetValuesOperation({google, admin, auth, user, args: {
    spreadsheetId: 'sheet123456',
    range: 'Ledger!A2:B2',
    values: [['Tea', 4]],
    requestId: 'sheet-update-001',
  }});
  assert.equal(updated.spreadsheetId, 'sheet123456');
  assert.equal(updated.range, 'Ledger!A2:B2');
  assert.equal(google.calls.sheetsValuesUpdate.at(-1).range, 'Ledger!A2:B2');
  assert.equal(admin._docs.get('driveBridgeAudit/sheet-update-001').operation, 'sheets.updateValues');
}

async function testWorkbookImportXlsx() {
  const admin = fakeAdmin();
  const sheetNames = ['README', 'CANON', 'HISTORICAL_RAILS', 'FACTORS', 'STATE', 'CASES', 'ACTIONS', 'CONTROL', 'ENGINE', 'TRACE', 'SOURCES'];
  const valuesBySheet = Object.fromEntries(sheetNames.map((name, index) => [name, [['Name', 'Value'], [name, index]]]));
  const google = fakeGoogle({fixedImportedSpreadsheetId: 'importedSheet123', importedSheetNames: sheetNames, valuesBySheet});
  const sourceCounts = Object.fromEntries(sheetNames.map((name) => [name, 4]));
  const imported = await importXlsxWorkbookOperation({google, admin, auth, user, args: {
    workbookBase64: Buffer.from('fake xlsx bytes').toString('base64'),
    fileName: 'Lexen_Vigil_Judgment_Engine.xlsx',
    title: 'Lexen Vigil Judgment Engine',
    parentFolderId: 'folder12345',
    expectedSheetNames: sheetNames,
    expectedPopulatedCellCounts: sourceCounts,
    requestId: 'workbook-import-001',
    callerNote: 'Import Lexen workbook',
  }});
  assert.equal(imported.spreadsheetId, 'importedSheet123');
  assert.deepEqual(imported.sheetNames, sheetNames);
  assert.equal(imported.warnings.length, 0);
  assert.equal(imported.populatedCellCountDiffs.every((entry) => entry.status === 'matched'), true);
  assert.equal(google.calls.driveCreate.length, 1);
  assert.equal(google.calls.driveCreate[0].requestBody.mimeType, 'application/vnd.google-apps.spreadsheet');
  assert.equal(google.calls.driveCreate[0].media.mimeType, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  assert.equal(google.calls.driveCreate[0].requestBody.parents[0], 'folder12345');
  assert.equal(google.calls.sheetsValuesGet.length, sheetNames.length);
  assert.equal(admin._docs.get('driveBridgeAudit/workbook-import-001').operation, 'workbook.importXlsx');

  const replay = await importXlsxWorkbookOperation({google, admin, auth, user, args: {workbookBase64: Buffer.from('other').toString('base64'), requestId: 'workbook-import-001'}});
  assert.equal(replay.idempotent, true);
  assert.equal(google.calls.driveCreate.length, 1);
}

async function testWorkbookImportResolvesDriveSourceFile() {
  const admin = fakeAdmin();
  const sheetNames = ['README'];
  const google = fakeGoogle({
    fixedImportedSpreadsheetId: 'resolvedImport123',
    importedSheetNames: sheetNames,
    valuesBySheet: {README: [['A']]},
    driveListFiles: [{id: 'xlsxSource123', name: 'Lexen_Vigil_Judgment_Engine.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', parents: ['sourceFolder123']}],
    mediaById: {xlsxSource123: Buffer.from('source xlsx bytes')},
  });
  const result = await importXlsxWorkbookOperation({google, admin, auth, user, args: {
    sourceFileName: 'Lexen_Vigil_Judgment_Engine.xlsx',
    sourceFolderId: 'sourceFolder123',
    parentFolderId: 'folder12345',
    expectedSheetNames: sheetNames,
    expectedPopulatedCellCounts: {README: 1},
    requestId: 'workbook-import-resolve-001',
  }});
  assert.equal(result.spreadsheetId, 'resolvedImport123');
  assert.equal(result.sourceFileId, 'xlsxSource123');
  assert.equal(google.calls.driveList.length, 1);
  assert.equal(google.calls.driveGet.some((call) => call.fileId === 'xlsxSource123' && call.alt === 'media'), true);
  assert.equal(admin._docs.get('driveBridgeAudit/workbook-import-resolve-001').operation, 'workbook.importXlsx');
}

async function testDriveOperationRegistryRunner() {
  const admin = fakeAdmin();
  const sheetNames = ['README', 'CANON'];
  const google = fakeGoogle({fixedImportedSpreadsheetId: 'operationImport123', importedSheetNames: sheetNames, valuesBySheet: {README: [['A']], CANON: [['B']]}});
  const result = await driveOperationRunOperation({google, admin, auth, user, args: {
    operation: 'workbook_import_xlsx',
    operationBatchId: 'drive-operation-workbook-001',
    args: {
      workbookBase64: Buffer.from('fake xlsx bytes').toString('base64'),
      fileName: 'Lexen_Vigil_Judgment_Engine.xlsx',
      expectedSheetNames: sheetNames,
      expectedPopulatedCellCounts: {README: 1, CANON: 1},
      requestId: 'drive-operation-workbook-001:import',
      callerNote: 'Registry import',
    },
  }});
  assert.equal(result.operation, 'workbook_import_xlsx');
  assert.equal(result.completed, true);
  assert.equal(result.result.spreadsheetId, 'operationImport123');
  assert.deepEqual(result.result.sheetNames, sheetNames);
  assert.equal(admin._docs.get('driveBridgeAudit/drive-operation-workbook-001:import').operation, 'workbook.importXlsx');
  const registry = createHomeCenterMcpServer({google: {}, admin: {}, googleClientId: () => '', googleClientSecret: () => ''})._registeredTools.health;
  assert(registry, 'health tool exists for liveness');
}


async function testSimulationOperationFrameLifecycle() {
  const admin = fakeAdmin();
  const project = await simulationOperationRunOperation({admin, user, args: {operation: 'simulation_project_create', args: {projectId: 'sim-project-lexen', title: 'Lexen WWII', doctrine: 'Preserve uncertainty.', requestId: 'sim-test-project'}}});
  assert.equal(project.result.project.projectId, 'sim-project-lexen');

  const begin = await simulationOperationRunOperation({admin, user, args: {operation: 'simulation_reference_begin', args: {projectId: 'sim-project-lexen', compilationId: 'sim-compilation-lexen-001', title: 'Lexen reference', requestId: 'sim-test-begin'}}});
  assert.equal(begin.result.compilation.status, 'open');

  const markdown = `# Project Identity
purpose: Normandy campaign simulation

## Entity: Lexen Vigil
id: character.lexen_vigil
type: character
confidence: high
rank_at_normandy: sergeant

Lexen is a Sherman commander at Normandy.

Sources:
- drive:1abc123

## Entity: Lexen Vigil Alternate
id: character.lexen_vigil
type: character
confidence: medium
rank_at_normandy: lieutenant

A conflicting note says Lexen is a lieutenant.

Sources:
- github:Valar05/example/file.md#L1-L4
`;
  await simulationOperationRunOperation({admin, user, args: {operation: 'simulation_reference_append', args: {compilationId: 'sim-compilation-lexen-001', sequence: 0, content: markdown, requestId: 'sim-test-append-0'}}});
  const retry = await simulationOperationRunOperation({admin, user, args: {operation: 'simulation_reference_append', args: {compilationId: 'sim-compilation-lexen-001', sequence: 0, content: markdown, requestId: 'sim-test-append-0-retry'}}});
  assert.equal(retry.result.idempotent, true);

  const finalized = await simulationOperationRunOperation({admin, user, args: {operation: 'simulation_reference_finalize', args: {compilationId: 'sim-compilation-lexen-001', requestId: 'sim-test-finalize'}}});
  assert.equal(finalized.result.compilation.status, 'finalized');

  const frame = await simulationOperationRunOperation({admin, user, args: {operation: 'build_simulation_frame', args: {projectId: 'sim-project-lexen', compilationId: 'sim-compilation-lexen-001', frameId: 'sim-frame-lexen-v1', activate: true, requestId: 'sim-test-build'}}});
  assert.equal(frame.result.frame.frameId, 'sim-frame-lexen-v1');
  assert.equal(frame.result.manifest.unresolvedConflictCount, 1);
  assert.equal(admin._docs.get('simulationProjects/sim-project-lexen').activeFrameId, 'sim-frame-lexen-v1');

  const query = await simulationOperationRunOperation({admin, user, args: {operation: 'simulation_frame_query', args: {projectId: 'sim-project-lexen', query: 'Lexen Normandy rank', limit: 5}}});
  assert.equal(query.result.frameId, 'sim-frame-lexen-v1');
  assert(query.result.records.length >= 1);
  assert(query.result.conflicts.length >= 1);

  const routedQuery = await driveOperationRunOperation({google: fakeGoogle(), admin, auth, user, args: {operation: 'simulation_frame_query', args: {projectId: 'sim-project-lexen', query: 'Lexen Normandy rank', limit: 5}}});
  assert.equal(routedQuery.completed, true);
  assert.equal(routedQuery.result.frameId, 'sim-frame-lexen-v1');
  assert(routedQuery.result.records.length >= 1);

  const packet = await simulationOperationRunOperation({admin, user, args: {operation: 'simulation_context_packet', args: {projectId: 'sim-project-lexen', query: 'Lexen Normandy rank', maxChars: 4000}}});
  assert(packet.result.packet.includes('Simulation Context Packet'));
  assert(packet.result.packet.includes('Invention Guard'));

  const run = await simulationOperationRunOperation({admin, user, args: {operation: 'run_simulation_frame', args: {projectId: 'sim-project-lexen', prompt: 'What does Lexen know at Normandy?'}}});
  assert.equal(run.result.runMode, 'deterministic_context_handoff_v1');
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
    'readiness',
    'drive_search',
    'drive_read',
    'sheets_search',
    'sheets_read',
    'workbook_import_xlsx',
    'docs_append',
    'simulation_operation',
    'storage_ingest_artifact',
    'drive_ingest_file',
    'render_blender_glb',
    'cartesia_voices',
    'cartesia_synthesize',
    'command_center_operation',
    'drive_create_folder',
    'docs_create',
  ]);

  process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
  const extended = createHomeCenterMcpServer({google: {}, admin: {}, googleClientId: () => '', googleClientSecret: () => ''});
  const extendedTools = Object.keys(extended._registeredTools);
  assert(extendedTools.includes('drive_move'));
  assert(extendedTools.includes('drive_workflow_run'));
  assert(extendedTools.includes('drive_operation'));
  assert(minimal._registeredTools.health, 'minimal server exposes liveness');
  assert(minimal._registeredTools.readiness, 'minimal server exposes readiness');
  assert(extendedTools.includes('workbook_import_xlsx'));
  assert(extendedTools.includes('sheets_create'));
  assert(extendedTools.includes('sheets_update_values'));
  assert(!extendedTools.includes('sheets_delete'));
  assert(!extendedTools.includes('sheets_trash'));
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
await testDocsCreateIncidentPayloads();
await testDocsCreateSchemaMatchesRuntime();
await testDocsCreateFailureRecovery();
await testContextSyncPublishSnapshot();
await testDriveOperationContextSyncPublishSnapshot();
await testSheetsCreateAndUpdate();
await testWorkbookImportXlsx();
await testWorkbookImportResolvesDriveSourceFile();
await testDriveOperationRegistryRunner();
await testSimulationOperationFrameLifecycle();
await testMcpOAuthRefreshUsesSecretValues();
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
