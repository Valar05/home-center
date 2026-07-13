#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const commandCenterSource = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
const {
  COMMAND_CENTER_COLLECTIONS,
  COMMAND_CENTER_DEFAULT_WORKERS,
  COMMAND_CENTER_DEFAULT_PROJECTS,
  COMMAND_CENTER_REQUIRED_ARTIFACTS,
  COMMAND_CENTER_DEFAULT_BASE_WORKSPACE,
  COMMAND_CENTER_ALLOWED_STATUSES,
  COMMAND_CENTER_TERMINAL_JOB_STATUSES,
  COMMAND_CENTER_AGENT_ACTIVATION_STATUSES,
  COMMAND_CENTER_CODEX_CLOUD_SURFACE,
  COMMAND_CENTER_DURABLE_SESSION_RESTORE_STRATEGIES,
  COMMAND_CENTER_DEFAULT_BUCKET_ID,
  COMMAND_CENTER_BUCKET_KINDS,
  COMMAND_CENTER_BUCKET_LAYOUT,
  cleanBaseWorkspace,
  cleanMutationPolicy,
  cleanOneShotExecution,
  cleanBucketObject,
  cleanRepoAgent,
  cleanAgentSession,
  cleanActivationTask,
  cleanCodexCloudRef,
  buildAgentResumePacket,
  cleanBrowserPlaybook,
  cleanProjectPacket,
  ownerKeyFromActor,
  ownerKeyFromCaller,
  assertOwnerAccess,
  recordsVisibleToCaller,
  deriveWorkerLiveness,
  isTerminalJobStatus,
  staleJobCandidate,
  selectWorker,
} = require('../functions/command_center_mcp');

const requiredCollections = [
  'projects',
  'jobs',
  'workers',
  'leases',
  'events',
  'questions',
  'mutationAuthorizations',
  'artifacts',
  'logs',
  'checkpoints',
  'bucketObjects',
  'appControlProfiles',
  'appControlRuns',
  'browserSessions',
  'browserEpisodes',
  'browserDiscoveries',
  'browserPlaybooks',
  'baseWorkspaces',
  'repoAgents',
  'agentSessions',
  'agentActivations',
  'agentArtifacts',
  'codexCloudRefs',
  'agentContextSnapshots',
  'jobActivations',
  'workerTokens',
  'idempotency',
];
for (const key of requiredCollections) {
  if (key.startsWith('appControl')) assert.match(COMMAND_CENTER_COLLECTIONS[key], /^appControl/);
  else if (key.startsWith('browser')) assert.match(COMMAND_CENTER_COLLECTIONS[key], /^browser/);
  else assert.match(COMMAND_CENTER_COLLECTIONS[key], /^commandCenter/);
}

const defaultWorker = COMMAND_CENTER_DEFAULT_WORKERS[0];
assert.equal(defaultWorker.workerId, 'cloud-codex-primary');
assert.equal(defaultWorker.engine, 'codex');
assert.equal(defaultWorker.health, 'placeholder');
assert.equal(defaultWorker.simulated, true);
assert.equal(defaultWorker.routable, false);
assert.deepEqual(defaultWorker.capabilities, []);
assert(defaultWorker.advertisedCapabilities.includes('github'));
assert(!defaultWorker.capabilities.includes('home-drive-mcp'));
assert(defaultWorker.advertisedCapabilities.includes('one-shot-worker'));
assert(defaultWorker.advertisedCapabilities.includes('prepared-workspace'));
assert(defaultWorker.advertisedCapabilities.includes('browser-worker'));
assert(defaultWorker.advertisedCapabilities.includes('playwright'));
assert(defaultWorker.advertisedCapabilities.includes('chrome-desktop'));
assert.equal(defaultWorker.simulated, true);
assert.match(defaultWorker.stalePremise, /not a real OpenAI Codex cloud worker/);

assert.throws(
  () => selectWorker(COMMAND_CENTER_DEFAULT_WORKERS, ['codex', 'github']),
  /No live real Command Center worker satisfies requirements: codex, github/
);

const homeDriveProject = COMMAND_CENTER_DEFAULT_PROJECTS['home-drive'];
assert.equal(homeDriveProject.projectId, 'home-drive');
assert.equal(homeDriveProject.repository, 'Valar05/home-center');
assert.equal(homeDriveProject.capability, 'home-drive-mcp');
assert.equal(homeDriveProject.durable, true);
assert.deepEqual(homeDriveProject.availableWorkers, ['home-drive-primary']);
const cleanedHomeDrive = cleanProjectPacket({...homeDriveProject, idempotencyKey: 'unused'});
assert.equal(cleanedHomeDrive.projectId, 'home-drive');
assert.equal(cleanedHomeDrive.repositoryBinding.kind, 'github_repository');

