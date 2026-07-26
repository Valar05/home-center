import assert from 'node:assert/strict';
import fs from 'node:fs';

const api = fs.readFileSync(new URL('../functions/audio_library_api.js', import.meta.url), 'utf8');
const audio = fs.readFileSync(new URL('../functions/audio_render_service.js', import.meta.url), 'utf8');
const index = fs.readFileSync(new URL('../functions/index.js', import.meta.url), 'utf8');

assert(api.includes("GENERATED_BUCKET = process.env.HOME_CENTER_GENERATED_BUCKET || 'home-center-generated'"), 'browser must use canonical generated bucket');
assert(api.includes("action === 'browse'"), 'browser API must browse the current indexed folder');
assert(api.includes("action === 'list'"), 'legacy browser API listing must remain available during rollout');
assert(api.includes("action === 'play'"), 'browser API must issue playback grants');
assert(api.includes("CATALOG_ROOT = 'indexes/audio/v1/catalog'"), 'folder discovery must use the durable audio catalog index');
assert(api.includes("delimiter: '/'"), 'folder discovery must be bounded to immediate children');
assert(api.includes("source: 'catalog-index-v1'"), 'folder responses must declare their indexed source');
assert(api.includes("collection('audioLibraryStreamTokens')"), 'playback grants must be short-lived server records');
assert(api.includes("Math.abs(Date.now() - timestampMs) > MAX_CLOCK_SKEW_MS"), 'signed requests must expire');
assert(api.includes("createVerify('RSA-SHA256')"), 'site-to-Home-Center requests must be signed');
assert(api.includes("if (!accessFor(metadata, email))"), 'playback must re-check object authorization');
assert(api.includes("res.set('Accept-Ranges', 'bytes')"), 'cloud player must support seek/range playback');
assert(api.includes("email === LEGACY_STEWARD"), 'unowned legacy objects must be quarantined to the bucket steward');
assert(api.includes("sharedWithFor(metadata).includes(email)"), 'explicit shares must be visible to their recipient');
assert(!api.includes('Access-Control-Allow-Origin'), 'audio library does not rely on a public CORS bucket');

assert(audio.includes("primaryStore: 'gcs'"), 'new renders must use GCS as primary store');
assert(audio.includes('ownerEmail: safeText(artifactContext.ownerEmail'), 'new objects must persist owner metadata');
assert(audio.includes('sharedWith: JSON.stringify'), 'new objects must persist explicit share metadata');
assert(audio.includes("storageRef = 'gs://' + GENERATED_ARTIFACT_BUCKET"), 'receipts must preserve exact gs URI');
assert(audio.includes('if (args.publishToDrive === false) return false'), 'publishToDrive false must remain a hard boundary');
assert(index.includes('exports.audioLibraryApi = onRequest'), 'Firebase exports the audio library endpoint');

console.log('Audio library contract: OK');
