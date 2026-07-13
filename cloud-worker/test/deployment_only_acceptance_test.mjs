#!/usr/bin/env node
import assert from 'node:assert/strict';
import {
  assessAcceptanceEvidence,
  classifyVerificationCommand,
  repositoryMutationRequired,
  summarizeVerificationResults,
  verificationCriterionPassed,
} from '../src/acceptance_policy.mjs';

const deploymentOnlyJob = {
  title: 'Deploy the already-built Command Center worker',
  objective: 'Deploy the approved revision and verify the live endpoint.',
  acceptanceCriteria: ['The live Cloud Run revision is healthy.'],
  mutationPolicy: {editFiles: 'deny', commit: 'deny', push: 'deny', deployProduction: 'allowed'},
};
const finalResult = `# Final Report

Deployment succeeded. Live revision command-center-worker-001 is serving and the health check passed.

The redundant IAM policy binding substep returned PERMISSION_DENIED; the service already had the required binding, so this warning was nonfatal.
`;

assert.equal(repositoryMutationRequired(deploymentOnlyJob), false);
assert.deepEqual(classifyVerificationCommand('node tools/read_only_contract_test.mjs'), {safe: true, reason: ''});
assert.deepEqual(classifyVerificationCommand('npm --prefix cloud-worker run check'), {safe: true, reason: ''});
assert.deepEqual(classifyVerificationCommand('Verify the live endpoint and record the revision.'), {safe: false, reason: 'prose_instruction'});
assert.deepEqual(classifyVerificationCommand('gcloud run deploy command-center-worker --source .'), {safe: false, reason: 'mutation_command'});
assert.deepEqual(classifyVerificationCommand('node tools/deploy_worker.mjs'), {safe: false, reason: 'mutation_command'});
assert.deepEqual(classifyVerificationCommand('npm run build'), {safe: false, reason: 'unapproved_executable'});
assert.deepEqual(classifyVerificationCommand('python tools/check.py'), {safe: false, reason: 'unapproved_executable'});
for (const command of [
  'node tools/read_only_contract_test.mjs $(touch /tmp/never)',
  'node tools/read_only_contract_test.mjs `touch /tmp/never`',
  'node tools/read_only_contract_test.mjs $HOME',
  'node tools/read_only_contract_test.mjs ${HOME}',
  'node tools/read_only_contract_test.mjs $((1 + 1))',
  'node tools/read_only_contract_test.mjs <(cat /etc/passwd)',
  'node tools/read_only_contract_test.mjs *.mjs',
  'node tools/read_only_contract_test.mjs {one,two}',
  'node tools/read_only_contract_test.mjs ~/fixture',
  'node tools/read_only_contract_test.mjs (cat /etc/passwd)',
  'node tools/read_only_contract_test.mjs fixture\\ name',
  'node tools/read_only_contract_test.mjs # ignored suffix',
]) {
  assert.deepEqual(classifyVerificationCommand(command), {safe: false, reason: 'unsafe_shell_syntax'}, command);
}

const mixedVerification = summarizeVerificationResults([
  {command: 'node tools/read_only_contract_test.mjs', status: 'executed', exitCode: 0},
  {command: 'npm run build', status: 'skipped', skipReason: 'unapproved_executable', exitCode: 0},
]);
assert.deepEqual(mixedVerification, {
  requestedCount: 2,
  executedCount: 1,
  skippedCount: 1,
  allExecutedChecksPassed: true,
  allRequestedCommandsExecuted: false,
  allVerificationPassed: false,
});
assert.equal(summarizeVerificationResults([
  {command: 'Verify the endpoint.', status: 'skipped', skipReason: 'prose_instruction', exitCode: 0},
]).allVerificationPassed, false);
assert.equal(verificationCriterionPassed([
  {command: 'Verify the endpoint.', status: 'skipped', skipReason: 'prose_instruction', exitCode: 0},
]), false, 'a skipped-only verification criterion must not pass the acceptance matrix');

const accepted = assessAcceptanceEvidence({
  job: deploymentOnlyJob,
  codexExitCode: 0,
  codexAcceptanceError: '',
  finalResult,
  verificationResults: [
    {command: 'Verify the live endpoint and record the revision.', status: 'skipped', skipReason: 'prose_instruction'},
    {command: 'gcloud run deploy command-center-worker --source .', status: 'skipped', skipReason: 'mutation_command'},
  ],
  gitEvidence: {diffHasContent: false, newCommitCreated: false},
});
assert.deepEqual(accepted.failures, []);
assert.equal(accepted.accepted, true);

const genuineAuthBlocker = assessAcceptanceEvidence({
  job: {...deploymentOnlyJob, objective: 'Deploy the approved revision.', acceptanceCriteria: []},
  codexExitCode: 0,
  finalResult: '# Final Report\n\nBLOCKED: terminal authentication failed; deployment was not completed.',
  verificationResults: [],
  gitEvidence: {diffHasContent: false, newCommitCreated: false},
});
assert.equal(genuineAuthBlocker.accepted, false);
assert.match(genuineAuthBlocker.failures.join('\n'), /blocker or authentication failure/i);

const repositoryTicket = {
  title: 'Fix parser',
  objective: 'Implement the parser fix.',
  acceptanceCriteria: [],
  mutationPolicy: {editFiles: 'allowed', commit: 'allowed'},
};
assert.equal(repositoryMutationRequired(repositoryTicket), true);
const missingDiff = assessAcceptanceEvidence({
  job: repositoryTicket,
  codexExitCode: 0,
  finalResult: '# Final Report\n\nImplementation complete.',
  verificationResults: [],
  gitEvidence: {diffHasContent: false, newCommitCreated: false},
});
assert.equal(missingDiff.accepted, false);
assert.match(missingDiff.failures.join('\n'), /no uncommitted diff/i);

console.log('Command Center deployment-only acceptance regression test: OK');
