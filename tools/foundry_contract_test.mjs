import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const {
  FOUNDRY_RECIPE_VERSION,
  foundryOperationEntries,
  queueFoundryRun,
  foundryStatus,
  promoteFoundryResult,
  executeFoundryJob,
  runChildProcess,
  runFoundryOperation,
} = require('../functions/foundry_capability.js');
const {driveOperationRegistry, createHomeCenterMcpServer, normalizeInstalledAppToolCall} = require('../functions/home_center_mcp.js');
const {runFoundryKernel, inspectGlbBytes} = await import('../functions/foundry_kernel.mjs');

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}
function hash(value) { return crypto.createHash('sha256').update(Buffer.isBuffer(value) ? value : Buffer.from(JSON.stringify(stable(value)))).digest('hex'); }

class Snapshot {
  constructor(value) { this.value = value; this.exists = value !== undefined; }
  data() { return structuredClone(this.value); }
}
class Ref {
  constructor(store, key) { this.store = store; this.key = key; }
  async get() { return new Snapshot(this.store.get(this.key)); }
  async create(value) { if (this.store.has(this.key)) { const error = new Error('already exists'); error.code = 6; throw error; } this.store.set(this.key, structuredClone(value)); }
  async set(value, options = {}) { const next = options.merge ? {...(this.store.get(this.key) || {}), ...structuredClone(value)} : structuredClone(value); this.store.set(this.key, next); }
}
class Firestore {
  constructor() { this.store = new Map(); this.transactionTail = Promise.resolve(); }
  collection(name) { return {doc: (id) => new Ref(this.store, `${name}/${id}`)}; }
  async runTransaction(fn) {
    const run = this.transactionTail.then(() => fn({get: (ref) => ref.get(), create: (ref, value) => ref.create(value), set: (ref, value, options) => ref.set(value, options)}));
    this.transactionTail = run.catch(() => {});
    return run;
  }
}
function fakeAdmin() { const db = new Firestore(); return {firestore: () => db, db}; }
class FakeStorage {
  constructor() { this.objects = new Map(); this.uploadCalls = 0; }
  bucket(name) {
    const self = this;
    return {
      name,
      file(objectName) {
        return {
          async download(options = {}) { const bytes = self.objects.get(`${name}/${objectName}`); if (!bytes) throw new Error(`missing object ${name}/${objectName}`); if (options.destination) { await fsp.writeFile(options.destination, bytes); return; } return [Buffer.from(bytes)]; },
          createReadStream() { const {Readable} = require('node:stream'); const bytes = self.objects.get(`${name}/${objectName}`); return Readable.from(bytes ? [bytes] : []); },
        };
      },
      async upload(localPath, options) { const key = `${name}/${options.destination}`; if (self.objects.has(key)) { const error = new Error('conditionNotMet'); error.code = 412; throw error; } self.objects.set(key, await fsp.readFile(localPath)); self.uploadCalls += 1; },
    };
  }
}

const recipes = {
  mechanical: {version: FOUNDRY_RECIPE_VERSION, domain: 'hard_surface', commands: [{op: 'mechanical_specimen'}]},
  setup: {version: FOUNDRY_RECIPE_VERSION, domain: 'character_setup', commands: [{op: 'add_weapon_bone'}, {op: 'attach_rigid_prop'}]},
  animation: {version: FOUNDRY_RECIPE_VERSION, domain: 'animation', commands: [{op: 'trim_clip'}, {op: 'retime_clip'}, {op: 'set_rotation_key'}]},
};
const fixture = {kind: 'foundry_fixture', fixtureId: 'foundry-character-v1'};

