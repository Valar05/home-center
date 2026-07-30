import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';

process.env.HOME_CENTER_ARTIFACT_BUCKET_TEST_FAKE = '1';
process.env.HOME_CENTER_GENERATED_BUCKET = 'home-center-generated';
const require = createRequire(import.meta.url);
const artifactBucket = require('../functions/artifact_bucket.js');

const doc = fs.readFileSync(new URL('../docs/ARTIFACT_BUCKET_ARCHITECTURE.md', import.meta.url), 'utf8');
assert(doc.includes('gs://home-center-generated'), 'architecture doc must name canonical generated bucket');
assert(doc.includes('Drive is a publishing destination, not a render cache'), 'architecture doc must keep Drive out of render-cache authority');
for (const key of ['owner', 'ownerEmail', 'project', 'stage', 'engine', 'createdBy', 'jobId', 'commit', 'timestamp', 'executionAuthorized', 'authorizationState', 'humanAcceptance']) assert(doc.includes('"' + key + '"'), 'metadata contract must include ' + key);
for (const rule of ['temp/`: delete after 7 days', 'delete after 30 days', '`logs/`: delete after 14 days']) assert(doc.includes(rule), 'lifecycle doc missing ' + rule);

const deployFunctions = fs.readFileSync(new URL('../tools/deploy_functions_termux.sh', import.meta.url), 'utf8');
const deployBlender = fs.readFileSync(new URL('../tools/deploy_blender_workspace_worker.sh', import.meta.url), 'utf8');
const setupBucket = fs.readFileSync(new URL('../tools/setup_generated_artifact_bucket.sh', import.meta.url), 'utf8');
assert(deployFunctions.includes('--runtime=nodejs22'), 'functions deploy must use Node 22');
assert(deployFunctions.includes('HOME_CENTER_GENERATED_BUCKET'), 'functions deploy must configure generated bucket');
assert(deployFunctions.includes('home-center-generated'), 'functions deploy must default to generated bucket');
assert(deployBlender.includes('HOME_CENTER_ARTIFACT_BUCKET'), 'Blender workspace deploy must configure the canonical artifact bucket');
assert(setupBucket.includes('--uniform-bucket-level-access'), 'bucket setup must enforce uniform access');
assert(setupBucket.includes('--public-access-prevention'), 'bucket setup must prevent public access');
assert(setupBucket.includes('--versioning'), 'bucket setup must enable versioning');
assert(setupBucket.includes('"age": 7') && setupBucket.includes('"age": 30') && setupBucket.includes('"age": 14'), 'bucket setup must install lifecycle rules');

assert.equal(artifactBucket.artifactPrefix({artifactType: 'glb', name: 'specimen.glb'}), 'glb');
assert.equal(artifactBucket.artifactPrefix({artifactType: 'contact_sheet', name: 'review.png'}), 'renders/contact-sheets');
assert.equal(artifactBucket.artifactPrefix({artifactType: 'rendered_frames', name: 'front.png'}), 'renders');
assert.notEqual(artifactBucket.artifactPrefix({artifactType: 'rendered_frames', name: 'front.png'}), 'renders/blender');

const audioSource = fs.readFileSync(new URL('../functions/audio_render_service.js', import.meta.url), 'utf8');
assert(audioSource.includes('uploadGeneratedArtifact'), 'audio.render must upload to generated bucket');
assert(audioSource.includes('publishGeneratedArtifactToDrive'), 'audio.render must publish to Drive only through publish helper');
assert(audioSource.includes("primary: 'gcs'"), 'audio.render receipt must report GCS primary store');
assert(audioSource.includes('driveIsRenderCache: false'), 'audio.render receipt must explicitly reject Drive as render cache');
assert(audioSource.includes("startsWith('gs://')"), 'audio.render_artifacts must accept gs:// refs');

const bytes = Buffer.from('artifact bucket contract fixture', 'utf8');
const uploaded = await artifactBucket.uploadGeneratedArtifact({bytes, name: 'fixture.txt', mimeType: 'text/plain', owner: 'drew', project: 'home-center', stage: 'temp', engine: 'contract-test', createdBy: 'contract-test', jobId: 'job-test', commit: 'abc123', requestId: 'req-test', artifactType: 'log'});
assert.equal(uploaded.durableRef.startsWith('gs://home-center-generated/logs/'), true);
assert.equal(uploaded.sha256, createHash('sha256').update(bytes).digest('hex'));
assert.equal(uploaded.readbackSha256, uploaded.sha256);
assert.equal(uploaded.metadata.owner, 'drew');
assert.equal(uploaded.metadata.approved, 'false');
assert.equal(uploaded.metadata.humanAcceptance, 'unreviewed');
const inspected = await artifactBucket.inspectGeneratedArtifact(uploaded.durableRef);
assert.equal(inspected.sha256, uploaded.sha256);
assert.equal(inspected.metadata.sha256, uploaded.sha256);
console.log('Home Center artifact bucket contract: OK');
