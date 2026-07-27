#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import fs from 'node:fs';

process.env.HOME_CENTER_ARTIFACT_BUCKET_TEST_FAKE = '1';
process.env.HOME_CENTER_GENERATED_BUCKET = 'home-center-generated';

const require = createRequire(import.meta.url);
const homeCenterSource = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
const commandCenterSource = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
const audioRenderSource = fs.readFileSync(new URL('../functions/audio_render_service.js', import.meta.url), 'utf8');
const vanguardScript = fs.readFileSync(new URL('../tools/vanguard_walk_render_blender.py', import.meta.url), 'utf8');

assert(homeCenterSource.includes('verifiedRenderGifMcpContent'), 'Home Center must verify private GCS GIF readback before MCP media attachment');
assert(homeCenterSource.includes('uploadVerifiedArtifact'), 'Home Center Blender GIF delivery must reuse the audio.render verified upload helper');
assert(audioRenderSource.includes("type: 'resource_link'"), 'The reused audio.render helper must produce resource_link content');
assert(!homeCenterSource.includes("type: 'image', data: buffer.toString('"), 'Home Center render GIF delivery must not use MCP ImageContent for animated GIFs');
assert(!homeCenterSource.includes("type: 'resource',\n    resource:"), 'Home Center render GIF delivery must not use embedded resource bytes for animated GIFs');
assert(homeCenterSource.includes("mimeType: 'image/gif'"), 'Home Center must preserve GIF MIME type');
assert(homeCenterSource.includes('HOME_CENTER_RENDER_INLINE_GIF_MAX_BYTES'), 'Inline GIF delivery must have a configurable byte ceiling');
assert(homeCenterSource.includes('parseRenderGsRef'), 'Inline GIF delivery must accept private gs:// refs only');
assert(!homeCenterSource.includes('https://storage.googleapis.com'), 'Inline GIF delivery must not fall back to public Storage URLs');
assert(!homeCenterSource.includes('getSignedUrl'), 'Inline GIF delivery must not leak signed URLs');
assert(commandCenterSource.includes('renderRequiredBundleKindsForOptions'), 'Command Center must use one helper for required render bundles');
assert(commandCenterSource.includes('const effectiveOptions'), 'Queued Command Center worker must derive completion from effective render options');
assert(commandCenterSource.includes("status: completed ? 'completed' : 'failed'"), 'Completed queued renders must persist terminal state');
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
  loopingGifRef: 'gs://home-center-generated/renders/gifs/cache123/walk-loop.gif',
  artifactHashes: {'walk-loop.gif': {byteCount: gifBytes.length, sha256: gifSha}},
  validation: {ok: true, missingBundleKinds: [], presentBundleKinds: ['looping_gif']},
};
const fakeStorage = {
  bucket(name) {
    assert.equal(name, 'home-center-generated');
    return {file(path) {
      assert.equal(path, 'renders/gifs/cache123/walk-loop.gif');
      return {async download() { return [gifBytes]; }};
    }};
  },
};
const driveStore = new Map();
const fakeGoogle = () => ({drive() { return {files: {
  async create(params) {
    const chunks = [];
    for await (const chunk of params.media.body) chunks.push(Buffer.from(chunk));
    const bytes = Buffer.concat(chunks);
    const id = 'driveGif12345';
    driveStore.set(id, {bytes, metadata: {id, name: params.requestBody.name, mimeType: params.requestBody.mimeType, webViewLink: 'https://drive/' + id, parents: params.requestBody.parents || []}});
    return {data: {...driveStore.get(id).metadata, size: String(bytes.length)}};
  },
  async get(params) {
    const item = driveStore.get(params.fileId);
    if (!item) throw new Error('missing fake drive file ' + params.fileId);
    if (params.alt === 'media') return {data: item.bytes};
    return {data: {...item.metadata, size: String(item.bytes.length)}};
  },
}}; }});
const verified = await verifiedRenderGifMcpContent(result, {storage: fakeStorage, google: fakeGoogle(), auth: {}, parentFolderId: 'folder12345'});
assert.equal(verified.delivery.ok, true);
assert.equal(verified.delivery.byteCount, gifBytes.length);
assert.equal(verified.delivery.sha256, gifSha);
assert.equal(verified.delivery.mimeType, 'image/gif');
assert.equal(verified.contentBlock.type, 'resource_link');
assert.equal(verified.contentBlock.mimeType, 'image/gif');
assert.equal(verified.contentBlock.name, 'walk-loop.gif');
assert.equal(verified.contentBlock.uri, 'drive://driveGif12345');
assert.equal(verified.contentBlock.size, gifBytes.length);
assert.equal(verified.delivery.durableRef, 'drive://driveGif12345');
assert.equal(verified.delivery.readbackByteCount, gifBytes.length);
assert.equal(verified.delivery.readbackSha256, gifSha);