// Complete authenticated production tools/list representation is immutable.
process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
const server = createHomeCenterMcpServer({google: {}, admin: {firestore() { return {}; }}, googleClientId: () => 'configured', googleClientSecret: () => 'configured'});
const listed = await server.server._requestHandlers.get('tools/list')({method: 'tools/list', params: {}}, {});
const currentTools = stable([...(listed.tools || [])].sort((a, b) => a.name.localeCompare(b.name)));
const baselineTools = JSON.parse(fs.readFileSync(path.join(root, 'contracts/home-center-top-level-mcp.v1.json'), 'utf8'));
assert.deepEqual(currentTools, baselineTools, 'complete installed top-level MCP contract changed');
assert.equal(hash(currentTools), '64fe900eeaaf2928c2b6114829ee758ff73cc05700373085a1ae63b6484d05f1');
assert.equal(currentTools.length, 58);
assert.deepEqual(currentTools.filter((tool) => /foundry/i.test(tool.name)), [], 'Foundry must never become a top-level MCP tool');
const prefixedCall = {jsonrpc: '2.0', id: 1, method: 'tools/call', params: {name: 'home_center_drive.drive_operation', arguments: {operation: 'foundry.asset.status'}}};
const normalizedCall = normalizeInstalledAppToolCall(prefixedCall, server._registeredTools);
assert.equal(normalizedCall.params.name, 'drive_operation', 'installed app namespace must resolve to the canonical registered tool');
assert.equal(prefixedCall.params.name, 'home_center_drive.drive_operation', 'normalization must not mutate the caller envelope');
const canonicalCall = {...prefixedCall, params: {...prefixedCall.params, name: 'drive_operation'}};
assert.strictEqual(normalizeInstalledAppToolCall(canonicalCall, server._registeredTools), canonicalCall, 'canonical calls must pass through unchanged');
const unknownPrefixCall = {...prefixedCall, params: {...prefixedCall.params, name: 'other_app.drive_operation'}};
assert.strictEqual(normalizeInstalledAppToolCall(unknownPrefixCall, server._registeredTools), unknownPrefixCall, 'arbitrary namespaces must not be accepted');
const unknownToolCall = {...prefixedCall, params: {...prefixedCall.params, name: 'home_center_drive.not_registered'}};
assert.strictEqual(normalizeInstalledAppToolCall(unknownToolCall, server._registeredTools), unknownToolCall, 'the installed namespace must not create unregistered tools');
delete process.env.HOME_CENTER_MCP_EXTENDED_TOOLS;

const dynamic = Object.keys(foundryOperationEntries()).sort();
assert.deepEqual(dynamic, ['foundry.asset.inspect', 'foundry.asset.promote', 'foundry.asset.run', 'foundry.asset.status']);
for (const operation of dynamic) assert.ok(driveOperationRegistry().operations[operation], `${operation} is not dynamically discoverable`);
assert.equal(driveOperationRegistry().invocationTool, 'drive_operation');
await assert.rejects(() => runFoundryOperation({operation: 'foundry.asset.unknown', admin: fakeAdmin(), user: {email: 'owner@example.com'}, args: {}}), (error) => error.code === 'foundry.operation.unsupported');

await assert.rejects(() => runFoundryKernel({recipe: {...recipes.mechanical, version: 'v0'}}), (error) => error.code === 'foundry.recipe.unsupported_version');
await assert.rejects(() => runFoundryKernel({recipe: {...recipes.mechanical, commands: [{op: 'arbitrary_boolean'}]}}), (error) => error.code === 'foundry.recipe.unsupported_operation');

const mechanicalA = await runFoundryKernel({recipe: recipes.mechanical, parameters: {segments: 20}});
const mechanicalB = await runFoundryKernel({recipe: recipes.mechanical, parameters: {segments: 20}});
assert.equal(hash(mechanicalA.glb), hash(mechanicalB.glb), 'mechanical GLB is not deterministic');
assert.equal(hash(mechanicalA.contactSheet), hash(mechanicalB.contactSheet), 'mechanical review evidence is not deterministic');
assert.ok(mechanicalA.report.triangleCount > 0 && mechanicalA.report.componentCount >= 4);
assert.ok(mechanicalA.report.validation.manifoldClosedComponents >= 1);

const setup = await runFoundryKernel({recipe: recipes.setup, fixtureId: 'foundry-character-v1'});
assert.equal(setup.report.preservation.meshHashEqual, true);
assert.equal(setup.report.preservation.animationHashEqual, true);
assert.equal(setup.report.preservation.originalJointOrderPreserved, true);
assert.equal(setup.report.preservation.originalInverseBindPrefixPreserved, true);
assert.equal(setup.report.preservation.addedJoint, 'weapon_socket_r');
assert.equal(setup.report.preservation.rigidPropSkinned, false);
const setupRoundTrip = await inspectGlbBytes(setup.glb);
assert.ok(setupRoundTrip.report.skins[0].joints.includes('weapon_socket_r'));
assert.ok(setupRoundTrip.report.hierarchy.some((node) => node.name === 'fixture_weapon' && node.parent === 'weapon_socket_r'));

const animation = await runFoundryKernel({recipe: recipes.animation, fixtureId: 'foundry-character-v1'});
assert.equal(animation.report.preservation.geometryHashEqual, true);
assert.equal(animation.report.preservation.skinHashEqual, true);
assert.equal(animation.report.preservation.outputClip, 'fixture_idle_foundry');
assert.ok(animation.skeletalOverlay.length > 100);
const animationRoundTrip = await inspectGlbBytes(animation.glb);
assert.equal(animationRoundTrip.report.animations[0].name, 'fixture_idle_foundry');
assert.ok(Math.abs(animationRoundTrip.report.animations[0].duration - 1.2) < 0.0001, 'animation was not retimed to the requested duration');