const nowMs = Date.now();
const realHomeDriveWorker = {workerId: 'home-drive-primary', health: 'healthy', lastHeartbeatAtMs: nowMs, simulated: false, capabilities: ['codex', 'home-drive-mcp', 'one-shot-worker', 'prepared-workspace']};
const staleHomeDriveWorker = {workerId: 'home-drive-stale', health: 'healthy', lastHeartbeatAtMs: nowMs - 10 * 60 * 1000, simulated: false, capabilities: ['codex', 'home-drive-mcp', 'one-shot-worker', 'prepared-workspace']};
const simulatedHomeDriveWorker = {workerId: 'cloud-codex-primary', health: 'healthy', lastHeartbeatAtMs: nowMs, simulated: true, capabilities: ['codex', 'home-drive-mcp', 'one-shot-worker', 'prepared-workspace']};
const retiredHomeDriveWorker = {...realHomeDriveWorker, workerId: 'home-drive-retired', status: 'retired', retiredAtMs: nowMs};
assert.equal(selectWorker([simulatedHomeDriveWorker, realHomeDriveWorker], ['home-drive-mcp'], {nowMs}).workerId, 'home-drive-primary');
assert.equal(deriveWorkerLiveness(retiredHomeDriveWorker, nowMs).health, 'healthy');
assert.equal(selectWorker([retiredHomeDriveWorker, realHomeDriveWorker], ['home-drive-mcp'], {nowMs}).workerId, 'home-drive-primary');
assert.throws(
  () => selectWorker([retiredHomeDriveWorker], ['home-drive-mcp'], {nowMs}),
  /No live real Command Center worker satisfies requirements: home-drive-mcp/
);
assert.equal(deriveWorkerLiveness(staleHomeDriveWorker, nowMs).health, 'stale');
assert.equal(deriveWorkerLiveness(realHomeDriveWorker, nowMs).registryHealth, 'healthy');
assert.throws(
  () => selectWorker([staleHomeDriveWorker], ['home-drive-mcp'], {nowMs}),
  /No live real Command Center worker satisfies requirements: home-drive-mcp/
);

assert.throws(
  () => selectWorker([{workerId: 'termux', health: 'healthy', lastHeartbeatAtMs: nowMs, simulated: false, capabilities: ['android']}], ['codex'], {nowMs}),
  /No live real Command Center worker satisfies requirements: codex/
);
const fallback = selectWorker([{workerId: 'termux', health: 'healthy', lastHeartbeatAtMs: nowMs, simulated: false, capabilities: ['android']}], [], {nowMs});
assert.equal(fallback.workerId, 'termux');
const ownerA = {actor: 'a@example.com', ownerKey: ownerKeyFromActor('a@example.com')};
const ownerB = {actor: 'b@example.com', ownerKey: ownerKeyFromActor('b@example.com')};
assert.equal(ownerKeyFromCaller(ownerA), ownerKeyFromActor('a@example.com'));
assert.doesNotThrow(() => assertOwnerAccess({ownerKey: ownerA.ownerKey}, ownerA, 'job'));
assert.throws(() => assertOwnerAccess({ownerKey: ownerA.ownerKey}, ownerB, 'job'), /not found for this Command Center owner/);
assert.deepEqual(recordsVisibleToCaller([{workerId: 'public'}, {workerId: 'a', ownerKey: ownerA.ownerKey}, {workerId: 'b', ownerKey: ownerB.ownerKey}], ownerA).map((worker) => worker.workerId), ['public', 'a']);
assert(COMMAND_CENTER_ALLOWED_STATUSES.includes('expired'));
assert(COMMAND_CENTER_TERMINAL_JOB_STATUSES.includes('expired'));
assert.equal(isTerminalJobStatus('expired'), true);
assert.equal(staleJobCandidate({jobId: 'job_stale', projectId: 'home-center', status: 'executing', updatedAtMs: nowMs - 3600000}, nowMs, 1800000, ['leased', 'executing', 'running', 'activating']).jobId, 'job_stale');
assert.equal(staleJobCandidate({jobId: 'job_running_stale', projectId: 'home-center', status: 'running', updatedAtMs: nowMs - 3600000}, nowMs, 1800000, ['leased', 'executing', 'running', 'activating']).jobId, 'job_running_stale');
assert.equal(staleJobCandidate({jobId: 'job_fresh', status: 'executing', updatedAtMs: nowMs - 1000}, nowMs, 1800000, ['leased', 'executing', 'running', 'activating']), null);

