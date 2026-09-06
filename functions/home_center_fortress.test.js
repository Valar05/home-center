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

test('Home Center work receipts survive restart and enforce one Punnett interrogation before execution', async () => {
  const admin = fakeAdmin();
  const auth = extraAuth();
  const serverA = createServer(admin);
  const taskId = 'fortress-interrogation-probe';
  const requestText = 'Patch it.';
  const question = 'Which acceptance surface owns completion?';

  parseToolResult(await callRegisteredHomeCenterTool(serverA, 'fortress_online', {}, auth));
  const requested = parseToolResult(await callRegisteredHomeCenterTool(serverA, 'home_center_work_request', {
    taskId,
    requestText,
    taskKind: 'code_patch_request',
    route: 'fortress_session_probe',
    interrogationQuestion: question,
    interrogationDomain: 'acceptance',
    interrogationAnswer: 'This early answer must not bypass the turn boundary.',
  }, auth));

  assert.equal(requested.ok, true);
  assert.equal(requested.work.normalizedState, 'AWAITING_ANSWER');
  assert.deepEqual(requested.work.statusHistory.map((entry) => entry.state), ['REQUESTED', 'AWAITING_ANSWER']);
  assert.equal(requested.work.interrogation.questionCount, 1);
  assert.equal(requested.work.interrogation.source, 'she-raw');
  assert.equal(requested.work.interrogation.perspective, 'punnett');
  assert.equal(requested.work.interrogation.domain, 'acceptance');
  assert.equal(requested.work.interrogation.question, question);
  assert.equal(requested.work.interrogation.answered, false);
  assert.match(requested.work.receipt.receiptRef, /^firestore:\/\/homeCenterWorkItems\//);

  const serverB = createServer(admin);
  const waitingStatus = parseToolResult(await callRegisteredHomeCenterTool(serverB, 'home_center_work_status', {taskId}, auth));
  assert.equal(waitingStatus.found, true);
  assert.equal(waitingStatus.work.normalizedState, 'AWAITING_ANSWER');
  assert.equal(waitingStatus.work.interrogation.answered, false);
  const waitingSession = parseToolResult(await callRegisteredHomeCenterTool(serverB, 'home_center_session_status', {}, auth));
  assert.equal(waitingSession.orientation.pending_work.length, 1);
  assert.equal(waitingSession.orientation.pending_work[0].interrogation.questionCount, 1);

  const completed = parseToolResult(await callRegisteredHomeCenterTool(serverB, 'home_center_work_request', {
    taskId,
    requestText,
    taskKind: 'code_patch_request',
    route: 'fortress_session_probe',
    interrogationAnswer: 'The durable Home Center receipt.',
  }, auth));

  assert.equal(completed.work.normalizedState, 'SUCCEEDED');
  assert.equal(completed.work.interrogation.answered, true);
  assert.deepEqual(
    completed.work.statusHistory.map((entry) => entry.state),
    ['REQUESTED', 'AWAITING_ANSWER', 'QUEUED', 'RUNNING', 'SUCCEEDED'],
  );
  assert.equal(completed.work.receipt.receiptRef, requested.work.receipt.receiptRef);

  const serverC = createServer(admin);
  const workStatus = parseToolResult(await callRegisteredHomeCenterTool(serverC, 'home_center_work_status', {taskId}, auth));
  assert.equal(workStatus.found, true);
  assert.equal(workStatus.work.normalizedState, 'SUCCEEDED');
  assert.equal(workStatus.work.interrogation.answered, true);

  const sessionStatus = parseToolResult(await callRegisteredHomeCenterTool(serverC, 'home_center_session_status', {}, auth));
  assert.equal(sessionStatus.active, true);
  assert.equal(sessionStatus.orientation.pending_work.length, 0);
  assert.equal(sessionStatus.orientation.recent_completed_work[0].taskId, taskId);
});


test('Home Center full-perspective Punnett records ownership QA and rejects agent-work tax', async () => {
  const admin = fakeAdmin();
  const auth = extraAuth();
  const server = createServer(admin);

  const valid = parseToolResult(await callRegisteredHomeCenterTool(server, 'home_center_work_request', {
    taskId: 'full-perspective-valid-probe',
    requestText: 'Build the commissioned thing.',
    taskKind: 'general_work_request',
    route: 'fortress_session_probe',
    interrogationQuestion: 'Which acceptance surface do you want to own completion?',
    interrogationDomain: 'acceptance',
  }, auth));
  assert.equal(valid.work.normalizedState, 'AWAITING_ANSWER');
  assert.equal(valid.work.interrogation.fullPerspective.version, 'dru.punnett-regnet-reneqa.v1');
  assert.equal(valid.work.interrogation.fullPerspective.mode, 'punnett_full_perspective');
  assert.equal(valid.work.interrogation.fullPerspective.verdict, 'PASS');
  assert.equal(valid.work.interrogation.fullPerspective.passes.regnet.status, 'PASS');
  assert.equal(valid.work.interrogation.fullPerspective.passes.reneQa.status, 'PASS');
  assert.equal(valid.work.interrogation.fullPerspective.passes.punnett.executionClaim, 'not_proven_by_engine');

  await assert.rejects(
    () => callRegisteredHomeCenterTool(server, 'home_center_work_request', {
      taskId: 'implementation-tax-probe',
      requestText: 'Update Regnet QA full perspective Punnett on the engine.',
      taskKind: 'engine_patch_request',
      route: 'fortress_session_probe',
      interrogationQuestion: 'Should the engine make Regnet and Rene QA two distinct passes or merge them into one judgment pass?',
      interrogationDomain: 'authority',
    }, auth),
    (error) => {
      assert.equal(error.code, 'interrogation_implementation_tax');
      assert.equal(error.details.verdict, 'FAIL');
      assert.equal(error.details.mode, 'punnett_full_perspective');
      return true;
    },
  );

  await assert.rejects(
    () => callRegisteredHomeCenterTool(server, 'home_center_work_request', {
      taskId: 'failure-tax-probe',
      requestText: 'Build the thing.',
      taskKind: 'general_work_request',
      route: 'fortress_session_probe',
      interrogationQuestion: 'What failure modes and regression risks should I anticipate?',
      interrogationDomain: 'taste',
    }, auth),
    (error) => {
      assert.equal(error.code, 'user_failure_tax');
      assert.equal(error.details.verdict, 'FAIL');
      return true;
    },
  );
});

test('Home Center work unit converges idempotently from state instead of repeated imperative', async () => {
  const admin = fakeAdmin();
  const auth = extraAuth();
  const server = createServer(admin);
  const taskId = 'outer-door-state-convergence-probe';
  const requestText = 'Apply the known outer-door policy.';

  const waiting = parseToolResult(await callRegisteredHomeCenterTool(server, 'home_center_work_request', {
    taskId,
    requestText,
    taskKind: 'state_convergence_probe',
    route: 'fortress_session_probe',
    interrogationQuestion: 'Is it hot?',
    interrogationDomain: 'constraint',
  }, auth));
  assert.equal(waiting.work.normalizedState, 'AWAITING_ANSWER');
  assert.equal(waiting.work.actionPolicy.version, 'dru.intent-idempotence.v1');
  assert.equal(waiting.work.actionPolicy.mode, 'state_convergence');
  assert.equal(waiting.work.actionPolicy.questionModel, 'state_before_imperative');
  assert.equal(waiting.work.actionPolicy.retryPolicy, 'same_task_id_no_duplicate_execution');
  assert.match(waiting.work.actionPolicy.idempotencyKey, /^home-center-work:[a-f0-9]{32}$/);

  const completed = parseToolResult(await callRegisteredHomeCenterTool(server, 'home_center_work_request', {
    taskId,
    requestText,
    interrogationAnswer: 'Yes. It is hot.',
  }, auth));
  assert.equal(completed.work.normalizedState, 'SUCCEEDED');
  const completedHistory = completed.work.statusHistory;
  const completedReceipt = completed.work.receipt.receiptRef;

  const retried = parseToolResult(await callRegisteredHomeCenterTool(server, 'home_center_work_request', {
    taskId,
    requestText,
    interrogationAnswer: 'Yes. It is hot.',
  }, auth));
  assert.equal(retried.work.normalizedState, 'SUCCEEDED');
  assert.deepEqual(retried.work.statusHistory, completedHistory);
  assert.equal(retried.work.receipt.receiptRef, completedReceipt);
  assert.equal(retried.work.actionPolicy.idempotencyKey, completed.work.actionPolicy.idempotencyKey);
});