const operationResult = await attachRenderGifMcpContent({operation: 'render.blender_glb', toolName: 'command_center.render.blender_glb', result}, {storage: fakeStorage, google: fakeGoogle(), auth: {}, parentFolderId: 'folder12345'});
assert.ok(Array.isArray(operationResult._mcpContent.content));
assert.equal(operationResult._mcpContent.content.length, 2);
const textBlock = operationResult._mcpContent.content.find((item) => item.type === 'text');
const linkBlock = operationResult._mcpContent.content.find((item) => item.type === 'resource_link');
assert.ok(textBlock);
assert.ok(linkBlock);
assert.equal(operationResult._mcpContent.content[0].type, 'text');
assert.equal(linkBlock.mimeType, 'image/gif');
assert.equal(linkBlock.name, 'walk-loop.gif');
assert.ok(!operationResult._mcpContent.content.some((item) => item.type === 'image' || item.type === 'resource' || item.type === 'audio'), 'GIF delivery must not return unsupported media content blocks');
assert.ok(!textBlock.text.includes(gifBytes.toString('base64')), 'JSON receipt must not contain Base64 media');
assert.ok(!textBlock.text.includes('https://storage.googleapis.com'), 'JSON receipt must not contain a public Storage URL');
assert.ok(!textBlock.text.includes('X-Goog-Signature'), 'JSON receipt must not contain signed URL material');
const receipt = JSON.parse(textBlock.text);
assert.equal(receipt.result.inlineMediaDelivery.ok, true);
assert.equal(receipt.result.inlineMediaDelivery.contentBlockType, 'resource_link');
assert.equal(receipt.result.inlineMediaDelivery.sha256, gifSha);
assert.equal(receipt.result.inlineMediaDelivery.durableRef, 'drive://driveGif12345');

const failureResult = await attachRenderGifMcpContent({operation: 'render.blender_glb', toolName: 'command_center.render.blender_glb', result}, {storage: fakeStorage});
assert.deepEqual(failureResult._mcpContent.content.map((item) => item.type), ['text']);
const failureReceipt = JSON.parse(failureResult._mcpContent.content[0].text);
assert.equal(failureReceipt.result.ok, true);
assert.equal(failureReceipt.result.status, 'completed');
assert.equal(failureReceipt.result.inlineMediaDelivery.ok, false);
assert.equal(failureReceipt.result.inlineMediaDelivery.errorCode, 'render_gif_resource_link_auth_missing');

const mismatch = await verifiedRenderGifMcpContent(result, {storage: {bucket() { return {file() { return {async download() { return [Buffer.from('different')]; }}; }}; }}, google: fakeGoogle(), auth: {}});
assert.equal(mismatch.contentBlock, null);
assert.equal(mismatch.delivery.ok, false);
assert.equal(mismatch.delivery.errorCode, 'render_gif_resource_link_readback_mismatch');

await assert.rejects(() => verifiedRenderGifMcpContent({...result, loopingGifRef: 'gs://other-bucket/renders/gifs/cache123/walk-loop.gif'}, {storage: fakeStorage}), /outside the configured private render bucket/);
await assert.rejects(() => verifiedRenderGifMcpContent({...result, loopingGifRef: 'https://storage.googleapis.com/home-center-generated/x.gif'}, {storage: fakeStorage}), /private gs:\/\/ artifact ref/);

assert.deepEqual(renderRequiredBundleKindsForOptions({includeBlend: false, includeDiagnostics: false}).filter((kind) => kind === 'three_d_artifact' || kind === 'diagnostic_view_renders'), []);
assert.ok(renderRequiredBundleKindsForOptions({includeBlend: true, includeDiagnostics: true}).includes('three_d_artifact'));
assert.ok(renderRequiredBundleKindsForOptions({includeBlend: true, includeDiagnostics: true}).includes('diagnostic_view_renders'));
assert.deepEqual(renderBundleOptionsFrom({includeBlend: false, includeDiagnostics: false}, {includeBlend: true, includeDiagnostics: true}), {includeBlend: false, includeDiagnostics: false});

console.log('Home Center Blender inline GIF contract: OK');
