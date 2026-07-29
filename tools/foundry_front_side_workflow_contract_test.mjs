#!/usr/bin/env node
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {executeFoundryScript} from '../functions/foundry_script_runtime.mjs';
import {runFoundryKernel} from '../functions/foundry_kernel.mjs';
import {subdivisionCageDigest} from '../functions/foundry_model_sheet.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'functions/package.json'));
const {FOUNDRY_MODEL_SHEET_VERSION_V2, resolveModelSheet} = require('../functions/foundry_capability.js');
const fixtureDir = path.join(root, 'docs/evidence/foundry-front-side-proof-v1');
const localSheet = JSON.parse(fs.readFileSync(path.join(fixtureDir, 'model-sheet.local.json'), 'utf8'));
const proofSource = JSON.parse(fs.readFileSync(path.join(fixtureDir, 'proof-source.json'), 'utf8'));
const script = fs.readFileSync(path.join(fixtureDir, 'crude-turret-proof.foundry.js'), 'utf8');
const workerSource = fs.readFileSync(path.join(root, 'functions/foundry_worker_process.mjs'), 'utf8');
const bridgeSource = fs.readFileSync(path.join(root, 'functions/home_center_mcp.js'), 'utf8');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'contracts/home-center-public-tool-manifest.v1.json'), 'utf8'));

class FakeStorage {
  constructor() { this.objects = new Map(); }
  bucket(name) { const objects = this.objects; return {file(objectName) { return {async download() { const bytes = objects.get(name + '/' + objectName); if (!bytes) throw new Error('missing object ' + name + '/' + objectName); return [Buffer.from(bytes)]; }}; }}; }
}
const storage = new FakeStorage(), owner = 'owner@example.com', modelSheet = structuredClone(localSheet);
for (const viewName of modelSheet.viewOrder) {
  const local = modelSheet.views[viewName].imageLocal, bytes = fs.readFileSync(path.join(fixtureDir, local.path)), artifactId = 'foundry-front-side-proof-' + viewName + '-v1', objectName = 'canonical/' + artifactId + '.png';
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), local.sha256);
  storage.objects.set('home-center-generated/' + objectName, bytes);
  storage.objects.set('home-center-generated/indexes/artifacts/v1/by-id/' + owner + '/' + artifactId + '.json', Buffer.from(JSON.stringify({source: {name: local.path, mimeType: 'image/png'}, destination: {bucket: 'home-center-generated', objectName, byteCount: bytes.length, sha256: local.sha256}})));
  modelSheet.views[viewName].image = {kind: 'home_center_artifact', artifactId, sha256: local.sha256, byteLength: bytes.length};
  delete modelSheet.views[viewName].imageLocal;
}
const resolved = await resolveModelSheet({storage, user: {email: owner}, modelSheet});
assert.equal(resolved.contractVersion, FOUNDRY_MODEL_SHEET_VERSION_V2);
assert.deepEqual(resolved.viewOrder, ['front', 'side']);
assert.deepEqual(Object.keys(resolved.views), ['front', 'side']);
assert.equal(resolved.authority.scope, 'workflow_fixture');
assert.equal(resolved.authority.productionUse, false);
await assert.rejects(() => resolveModelSheet({storage, user: {email: owner}, modelSheet: {...modelSheet, viewOrder: ['front'], views: {front: modelSheet.views.front}}}), (error) => error.code === 'foundry.model_sheet.view_order_invalid');
await assert.rejects(() => resolveModelSheet({storage, user: {email: owner}, modelSheet: {...modelSheet, authority: {...modelSheet.authority, productionUse: true}}}), (error) => error.code === 'foundry.model_sheet.provenance_required');

assert.doesNotMatch(script, /D78461|Sherman|controlPoints|createCylinder|boolean|fixedViews|perspective/i);
assert.match(script, /fitSubdivisionCage/);
const plan = await executeFoundryScript({version: 'foundry-js.v1', text: script, seed: 1});
const result = await runFoundryKernel({plan, domain: 'hard_surface', reviewPreset: 'registered-model-sheet-only', modelSheet: resolved});
const cage = result.evidence.cageEvidence['shared-proof-cage'];
assert(cage && cage.fit, 'shared fitted cage evidence is missing');
assert.equal(subdivisionCageDigest(cage), proofSource.cage.expectedFittedCageSha256);
assert.equal(cage.fit.fittedCageSha256, proofSource.cage.expectedFittedCageSha256);
assert.deepEqual(cage.fit.views, ['front', 'side']);
assert.equal(result.report.componentCount, 1);
assert.equal(result.report.hierarchy[0].name, 'Crude_Turret_Volume');
assert.equal(result.report.validation.manifoldClosedComponents, 1);
assert.equal(result.report.validation.nonManifoldComponents, 0);
assert.equal(result.report.validation.degenerateTriangles, 0);
assert.equal(result.report.triangleCount, 1024);
assert.equal(result.report.hierarchy.some((entry) => /cage/i.test(entry.name)), false);
assert.deepEqual(result.evidence.modelSheetReview.views, ['front', 'side']);
for (const viewName of ['front', 'side']) {
  assert(cage.fit.initial.views[viewName].p95BoundaryErrorRingFraction > 0.02, viewName + ' initial box should fail the fit threshold');
  assert(cage.fit.final.views[viewName].p95BoundaryErrorRingFraction < 0.01, viewName + ' fitted cage should materially clear the fit threshold');
}
assert.match(workerSource, /registered-model-sheet-only/);
assert.match(workerSource, /model-sheet-cage\.json/);
assert.match(workerSource, /foundry\.review\.model_sheet_fit_failed/);
assert.doesNotMatch(bridgeSource, /server\.registerTool\(['"]foundry/i);
assert.equal(manifest.toolCount, 57);
assert.equal(manifest.canonicalToolsSha256, '5c7cee977116422e47ae817920d41b63227d841348fd6c0769f6c9f1568b6498');

console.log(JSON.stringify({ok: true, modelSheet: resolved.id, viewOrder: resolved.viewOrder, solver: cage.fit.solver, evaluations: cage.fit.evaluations, initial: Object.fromEntries(resolved.viewOrder.map((name) => [name, cage.fit.initial.views[name].p95BoundaryErrorRingFraction])), final: Object.fromEntries(resolved.viewOrder.map((name) => [name, cage.fit.final.views[name].p95BoundaryErrorRingFraction])), sharedCageSha256: cage.fit.fittedCageSha256, component: result.report.hierarchy[0].name, triangles: result.report.triangleCount, topLevelToolCount: manifest.toolCount}, null, 2));
