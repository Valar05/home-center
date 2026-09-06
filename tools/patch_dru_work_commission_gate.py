#!/usr/bin/env python3
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_fortress() -> None:
    path = Path("functions/home_center_fortress.js")
    text = path.read_text()
    text = replace_once(
        text,
        "const WORK_STATES = new Set(['REQUESTED', 'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNKNOWN']);",
        "const WORK_STATES = new Set(['REQUESTED', 'AWAITING_ANSWER', 'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNKNOWN']);\nconst WORK_INTERROGATION_DOMAINS = new Set(['intent', 'constraint', 'acceptance', 'authority', 'taste']);",
        "work states",
    )

    normalize_anchor = r"""function normalizeWorkState(value) {
  const state = safeText(value, 40).toUpperCase();
  return WORK_STATES.has(state) ? state : 'UNKNOWN';
}"""
    normalize_replacement = normalize_anchor + r"""

function normalizeInterrogationDomain(value) {
  const domain = safeText(value, 40).toLowerCase();
  if (WORK_INTERROGATION_DOMAINS.has(domain)) return domain;
  const err = new Error('interrogationDomain must be one of intent, constraint, acceptance, authority, or taste. Failure analysis, implementation, regressions, and verification belong to Fortress, not the user.');
  err.status = 400;
  err.code = 'invalid_interrogation_domain';
  throw err;
}

function publicInterrogation(value = {}) {
  const interrogation = safeObject(value);
  return {
    required: interrogation.required !== false,
    questionCount: 1,
    source: safeText(interrogation.source, 80) || 'she-raw',
    perspective: safeText(interrogation.perspective, 80) || 'punnett',
    domain: safeText(interrogation.domain, 40),
    question: safeText(interrogation.question, 600),
    answered: Boolean(safeText(interrogation.answer, 2000)),
    askedAtMs: Number(interrogation.askedAtMs || 0) || 0,
    answeredAtMs: Number(interrogation.answeredAtMs || 0) || 0,
  };
}

function interrogationForNewWork(args = {}, timeMs = nowMs()) {
  const question = safeText(args.interrogationQuestion, 600);
  if (!question) {
    const err = new Error('Exactly one Punnett-routed She-Raw interrogationQuestion is required before Home Center may execute a work commission.');
    err.status = 400;
    err.code = 'interrogation_question_required';
    throw err;
  }
  if ((question.match(/\?/g) || []).length > 1) {
    const err = new Error('interrogationQuestion must contain exactly one question, not a questionnaire.');
    err.status = 400;
    err.code = 'multiple_interrogation_questions';
    throw err;
  }
  return {
    required: true,
    questionCount: 1,
    source: 'she-raw',
    perspective: 'punnett',
    domain: normalizeInterrogationDomain(args.interrogationDomain),
    question,
    answer: '',
    askedAtMs: timeMs,
    answeredAtMs: 0,
  };
}

async function loadWorkItem(admin, caller, taskId) {
  const cleanTaskId = safeText(taskId, 120);
  if (!cleanTaskId) return null;
  const snap = await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.workItems).doc(cleanTaskId).get();
  if (!snap.exists) return null;
  const work = {taskId: cleanTaskId, ...(snap.data() || {})};
  assertOwnerAccess(work, caller, 'Home Center work item');
  return work;
}"""
    text = replace_once(text, normalize_anchor, normalize_replacement, "interrogation helpers")

    text = replace_once(
        text,
        "    normalizedState: normalizeWorkState(work.normalizedState || work.status),\n    receiptRefs: safeList(work.receiptRefs, 10, 800),",
        "    normalizedState: normalizeWorkState(work.normalizedState || work.status),\n    interrogation: publicInterrogation(work.interrogation),\n    receiptRefs: safeList(work.receiptRefs, 10, 800),",
        "work summary interrogation",
    )
    text = replace_once(
        text,
        "    summary: safeText(work.resultSummary || work.requestText, 400),\n    updatedAtMs: Number(work.updatedAtMs || 0) || 0,",
        "    summary: safeText(work.resultSummary || work.requestText, 400),\n    interrogation: publicInterrogation(work.interrogation),\n    updatedAtMs: Number(work.updatedAtMs || 0) || 0,",
        "work receipt interrogation",
    )
    text = replace_once(
        text,
        "    route,\n    requestText: safeText(args.requestText, 2000),\n    normalizedState: 'REQUESTED',",
        "    route,\n    requestText: safeText(args.requestText, 2000),\n    interrogation: interrogationForNewWork(args, timeMs),\n    normalizedState: 'REQUESTED',",
        "staged work interrogation",
    )

    old_operation = r"""async function homeCenterWorkRequestOperation({admin, caller, args = {}, now: nowFn = nowMs, executeWork = null} = {}) {
  const timeMs = nowFn();
  const active = await ensureActiveSession(admin, caller, args, {nowMs: timeMs});
  let work = stagedWorkItem(caller, active.session, args, timeMs);
  const executor = typeof executeWork === 'function' ? executeWork : defaultFortressWorkExecutor;
  work = await executor({admin, caller, session: active.session, project: active.project, work, args, now: nowFn});
  work.receiptRefs = mergeUniqueStrings(work.receiptRefs, [workReceiptForItem(work).receiptRef], 10);
  await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.workItems).doc(work.taskId).set(work, {merge: false});
  const nextSession = await persistSessionWorkLink(admin, active.session, work, Number(work.updatedAtMs || timeMs) || timeMs);
  return {
    ok: true,
    work: {
      taskId: work.taskId,
      normalizedState: normalizeWorkState(work.status),
      route: work.route,
      requestText: work.requestText,
      receipt: workReceiptForItem(work),
      statusHistory: safeObjectList(work.statusHistory, 20),
    },
    orientation: await loadOrientation(admin, nextSession, active.project),
  };
}"""
    new_operation = r"""async function homeCenterWorkRequestOperation({admin, caller, args = {}, now: nowFn = nowMs, executeWork = null} = {}) {
  const timeMs = nowFn();
  const active = await ensureActiveSession(admin, caller, args, {nowMs: timeMs});
  const requestedTaskId = safeText(args.taskId, 120);
  let work = requestedTaskId ? await loadWorkItem(admin, caller, requestedTaskId) : null;

  if (!work) {
    work = stagedWorkItem(caller, active.session, args, timeMs);
    work = advanceWorkItem(work, 'AWAITING_ANSWER', 'Exactly one Punnett-routed She-Raw question must be answered before execution.', timeMs + 1);
  } else {
    const requestText = safeText(args.requestText, 2000);
    if (requestText && requestText !== safeText(work.requestText, 2000)) {
      const err = new Error('A work item cannot change commissions while resuming its interrogation.');
      err.status = 409;
      err.code = 'work_request_changed';
      throw err;
    }
    const suppliedQuestion = safeText(args.interrogationQuestion, 600);
    if (suppliedQuestion && suppliedQuestion !== safeText(work.interrogation && work.interrogation.question, 600)) {
      const err = new Error('The one interrogation question is immutable after it is recorded.');
      err.status = 409;
      err.code = 'interrogation_question_changed';
      throw err;
    }
    const suppliedDomain = safeText(args.interrogationDomain, 40).toLowerCase();
    if (suppliedDomain && suppliedDomain !== safeText(work.interrogation && work.interrogation.domain, 40)) {
      const err = new Error('The interrogation domain is immutable after it is recorded.');
      err.status = 409;
      err.code = 'interrogation_domain_changed';
      throw err;
    }
    if (normalizeWorkState(work.status) === 'AWAITING_ANSWER') {
      const answer = safeText(args.interrogationAnswer, 2000);
      if (answer) {
        work = {
          ...work,
          interrogation: {
            ...safeObject(work.interrogation),
            answer,
            answeredAtMs: timeMs,
          },
          updatedAtMs: timeMs,
        };
        const executor = typeof executeWork === 'function' ? executeWork : defaultFortressWorkExecutor;
        work = await executor({admin, caller, session: active.session, project: active.project, work, args, now: nowFn});
      }
    }
  }

  work.receiptRefs = mergeUniqueStrings(work.receiptRefs, [workReceiptForItem(work).receiptRef], 10);
  await collection(admin, HOME_CENTER_FORTRESS_COLLECTIONS.workItems).doc(work.taskId).set(work, {merge: false});
  const nextSession = await persistSessionWorkLink(admin, active.session, work, Number(work.updatedAtMs || timeMs) || timeMs);
  return {
    ok: true,
    work: {
      taskId: work.taskId,
      normalizedState: normalizeWorkState(work.status),
      route: work.route,
      requestText: work.requestText,
      interrogation: publicInterrogation(work.interrogation),
      receipt: workReceiptForItem(work),
      statusHistory: safeObjectList(work.statusHistory, 20),
    },
    orientation: await loadOrientation(admin, nextSession, active.project),
  };
}"""
    text = replace_once(text, old_operation, new_operation, "work request operation")
    text = replace_once(
        text,
        "      normalizedState: normalizeWorkState(work.status),\n      statusHistory: safeObjectList(work.statusHistory, 20),\n      receipt: workReceiptForItem(work),",
        "      normalizedState: normalizeWorkState(work.status),\n      interrogation: publicInterrogation(work.interrogation),\n      statusHistory: safeObjectList(work.statusHistory, 20),\n      receipt: workReceiptForItem(work),",
        "work status interrogation",
    )
    path.write_text(text)


