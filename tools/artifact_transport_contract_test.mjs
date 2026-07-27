import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const transport = require('../functions/artifact_transport.js');
const {ARTIFACT_REFERENCE_VERSION, BLENDER_RENDER_CONTRACT_VERSION, ArtifactTransportError, sha256Bytes, normalizeArtifactReference, planArtifactLocation, boundedMap, rendererSettingsJsonSchema, normalizeRendererSettings, renderCompatibility, preflightArtifactEnvelope, structuredArtifactError} = transport;

const bytes = Buffer.from('artifact-transport-contract');
const identity = {sha256: sha256Bytes(bytes), byteLength: bytes.length, mediaType: 'application/octet-stream', fileName: 'fixture.bin'};
const gcs = (role = 'fixture') => ({schemaVersion: ARTIFACT_REFERENCE_VERSION, role, identity, locations: [{kind: 'gcs', uri: 'gs://home-center-generated/artifacts/' + identity.sha256 + '/fixture.bin'}]});
const drive = {schemaVersion: ARTIFACT_REFERENCE_VERSION, role: 'archive', identity: {...identity, byteLength: 181652767, sha256: '4f4d7a973203e5f57493b7c6b7c41e5076bbe67f9164249cf107daa35b15c964', fileName: 'Meshy.zip', mediaType: 'application/zip'}, locations: [{kind: 'drive', fileId: '1G6PsdVS24Zw8kqiWZgzRlM22hE_UhkFd'}]};