const policy = cleanMutationPolicy({editFiles: 'allowed', push: 'confirm'});
assert.equal(policy.editFiles, 'allowed');
assert.equal(policy.runTests, 'allowed');
assert.equal(policy.push, 'confirm');
assert.equal(policy.destructive, 'deny');

assert(COMMAND_CENTER_REQUIRED_ARTIFACTS.includes('job-intake.json'));
assert(COMMAND_CENTER_REQUIRED_ARTIFACTS.includes('implementation.patch'));
assert(COMMAND_CENTER_REQUIRED_ARTIFACTS.includes('final-report.md'));
assert.equal(COMMAND_CENTER_DEFAULT_BASE_WORKSPACE.restoreStrategy, 'copy_overlay');
assert.equal(cleanBaseWorkspace({baseWorkspaceId: 'tank-base', snapshotRef: 'worker-local://tank'}).baseWorkspaceId, 'tank-base');
const oneShot = cleanOneShotExecution({requiredArtifacts: ['render.png'], verificationCommands: ['npm test']});
assert.equal(oneShot.executionMode, 'one_shot');
assert(oneShot.requiredArtifacts.includes('render.png'));
assert(oneShot.requiredArtifacts.includes('job-intake.json'));
assert.equal(oneShot.verificationCommands[0], 'npm test');

assert.equal(COMMAND_CENTER_DEFAULT_BUCKET_ID, 'command-center');
for (const kind of ['memory.past_log', 'memory.current_condensed', 'skill.scratch', 'skill.promoted', 'note.cross_repo', 'app_control.profile', 'app_control.run', 'app_control.frame_lane', 'browser.session', 'browser.episode', 'browser.discovery', 'browser.playbook']) {
  assert(COMMAND_CENTER_BUCKET_KINDS.includes(kind));
}
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['memory/past-logs'].kind, 'memory.past_log');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['memory/current-condensed'].kind, 'memory.current_condensed');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['skills/scratch'].kind, 'skill.scratch');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['skills/promoted'].kind, 'skill.promoted');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['notes/cross-repo'].kind, 'note.cross_repo');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['app-control/profiles'].kind, 'app_control.profile');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['app-control/runs'].kind, 'app_control.run');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['app-control/frame-lanes'].kind, 'app_control.frame_lane');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['browser/sessions'].kind, 'browser.session');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['browser/episodes'].kind, 'browser.episode');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['browser/discoveries'].kind, 'browser.discovery');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['browser/playbooks'].kind, 'browser.playbook');
assert.match(COMMAND_CENTER_BUCKET_LAYOUT.storagePolicy.secretPolicy, /No bearer tokens/);