def patch_mcp() -> None:
    path = Path("functions/home_center_mcp.js")
    text = path.read_text()
    text = replace_once(
        text,
        "    description: 'Record a durable Home Center work request for the active session, normalize its high-level state, and return a durable receipt. Use route=fortress_session_probe for the continuity test capability path.',",
        "    description: 'Record the basic durable unit of commissioned Home Center work. First invocation records exactly one Punnett-routed She-Raw interrogation question and must stop in AWAITING_ANSWER without executing. Resume the same taskId with interrogationAnswer to permit execution. Use route=fortress_session_probe for the continuity test capability path.',",
        "work tool description",
    )
    text = replace_once(
        text,
        "      requestText: z.string().describe('The work request to record and route.'),\n      artifactRefs: z.array(z.string()).optional().describe('Optional artifact or receipt refs already associated with this request.'),",
        "      requestText: z.string().describe('The work request to record and route. Repeat the unchanged commission when resuming an existing taskId.'),\n      interrogationQuestion: z.string().optional().describe('Exactly one pre-execution question selected through She-Raw with requestedPerspective=Punnett. Required on first task creation by the operation. It may ask only for user-owned intent, constraint, acceptance, authority, or taste.'),\n      interrogationDomain: z.enum(['intent', 'constraint', 'acceptance', 'authority', 'taste']).optional().describe('User-owned domain for the one interrogation question. Failure modes, implementation, regressions, and verification strategy are intentionally excluded.'),\n      interrogationAnswer: z.string().optional().describe('The user answer when resuming the same taskId. An answer supplied on first creation cannot bypass the required turn boundary.'),\n      artifactRefs: z.array(z.string()).optional().describe('Optional artifact or receipt refs already associated with this request.'),",
        "work tool schema",
    )
    path.write_text(text)