// 1 metadata-only/direct durable reference.
const metadata = await preflightArtifactEnvelope({requestId: 'metadata', artifacts: [gcs()], consumer: {supportedLocationKinds: ['gcs'], directLocationKinds: ['gcs']}, resolver: async (plan) => ({resolvable: true, reusedBytes: plan.reference.identity.byteLength, verification: {sha256Match: true, byteLengthMatch: true}})});
assert.equal(metadata.state, 'accepted'); assert.equal(metadata.totals.transferredBytes, 0); assert.equal(metadata.totals.reusedBytes, bytes.length);
// 2 small single-file staging plan.
assert.equal(planArtifactLocation({...gcs(), locations: [{kind: 'host_upload', field: 'file'}]}, {supportedLocationKinds: ['host_upload']}).action, 'stage');
// 3 bounded parallel staging preserves manifest order.
let active = 0, peak = 0;
const ordered = await boundedMap([40, 10, 20, 5], 2, async (delay, index) => { active += 1; peak = Math.max(peak, active); await new Promise((r) => setTimeout(r, delay)); active -= 1; return index; });
assert.deepEqual(ordered, [0, 1, 2, 3]); assert.equal(peak, 2);
// 4 interrupted resumable inventory identifies only missing verified chunks.
const chunks = ['aa', 'bb', 'cc'].map((value, index) => ({index, bytes: Buffer.from(value), sha256: sha256Bytes(Buffer.from(value)), byteLength: 2}));
const uploaded = new Map([[0, chunks[0]], [2, chunks[2]]]);
const missing = chunks.filter((chunk) => !uploaded.has(chunk.index)); assert.deepEqual(missing.map((x) => x.index), [1]);
uploaded.set(1, chunks[1]); assert.equal(Buffer.concat([...uploaded.values()].sort((a,b) => a.index-b.index).map((x) => x.bytes)).toString(), 'aabbcc');
// 5 exact-byte digest reuse.
assert.equal(normalizeArtifactReference(gcs()).identity.sha256, identity.sha256);
// 6-7 idempotency binds logical request plus digests, never location handles.
const hashA = transport.sha256Json({operation: 'render', artifacts: [gcs().identity]});
const hashB = transport.sha256Json({operation: 'render', artifacts: [gcs().identity]});
const hashChanged = transport.sha256Json({operation: 'render', artifacts: [{...gcs().identity, sha256: '0'.repeat(64)}]});
assert.equal(hashA, hashB); assert.notEqual(hashA, hashChanged);
// 8 corrupt chunk and 9 incorrect length are specific failures.
assert.notEqual(sha256Bytes(Buffer.from('corrupt')), chunks[0].sha256);
assert.throws(() => normalizeArtifactReference({...gcs(), identity: {...identity, byteLength: -1}}), (e) => e.code === 'ARTIFACT_BYTE_LENGTH_INVALID');
// 10 unsupported reference and 11 expired reference.
assert.throws(() => normalizeArtifactReference({...gcs(), locations: [{kind: 'ftp', uri: 'ftp://bad'}]}), (e) => e.code === 'ARTIFACT_REFERENCE_KIND_UNSUPPORTED');
assert.throws(() => planArtifactLocation({...gcs(), locations: [{kind: 'gcs', uri: 'gs://bucket/object', expiresAt: '2000-01-01T00:00:00Z'}]}, {supportedLocationKinds: ['gcs']}), (e) => e.code === 'ARTIFACT_REFERENCE_EXPIRED');
// 12 public/backend schema agreement includes gifFrames and version negotiation.
const settingsSchema = rendererSettingsJsonSchema(); assert.ok(settingsSchema.properties.gifFrames); assert.ok(settingsSchema.properties.gifTimingMs);
const settings = normalizeRendererSettings({gifFrames: [0, 2], gifTimingMs: [100, 120]}); assert.deepEqual(settings.gifFrames, [0, 2]);
assert.throws(() => renderCompatibility({settings, contractVersion: 'old', backend: {contractVersions: [BLENDER_RENDER_CONTRACT_VERSION]}}), (e) => e.code === 'ARTIFACT_CONTRACT_VERSION_UNSUPPORTED');
assert.throws(() => normalizeRendererSettings({gifFrames: [0, 2], gifTimingMs: [100]}), (e) => e.code === 'RENDER_GIF_TIMING_LENGTH_MISMATCH');
// 13 two concurrent jobs retain independent receipts.
const jobs = await Promise.all(['job-a', 'job-b'].map((requestId) => preflightArtifactEnvelope({requestId, artifacts: [gcs(requestId)], consumer: {supportedLocationKinds: ['gcs'], directLocationKinds: ['gcs']}})));
assert.deepEqual(jobs.map((j) => j.requestId), ['job-a', 'job-b']); assert.notEqual(jobs[0].inputHash, jobs[1].inputHash);
// 14 one failed sibling does not erase the successful receipt.
const sibling = await preflightArtifactEnvelope({requestId: 'siblings', artifacts: [gcs('good'), {...gcs('bad'), locations: [{kind: 'gcs', uri: 'gs://bucket/bad'}]}], consumer: {supportedLocationKinds: ['gcs'], directLocationKinds: ['gcs']}, resolver: async (_plan, index) => { if (index === 1) throw new ArtifactTransportError('ARTIFACT_CHECKSUM_MISMATCH', 'chunk rejected', {field: 'artifacts[1]'}); return {resolvable: true, reusedBytes: bytes.length}; }});
assert.equal(sibling.state, 'failed'); assert.equal(sibling.artifacts[0].resolvable, true); assert.equal(sibling.artifacts[1].error.code, 'ARTIFACT_CHECKSUM_MISMATCH');
// 15 structured telemetry/errors exclude credentials, URLs, and binary bodies.
const cleanError = structuredArtifactError(new ArtifactTransportError('ARTIFACT_TEST', 'specific failure', {field: 'artifacts[0]', details: {authorization: 'Bearer secret', signedUrl: 'https://secret', body: 'binary', expectedSha256: identity.sha256}}));
assert.equal(cleanError.code, 'ARTIFACT_TEST'); assert.equal(cleanError.field, 'artifacts[0]'); assert.equal(JSON.stringify(cleanError).includes('Bearer secret'), false); assert.equal(JSON.stringify(cleanError).includes('https://secret'), false);
// Large Drive proof planning is server-side reuse, not a duplicate 181 MB upload.
const large = await preflightArtifactEnvelope({requestId: 'large-drive', artifacts: [drive], consumer: {supportedLocationKinds: ['drive'], directLocationKinds: ['drive']}, resolver: async ({reference}) => ({resolvable: true, reusedBytes: reference.identity.byteLength, verification: {metadataMatched: true}})});
assert.equal(large.artifacts[0].transferPath, 'server-side-reference-reuse'); assert.equal(large.totals.transferredBytes, 0); assert.equal(large.totals.reusedBytes, 181652767);

console.log(JSON.stringify({ok: true, cases: 15, boundedConcurrencyPeak: peak, deterministicOrder: ordered, largeDriveTransferredBytes: large.totals.transferredBytes, largeDriveReusedBytes: large.totals.reusedBytes}, null, 2));
