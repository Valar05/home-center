import assert from 'node:assert/strict';
import Module from 'node:module';
import {createRequire} from 'node:module';

const sourceSha = 'c10707777c404e9dda6af4d9cd450b321d12688402ac6894d54859cd30a06b35';
const scriptSha = 'ae64b5aec3a7fbf37aaba249074fc9f1ff48a7ef0d10e83907cdd7c75fd4bcea';
const sourceObject = 'artifacts/sha256/' + sourceSha + '/diagnostic-regnet-sprint-stop.glb';
const scriptObject = 'artifacts/sha256/' + scriptSha + '/candidate-001.foundry.js';
const gcsMeta = new Map([
  ['home-center-generated/' + sourceObject, {size: '682056', generation: '101', metadata: {sha256: sourceSha}}],
  ['home-center-generated/' + scriptObject, {size: '38307', generation: '102', metadata: {sha256: scriptSha}}],
]);
const original = Module._load;
Module._load = function(request, parent, isMain) {
  if (request === '@google-cloud/storage') return {Storage: class {bucket(name) {return {file(object) {return {async getMetadata() {const value = gcsMeta.get(name + '/' + object); if (!value) throw new Error('not found'); return [value];}};}};}}};
  return original.call(this, request, parent, isMain);
};
class Doc {constructor(map, id) {this.map = map; this.id = id;} async get() {const value = this.map.get(this.id); return {exists: value !== undefined, data: () => value};} async create(value) {if (this.map.has(this.id)) throw new Error('exists'); this.map.set(this.id, structuredClone(value));}}
class Firestore {constructor() {this.cols = new Map();} collection(name) {if (!this.cols.has(name)) this.cols.set(name, new Map()); const map = this.cols.get(name); return {doc: (id) => new Doc(map, id)};}}
const firestore = new Firestore();
const admin = {firestore: () => firestore};
const user = {email: 'dclarke1005@gmail.com'};
const google = {drive: () => ({files: {get: async ({fileId}) => {assert.equal(fileId, '1G6PsdVS24Zw8kqiWZgzRlM22hE_UhkFd'); return {data: {id: fileId, name: 'Meshy.zip', mimeType: 'application/zip', size: '181652767', md5Checksum: '1569b7cce0ffdd7d547c4eb6b1aa7384'}};}}})};
const require = createRequire(import.meta.url);
const {artifactTransportPreflightOperation, artifactTransportStatusOperation} = require('../functions/home_center_mcp.js');
const ref = (role, identity, uri) => ({schemaVersion: 'home-center.artifact-reference.v1', role, identity, locations: [{kind: 'gcs', uri}]});
const glb = ref('source_glb', {sha256: sourceSha, byteLength: 682056, mediaType: 'model/gltf-binary', fileName: 'diagnostic-regnet-sprint-stop.glb'}, 'gs://home-center-generated/' + sourceObject);
const script = ref('foundry_script', {sha256: scriptSha, byteLength: 38307, mediaType: 'application/javascript', fileName: 'candidate-001.foundry.js'}, 'gs://home-center-generated/' + scriptObject);
const args = {requestId: 'regnet-candidate-001-foundry-transport-proof', targetOperation: 'foundry.asset.run', artifacts: [glb, script], consumer: {supportedLocationKinds: ['gcs'], directLocationKinds: ['gcs']}, concurrency: 2};
const first = await artifactTransportPreflightOperation({google, admin, auth: {}, user, args});
assert.equal(first.state, 'accepted');
assert.equal(first.attached, false);
assert.equal(first.totals.transferredBytes, 0);
assert.equal(first.totals.reusedBytes, 720363);
assert.deepEqual(first.artifacts.map((item) => item.role), ['source_glb', 'foundry_script']);
assert.equal(first.artifacts.every((item) => item.verification.sha256Match), true);
const replay = await artifactTransportPreflightOperation({google, admin, auth: {}, user, args});
assert.equal(replay.attached, true);
await assert.rejects(() => artifactTransportPreflightOperation({google, admin, auth: {}, user, args: {...args, artifacts: [{...glb, identity: {...glb.identity, sha256: '0'.repeat(64)}}, script]}}), /different artifact identities/);
const status = await artifactTransportStatusOperation({admin, user, args: {requestId: args.requestId}});
assert.equal(status.inputHash, first.inputHash);
const drive = {schemaVersion: 'home-center.artifact-reference.v1', role: 'archive', identity: {sha256: '4f4d7a973203e5f57493b7c6b7c41e5076bbe67f9164249cf107daa35b15c964', byteLength: 181652767, mediaType: 'application/zip', fileName: 'Meshy.zip'}, locations: [{kind: 'drive', fileId: '1G6PsdVS24Zw8kqiWZgzRlM22hE_UhkFd'}]};
const large = await artifactTransportPreflightOperation({google, admin, auth: {}, user, args: {requestId: 'meshy-large-reference-proof', artifacts: [drive], consumer: {supportedLocationKinds: ['drive'], directLocationKinds: ['drive']}}});
assert.equal(large.state, 'accepted');
assert.equal(large.totals.transferredBytes, 0);
assert.equal(large.totals.reusedBytes, 181652767);
assert.equal(large.artifacts[0].verification.providerMd5, '1569b7cce0ffdd7d547c4eb6b1aa7384');
console.log(JSON.stringify({ok: true, foundry: {artifacts: 2, reusedBytes: first.totals.reusedBytes, transferredBytes: 0, hashes: first.artifacts.map((item) => item.identity.sha256)}, largeDrive: {byteLength: 181652767, transferredBytes: 0, reusedBytes: 181652767}, idempotentAttach: true}, null, 2));
