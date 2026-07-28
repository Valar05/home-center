#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  renderBlenderGlb,
  renderRequestStatus,
  reconcileRenderRequest,
  executeQueuedRenderRequest,
  renderRequestInputHash,
} = require('../functions/command_center_mcp.js');

class Snapshot {
  constructor(value) { this.value = value; this.exists = value !== undefined; }
  data() { return this.value; }
}
class Doc {
  constructor(store, path) { this.store = store; this.path = path; this.id = path.split('/').pop(); }
  async get() { return new Snapshot(this.store.get(this.path)); }
  set(value, options = {}) { const prior = this.store.get(this.path) || {}; this.store.set(this.path, options.merge ? {...prior, ...value} : value); }
  create(value) { if (this.store.has(this.path)) throw Object.assign(new Error('already exists'), {code: 6}); this.store.set(this.path, value); }
}
class Collection {
  constructor(store, name) { this.store = store; this.name = name; }
  doc(id) { return new Doc(this.store, this.name + '/' + id); }
}
function fakeAdmin() {
  const store = new Map();
  const firestore = () => ({
    collection: (name) => new Collection(store, name),
    runTransaction: async (callback) => callback({
      get: async (ref) => ref.get(),
      set: (ref, value, options) => ref.set(value, options),
      create: (ref, value) => ref.create(value),
    }),
  });
  return {store, firestore};
}

const admin = fakeAdmin();
const token = 'queue-contract-token';
const tokenHash = createHash('sha256').update(token).digest('hex');
admin.store.set('mcpOAuthAccessTokens/' + tokenHash, {email: 'dclarke1005@gmail.com', expiresAtMs: Date.now() + 600000});
const extra = {requestInfo: {headers: new Map([['authorization', 'Bearer ' + token]])}};
const caller = {actor: 'dclarke1005@gmail.com', ownerKey: 'owner_' + createHash('sha256').update('dclarke1005@gmail.com').digest('hex').slice(0, 32)};
const refs = {
  glb: 'gs://proof/input.glb',
  script: 'gs://proof/render.py',
};
const stagedInputs = [
  {ref: refs.glb, sha256: '1'.repeat(64), byteCount: 100, fileName: 'input.glb', materializedFrom: 'glbDurableRef', materializedBy: 'artifact_transport.preflight'},
  {ref: refs.script, sha256: '2'.repeat(64), byteCount: 50, fileName: 'render.py', materializedFrom: 'scriptDurableRef', materializedBy: 'artifact_transport.preflight'},
];
const baseArgs = {
  idempotencyKey: 'queue-proof-1',
  contractVersion: 'home-center.blender-render-request.v2',
  glbRef: refs.glb,
  scriptRef: refs.script,
  stagedInputs,
  settings: {gifFrames: [0, 1], gifTimingMs: [100, 120], includeBlend: true, includeDiagnostics: true},
  executionContract: {includeBlend: true, includeDiagnostics: true},
  cache: true,
};
const enqueued = [];
const enqueueRenderTask = async (payload) => { enqueued.push(payload); };
await assert.rejects(
  () => renderBlenderGlb(admin, extra, {...baseArgs, idempotencyKey: 'queue-drive-ref-rejected', glbRef: 'drive://raw-user-file'}, {enqueueRenderTask}),
  /cannot retain user OAuth credentials/,
);
const first = await renderBlenderGlb(admin, extra, baseArgs, {enqueueRenderTask});
assert.equal(first.accepted, true);
assert.equal(first.status, 'queued');
assert.equal(first.attached, false);
assert.equal(enqueued.length, 1);
assert.match(first.inputHash, /^[a-f0-9]{64}$/);
assert.equal(renderRequestInputHash({
  contractVersion: baseArgs.contractVersion,
  glbRef: refs.glb,
  scriptRef: refs.script,
  stagedInputs,
  settings: {width: 1280, height: 960, camera: 'front_3q', outputName: 'render.png', samples: 64, fixedCameras: ['front_3q'], diagnosticViews: ['front', 'side', 'top'], action: '', expectedAction: '', authoredKeys: [], evidenceFrames: [], gifFrames: [0, 1], gifTimingMs: [100, 120], allowRepeatedGifFrames: false, includeBlend: true, includeDiagnostics: true},
  executionContract: {contractVersion: 'glb-script-durable-3d-artifact-v1', atomicOperation: 'GLB + script + execution contract -> durable 3D artifact + visual evidence', requireBundleKinds: ['rendered_frames','contact_sheet','native_pose_animation_data','script_input_hashes','blender_version_settings','stdout_stderr','fixed_camera_renders','diagnostic_view_renders','validation_manifest','original_script','three_d_artifact'], framesAreInsufficient: true, preserve3dTruth: true, includeBlend: true, includeDiagnostics: true},
}), first.inputHash);

const replay = await renderBlenderGlb(admin, extra, baseArgs, {enqueueRenderTask});
assert.equal(replay.attached, true);
assert.equal(enqueued.length, 1, 'same exact request must not enqueue a duplicate task');
await assert.rejects(
  () => renderBlenderGlb(admin, extra, {...baseArgs, stagedInputs: [stagedInputs[0], {...stagedInputs[1], sha256: '3'.repeat(64)}]}, {enqueueRenderTask}),
  /different render artifact identities/,
);

