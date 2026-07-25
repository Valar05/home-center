#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import fs from 'node:fs';

const require = createRequire(import.meta.url);
const homeCenterSource = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
const commandCenterSource = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
const vanguardScript = fs.readFileSync(new URL('../tools/vanguard_walk_render_blender.py', import.meta.url), 'utf8');

assert(homeCenterSource.includes('verifiedRenderGifMcpContent'), 'Home Center must verify private GCS GIF readback before MCP media attachment');
assert(homeCenterSource.includes("type: 'image'"), 'Home Center must return a structured MCP image content block');
assert(homeCenterSource.includes("mimeType: 'image/gif'"), 'Home Center must preserve GIF MIME type');
assert(homeCenterSource.includes('HOME_CENTER_RENDER_INLINE_GIF_MAX_BYTES'), 'Inline GIF delivery must have a configurable byte ceiling');
assert(homeCenterSource.includes('parseRenderGsRef'), 'Inline GIF delivery must accept private gs:// refs only');
assert(!homeCenterSource.includes('https://storage.googleapis.com'), 'Inline GIF delivery must not fall back to public Storage URLs');
assert(!homeCenterSource.includes('getSignedUrl'), 'Inline GIF delivery must not leak signed URLs');
assert(commandCenterSource.includes('renderRequiredBundleKindsForOptions'), 'Command Center must use one helper for required render bundles');
assert(commandCenterSource.includes('const effectiveRenderOptions'), 'Command Center wrapper must derive completion from effective render options');
assert(commandCenterSource.includes("failureKind: status === 'completed' ? ''"), 'Completed lightweight renders must clear failureKind');
assert(vanguardScript.includes("normalized_name = requested + '_rig'"), 'Vanguard resolver must allow only the known glTF _rig suffix');
assert(vanguardScript.includes("forbidden = [name for name in available if name in {'Rest', 'Idle'}]"), 'Vanguard resolver must explicitly forbid Rest/Idle fallback');
assert(vanguardScript.includes("'activeSemanticAction': semantic_action_name(action.name, expected_action)"), 'Vanguard native evidence must record semantic action separate from importer provenance');
assert(vanguardScript.includes("FRAME_DURATIONS_MS = [110, 90, 100, 110, 110, 90, 100, 110]"), 'Vanguard script must preserve requested timing');
assert(vanguardScript.includes("'weaponRPresent': inventory['weaponRPresent']"), 'Vanguard script must verify Weapon.R presence');
assert(vanguardScript.includes("'embeddedSwordCount': inventory['swordObjectCount']"), 'Vanguard script must record exact sword count');

const {verifiedRenderGifMcpContent, attachRenderGifMcpContent} = require('../functions/home_center_mcp.js');
const {renderRequiredBundleKindsForOptions, renderBundleOptionsFrom} = require('../functions/command_center_mcp.js');

const gifBytes = Buffer.from('GIF89a contract animated bytes');
const gifSha = createHash('sha256').update(gifBytes).digest('hex');
const result = {
  ok: true,
  status: 'completed',
  loopingGifRef: 'gs://home-center-dclar-command-center-renders/command-center-renders/cache123/walk-loop.gif',
  artifactHashes: {'walk-loop.gif': {byteCount: gifBytes.length, sha256: gifSha}},
  validation: {ok: true, missingBundleKinds: [], presentBundleKinds: ['looping_gif']},
};
const fakeStorage = {
  bucket(name) {
    assert.equal(name, 'home-center-dclar-command-center-renders');
    return {file(path) {
      assert.equal(path, 'command-center-renders/cache123/walk-loop.gif');
      return {async download() { return [gifBytes]; }};
    }};
  },
};
const verified = await verifiedRenderGifMcpContent(result, {storage: fakeStorage});
assert.equal(verified.delivery.ok, true);
assert.equal(verified.delivery.byteCount, gifBytes.length);
assert.equal(verified.delivery.sha256, gifSha);
assert.equal(verified.delivery.mimeType, 'image/gif');
assert.equal(verified.contentBlock.type, 'image');
assert.equal(verified.contentBlock.mimeType, 'image/gif');
assert.equal(Buffer.from(verified.contentBlock.data, 'base64').toString('utf8'), gifBytes.toString('utf8'));

const operationResult = await attachRenderGifMcpContent({operation: 'render.blender_glb', toolName: 'command_center.render.blender_glb', result}, {storage: fakeStorage});
assert.ok(Array.isArray(operationResult._mcpContent.content));
assert.equal(operationResult._mcpContent.content.length, 2);
const textBlock = operationResult._mcpContent.content.find((item) => item.type === 'text');
const imageBlock = operationResult._mcpContent.content.find((item) => item.type === 'image');
assert.ok(textBlock);
assert.ok(imageBlock);
assert.equal(imageBlock.mimeType, 'image/gif');
assert.ok(!textBlock.text.includes(imageBlock.data), 'JSON receipt must not contain inline media Base64');
assert.ok(!textBlock.text.includes('https://storage.googleapis.com'), 'JSON receipt must not contain a public Storage URL');
assert.ok(!textBlock.text.includes('X-Goog-Signature'), 'JSON receipt must not contain signed URL material');
const receipt = JSON.parse(textBlock.text);
assert.equal(receipt.result.inlineMediaDelivery.ok, true);
assert.equal(receipt.result.inlineMediaDelivery.contentBlockType, 'image');
assert.equal(receipt.result.inlineMediaDelivery.sha256, gifSha);

const mismatch = await verifiedRenderGifMcpContent(result, {storage: {bucket() { return {file() { return {async download() { return [Buffer.from('different')]; }}; }}; }}});
assert.equal(mismatch.contentBlock, null);
assert.equal(mismatch.delivery.ok, false);
assert.equal(mismatch.delivery.errorCode, 'render_inline_gif_readback_mismatch');

const tooLarge = await verifiedRenderGifMcpContent({...result, artifactHashes: {'walk-loop.gif': {byteCount: 3 * 1024 * 1024, sha256: gifSha}}}, {storage: fakeStorage});
assert.equal(tooLarge.contentBlock, null);
assert.equal(tooLarge.delivery.errorCode, 'render_inline_gif_too_large');
await assert.rejects(() => verifiedRenderGifMcpContent({...result, loopingGifRef: 'gs://other-bucket/command-center-renders/cache123/walk-loop.gif'}, {storage: fakeStorage}), /outside the configured private render bucket/);
await assert.rejects(() => verifiedRenderGifMcpContent({...result, loopingGifRef: 'https://storage.googleapis.com/home-center-dclar-command-center-renders/x.gif'}, {storage: fakeStorage}), /private gs:\/\/ artifact ref/);

assert.deepEqual(renderRequiredBundleKindsForOptions({includeBlend: false, includeDiagnostics: false}).filter((kind) => kind === 'three_d_artifact' || kind === 'diagnostic_view_renders'), []);
assert.ok(renderRequiredBundleKindsForOptions({includeBlend: true, includeDiagnostics: true}).includes('three_d_artifact'));
assert.ok(renderRequiredBundleKindsForOptions({includeBlend: true, includeDiagnostics: true}).includes('diagnostic_view_renders'));
assert.deepEqual(renderBundleOptionsFrom({includeBlend: false, includeDiagnostics: false}, {includeBlend: true, includeDiagnostics: true}), {includeBlend: false, includeDiagnostics: false});

console.log('Home Center Blender inline GIF contract: OK');