def patch_runtime() -> None:
    path = Path("functions/index.js")
    text = path.read_text()
    old = r"""  if (mutationAuthorized) {
    fortressInstructions.push('For explicit engineering actions such as fix, patch, repair, or update requests, create or inspect durable Home Center work state before claiming completion. Use home_center_work_request to record the work request and home_center_work_status to report the durable result or receipt.');
  }"""
    new = r"""  fortressInstructions.push('Fortress Online is the standing operating state. If the latest user utterance is a new commission for work of any kind—code, simulation, game, image, video, audio, sound effect, document, artifact, analysis, mutation, or other execution—route exactly one pre-execution interrogation question through She-Raw with requestedPerspective=Punnett. Ask only for a user-owned intent, constraint, acceptance, authority, or taste variable; never ask the user to supply failure modes, implementation, regressions, risk analysis, or verification strategy. Record the commission through home_center_work_request with interrogationQuestion and interrogationDomain before execution; its first invocation must remain AWAITING_ANSWER. Surface only that one question and end the turn. The user answer is continuation of the same commission, not a new commission: resume the same taskId with interrogationAnswer, then plan, anticipate failure internally, execute through the authorized lane, verify, and stop. Never bypass the two-invocation work gate.');
  if (mutationAuthorized) {
    fortressInstructions.push('Mutation authorization changes what may execute after interrogation; it never bypasses the one-question commission gate.');
  }"""
    path.write_text(replace_once(text, old, new, "runtime fortress work instruction"))


