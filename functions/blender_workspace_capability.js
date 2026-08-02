'use strict';

const {createHash} = require('node:crypto');
const {CloudTasksClient} = require('@google-cloud/tasks');
const {Storage} = require('@google-cloud/storage');
const {readArtifactOperation, ARTIFACT_BUCKET} = require('./artifact_ingest_service');

const CONTRACT_VERSION = 'home-center.blender-workspace.v1';
const RECIPE_VERSION = 'home-center.blender-workspace-recipe.v1';
const REGISTRY_VERSION = '2026-08-02.blender-render-deprecated-v1';
const RENDER_DEPRECATION = Object.freeze({status: 'deprecated', deprecated: true, retainedForCompatibility: true, agentPolicy: 'Do not select blender.workspace.render for new work.', alternatives: ['blender.workspace.inspect', 'blender.workspace.export']});
const WORKSPACES = 'blenderWorkspaces';
const REVISIONS = 'blenderWorkspaceRevisions';
const OPERATIONS = 'blenderWorkspaceOperations';
const IDEMPOTENCY = 'blenderWorkspaceIdempotency';
const DEFAULT_REGION = process.env.BLENDER_WORKSPACE_REGION || 'us-central1';
const DEFAULT_QUEUE = process.env.BLENDER_WORKSPACE_QUEUE || 'blenderWorkspace';
const MAX_REVISIONS = 500;
let tasksClient = null;
let storageClient = null;