let invokeCount = 0;
const requiredKinds = ['rendered_frames','contact_sheet','native_pose_animation_data','script_input_hashes','blender_version_settings','stdout_stderr','fixed_camera_renders','diagnostic_view_renders','validation_manifest','original_script','three_d_artifact'];
const completed = await executeQueuedRenderRequest(admin, enqueued[0], {invokeRenderService: async () => {
  invokeCount += 1;
  return {ok: true, status: 'completed', cacheKey: 'a'.repeat(64), bundle: {unboundedProviderPayload: 'x'.repeat(100000)}, refs: {renderedFrames: ['gs://proof/frame.png'], fixedCameraRenders: ['gs://proof/front.png'], diagnosticViewRenders: ['gs://proof/side.png'], threeDArtifacts: ['gs://proof/out.glb'], validationManifest: 'gs://proof/manifest.json'}, validationManifest: {presentBundleKinds: requiredKinds, ok: true, gifPlaybackContract: {gifFrameSelection: 'explicit', gifFrames: [0, 1], gifTimingMs: [100, 120], selectedFrames: [{playbackIndex: 0, evidenceFrame: 0, name: 'frame-0.png', timingMs: 100}]}}, renderOptions: {includeBlend: true, includeDiagnostics: true}};
}});
assert.equal(completed.status, 'completed');
assert.equal(invokeCount, 1);
await executeQueuedRenderRequest(admin, enqueued[0], {invokeRenderService: async () => { invokeCount += 1; throw new Error('must not execute'); }});
assert.equal(invokeCount, 1, 'terminal task replay must attach without another renderer invocation');
const status = await renderRequestStatus(admin, caller, {renderId: first.renderId});
assert.equal(status.status, 'completed');
assert.equal(status.result.renderRefs.length, 1);
assert.equal(status.result.bundle, undefined);
assert.deepEqual(status.result.validation.gifPlayback.gifFrames, [0, 1]);
assert.deepEqual(status.result.validation.gifPlayback.gifTimingMs, [100, 120]);
assert.ok(JSON.stringify(status).length < 50000, 'status must remain bounded when the provider result contains an unbounded bundle');
assert.equal(JSON.stringify(status).includes('Bearer'), false);

const ambiguousArgs = {...baseArgs, idempotencyKey: 'queue-proof-ambiguous', stagedInputs: [stagedInputs[0], {...stagedInputs[1], sha256: '4'.repeat(64)}]};
const ambiguous = await renderBlenderGlb(admin, extra, ambiguousArgs, {enqueueRenderTask});
const ambiguousTask = enqueued.at(-1);
const quarantined = await executeQueuedRenderRequest(admin, ambiguousTask, {invokeRenderService: async () => { const error = new Error('connection closed after request dispatch'); error.status = 503; error.failureKind = 'transport'; throw error; }});
assert.equal(quarantined.status, 'quarantined');
const beforeReconcile = enqueued.length;
const reconciled = await reconcileRenderRequest(admin, caller, {renderId: ambiguous.renderId, resolution: 'retry_safe', evidence: 'Provider logs show no output manifest and aborted process.', idempotencyKey: 'reconcile-ambiguous-1'}, {enqueueRenderTask});
assert.equal(reconciled.status, 'queued');
assert.equal(reconciled.executionAttempt, 1);
assert.equal(enqueued.length, beforeReconcile + 1, 'explicit reconciliation may enqueue exactly one new attempt');

const stalledArgs = {...baseArgs, idempotencyKey: 'queue-proof-stalled', stagedInputs: [stagedInputs[0], {...stagedInputs[1], sha256: '5'.repeat(64)}]};
const stalled = await renderBlenderGlb(admin, extra, stalledArgs, {enqueueRenderTask});
const stalledPath = 'commandCenterRenderRequests/' + stalled.renderId;
admin.store.set(stalledPath, {...admin.store.get(stalledPath), status: 'running', enqueueStatus: 'running', lease: {leaseId: 'expired', holder: 'worker', acquiredAtMs: Date.now() - 3000, expiresAtMs: Date.now() - 1000}});
const stalledStatus = await renderRequestStatus(admin, caller, {renderId: stalled.renderId});
assert.equal(stalledStatus.status, 'stalled');
const stalledReconcile = await reconcileRenderRequest(admin, caller, {renderId: stalled.renderId, resolution: 'retry_safe', evidence: 'Lease expired and provider inventory contains no output manifest.', idempotencyKey: 'reconcile-stalled-1'}, {enqueueRenderTask});
assert.equal(stalledReconcile.status, 'queued');
assert.equal(stalledReconcile.executionAttempt, 1);
console.log(JSON.stringify({ok: true, firstReceipt: first, completedStatus: status.status, ambiguousStatus: quarantined.status, stalledStatus: stalledStatus.status, enqueueCount: enqueued.length, invokeCount}, null, 2));
