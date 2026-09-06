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

const domainAnchor = "const WORK_INTERROGATION_DOMAINS = new Set(['intent', 'constraint', 'acceptance', 'authority', 'taste']);\n";
const reviewCode = `const WORK_INTERROGATION_DOMAINS = new Set(['intent', 'constraint', 'acceptance', 'authority', 'taste']);
const FULL_PERSPECTIVE_VERSION = 'dru.punnett-regnet-reneqa.v1';
const INTERROGATION_AGENT_WORK_PATTERNS = Object.freeze([
  {code: 'USER_FAILURE_TAX', pattern: /\\b(failure modes?|pre-?mortem|risk analysis|regressions?|verification strategy|test strategy|test plan)\\b/i},
  {code: 'IMPLEMENTATION_TAX', pattern: /\\b(implementation|architecture|internal mechanics?|engine structure|distinct passes?|separate passes?|merge(?:d|s|ing)?|split(?:ting)?|refactor(?:ing)?)\\b/i},
  {code: 'ENGINE_CHOICE_TAX', pattern: /\\bshould (?:the )?(?:engine|agent|system|fortress)\\s+(?:use|make|merge|split|replace|implement|structure)\\b/i},
  {code: 'IMPLEMENTER_QUESTION', pattern: /\\bhow should (?:i|we)\\s+(?:implement|architect|structure|merge|split|refactor|test|verify)\\b/i},
]);

function fullPerspectiveInterrogationReview(question, domain) {
  const hits = INTERROGATION_AGENT_WORK_PATTERNS
    .filter((entry) => entry.pattern.test(question))
    .map((entry) => entry.code);
  if (hits.length) {
    const failureKind = hits.includes('USER_FAILURE_TAX') ? 'user_failure_tax' : 'interrogation_implementation_tax';
    const err = new Error('Punnett interrogation failed Regnet + Rene QA ownership review: the question pushes agent-owned implementation, failure analysis, regression, or verification work onto Drew.');
    err.status = 400;
    err.code = failureKind;
    err.failureKind = failureKind;
    err.details = {
      version: FULL_PERSPECTIVE_VERSION,
      mode: 'punnett_full_perspective',
      verdict: 'FAIL',
      domain,
      hits,
      regnet: 'The person is not the machinery. Ask for an affected-person need or user-owned constraint, not the mechanism the system can own.',
      reneQa: 'A user-owned domain label cannot launder implementation, failure, regression, risk, test, or verification work into a valid interrogation.',
    };
    throw err;
  }
  return {
    version: FULL_PERSPECTIVE_VERSION,
    mode: 'punnett_full_perspective',
    verdict: 'PASS',
    domain,
    passes: {
      punnett: {
        status: 'declared',
        source: 'she-raw',
        perspective: 'punnett',
        executionClaim: 'not_proven_by_engine',
        law: 'Exactly one question may request a user-owned variable.',
      },
      regnet: {
        status: 'PASS',
        law: 'The person is not the machinery; challenge respectable-looking questions that merely offload the system mechanism.',
        check: 'No agent-owned implementation/failure/verification work was detected in the proposed question.',
      },
      reneQa: {
        status: 'PASS',
        law: 'Scope fidelity applies to interrogation itself; intent/constraint/acceptance/authority/taste labels do not excuse wrong-owner work.',
        check: 'Question stayed inside the declared user-owned domain and passed the agent-work tax screen.',
      },
    },
  };
}
`;
fortress = replaceOnce(fortress, domainAnchor, reviewCode, 'full perspective review');

fortress = replaceOnce(
  fortress,
  `    answeredAtMs: Number(interrogation.answeredAtMs || 0) || 0,
  };
}`,
  `    answeredAtMs: Number(interrogation.answeredAtMs || 0) || 0,
    fullPerspective: safeObject(interrogation.fullPerspective),
  };
}`,
  'public interrogation receipt',
);

fortress = replaceOnce(
  fortress,
  `  return {
    required: true,
    questionCount: 1,
    source: 'she-raw',
    perspective: 'punnett',
    domain: normalizeInterrogationDomain(args.interrogationDomain),
    question,
    answer: '',`,
  `  const domain = normalizeInterrogationDomain(args.interrogationDomain);
  const fullPerspective = fullPerspectiveInterrogationReview(question, domain);
  return {
    required: true,
    questionCount: 1,
    source: 'she-raw',
    perspective: 'punnett',
    domain,
    question,
    fullPerspective,
    answer: '',`,
  'interrogation ownership gate',
);

fs.writeFileSync(fortressPath, fortress);

const testPath = 'functions/home_center_fortress.test.js';
let tests = fs.readFileSync(testPath, 'utf8');
const testMarker = "test('Home Center full-perspective Punnett records ownership QA and rejects agent-work tax'";
if (!tests.includes(testMarker)) {
  tests += `

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
`;
}
fs.writeFileSync(testPath, tests);

const rulePath = '.continue/rules/05-judgement-jar-simulation-trap.md';
let rule = fs.readFileSync(rulePath, 'utf8');
if (!rule.includes('## Full-perspective interrogation ownership QA')) {
  const marker = '## Maximal effort law';
  const section = `## Full-perspective interrogation ownership QA

The one-question gate is itself subject to judgment before it can tax the user.

- Punnett remains the intended She-Raw question-selection perspective. Do not claim a live She-Raw/Punnett invocation without its receipt.
- Regnet challenges the proposed question's model: **the person is not the machinery**. Ask for an affected-person need or genuinely user-owned constraint, not an internal mechanism Fortress can determine.
- Rene QA enforces scope fidelity on the question itself. A label such as intent, constraint, acceptance, authority, or taste cannot launder implementation, architecture, merge/split strategy, failure analysis, regressions, risk, testing, or verification into user-owned work.
- Before a question is persisted or surfaced, the atomic work gate must record a full-perspective PASS receipt. Rejected questions must fail before an AWAITING_ANSWER work item is created.
- The engine records Punnett as intended/declarative unless the live She-Raw execution is actually evidenced; this prevents fake Punnett attribution.

Failure labels:

- \`USER_FAILURE_TAX\`: the question pushes Fortress-owned failure, regression, risk, testing, or verification analysis onto Drew.
- \`INTERROGATION_IMPLEMENTATION_TAX\`: the question pushes internal engine architecture, merge/split strategy, implementation mechanics, or other implementer-owned choice onto Drew, even when mislabeled as taste or authority.

Acceptance requires a valid user-owned question to persist \`fullPerspective.version=dru.punnett-regnet-reneqa.v1\`, \`mode=punnett_full_perspective\`, Regnet PASS, and Rene QA PASS. The exact rejected architecture question “Should the engine make Regnet and Rene QA two distinct passes or merge them into one judgment pass?” must fail as \`interrogation_implementation_tax\`.

`;
  rule = replaceOnce(rule, marker, section + marker, 'full perspective doctrine section');
}
fs.writeFileSync(rulePath, rule);