const admin = fakeAdmin();
const storage = new FakeStorage();
const enqueued = [];
const enqueue = async (payload) => { enqueued.push(structuredClone(payload)); };
const user = {email: 'owner@example.com'};
const baseArgs = {recipe: recipes.mechanical, parameters: {segments: 16}, reviewPreset: 'fixed-four-view', idempotencyKey: 'mechanical-1', namespace: 'specimen-a'};
const accepted = await runFoundryOperation({operation: 'foundry.asset.run', admin, storage, user, args: baseArgs, enqueue});
assert.equal(accepted.accepted, true);
assert.equal(accepted.attached, false);
assert.equal(enqueued.length, 1);
const attached = await queueFoundryRun({admin, storage, user, args: baseArgs, enqueue});
assert.equal(attached.attached, true);
assert.equal(attached.jobId, accepted.jobId);
assert.equal(enqueued.length, 1, 'idempotent replay enqueued duplicate work');
await assert.rejects(() => queueFoundryRun({admin, storage, user, args: {...baseArgs, parameters: {segments: 18}}, enqueue}), (error) => error.code === 'foundry.idempotency_conflict');

const inspectAccepted = await runFoundryOperation({operation: 'foundry.asset.inspect', admin, storage, user, args: {source: fixture, idempotencyKey: 'inspect-fixture', namespace: 'inspect-fixture'}, enqueue});
assert.equal(inspectAccepted.accepted, true);
assert.equal(enqueued.length, 2);

const acceptedB = await queueFoundryRun({admin, storage, user, args: {...baseArgs, idempotencyKey: 'mechanical-2', namespace: 'specimen-b'}, enqueue});
assert.notEqual(acceptedB.jobId, accepted.jobId);
assert.notEqual(acceptedB.inputHash, accepted.inputHash);
assert.equal(enqueued.length, 3);

const completedA = await executeFoundryJob(admin, enqueued[0], {storage});
const uploadCountAfterA = storage.uploadCalls;
const replayA = await executeFoundryJob(admin, enqueued[0], {storage});
assert.equal(replayA.result.resultHash, completedA.result.resultHash);
assert.equal(storage.uploadCalls, uploadCountAfterA, 'completed replay duplicated immutable uploads');
const completedB = await executeFoundryJob(admin, enqueued[2], {storage});
assert.notEqual(completedA.result.cacheKey, completedB.result.cacheKey);
assert.ok(completedA.result.artifacts.every((artifact) => artifact.storageRef.includes('/specimen-a/')));
assert.ok(completedB.result.artifacts.every((artifact) => artifact.storageRef.includes('/specimen-b/')));
assert.ok(completedA.result.artifacts.every((artifact) => !artifact.storageRef.toLowerCase().includes('/latest')));
assert.ok(Buffer.byteLength(JSON.stringify(completedA)) < 64 * 1024, 'Foundry receipt is unbounded');

const leaseAccepted = await queueFoundryRun({admin, storage, user, args: {...baseArgs, idempotencyKey: 'mechanical-lease', namespace: 'specimen-lease'}, enqueue});
const leasePayload = enqueued.at(-1);
const uploadsBeforeLease = storage.uploadCalls;
const leaseResults = await Promise.all([executeFoundryJob(admin, leasePayload, {storage}), executeFoundryJob(admin, leasePayload, {storage})]);
assert.ok(leaseResults.some((receipt) => receipt.state === 'completed'));
assert.equal(storage.uploadCalls - uploadsBeforeLease, 7, 'active duplicate delivery executed or uploaded twice');
assert.equal((await foundryStatus({admin, user, args: {jobId: leaseAccepted.jobId}})).state, 'completed');
assert.ok([...storage.objects.keys()].some((key) => key.includes('/logs/stdout.log')), 'bounded stdout log was not persisted');
assert.ok([...storage.objects.keys()].some((key) => key.includes('/logs/stderr.log')), 'bounded stderr log was not persisted');