def patch_doctrine() -> None:
    skill_path = Path("skills/dru-simulation-trap/SKILL.md")
    skill = skill_path.read_text()
    skill = replace_once(
        skill,
        "## Sticky Fortress\n\nOnce `Fortress Online` has been invoked in the active conversation/session, the mode stays latched until Drew explicitly cancels or replaces it. Later ordinary utterances still run the full machine. The named phrases are emphasis pulses into the latched machine, not on/off switches.\n",
        "## Standing Fortress\n\n`Fortress Online` is always active. It is the default operating state, not a toggle and not a latch that first requires invocation. Ordinary utterances always run the full machine. Saying `Fortress Online` is an emphasis pulse for durability, remote truth, continuity, authoritative lanes, mutation, and receipts; it never turns the machine on because the machine was already on.\n",
        "skill standing fortress",
    )
    skill_gate = """## Commission gate — Jackie Chan's vow

A **commission** is any utterance that authorizes work to be produced or changed: simulation, game, code, image, video, sound effect, audio, document, artifact, analysis, mutation, or equivalent execution.

Every new commission gets **exactly one** non-volunteering interrogation question before substantive execution. Never zero. Never a questionnaire. The question is selected through She-Raw with `requestedPerspective=Punnett` and may ask only for a variable Drew owns: intent, constraint, acceptance, authority, or taste. Failure modes, implementation risk, regressions, pre-mortem analysis, and verification strategy are Fortress work and must never be taxed back onto Drew.

The durable gate is `home_center_work_request` itself:

1. After the clock is visible, select the one Punnett question.
2. Record the commission with `interrogationQuestion` and `interrogationDomain`.
3. The first work invocation must persist `AWAITING_ANSWER` and execute nothing, even if an answer is accidentally supplied early.
4. Surface that one question and stop the turn.
5. Drew's answer is continuation of the same commission, not a new commission. Resume the same `taskId` with `interrogationAnswer`.
6. Only then plan, anticipate likely failure internally, execute, verify, and stop at the requested state.

**Jackie Chan's vow:** embody kinesis and kinetic compression. Plan before action. Anticipate the hit yourself. Use the fewest meaningful state transitions that fully satisfy the commission. Reduce wasted verbs. Do not volunteer adjacent work. Do not keep moving after the requested state exists.

Failure labels: `COMMISSION_GATE_BYPASS`, `INTERROGATION_MULTIPLY`, `USER_FAILURE_TAX`, `WORK_AFTER_STOP`.

"""
    skill = replace_once(skill, "## Effort law\n", skill_gate + "## Effort law\n", "skill commission gate")
    skill = replace_once(
        skill,
        "`WILDCARD_BYPASS`, `KEYWORD_ONLY_FORTRESS`, `EMPHASIS_ISOLATION`, `CLOCK_SPINAL_BYPASS`, `CLOCK_LATENCY_BYPASS`, `SIMULATION_AS_THEATER`, `MAXIMAL_EFFORT_BLOAT`.",
        "`WILDCARD_BYPASS`, `KEYWORD_ONLY_FORTRESS`, `EMPHASIS_ISOLATION`, `CLOCK_SPINAL_BYPASS`, `CLOCK_LATENCY_BYPASS`, `COMMISSION_GATE_BYPASS`, `INTERROGATION_MULTIPLY`, `USER_FAILURE_TAX`, `WORK_AFTER_STOP`, `SIMULATION_AS_THEATER`, `MAXIMAL_EFFORT_BLOAT`.",
        "skill failure labels",
    )
    skill_path.write_text(skill)

    rule_path = Path(".continue/rules/05-judgement-jar-simulation-trap.md")
    rule = rule_path.read_text()
    rule = replace_once(
        rule,
        "## Sticky latch\n\nOnce `Fortress Online` has been invoked in a conversation/session, Fortress remains latched until Drew explicitly cancels or replaces that operating mode. Ordinary subsequent utterances do not turn it off. Every later utterance still enters the complete wildcard machine; named phrases only change emphasis.\n",
        "## Standing Fortress\n\n`Fortress Online` is always active. It is the default operating state and requires no prior invocation. Every utterance enters the complete wildcard machine; named phrases only change emphasis. No branch may ask whether Fortress is active.\n",
        "rule standing fortress",
    )
    rule_gate = """## Work commission gate

A work commission is any user utterance that authorizes production or mutation of a simulation, game, code change, image, video, sound effect, audio artifact, document, analysis artifact, or other executable result.

After the clock is visible and before substantive execution, every **new** commission must cross exactly one interrogation boundary:

1. Route question selection through She-Raw with `requestedPerspective=Punnett`.
2. Ask exactly one question. The domain must be user-owned intent, constraint, acceptance, authority, or taste.
3. Never ask Drew for failure modes, implementation choices that Fortress can own, regressions, pre-mortem analysis, risk analysis, or verification strategy. Those are internal Fortress duties.
4. Record the commission at the basic work unit with `home_center_work_request`, including the selected question and domain. The first invocation must persist `AWAITING_ANSWER` and perform no work.
5. Surface that single question and end the turn. Do not volunteer adjacent work or a second question.
6. The user's answer continues the same commission. Resume the same `taskId` with `interrogationAnswer`; do not classify the answer as a new commission.
7. After the answer, plan before action, anticipate likely failure internally, execute the smallest sufficient causal sequence, verify on the authorized surface, and stop when the requested state exists.

This is Jackie Chan's vow: **embody kinesis; compress kinesis**. Movement must earn itself. `COMMISSION_GATE_BYPASS` means work began before the durable question boundary. `INTERROGATION_MULTIPLY` means more than one question was imposed. `USER_FAILURE_TAX` means Fortress outsourced its own failure analysis to Drew. `WORK_AFTER_STOP` means action continued after the commissioned state was satisfied.

"""
    rule = replace_once(rule, "## Maximal effort law\n", rule_gate + "## Maximal effort law\n", "rule commission gate")
    rule = replace_once(
        rule,
        "- `SIMULATION_AS_THEATER`: DRU claims to simulate/preflight but produces no observable improvement, execution, or gate effect.",
        "- `COMMISSION_GATE_BYPASS`: substantive work begins before the one-question durable interrogation boundary.\n- `INTERROGATION_MULTIPLY`: more than one interrogation question is imposed for one commission.\n- `USER_FAILURE_TAX`: failure analysis, implementation risk, regressions, or verification strategy are pushed back onto Drew.\n- `WORK_AFTER_STOP`: Fortress continues acting after the commissioned state is satisfied.\n- `SIMULATION_AS_THEATER`: DRU claims to simulate/preflight but produces no observable improvement, execution, or gate effect.",
        "rule failure labels",
    )
    rule = replace_once(
        rule,
        "Pass only if arbitrary user text with no trigger phrase causes immediate visible live clock delivery before any other user-visible output or non-clock external work, then the full preflight continues. Every named emphasis phrase must bias the same machine without replacing it or suppressing the clock. Interruptions force fresh immediate reacquisition. After Fortress has latched, ordinary later turns remain fully governed without Drew chanting a gate name.",
        "Pass only if arbitrary user text with no trigger phrase causes immediate visible live clock delivery before any other user-visible output or non-clock external work, then the full preflight continues. Every named emphasis phrase must bias the same machine without replacing it or suppressing the clock. Fortress is already active on ordinary turns. Every new work commission records exactly one Punnett-routed, user-authority-only interrogation question at `home_center_work_request`, remains `AWAITING_ANSWER` without execution on the first invocation, resumes the same task after the answer, keeps failure analysis inside Fortress, and stops when the requested state is satisfied. Interruptions force fresh immediate clock reacquisition.",
        "rule acceptance",
    )
    rule_path.write_text(rule)


def patch_test() -> None:
    path = Path("functions/home_center_fortress.test.js")
    text = path.read_text()
    marker = "test('Home Center work receipts survive restart and stay readable through session status', async () => {"
    replacement_marker = "test('Home Center work receipts survive restart and enforce one Punnett interrogation before execution', async () => {"
    if replacement_marker in text:
        return
    start = text.find(marker)
    if start < 0:
        raise RuntimeError("work receipt test anchor missing")
    replacement = r"""test('Home Center work receipts survive restart and enforce one Punnett interrogation before execution', async () => {
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
"""
    path.write_text(text[:start] + replacement)


patch_fortress()
patch_mcp()
patch_runtime()
patch_doctrine()
patch_test()
print("DRU work commission gate patch applied")