function tasks() { if (!tasksClient) tasksClient = new CloudTasksClient(); return tasksClient; }
function storage() { if (!storageClient) storageClient = new Storage(); return storageClient; }
function text(value, max = 1000) { const clean = typeof value === 'string' ? value.trim() : ''; return clean.slice(0, max); }
function stable(value) { if (Array.isArray(value)) return value.map(stable); if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])])); return value; }
function sha256(value) { return createHash('sha256').update(value).digest('hex'); }
function hashJson(value) { return sha256(Buffer.from(JSON.stringify(stable(value)))); }
function fail(code, message, status = 400, details = {}) { const error = new Error(message); error.code = code; error.status = status; error.details = details; return error; }
function ownerEmail(user) { const owner = text(user && user.email, 320).toLowerCase(); if (!owner) throw fail('blender.workspace.owner_required', 'An authenticated workspace owner is required.', 401); return owner; }
function ownerHash(owner) { return sha256(Buffer.from(owner)).slice(0, 24); }
function requestKey(args) { const value = text(args.idempotencyKey || args.requestId, 180); if (!value) throw fail('blender.workspace.idempotency_required', 'idempotencyKey is required.'); return value; }
function approved(args) { if (args.approved !== true) throw fail('blender.workspace.approval_required', 'approved=true is required for workspace mutations.', 409); }
function id(prefix, value, length = 32) { return prefix + '_' + sha256(Buffer.from(value)).slice(0, length); }
function projectId(admin) { return process.env.BLENDER_WORKSPACE_PROJECT || process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT || admin.app().options.projectId || ''; }
function revisionRef(admin, revisionId) { return admin.firestore().collection(REVISIONS).doc(revisionId); }
function workspaceRef(admin, workspaceId) { return admin.firestore().collection(WORKSPACES).doc(workspaceId); }
function operationRef(admin, operationId) { return admin.firestore().collection(OPERATIONS).doc(operationId); }
function boundedRecipe(value) {
  const recipe = value && typeof value === 'object' && !Array.isArray(value) ? stable(value) : {};
  if (recipe.contractVersion !== RECIPE_VERSION) throw fail('blender.workspace.recipe_version', 'recipe.contractVersion must be ' + RECIPE_VERSION + '.');
  if (!Array.isArray(recipe.operations) || recipe.operations.length < 1 || recipe.operations.length > 512) throw fail('blender.workspace.recipe_operations', 'recipe.operations must contain 1-512 typed Blender operations.');
  const bytes = Buffer.byteLength(JSON.stringify(recipe));
  if (bytes > 512 * 1024) throw fail('blender.workspace.recipe_too_large', 'Typed Blender recipe exceeds 512 KiB.', 413);
  return recipe;
}
function operationEntries() {
  return {
    'blender.workspace.create': {summary: 'Create an owner-scoped persistent Blender workspace and immutable initial .blend revision, optionally from an authorized Home Center artifact.', write: true, requiresRequestId: true, input: {approved: 'must be true', idempotencyKey: 'string', workspaceName: 'string', source: 'optional {kind:empty|home_center_artifact,artifactId}', recipe: RECIPE_VERSION}},
    'blender.workspace.inspect': {summary: 'Read actual hierarchy, topology, transforms, pivots, modifiers, constraints, materials, animation and warnings from one exact immutable Blender revision.', write: false, input: {workspaceId: 'string', revisionId: 'string'}},
    'blender.workspace.history': {summary: 'List the immutable revision lineage and explicit current revision for one owned Blender workspace.', write: false, input: {workspaceId: 'string'}},
    'blender.workspace.mutate': {summary: 'Apply one typed bpy/BMesh recipe to an explicit base revision and create a new immutable .blend revision; stale writes fail closed.', write: true, requiresRequestId: true, input: {approved: 'must be true', workspaceId: 'string', baseRevisionId: 'string', idempotencyKey: 'string', recipe: RECIPE_VERSION}},
    'blender.workspace.restore': {summary: 'Restore an earlier immutable .blend by creating a new revision from it; historical revisions are never overwritten.', write: true, requiresRequestId: true, input: {approved: 'must be true', workspaceId: 'string', baseRevisionId: 'current revision', sourceRevisionId: 'historical revision', idempotencyKey: 'string'}},
    'blender.workspace.render': {summary: 'DEPRECATED: retained for compatibility only. Do not select for new work. Legacy callers may still render evidence from one exact Blender revision.', write: true, requiresRequestId: true, deprecated: true, status: 'deprecated', retainedForCompatibility: true, agentPolicy: RENDER_DEPRECATION.agentPolicy, alternatives: RENDER_DEPRECATION.alternatives, input: {approved: 'must be true', workspaceId: 'string', revisionId: 'string', idempotencyKey: 'string', presets: 'optional array'}},
    'blender.workspace.export': {summary: 'Export one exact persistent .blend revision as .blend, articulated animated GLB, inspection manifest and validation report.', write: true, requiresRequestId: true, input: {approved: 'must be true', workspaceId: 'string', revisionId: 'string', idempotencyKey: 'string'}},
    'blender.workspace.status': {summary: 'Poll one owned Blender workspace operation and receive immutable hashes and signed retrieval URLs when terminal.', write: false, input: {operationId: 'string'}},
  };
}
async function resolveSource({user, args}) {
  const source = args.source && typeof args.source === 'object' ? args.source : {kind: 'empty'};
  const kind = text(source.kind, 80) || 'empty';
  if (kind === 'empty') return {kind: 'empty'};
  if (kind !== 'home_center_artifact') throw fail('blender.workspace.source_kind', 'source.kind must be empty or home_center_artifact.');
  const artifactId = text(source.artifactId, 180);
  const result = await readArtifactOperation({storage: storage(), user, args: {artifactId}});
  const manifest = result.manifest || {}, destination = manifest.destination || {};
  const objectName = text(destination.objectName, 1200) || text(destination.storageRef, 1400).replace(/^gs:\/\/[^/]+\//, '');
  const bucket = text(destination.bucket, 240) || ARTIFACT_BUCKET;
  const digest = text(destination.sha256, 64).toLowerCase();
  const byteLength = Number(destination.byteCount || destination.byteLength || 0);
  const name = text(manifest.identity && manifest.identity.name || manifest.name || source.name, 240).toLowerCase();
  if (!objectName || !/^[a-f0-9]{64}$/.test(digest) || !Number.isSafeInteger(byteLength) || byteLength < 1) throw fail('blender.workspace.source_manifest', 'Authorized artifact lacks a complete immutable object identity.', 422);
  if (!name.endsWith('.blend') && !name.endsWith('.glb')) throw fail('blender.workspace.source_format', 'Workspace import supports .blend or .glb source artifacts.', 415);
  return {kind, artifactId, bucket, objectName, sha256: digest, byteLength, format: name.endsWith('.blend') ? 'blend' : 'glb'};
}
async function enqueue(admin, operationId) {
  const target = text(process.env.BLENDER_WORKSPACE_TASK_URL, 1600);
  const serviceAccountEmail = text(process.env.BLENDER_WORKSPACE_TASK_SERVICE_ACCOUNT, 320);
  const project = projectId(admin);
  if (!target || !serviceAccountEmail || !project) throw fail('blender.workspace.executor_unconfigured', 'Blender workspace task target is not configured.', 503);
  const parent = tasks().queuePath(project, DEFAULT_REGION, DEFAULT_QUEUE);
  const name = tasks().taskPath(project, DEFAULT_REGION, DEFAULT_QUEUE, operationId.replace(/[^A-Za-z0-9_-]/g, '-'));
  const task = {name, httpRequest: {httpMethod: 'POST', url: target + '/task', headers: {'Content-Type': 'application/json'}, body: Buffer.from(JSON.stringify({operationId})).toString('base64'), oidcToken: {serviceAccountEmail, audience: target}}};
  try { await tasks().createTask({parent, task}); }
  catch (error) { if (Number(error && error.code) !== 6 && !/already exists/i.test(String(error && error.message))) throw error; }
}
async function createWorkspace({admin, user, args}) {
  approved(args); const owner = ownerEmail(user), key = requestKey(args); const inputRecipe = boundedRecipe(args.recipe);
  const source = await resolveSource({user, args}); const inputHash = hashJson({owner, key, source, recipe: inputRecipe, workspaceName: text(args.workspaceName, 160)});
  const workspaceId = id('bws', owner + ':' + key, 30), revisionId = id('brv', workspaceId + ':initial:' + inputHash, 30), operationId = id('bop', owner + ':create:' + key, 30), idemRef = admin.firestore().collection(IDEMPOTENCY).doc(id('idem', owner + ':create:' + key, 40));
  let attached = false;
  await admin.firestore().runTransaction(async (tx) => {
    const existing = await tx.get(idemRef);
    if (existing.exists) { const data = existing.data() || {}; if (data.inputHash !== inputHash) throw fail('blender.workspace.idempotency_conflict', 'idempotencyKey is bound to different workspace input.', 409); attached = true; return; }
    const now = new Date().toISOString();
    tx.create(workspaceRef(admin, workspaceId), {contractVersion: CONTRACT_VERSION, workspaceId, workspaceName: text(args.workspaceName, 160) || 'Blender Workspace', owner, ownerHash: ownerHash(owner), currentRevisionId: null, pendingOperationId: operationId, revisionIds: [], createdAt: now, updatedAt: now});
    tx.create(revisionRef(admin, revisionId), {contractVersion: CONTRACT_VERSION, workspaceId, revisionId, parentRevisionId: null, owner, state: 'reserved', createdByOperationId: operationId, createdAt: now});
    tx.create(operationRef(admin, operationId), {contractVersion: CONTRACT_VERSION, operationId, kind: 'create', state: 'queued', owner, ownerHash: ownerHash(owner), workspaceId, targetRevisionId: revisionId, baseRevisionId: null, inputHash, source, recipeJson: JSON.stringify(inputRecipe), humanAcceptance: 'unreviewed', createdAt: now, updatedAt: now});
    tx.create(idemRef, {owner, kind: 'create', inputHash, operationId, workspaceId, revisionId, createdAt: now});
  });
  if (!attached) await enqueue(admin, operationId);
  return {contractVersion: CONTRACT_VERSION, operationId, workspaceId, targetRevisionId: revisionId, state: 'queued', attached};
}
async function loadOwnedWorkspace(admin, owner, workspaceId) { const snap = await workspaceRef(admin, workspaceId).get(); if (!snap.exists) throw fail('blender.workspace.not_found', 'Workspace not found.', 404); const data = snap.data() || {}; if (data.owner !== owner) throw fail('blender.workspace.forbidden', 'Workspace is not owned by this caller.', 403); return {ref: snap.ref, data}; }
async function loadOwnedRevision(admin, owner, workspaceId, revisionId) { const snap = await revisionRef(admin, revisionId).get(); if (!snap.exists) throw fail('blender.workspace.revision_not_found', 'Revision not found.', 404); const data = snap.data() || {}; if (data.owner !== owner || data.workspaceId !== workspaceId) throw fail('blender.workspace.revision_forbidden', 'Revision is not owned by this workspace owner.', 403); return data; }
async function reserveMutation({admin, user, args, kind}) {
  approved(args); const owner = ownerEmail(user), key = requestKey(args), workspaceId = text(args.workspaceId, 80), baseRevisionId = text(args.baseRevisionId, 80); if (!workspaceId || !baseRevisionId) throw fail('blender.workspace.base_required', 'workspaceId and baseRevisionId are required.');
  const recipe = kind === 'mutate' ? boundedRecipe(args.recipe) : {contractVersion: RECIPE_VERSION, operations: [{op: 'workspace.restore', sourceRevisionId: text(args.sourceRevisionId, 80)}]};
  const sourceRevisionId = kind === 'restore' ? text(args.sourceRevisionId, 80) : baseRevisionId;
  if (kind === 'restore' && !sourceRevisionId) throw fail('blender.workspace.restore_source_required', 'sourceRevisionId is required.');
  await loadOwnedRevision(admin, owner, workspaceId, sourceRevisionId);
  const inputHash = hashJson({owner, kind, workspaceId, baseRevisionId, sourceRevisionId, recipe});
  const operationId = id('bop', owner + ':' + kind + ':' + key, 30), targetRevisionId = id('brv', workspaceId + ':' + operationId + ':' + inputHash, 30), idemRef = admin.firestore().collection(IDEMPOTENCY).doc(id('idem', owner + ':' + kind + ':' + key, 40)); let attached = false;
  await admin.firestore().runTransaction(async (tx) => {
    const existing = await tx.get(idemRef); if (existing.exists) { const data = existing.data() || {}; if (data.inputHash !== inputHash) throw fail('blender.workspace.idempotency_conflict', 'idempotencyKey is bound to different mutation input.', 409); attached = true; return; }
    const wsRef = workspaceRef(admin, workspaceId), wsSnap = await tx.get(wsRef); if (!wsSnap.exists) throw fail('blender.workspace.not_found', 'Workspace not found.', 404); const ws = wsSnap.data() || {}; if (ws.owner !== owner) throw fail('blender.workspace.forbidden', 'Workspace is not owned by this caller.', 403);
    if (ws.currentRevisionId !== baseRevisionId) throw fail('blender.workspace.revision_conflict', 'baseRevisionId is stale.', 409, {baseRevisionId, currentRevisionId: ws.currentRevisionId});
    if (ws.pendingOperationId) throw fail('blender.workspace.concurrent_mutation', 'Another mutation is pending for this workspace.', 409, {pendingOperationId: ws.pendingOperationId});
    const now = new Date().toISOString(); tx.update(wsRef, {pendingOperationId: operationId, updatedAt: now});
    tx.create(revisionRef(admin, targetRevisionId), {contractVersion: CONTRACT_VERSION, workspaceId, revisionId: targetRevisionId, parentRevisionId: baseRevisionId, restoredFromRevisionId: kind === 'restore' ? sourceRevisionId : null, owner, state: 'reserved', createdByOperationId: operationId, createdAt: now});
    tx.create(operationRef(admin, operationId), {contractVersion: CONTRACT_VERSION, operationId, kind, state: 'queued', owner, ownerHash: ownerHash(owner), workspaceId, baseRevisionId, sourceRevisionId, targetRevisionId, inputHash, recipeJson: JSON.stringify(recipe), humanAcceptance: 'unreviewed', createdAt: now, updatedAt: now});
    tx.create(idemRef, {owner, kind, inputHash, operationId, workspaceId, targetRevisionId, createdAt: now});
  });
  if (!attached) await enqueue(admin, operationId);
  return {contractVersion: CONTRACT_VERSION, operationId, workspaceId, baseRevisionId, targetRevisionId, state: 'queued', attached};
}
async function reserveDerived({admin, user, args, kind}) {
  approved(args); const owner = ownerEmail(user), key = requestKey(args), workspaceId = text(args.workspaceId, 80), revisionId = text(args.revisionId, 80); if (!workspaceId || !revisionId) throw fail('blender.workspace.revision_required', 'workspaceId and revisionId are required.');
  const revision = await loadOwnedRevision(admin, owner, workspaceId, revisionId); if (revision.state !== 'completed') throw fail('blender.workspace.revision_not_ready', 'Revision is not completed.', 409);
  const request = kind === 'render' ? {presets: Array.isArray(args.presets) ? args.presets.map((v) => text(v, 80)).filter(Boolean).slice(0, 32) : []} : {};
  const inputHash = hashJson({owner, kind, workspaceId, revisionId, request}), operationId = id('bop', owner + ':' + kind + ':' + key, 30), idemRef = admin.firestore().collection(IDEMPOTENCY).doc(id('idem', owner + ':' + kind + ':' + key, 40)); let attached = false;
  await admin.firestore().runTransaction(async (tx) => { const existing = await tx.get(idemRef); if (existing.exists) { const data = existing.data() || {}; if (data.inputHash !== inputHash) throw fail('blender.workspace.idempotency_conflict', 'idempotencyKey is bound to different derived output.', 409); attached = true; return; } const now = new Date().toISOString(); tx.create(operationRef(admin, operationId), {contractVersion: CONTRACT_VERSION, operationId, kind, state: 'queued', owner, ownerHash: ownerHash(owner), workspaceId, revisionId, inputHash, request, humanAcceptance: 'unreviewed', createdAt: now, updatedAt: now}); tx.create(idemRef, {owner, kind, inputHash, operationId, workspaceId, revisionId, createdAt: now}); });
  if (!attached) await enqueue(admin, operationId); const response = {contractVersion: CONTRACT_VERSION, operationId, workspaceId, revisionId, state: 'queued', attached}; if (kind === 'render') response.deprecation = {...RENDER_DEPRECATION}; return response;
}
async function signedArtifacts(record) { const artifacts = Array.isArray(record.result && record.result.artifacts) ? record.result.artifacts : []; return Promise.all(artifacts.map(async (artifact) => { try { const [url] = await storage().bucket(artifact.bucket).file(artifact.objectName).getSignedUrl({version: 'v4', action: 'read', expires: Date.now() + 24 * 60 * 60 * 1000}); return {...artifact, signedUrl: url, signedUrlExpiresInSeconds: 86400}; } catch (error) { return {...artifact, signedUrl: null, signedUrlError: text(error.message, 300)}; } })); }
async function inspect({admin, user, args}) { const owner = ownerEmail(user), workspaceId = text(args.workspaceId, 80), revisionId = text(args.revisionId, 80); const ws = await loadOwnedWorkspace(admin, owner, workspaceId), revision = await loadOwnedRevision(admin, owner, workspaceId, revisionId); return {contractVersion: CONTRACT_VERSION, workspaceId, revisionId, currentRevisionId: ws.data.currentRevisionId, historical: ws.data.currentRevisionId !== revisionId, state: revision.state, scene: revision.inspection || null, validation: revision.validation || null, source: revision.scene || null}; }
async function history({admin, user, args}) { const owner = ownerEmail(user), workspaceId = text(args.workspaceId, 80), ws = await loadOwnedWorkspace(admin, owner, workspaceId); const ids = Array.isArray(ws.data.revisionIds) ? ws.data.revisionIds.slice(-MAX_REVISIONS) : []; const snapshots = await Promise.all(ids.map((revisionId) => revisionRef(admin, revisionId).get())); return {contractVersion: CONTRACT_VERSION, workspaceId, workspaceName: ws.data.workspaceName, currentRevisionId: ws.data.currentRevisionId, pendingOperationId: ws.data.pendingOperationId || null, revisions: snapshots.filter((s) => s.exists).map((s) => { const r = s.data() || {}; return {revisionId: r.revisionId, parentRevisionId: r.parentRevisionId || null, restoredFromRevisionId: r.restoredFromRevisionId || null, state: r.state, scene: r.scene || null, createdAt: r.createdAt, completedAt: r.completedAt}; })}; }
async function status({admin, user, args}) { const owner = ownerEmail(user), operationId = text(args.operationId, 80); const snap = await operationRef(admin, operationId).get(); if (!snap.exists) throw fail('blender.workspace.operation_not_found', 'Operation not found.', 404); const record = snap.data() || {}; if (record.owner !== owner) throw fail('blender.workspace.operation_forbidden', 'Operation is not owned by this caller.', 403); const artifacts = record.state === 'completed' ? await signedArtifacts(record) : []; return {contractVersion: CONTRACT_VERSION, operationId, kind: record.kind, state: record.state, workspaceId: record.workspaceId, baseRevisionId: record.baseRevisionId || null, revisionId: record.targetRevisionId || record.revisionId || null, humanAcceptance: record.humanAcceptance || 'unreviewed', deprecation: record.kind === 'render' ? {...RENDER_DEPRECATION} : null, blockingError: record.blockingError || null, result: record.result ? {...record.result, artifacts} : null, createdAt: record.createdAt, updatedAt: record.updatedAt}; }
async function runOperation({operation, admin, user, args = {}}) { if (operation === 'blender.workspace.create') return createWorkspace({admin, user, args}); if (operation === 'blender.workspace.inspect') return inspect({admin, user, args}); if (operation === 'blender.workspace.history') return history({admin, user, args}); if (operation === 'blender.workspace.mutate' || operation === 'blender.workspace.restore') return reserveMutation({admin, user, args, kind: operation.split('.').pop()}); if (operation === 'blender.workspace.render' || operation === 'blender.workspace.export') return reserveDerived({admin, user, args, kind: operation.split('.').pop()}); if (operation === 'blender.workspace.status') return status({admin, user, args}); throw fail('blender.workspace.operation_unsupported', 'Unsupported Blender workspace operation: ' + operation); }
function retiredFoundryError(operation) { return fail('CAPABILITY_RETIRED', 'Foundry authoring is retired. Use the persistent Home Center Blender workspace operations.', 410, {operation, retired: true, dispatched: false, replacement: ['blender.workspace.create', 'blender.workspace.mutate', 'blender.workspace.inspect', 'blender.workspace.export']}); }
module.exports = {CONTRACT_VERSION, RECIPE_VERSION, REGISTRY_VERSION, RENDER_DEPRECATION, operationEntries, runOperation, retiredFoundryError, hashJson};