const timeoutAccepted = await queueFoundryRun({admin, storage, user, args: {...baseArgs, idempotencyKey: 'mechanical-timeout', namespace: 'specimen-timeout'}, enqueue});
const timeoutPayload = enqueued.at(-1);
await assert.rejects(() => executeFoundryJob(admin, timeoutPayload, {storage, timeoutMs: 100, spawnImpl: (_command, _args, options) => spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], options)}), (error) => error.code === 'foundry.worker.timeout');
const timeoutStatus = await foundryStatus({admin, user, args: {jobId: timeoutAccepted.jobId}});
assert.equal(timeoutStatus.state, 'failed');
assert.equal(timeoutStatus.execution.timedOut, true);
assert.ok([...storage.objects.keys()].some((key) => key.includes('/specimen-timeout/') && key.includes('/attempt-0/logs/stdout.log')), 'failed worker logs were not persisted');

const status = await runFoundryOperation({operation: 'foundry.asset.status', admin, user, args: {jobId: accepted.jobId}});
assert.equal(status.state, 'completed');
await assert.rejects(() => foundryStatus({admin, user: {email: 'other@example.com'}, args: {jobId: accepted.jobId}}), (error) => error.code === 'foundry.job_forbidden');
const promotion = await runFoundryOperation({operation: 'foundry.asset.promote', admin, user, args: {approved: true, jobId: accepted.jobId, resultHash: completedA.result.resultHash, requestId: 'promote-1'}});
const promotionReplay = await promoteFoundryResult({admin, user, args: {approved: true, jobId: accepted.jobId, resultHash: completedA.result.resultHash, requestId: 'promote-1'}});
assert.deepEqual(promotionReplay, promotion);
assert.match(promotion.viewerUrl, /^https:\/\/valar05\.github\.io\/model-viewer-lab\/model-viewer\.html\?/);
assert.ok(promotion.links.some((link) => link.kind === 'glb'));
assert.ok(promotion.links.every((link) => link.url.includes(promotion.promotionId)));
await assert.rejects(() => promoteFoundryResult({admin, user, args: {approved: false, jobId: accepted.jobId, resultHash: completedA.result.resultHash}}), (error) => error.code === 'foundry.promotion.approval_required');

const timeoutRoot = await fsp.mkdtemp(path.join(os.tmpdir(), 'foundry-timeout-test-'));
try {
  const timeoutResult = await runChildProcess({requestPath: path.join(timeoutRoot, 'request.json'), outputDir: timeoutRoot, stdoutPath: path.join(timeoutRoot, 'stdout.log'), stderrPath: path.join(timeoutRoot, 'stderr.log'), timeoutMs: 100, spawnImpl: (_command, _args, options) => spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], options)});
  assert.equal(timeoutResult.timedOut, true);
  assert.notEqual(timeoutResult.signal, null);
} finally { await fsp.rm(timeoutRoot, {recursive: true, force: true}); }

const logRoot = await fsp.mkdtemp(path.join(os.tmpdir(), 'foundry-log-test-'));
try {
  const logResult = await runChildProcess({requestPath: path.join(logRoot, 'request.json'), outputDir: logRoot, stdoutPath: path.join(logRoot, 'stdout.log'), stderrPath: path.join(logRoot, 'stderr.log'), timeoutMs: 2000, spawnImpl: (_command, _args, options) => spawn(process.execPath, ['-e', `process.stdout.write('x'.repeat(100000)); process.stderr.write('y'.repeat(100000))`], options)});
  assert.equal(logResult.code, 0);
  assert.equal(logResult.stdout.truncated, true);
  assert.equal(logResult.stderr.truncated, true);
  assert.ok(logResult.stdout.bytes <= 64 * 1024 && logResult.stderr.bytes <= 64 * 1024);
} finally { await fsp.rm(logRoot, {recursive: true, force: true}); }

for (const file of ['functions/foundry_capability.js', 'functions/foundry_kernel.mjs', 'functions/foundry_worker_process.mjs']) {
  const source = fs.readFileSync(path.join(root, file), 'utf8');
  assert.doesNotMatch(source, /\bbpy\b|spawn\s*\([^\n]*blender|exec(?:File)?\s*\([^\n]*blender/i, `${file} contains a Blender invocation`);
  assert.doesNotMatch(source, /[\/'"]latest[\/'"]|globalLatest|latestArtifact/i, `${file} contains mutable latest behavior`);
}

console.log(JSON.stringify({
  ok: true,
  baselineTopLevelMcpHash: hash(baselineTools),
  finalTopLevelMcpHash: hash(currentTools),
  dynamicOperations: dynamic,
  deterministicMechanicalGlbSha256: hash(mechanicalA.glb),
  characterGlbSha256: hash(setup.glb),
  animationGlbSha256: hash(animation.glb),
  isolatedJobs: [completedA.jobId, completedB.jobId],
  immutableObjects: storage.objects.size,
  duplicateUploadsOnReplay: 0,
}, null, 2));
