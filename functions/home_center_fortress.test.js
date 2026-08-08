const assert = require('node:assert/strict');
const test = require('node:test');

const {createHomeCenterMcpServer, callRegisteredHomeCenterTool} = require('./home_center_mcp');

function fakeGoogle() {
  return {
    auth: {
      OAuth2: class {
        setCredentials() {}
        on() {}
      },
    },
  };
}

class FakeSnapshot {
  constructor(value, id = '') {
    this.exists = value !== undefined;
    this._value = value;
    this.id = id;
  }
  data() {
    return this.exists ? structuredClone(this._value) : undefined;
  }
}

class FakeFirestore {
  constructor() {
    this.documents = new Map();
  }
  collection(name) {
    return {
      doc: (id) => {
        const key = `${name}/${id}`;
        return {
          key,
          id,
          get: async () => new FakeSnapshot(this.documents.get(key), id),
          set: async (value, options = {}) => {
            const existing = this.documents.get(key) || {};
            this.documents.set(key, options.merge ? {...existing, ...structuredClone(value)} : structuredClone(value));
          },
        };
      },
    };
  }
}

function fakeAdmin() {
  const db = new FakeFirestore();
  const firestore = function firestore() {
    return db;
  };
  firestore.FieldValue = {
    serverTimestamp() {
      return {__serverTimestamp: true};
    },
  };
  return {
    firestore,
    _db: db,
  };
}

function createServer(admin) {
  return createHomeCenterMcpServer({
    google: fakeGoogle(),
    admin,
    googleClientId: () => '',
    googleClientSecret: () => '',
    githubToken: () => '',
    githubAdmin: {},
    cartesiaApiKey: () => '',
    geminiApiKey: () => '',
  });
}

function extraAuth(email = 'drew@example.com') {
  return {
    homeCenterAuth: {
      user: {email, authKind: 'test'},
      auth: {},
    },
  };
}

function parseToolResult(result) {
  const text = Array.isArray(result && result.content)
    ? result.content.map((item) => item && item.type === 'text' ? item.text : '').join('\n').trim()
    : '';
  return text ? JSON.parse(text) : {};
}

test('Fortress Online reconstructs the durable objective after a fresh Home Center server instance', async () => {
  const admin = fakeAdmin();
  const serverA = createServer(admin);
  const auth = extraAuth();

  const orientA = parseToolResult(await callRegisteredHomeCenterTool(serverA, 'fortress_online', {}, auth));
  assert.equal(orientA.ok, true);
  assert.equal(orientA.createdSession, true);
  assert.equal(orientA.orientation.current_objective, '');

  const updated = parseToolResult(await callRegisteredHomeCenterTool(serverA, 'home_center_session_update', {
    currentObjective: 'We\'re fixing Vanguard SwordAttack3 drift.',
    objectiveStatement: 'We\'re fixing Vanguard SwordAttack3 drift.',
  }, auth));
  assert.equal(updated.ok, true);
  assert.equal(updated.orientation.current_objective, 'We\'re fixing Vanguard SwordAttack3 drift.');

  const serverB = createServer(admin);
  const orientB = parseToolResult(await callRegisteredHomeCenterTool(serverB, 'fortress_online', {}, auth));
  assert.equal(orientB.ok, true);
  assert.equal(orientB.createdSession, false);
  assert.equal(orientB.orientation.current_objective, 'We\'re fixing Vanguard SwordAttack3 drift.');

  const status = parseToolResult(await callRegisteredHomeCenterTool(serverB, 'home_center_session_status', {}, auth));
  assert.equal(status.active, true);
  assert.equal(status.orientation.current_objective, 'We\'re fixing Vanguard SwordAttack3 drift.');
  assert.equal(
    [...admin._db.documents.keys()].filter((key) => key.startsWith('homeCenterSessions/')).length,
    1,
  );
});

test('Home Center work receipts survive restart and stay readable through session status', async () => {
  const admin = fakeAdmin();
  const auth = extraAuth();
  const serverA = createServer(admin);

  parseToolResult(await callRegisteredHomeCenterTool(serverA, 'fortress_online', {}, auth));
  const requested = parseToolResult(await callRegisteredHomeCenterTool(serverA, 'home_center_work_request', {
    requestText: 'Patch it.',
    taskKind: 'code_patch_request',
    route: 'fortress_session_probe',
  }, auth));

  assert.equal(requested.ok, true);
  assert.equal(requested.work.normalizedState, 'SUCCEEDED');
  assert.deepEqual(
    requested.work.statusHistory.map((entry) => entry.state),
    ['REQUESTED', 'QUEUED', 'RUNNING', 'SUCCEEDED'],
  );
  assert.match(requested.work.receipt.receiptRef, /^firestore:\/\/homeCenterWorkItems\//);

  const serverB = createServer(admin);
  const workStatus = parseToolResult(await callRegisteredHomeCenterTool(serverB, 'home_center_work_status', {}, auth));
  assert.equal(workStatus.found, true);
  assert.equal(workStatus.work.normalizedState, 'SUCCEEDED');
  assert.equal(workStatus.work.receipt.receiptRef, requested.work.receipt.receiptRef);

  const sessionStatus = parseToolResult(await callRegisteredHomeCenterTool(serverB, 'home_center_session_status', {}, auth));
  assert.equal(sessionStatus.active, true);
  assert.equal(sessionStatus.orientation.pending_work.length, 0);
  assert.equal(sessionStatus.orientation.recent_completed_work[0].taskId, requested.work.taskId);
});
