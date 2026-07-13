const MUTATION_COMMAND = /(?:^|\s)(?:gcloud\s+(?:run\s+deploy|functions\s+deploy|projects\s+add-iam-policy-binding)|firebase\s+deploy|git\s+(?:push|commit|merge|rebase|reset|checkout|switch|clean|tag)|gh\s+pr\s+(?:create|merge|close|edit)|npm\s+(?:publish|install|uninstall)|yarn\s+(?:add|remove|publish)|pnpm\s+(?:add|remove|publish)|kubectl\s+(?:apply|create|delete|patch|set|rollout)|terraform\s+(?:apply|destroy|import)|docker\s+(?:push|build)|rm\b|mv\b|cp\b|sed\s+-i\b|tee\b|curl\b[^\n]*(?:-X|--request)\s*(?:POST|PUT|PATCH|DELETE))|\b(?:deploy|publish|release|migration|seed)[-_./a-z0-9]*\.(?:m?js|cjs|sh|ts)\b/i;

const SAFE_EXECUTABLE = /^(?:node\s+(?:--check\s+\S+|\S*(?:test|check|lint|read[_-]?only|status|health|probe)\S*\.m?js\b)|npm\s+(?:(?:--prefix\s+\S+\s+)?run\s+(?:test|check|lint|typecheck)\b|test\b)|npx\s+(?:eslint|tsc|vitest|jest)\b|git\s+(?:status|diff|log|show|rev-parse|branch|remote)\b|rg\b|grep\b|find\b|cat\b|head\b|tail\b|ls\b|pwd\b|test\b|sh\s+-n\b|bash\s+-n\b)/i;

// Verification commands are passed to a shell. Reject expansion and control
// syntax before checking the executable allowlist so an allowlisted prefix
// cannot smuggle additional reads, writes, or commands into the shell.
const UNSAFE_SHELL_SYNTAX = /[\r\n;&|><`$*?\[\]{}~()\\#]/;

export function classifyVerificationCommand(value) {
  const command = String(value || '').trim();
  if (!command || /^run repository-defined /i.test(command)) return {safe: false, reason: 'prose_instruction'};
  if (MUTATION_COMMAND.test(command)) return {safe: false, reason: 'mutation_command'};
  if (UNSAFE_SHELL_SYNTAX.test(command)) return {safe: false, reason: 'unsafe_shell_syntax'};
  if (!SAFE_EXECUTABLE.test(command)) {
    return {safe: false, reason: /^[A-Z][a-z]+(?:\s|$)/.test(command) ? 'prose_instruction' : 'unapproved_executable'};
  }
  return {safe: true, reason: ''};
}

export function summarizeVerificationResults(verificationResults = []) {
  const requestedCount = verificationResults.length;
  const executed = verificationResults.filter((result) => result.status !== 'skipped');
  const executedCount = executed.length;
  const skippedCount = requestedCount - executedCount;
  const allExecutedChecksPassed = executedCount > 0 && executed.every((result) => result.exitCode === 0);
  const allRequestedCommandsExecuted = executedCount === requestedCount;
  return {
    requestedCount,
    executedCount,
    skippedCount,
    allExecutedChecksPassed,
    allRequestedCommandsExecuted,
    allVerificationPassed: allExecutedChecksPassed && allRequestedCommandsExecuted,
  };
}

export function verificationCriterionPassed(verificationResults = []) {
  return summarizeVerificationResults(verificationResults).allVerificationPassed;
}

function policyAllowsRepositoryMutation(job = {}) {
  const policy = job.mutationPolicy || {};
  return policy.editFiles !== 'deny' || policy.commit !== 'deny';
}

function mutationLanguage(job = {}) {
  return [job.title || '', job.objective || '', ...(job.acceptanceCriteria || [])].join('\n')
    .replace(/\b(do not|don't|no|without|must not)\b[^.\n;]*(commit|push|pull request|\bPR\b|draft PR|deploy|deployment|external mutation|external provider)[^.\n;]*/gi, '');
}

export function repositoryMutationRequired(job = {}) {
  if (!policyAllowsRepositoryMutation(job)) return false;
  return /fix|repair|implement|add red|red test|patch|changed-file|commit|build/i.test(mutationLanguage(job));
}

export function pullRequestRequired(job = {}) {
  const policy = job.mutationPolicy || {};
  if (policy.push === 'deny' || policy.commit === 'deny') return false;
  return /pull request|\bPR\b|draft PR|push/i.test(mutationLanguage(job));
}

function terminalBlockerReported(finalResult) {
  const bounded = String(finalResult || '').slice(-12000);
  const success = /(?:deployment|deploy|live revision|live endpoint|service).{0,100}(?:succeeded|successful|completed|serving|healthy|passed)/is.test(bounded);
  const nonfatal = /(?:nonfatal|non-fatal|redundant|already had|already exists).{0,160}(?:IAM|permission|binding|warning|failed|denied)|(?:IAM|permission|binding).{0,160}(?:nonfatal|non-fatal|redundant|already had|already exists)/is.test(bounded);
  const explicitTerminalBlock = /(?:^|\n)\s*(?:#{1,6}\s*)?(?:final status\s*:\s*)?(?:blocked|authentication failed|auth(?:entication)? blocker)\b|(?:could not|cannot|unable to)\s+(?:complete|deploy|push|open)/im.test(bounded);
  return explicitTerminalBlock && !(success && nonfatal);
}

export function assessAcceptanceEvidence({job = {}, codexExitCode = 0, codexAcceptanceError = '', finalResult = '', verificationResults = [], gitEvidence = {}}) {
  const failures = [];
  if (codexExitCode !== 0) failures.push(`Codex exited ${codexExitCode}.`);
  if (codexAcceptanceError) failures.push(codexAcceptanceError);
  for (const result of verificationResults) {
    if (result.status !== 'skipped' && result.exitCode !== 0) failures.push(`Verification failed: ${result.command} exited ${result.exitCode}.`);
  }
  if (terminalBlockerReported(finalResult)) failures.push('Codex reported a blocker or authentication failure instead of completing the mutation.');
  if (repositoryMutationRequired(job) && !gitEvidence.diffHasContent && !gitEvidence.newCommitCreated) {
    failures.push('Mutation ticket produced no uncommitted diff and no new commit relative to the restored base commit.');
  }
  if (pullRequestRequired(job) && !/https:\/\/github\.com\/[^\s)]+\/pull\/\d+/i.test(String(finalResult).slice(-12000))) {
    failures.push('Ticket required push/PR evidence but no GitHub pull request URL was produced.');
  }
  return {accepted: failures.length === 0, failures};
}
