import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {executeFoundryScript} from './foundry_script_runtime.mjs';
import {runFoundryKernel, FOUNDRY_KERNEL_VERSION, FOUNDRY_RUN_VERSION} from './foundry_kernel.mjs';
import {renderFixedViews} from './foundry_review_renderer.mjs';

const requestPath = process.argv[2];
const outputDir = process.argv[3];
if (!requestPath || !outputDir) throw new Error('usage: foundry_worker_process.mjs REQUEST_JSON OUTPUT_DIR');
const request = JSON.parse(await fs.readFile(requestPath, 'utf8'));
const sourceBytes = request.sourcePath ? await fs.readFile(request.sourcePath) : null;
const scriptText = request.scriptPath ? await fs.readFile(request.scriptPath, 'utf8') : String(request.scriptText || '');
const plan = await executeFoundryScript({version: request.scriptVersion, text: scriptText, parameters: request.parameters || {}, seed: request.scriptSeed || 1});
const result = await runFoundryKernel({sourceBytes, plan, domain: request.domain, reviewPreset: request.reviewPreset});
await fs.mkdir(outputDir, {recursive: true});
const artifacts = [];
async function write(name, bytes, mediaType, kind) {
  if (!bytes) return;
  const value = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes);
  await fs.writeFile(path.join(outputDir, name), value);
  artifacts.push({name, mediaType, kind, byteLength: value.length, sha256: createHash('sha256').update(value).digest('hex')});
}
await write('foundry-result.glb', result.glb, 'model/gltf-binary', 'glb');
const review = await renderFixedViews({glbPath: path.join(outputDir, 'foundry-result.glb'), views: result.reviewViews});
for (const view of result.reviewViews) await write('fixed-' + view + '.png', review.views[view], 'image/png', 'fixedView');
await write('contact-sheet.png', review.contactSheet, 'image/png', 'contactSheet');
await write('skeletal-overlay.png', review.skeletalOverlay, 'image/png', 'skeletalOverlay');
await write('validation-report.json', Buffer.from(JSON.stringify(result.report, null, 2) + '\n'), 'application/json', 'report');
await write('preservation-evidence.json', Buffer.from(JSON.stringify(result.evidence, null, 2) + '\n'), 'application/json', 'evidence');
await write('change-evidence.json', Buffer.from(JSON.stringify({scriptVersion: plan.scriptVersion, operationCount: plan.operationCount, changes: result.evidence.changes, touched: result.evidence.touched, notes: result.evidence.notes}, null, 2) + '\n'), 'application/json', 'changeEvidence');
const manifest = {schemaVersion: 'home-center.foundry-result.v2', runVersion: FOUNDRY_RUN_VERSION, kernelVersion: FOUNDRY_KERNEL_VERSION, domain: request.domain, reviewPreset: request.reviewPreset, reviewViews: result.reviewViews, artifacts, report: result.report, rendering: {engine: 'three.js-headless-chromium', network: 'loopback_only', diagnostics: review.diagnostics}, humanAcceptance: 'unreviewed'};
await fs.writeFile(path.join(outputDir, 'foundry-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
process.stdout.write(JSON.stringify({ok: true, runVersion: FOUNDRY_RUN_VERSION, kernelVersion: FOUNDRY_KERNEL_VERSION, operationCount: plan.operationCount, artifactCount: artifacts.length + 1}) + '\n');
