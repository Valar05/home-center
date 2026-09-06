'use strict';

const fs = require('node:fs');

function replaceOnce(text, before, after, label) {
  const first = text.indexOf(before);
  if (first < 0) throw new Error(`Missing patch anchor: ${label}`);
  if (text.indexOf(before, first + before.length) >= 0) throw new Error(`Ambiguous patch anchor: ${label}`);
  return text.slice(0, first) + after + text.slice(first + before.length);
}

const fortressPath = 'functions/home_center_fortress.js';
let fortress = fs.readFileSync(fortressPath, 'utf8');

fortress = replaceOnce(
  fortress,
  "const FULL_PERSPECTIVE_VERSION = 'dru.punnett-regnet-reneqa.v1';\n",
  "const FULL_PERSPECTIVE_VERSION = 'dru.punnett-regnet-reneqa.v1';\nconst INTENT_IDEMPOTENCE_VERSION = 'dru.intent-idempotence.v1';\n",
  'intent idempotence version',
);

fortress = replaceOnce(
  fortress,
  `function hashText(value, length = 16) {
  return createHash('sha256').update(String(value || '')).digest('hex').slice(0, length);
}

function slug`,
  `function hashText(value, length = 16) {
  return createHash('sha256').update(String(value || '')).digest('hex').slice(0, length);
}

function idempotentActionPolicy(taskId) {
  const stableTaskId = safeText(taskId, 120);
  return {
    version: INTENT_IDEMPOTENCE_VERSION,
    mode: 'state_convergence',
    intentModel: 'desired_state_not_repeated_imperative',
    questionModel: 'state_before_imperative',
    retryPolicy: 'same_task_id_no_duplicate_execution',
    idempotencyKey: `home-center-work:${hashText(stableTaskId, 32)}`,
    law: 'Observe the state predicate; perform the smallest deterministic transition toward the desired state; once satisfied, repeating the same work item is a no-op.',
  };
}

function slug`,
  'idempotent action policy helper',
);

fortress = replaceOnce(
  fortress,
  `    interrogation: publicInterrogation(work.interrogation),
    receiptRefs: safeList(work.receiptRefs, 10, 800),`,
  `    interrogation: publicInterrogation(work.interrogation),
    actionPolicy: safeObject(work.actionPolicy),
    receiptRefs: safeList(work.receiptRefs, 10, 800),`,
  'orientation action policy',
);

fortress = replaceOnce(
  fortress,
  `    interrogation: publicInterrogation(work.interrogation),
    updatedAtMs: Number(work.updatedAtMs || 0) || 0,
  };
}

function stagedWorkItem`,
  `    interrogation: publicInterrogation(work.interrogation),
    actionPolicy: safeObject(work.actionPolicy),
    updatedAtMs: Number(work.updatedAtMs || 0) || 0,
  };
}

function stagedWorkItem`,
  'work receipt action policy',
);

fortress = replaceOnce(
  fortress,
  `function stagedWorkItem(caller = {}, session = {}, args = {}, timeMs = nowMs()) {
  const taskId = safeText(args.taskId, 120) || \`work-\${timeMs}-\${randomUUID().slice(0, 8)}\`;
  const route = safeText(args.route, 120) || 'manual_followup';
  return {`,
  `function stagedWorkItem(caller = {}, session = {}, args = {}, timeMs = nowMs()) {
  const taskId = safeText(args.taskId, 120) || \`work-\${timeMs}-\${randomUUID().slice(0, 8)}\`;
  const route = safeText(args.route, 120) || 'manual_followup';
  const actionPolicy = idempotentActionPolicy(taskId);
  return {`,
  'stage action policy',
);

fortress = replaceOnce(
  fortress,
  `    taskKind: safeText(args.taskKind, 120) || 'general_work_request',
    route,
    requestText: safeText(args.requestText, 2000),`,
  `    taskKind: safeText(args.taskKind, 120) || 'general_work_request',
    route,
    actionPolicy,
    requestText: safeText(args.requestText, 2000),`,
  'persist action policy',
);

fortress = replaceOnce(
  fortress,
  `      requestText: work.requestText,
      interrogation: publicInterrogation(work.interrogation),
      receipt: workReceiptForItem(work),`,
  `      requestText: work.requestText,
      interrogation: publicInterrogation(work.interrogation),
      actionPolicy: safeObject(work.actionPolicy),
      receipt: workReceiptForItem(work),`,
  'work request output action policy',
);

fortress = replaceOnce(
  fortress,
  `      normalizedState: normalizeWorkState(work.status),
      interrogation: publicInterrogation(work.interrogation),
      statusHistory: safeObjectList(work.statusHistory, 20),`,
  `      normalizedState: normalizeWorkState(work.status),
      interrogation: publicInterrogation(work.interrogation),
      actionPolicy: safeObject(work.actionPolicy),
      statusHistory: safeObjectList(work.statusHistory, 20),`,
  'work status output action policy',
);

fs.writeFileSync(fortressPath, fortress);

const testPath = 'functions/home_center_fortress.test.js';
let tests = fs.readFileSync(testPath, 'utf8');
const marker = "test('Home Center work unit converges idempotently from state instead of repeated imperative'";
if (!tests.includes(marker)) {
  tests += `

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
`;
}
fs.writeFileSync(testPath, tests);

const rulePath = '.continue/rules/05-judgement-jar-simulation-trap.md';
let rule = fs.readFileSync(rulePath, 'utf8');
if (!rule.includes('## Intentional action is idempotent state convergence')) {
  const marker = '## Maximal effort law';
  const section = `## Intentional action is idempotent state convergence

Drew's stronger form of “everything I do should be on purpose” is operational rather than moralistic: **actions must converge idempotently on intended state**.

- Ask for the state that determines the action, not repeated permission for a mechanism whose policy is already known.
- Drew's canonical example: do not ask “should I close the outer door?” Ask “is it hot?” If hot, close the outer door. Once closed under the same hot-state policy, repeating the operation does nothing.
- Prefer state setters over blind imperative repetition.
- Every Home Center work item carries a stable idempotency identity derived from its task identity. Retrying the same completed work item must not execute the transition again.
- For inherently non-idempotent provider actions such as sending, purchasing, creating, charging, or appending, the implementation must supply a stable provider idempotency key, precondition/readback guard, or durable receipt before retry is considered safe.
- “I did not do it on purpose” does not become “consciously deliberate every muscle twitch.” It becomes: consequential operations have a desired state and a retry-safe convergence rule.

Failure labels:

- \`NON_IDEMPOTENT_ACTION\`: retrying the same commissioned operation can create additional consequence after the desired state is already satisfied.
- \`IMPERATIVE_REASK\`: the system asks the user whether to perform a known deterministic action instead of retrieving the state predicate needed to apply the policy.

Acceptance: the atomic Home Center work receipt exposes \`actionPolicy.version=dru.intent-idempotence.v1\`, \`mode=state_convergence\`, \`questionModel=state_before_imperative\`, and a stable idempotency key. Replaying the same completed taskId must preserve the completed status history and receipt without a second execution.

`;
  rule = replaceOnce(rule, marker, section + marker, 'idempotent intent doctrine');
}
fs.writeFileSync(rulePath, rule);