const bucketObject = cleanBucketObject({
  idempotencyKey: 'bucket-test-001',
  kind: 'skill.scratch',
  title: 'Long running executor observation',
  body: 'Capture stdout batches and heartbeat evidence before promoting.',
  projectId: 'home-center',
  repository: 'Valar05/home-center',
  jobId: 'job_12345678',
  tags: ['worker', 'streaming'],
}, {actor: 'tester@example.com'});
assert.equal(bucketObject.bucketId, 'command-center');
assert.equal(bucketObject.kind, 'skill.scratch');
assert.equal(bucketObject.lane, 'skills/scratch');
assert.match(bucketObject.path, /^skills\/scratch\//);
assert.equal(bucketObject.projectId, 'home-center');
assert.equal(bucketObject.jobId, 'job_12345678');
assert.equal(bucketObject.provenance.noSecrets, true);
const forbiddenBearerFixture = ['Authorization:', 'Bearer', 'abcdefghijklmnopqrstuvwxyz'].join(' ');
assert.throws(() => cleanBucketObject({
  kind: 'note.cross_repo',
  title: 'bad',
  body: forbiddenBearerFixture,
}, {actor: 'tester@example.com'}), /must not contain reusable secrets/);

assert(COMMAND_CENTER_AGENT_ACTIVATION_STATUSES.includes('needs_human'));
assert.equal(COMMAND_CENTER_CODEX_CLOUD_SURFACE.surfaceId, 'openai-codex-cloud');
assert(COMMAND_CENTER_DURABLE_SESSION_RESTORE_STRATEGIES.includes('gcs_snapshot'));
assert.match(COMMAND_CENTER_CODEX_CLOUD_SURFACE.launchUrl, /^https:\/\/chatgpt\.com\/codex/);
assert.match(COMMAND_CENTER_CODEX_CLOUD_SURFACE.credentialPolicy, /Do not copy cookies/);
const repoAgent = cleanRepoAgent({
  agentId: 'home-center',
  projectId: 'home-center',
  repository: 'Valar05/home-center',
  contextRefs: ['docs/COMMAND_CENTER_MCP.md'],
}, {actor: 'tester@example.com'});
assert.equal(repoAgent.agentId, 'home-center');
assert.equal(repoAgent.agentType, 'repo_agent');
assert.equal(repoAgent.codexCloudSurface.surfaceId, 'openai-codex-cloud');
const session = cleanAgentSession({sessionId: 'session_home_center', title: 'Home Center Codex'}, repoAgent, {actor: 'tester@example.com'});
assert.equal(session.agentId, 'home-center');
assert.equal(session.sessionKind, 'durable_worker_session');
assert.equal(session.repositoryOptional, true);
assert.equal(session.runtime, 'cloud-run-debian');
assert.equal(session.restoreStrategy, 'gcs_snapshot');
const repoLessSession = cleanAgentSession({
  sessionId: 'session_general_research',
  projectId: 'general-research',
  title: 'General research worker',
  workerFamily: 'cloud-run-debian-research',
  currentWorkspaceSnapshotRef: 'gs://home-center-worker-sessions/general/snapshot-a.tgz',
}, {}, {actor: 'tester@example.com'});
assert.equal(repoLessSession.repository, '');
assert.equal(repoLessSession.projectId, 'general-research');
assert.equal(repoLessSession.workerFamily, 'cloud-run-debian-research');
assert.equal(repoLessSession.currentWorkspaceSnapshotRef, 'gs://home-center-worker-sessions/general/snapshot-a.tgz');
const task = cleanActivationTask({title: 'Inspect bridge', prompt: 'Inspect the durable Codex cloud bridge.', acceptanceCriteria: ['Report exact next files.']});
assert.equal(task.taskType, 'codex_cloud');
assert.match(task.prompt, /durable Codex cloud bridge/);
const codexRef = cleanCodexCloudRef({url: 'https://chatgpt.com/codex/tasks/abc', title: 'Real Codex task', status: 'running'});
assert.equal(codexRef.surface, 'openai-codex-cloud');
assert.throws(() => cleanCodexCloudRef({url: 'https://example.com/codex'}), /real ChatGPT\/OpenAI Codex cloud surface/);
assert.throws(() => cleanCodexCloudRef({url: 'https://chatgpt.com/codex/tasks/abc', summary: forbiddenBearerFixture}), /must not contain reusable credentials/);
const resumePacket = buildAgentResumePacket(repoAgent, session, {activationId: 'activation_12345678', status: 'queued', task, artifactRefs: [], codexCloudRefIds: []});
assert.equal(resumePacket.packetVersion, 'command-center-codex-cloud-resume-v1');
assert.equal(resumePacket.executionSurface.surfaceId, 'openai-codex-cloud');
assert.equal(resumePacket.workerSessionContract.durable, true);
assert.equal(resumePacket.workerSessionContract.repositoryOptional, true);
assert(resumePacket.bridgeInstructions.some((line) => line.includes('Restore the durable worker session workspace')));
assert.equal(resumePacket.activation.realWorkerRequired, false);

assert(commandCenterSource.includes("server.registerTool('command_center.jobs.get_handoff'"));
assert(commandCenterSource.includes("server.registerTool('command_center_operation'"));
assert(commandCenterSource.includes('runCommandCenterOperation'));
assert(commandCenterSource.includes("server.registerTool('command_center.projects.upsert'"));
assert(commandCenterSource.includes("server.registerTool('command_center.agents.upsert_repo_agent'"));
assert(commandCenterSource.includes("server.registerTool('command_center.agents.create_activation'"));
assert(commandCenterSource.includes("server.registerTool('command_center.agents.get_resume_packet'"));
assert(commandCenterSource.includes("server.registerTool('command_center.agents.record_codex_cloud_ref'"));
assert(commandCenterSource.includes("server.registerTool('command_center.agents.record_artifact'"));
assert(commandCenterSource.includes("server.registerTool('command_center.agents.complete_activation'"));
assert(commandCenterSource.includes("server.registerTool('command_center.agents.get_handoff'"));
assert(commandCenterSource.includes("server.registerTool('command_center.workers.wake'"));
assert(commandCenterSource.includes("case 'workers.wake'"));
assert(commandCenterSource.includes('Restore the durable worker session workspace'));
assert(commandCenterSource.includes('activationWorkerRequirements'));
assert(commandCenterSource.includes('deriveWorkerLiveness'));
assert(commandCenterSource.includes('reconcileStaleJobs'));
assert(commandCenterSource.includes("livenessState: heartbeatFresh ? 'live'"));
assert(commandCenterSource.includes("activatable: activatableWorkers.length"));
assert(commandCenterSource.includes("type: 'job_queued_no_worker'"));
assert(commandCenterSource.includes("lease: null, activation: null"));
assert(commandCenterSource.includes("requiredIndex: {collectionGroup: COMMAND_CENTER_COLLECTIONS.jobs"));
assert(commandCenterSource.includes("['leased', 'executing', 'running', 'activating']"));
assert(commandCenterSource.includes("status: 'expired'"));
assert(commandCenterSource.includes("selectWorker(recordsVisibleToCaller(await workerRecords(admin), caller), workerRequirements, {requireActivationChannel: false})"));
assert(commandCenterSource.includes("realWorkerRequired: true"));
assert(commandCenterSource.includes("selectedWorkerId: worker.workerId"));
assert(commandCenterSource.includes("Durable Codex worker activation completion requires at least one artifact."));
assert(commandCenterSource.includes("Durable worker session completion requires nextWorkspaceSnapshotRef."));
assert(commandCenterSource.includes("activation: z.record(z.string(), z.any()).optional(), runtime: z.record(z.string(), z.any()).optional(), cloudRunJob: z.record(z.string(), z.any()).optional(), sessionPolicy: z.record(z.string(), z.any()).optional()"));
assert(commandCenterSource.includes("case 'workers.retire'"));
assert(commandCenterSource.includes("server.registerTool('command_center.workers.retire'"));
assert(commandCenterSource.includes("queryOwnedCollection(admin, COMMAND_CENTER_COLLECTIONS.jobs"));
assert(commandCenterSource.includes("ownerKey: ownerKeyFromCaller(caller)"));
assert(commandCenterSource.includes("repository: safeText(args.repository, 240)"));
assert(commandCenterSource.includes("'acceptance-matrix.json'"));
assert(commandCenterSource.includes("app.post('/agent/claim'"));
assert(commandCenterSource.includes("app.post('/agent/heartbeat'"));
assert(commandCenterSource.includes("app.post('/agent/codex-ref'"));
assert(commandCenterSource.includes("app.post('/agent/artifacts'"));
assert(commandCenterSource.includes("app.post('/agent/complete'"));
assert(commandCenterSource.includes("server.registerTool('command_center.app_control.seed_profiles'"));
assert(commandCenterSource.includes("server.registerTool('command_center.app_control.list_profiles'"));
assert(commandCenterSource.includes("server.registerTool('command_center.browser_sessions.create'"));
assert(commandCenterSource.includes("server.registerTool('command_center.browser_sessions.record_episode'"));
assert(commandCenterSource.includes("server.registerTool('command_center.browser_discoveries.promote'"));
assert(commandCenterSource.includes("server.registerTool('command_center.browser_playbooks.lookup'"));
assert(commandCenterSource.includes('Coordinate-only browser discoveries cannot be promoted'));
const householdPlaybook = cleanBrowserPlaybook({
  taskKey: 'chatgpt.command_center_connector.verify',
  origin: 'https://chatgpt.com',
  learnedBy: 'drew',
  shareScope: 'household',
  replayAudience: 'june',
  actions: [{type: 'click', selectorLadder: [{kind: 'id', selector: '#connect', confidence: 0.95}]}],
});
assert.equal(householdPlaybook.taskKey, 'chatgpt.command_center_connector.verify');
assert.equal(householdPlaybook.learnedBy, 'drew');
assert.equal(householdPlaybook.shareScope, 'household');
assert.equal(householdPlaybook.replayAudience, 'june');
assert.match(householdPlaybook.selectorPolicy, /html_id/);
assert.match(householdPlaybook.householdLearningContract, /First successful household use/);
assert(commandCenterSource.includes("server.registerTool('command_center.jobs.create_followup'"));
assert(commandCenterSource.includes('synthesizeJobHandoff'));
assert(commandCenterSource.includes('createFollowupJob'));

console.log('Command Center MCP contract test: OK');
