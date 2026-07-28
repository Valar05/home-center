import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {runFoundryKernel, FOUNDRY_KERNEL_VERSION} from './foundry_kernel.mjs';

const requestPath = process.argv[2];
const outputDir = process.argv[3];
if (!requestPath || !outputDir) throw new Error('usage: foundry_worker_process.mjs REQUEST_JSON OUTPUT_DIR');
const request = JSON.parse(await fs.readFile(requestPath, 'utf8'));
const sourceBytes = request.sourcePath ? await fs.readFile(request.sourcePath) : null;
const result = await runFoundryKernel({...request, sourceBytes});
await fs.mkdir(outputDir, {recursive: true});
const artifacts = [];
async function write(name, bytes, mediaType, kind) {
  if (!bytes) return;
  await fs.writeFile(path.join(outputDir, name), bytes);
  artifacts.push({name, mediaType, kind, byteLength: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex')});
}
await write('foundry-result.glb', result.glb, 'model/gltf-binary', 'glb');
await write('contact-sheet.png', result.contactSheet, 'image/png', 'contactSheet');
await write('skeletal-overlay.png', result.skeletalOverlay, 'image/png', 'skeletalOverlay');
const reportBytes = Buffer.from(JSON.stringify(result.report, null, 2) + '\n');
await write('validation-report.json', reportBytes, 'application/json', 'report');
const evidenceBytes = Buffer.from(JSON.stringify(result.evidence || {}, null, 2) + '\n');
await write('preservation-evidence.json', evidenceBytes, 'application/json', 'evidence');
const manifest = {schemaVersion: 'home-center.foundry-result.v1', kernelVersion: FOUNDRY_KERNEL_VERSION, domain: request.recipe.domain, artifacts, report: result.report};
await fs.writeFile(path.join(outputDir, 'foundry-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
process.stdout.write(JSON.stringify({ok: true, kernelVersion: FOUNDRY_KERNEL_VERSION, domain: request.recipe.domain, artifactCount: artifacts.length}) + '\n');
