import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {EventEmitter} from 'node:events';
import {PassThrough} from 'node:stream';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'functions/package.json'));
const {Accessor, Document, NodeIO} = await import(new URL('../functions/node_modules/@gltf-transform/core/dist/index.js', import.meta.url));
const {PNG} = require('pngjs');
const {
  FOUNDRY_RUN_VERSION,
  FOUNDRY_SCRIPT_VERSION,
  foundryOperationEntries,
  queueFoundryRun,
  foundryStatus,
  promoteFoundryResult,
  executeFoundryJob,
  runChildProcess,
  runFoundryOperation,
} = require('../functions/foundry_capability.js');
const {driveOperationRegistry, createHomeCenterMcpServer} = require('../functions/home_center_mcp.js');
const {executeFoundryScript} = await import('../functions/foundry_script_runtime.mjs');
const {runFoundryKernel, inspectGlbBytes} = await import('../functions/foundry_kernel.mjs');
const {assertReviewImageNonBlank, buildContactSheet, REVIEW_WIDTH, REVIEW_HEIGHT} = await import('../functions/foundry_review_renderer.mjs');

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}
function digest(value) { return crypto.createHash('sha256').update(Buffer.isBuffer(value) ? value : Buffer.from(JSON.stringify(stable(value)))).digest('hex'); }

class Snapshot {
  constructor(ref, value) { this.ref = ref; this.value = value; this.exists = value !== undefined; }
  data() { return structuredClone(this.value); }
}
class Ref {
  constructor(store, key) { this.store = store; this.key = key; }
  async get() { return new Snapshot(this, this.store.get(this.key)); }
  async create(value) { if (this.store.has(this.key)) { const error = new Error('already exists'); error.code = 6; throw error; } this.store.set(this.key, structuredClone(value)); }
  async set(value, options = {}) { this.store.set(this.key, options.merge ? {...(this.store.get(this.key) || {}), ...structuredClone(value)} : structuredClone(value)); }
}
class Firestore {
  constructor() { this.store = new Map(); this.transactionTail = Promise.resolve(); }
  collection(name) { return {doc: (id) => new Ref(this.store, name + '/' + id)}; }
  async runTransaction(fn) {
    const run = this.transactionTail.then(() => fn({get: (ref) => ref.get(), create: (ref, value) => ref.create(value), set: (ref, value, options) => ref.set(value, options)}));
    this.transactionTail = run.catch(() => {});
    return run;
  }
}
function fakeAdmin() { const db = new Firestore(); return {firestore: () => db, db}; }
class FakeStorage {
  constructor() { this.objects = new Map(); this.uploadCalls = 0; }
  bucket(name) {
    const self = this;
    return {
      name,
      file(objectName) {
        return {
          async download(options = {}) {
            const bytes = self.objects.get(name + '/' + objectName);
            if (!bytes) throw new Error('missing object ' + name + '/' + objectName);
            if (options.destination) { await fsp.writeFile(options.destination, bytes); return; }
            return [Buffer.from(bytes)];
          },
          createReadStream() { const {Readable} = require('node:stream'); return Readable.from([self.objects.get(name + '/' + objectName) || Buffer.alloc(0)]); },
        };
      },
      async upload(localPath, options) {
        const key = name + '/' + options.destination;
        if (self.objects.has(key)) { const error = new Error('conditionNotMet'); error.code = 412; throw error; }
        self.objects.set(key, await fsp.readFile(localPath));
        self.uploadCalls += 1;
      },
    };
  }
}

async function characterFixture() {
  const doc = new Document();
  const buffer = doc.createBuffer('fixture-buffer');
  const scene = doc.createScene('Fixture Scene');
  const position = doc.createAccessor('body-position', buffer).setType(Accessor.Type.VEC3).setArray(new Float32Array([-0.5,0,0, 0.5,0,0, 0,1,0]));
  const normal = doc.createAccessor('body-normal', buffer).setType(Accessor.Type.VEC3).setArray(new Float32Array([0,0,1, 0,0,1, 0,0,1]));
  const joints = doc.createAccessor('body-joints', buffer).setType(Accessor.Type.VEC4).setArray(new Uint16Array([0,0,0,0, 0,0,0,0, 0,0,0,0]));
  const weights = doc.createAccessor('body-weights', buffer).setType(Accessor.Type.VEC4).setArray(new Float32Array([1,0,0,0, 1,0,0,0, 1,0,0,0]));
  const indices = doc.createAccessor('body-indices', buffer).setType(Accessor.Type.SCALAR).setArray(new Uint16Array([0,1,2]));
  const primitive = doc.createPrimitive().setAttribute('POSITION', position).setAttribute('NORMAL', normal).setAttribute('JOINTS_0', joints).setAttribute('WEIGHTS_0', weights).setIndices(indices);
  const body = doc.createNode('body').setMesh(doc.createMesh('body-mesh').addPrimitive(primitive));
  const rootBone = doc.createNode('root');
  const hand = doc.createNode('hand_r').setTranslation([0.4,0.8,0]);
  rootBone.addChild(hand);
  const ibm = doc.createAccessor('inverse-bind', buffer).setType(Accessor.Type.MAT4).setArray(new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1, 1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]));
  const skin = doc.createSkin('fixture-skin').addJoint(rootBone).addJoint(hand).setSkeleton(rootBone).setInverseBindMatrices(ibm);
  body.setSkin(skin);
  const weaponPrimitive = doc.createPrimitive().setAttribute('POSITION', doc.createAccessor('weapon-position', buffer).setType(Accessor.Type.VEC3).setArray(new Float32Array([0,0,0, 0.3,0,0, 0,0.08,0]))).setIndices(doc.createAccessor('weapon-indices', buffer).setType(Accessor.Type.SCALAR).setArray(new Uint16Array([0,1,2])));
  const weapon = doc.createNode('weapon').setMesh(doc.createMesh('weapon-mesh').addPrimitive(weaponPrimitive));
  scene.addChild(rootBone).addChild(body).addChild(weapon);
  const times = doc.createAccessor('idle-times', buffer).setType(Accessor.Type.SCALAR).setArray(new Float32Array([0,1,2]));
  const rotations = doc.createAccessor('idle-rotations', buffer).setType(Accessor.Type.VEC4).setArray(new Float32Array([0,0,0,1, 0,0.258819,0,0.965926, 0,0,0,1]));
  const sampler = doc.createAnimationSampler('idle-sampler').setInput(times).setOutput(rotations).setInterpolation('LINEAR');
  const channel = doc.createAnimationChannel('idle-channel').setSampler(sampler).setTargetNode(hand).setTargetPath('rotation');
  doc.createAnimation('idle').addSampler(sampler).addChannel(channel);
  return Buffer.from(await new NodeIO().writeBinary(doc));
}

function reviewPng(blank = false) {
  const png = new PNG({width: REVIEW_WIDTH, height: REVIEW_HEIGHT});
  for (let y = 0; y < REVIEW_HEIGHT; y++) for (let x = 0; x < REVIEW_WIDTH; x++) {
    const offset = (y * REVIEW_WIDTH + x) * 4;
    const model = !blank && x > 130 && x < 510 && y > 110 && y < 540;
    png.data[offset] = model ? 80 + (x % 120) : 23;
    png.data[offset + 1] = model ? 130 + (y % 90) : 26;
    png.data[offset + 2] = model ? 95 : 24;
    png.data[offset + 3] = 255;
  }
  return PNG.sync.write(png);
}

function fakeWorkerSpawn(glbBytes) {
  return (_command, args) => {
    const child = new EventEmitter();
    child.pid = 999999;
    child.stdout = new PassThrough();
    child.stderr = new PassThrough();
    child.kill = () => {};
    const outputDir = args.at(-1);
    setTimeout(async () => {
      try {
        await fsp.mkdir(outputDir, {recursive: true});
        const png = reviewPng(false);
        const artifacts = {
          'foundry-result.glb': glbBytes,
          'fixed-front.png': png,
          'fixed-back.png': png,
          'fixed-left.png': png,
          'fixed-right.png': png,
          'fixed-top.png': png,
          'fixed-perspective.png': png,
          'contact-sheet.png': buildContactSheet({front:png,back:png,left:png,right:png,top:png,perspective:png}, ['front','back','left','right','top','perspective']),
          'validation-report.json': Buffer.from(JSON.stringify({kernelVersion:'test',runVersion:FOUNDRY_RUN_VERSION,domain:'hard_surface',triangleCount:1,componentCount:1,validation:{}})),
          'preservation-evidence.json': Buffer.from('{}'),
          'change-evidence.json': Buffer.from('{}'),
          'foundry-manifest.json': Buffer.from(JSON.stringify({schemaVersion:'home-center.foundry-result.v2',humanAcceptance:'unreviewed'})),
        };
        await Promise.all(Object.entries(artifacts).map(([name, bytes]) => fsp.writeFile(path.join(outputDir, name), bytes)));
        child.stdout.end('{"ok":true}\n'); child.stderr.end(); child.emit('close', 0, null);
      } catch (error) { child.stderr.end(String(error)); child.stdout.end(); child.emit('close', 1, null); }
    }, 10);
    return child;
  };
}

process.env.HOME_CENTER_MCP_EXTENDED_TOOLS = 'true';
const server = createHomeCenterMcpServer({google: {}, admin: {firestore() { return {}; }}, googleClientId: () => 'configured', googleClientSecret: () => 'configured'});
const listed = await server.server._requestHandlers.get('tools/list')({method:'tools/list',params:{}},{});
const currentTools = stable([...(listed.tools || [])].sort((a,b) => a.name.localeCompare(b.name)));
const committedTools = JSON.parse(fs.readFileSync(path.join(root, 'contracts/home-center-top-level-mcp.v1.json'), 'utf8'));
assert.deepEqual(currentTools, committedTools, 'committed top-level MCP contract drifted');
assert.equal(currentTools.some((tool) => /foundry/i.test(tool.name)), false, 'Foundry leaked into top-level MCP');
assert.equal(currentTools.some((tool) => tool.name === 'render_blender_glb'), false, 'retired renderer remains top-level');
delete process.env.HOME_CENTER_MCP_EXTENDED_TOOLS;

const dynamic = Object.keys(foundryOperationEntries()).sort();
assert.deepEqual(dynamic, ['foundry.asset.inspect','foundry.asset.promote','foundry.asset.run','foundry.asset.status']);
for (const operation of dynamic) assert.ok(driveOperationRegistry().operations[operation], operation + ' is not dynamically discoverable');
assert.equal(driveOperationRegistry().invocationTool, 'drive_operation');

const hardScript = "foundry.material.create('steel',{baseColor:[0.22,0.28,0.25,1],metallic:0.7,roughness:0.38}); foundry.scene.createProfileExtrusion('body',{profile:[[-1,-0.5],[1,-0.5],[1,0.5],[-1,0.5]],depth:0.6,material:'steel'}); foundry.scene.createCylinder('wheel',{radius:0.32,depth:0.22,segments:20,translation:[-0.65,-0.42,0],material:'steel'}); foundry.scene.array('wheel',{count:3,offset:[0.65,0,0],namePrefix:'wheel'}); foundry.scene.mirror('wheel','z',{name:'wheel-mirror'}); foundry.mesh.recalculateNormals('body'); foundry.review.fixedViews(['front','back','left','right','top','perspective']);";
const hardPlanA = await executeFoundryScript({version:FOUNDRY_SCRIPT_VERSION,text:hardScript,parameters:{},seed:77});
const hardPlanB = await executeFoundryScript({version:FOUNDRY_SCRIPT_VERSION,text:hardScript,parameters:{},seed:77});
assert.deepEqual(hardPlanA, hardPlanB);
assert.equal(hardPlanA.operationCount, 7);
await assert.rejects(() => executeFoundryScript({version:'foundry-js.v0',text:hardScript}), (error) => error.code === 'foundry.script.unsupported_version');
await assert.rejects(() => executeFoundryScript({version:FOUNDRY_SCRIPT_VERSION,text:'fetch("https://example.com")'}), (error) => error.code === 'foundry.script.failed');
await assert.rejects(() => runFoundryKernel({plan:{operations:[{namespace:'mesh',operation:'arbitrary',args:[]}],notes:[]}}), (error) => error.code === 'foundry.script.unsupported_operation');
const hardA = await runFoundryKernel({plan:hardPlanA,domain:'hard_surface',reviewPreset:'fixed-six-view'});
const hardB = await runFoundryKernel({plan:hardPlanB,domain:'hard_surface',reviewPreset:'fixed-six-view'});
assert.equal(digest(hardA.glb), digest(hardB.glb), 'procedural GLB must be deterministic');
assert.ok(hardA.report.triangleCount > 0 && hardA.report.componentCount >= 5);
assert.ok(hardA.report.validation.manifoldClosedComponents >= 1);

const fixtureBytes = await characterFixture();
const before = await inspectGlbBytes(fixtureBytes);
const setupPlan = await executeFoundryScript({version:FOUNDRY_SCRIPT_VERSION,text:"foundry.rig.addBone('hand_r','weapon_socket_r',{translation:[0.18,0,0]}); foundry.rig.attachRigid('weapon','weapon_socket_r',{translation:[0.04,0,0]}); foundry.validation.assert('node_exists','weapon_socket_r');",seed:1});
const setup = await runFoundryKernel({sourceBytes:fixtureBytes,plan:setupPlan,domain:'character_setup'});
const setupInspect = await inspectGlbBytes(setup.glb);
assert.equal(setup.evidence.preservation.beforeHashes.meshes, setup.evidence.preservation.afterHashes.meshes, 'character mesh arrays changed');
assert.equal(setup.evidence.preservation.beforeHashes.animations, setup.evidence.preservation.afterHashes.animations, 'unrelated clips changed');
assert.ok(setupInspect.report.skins[0].joints.includes('weapon_socket_r'));
assert.ok(setupInspect.report.hierarchy.some((node) => node.name === 'weapon' && node.parent === 'weapon_socket_r' && node.skin === null));
assert.equal(before.preservation.hashes.meshes, setup.evidence.preservation.beforeHashes.meshes);

const animationPlan = await executeFoundryScript({version:FOUNDRY_SCRIPT_VERSION,text:"foundry.animation.trim('idle',{start:0.25,end:1.75,duration:1.5,outputClip:'idle_foundry'}); foundry.animation.retime('idle_foundry',1.2); foundry.animation.setKey('idle_foundry','hand_r','rotation',0.6,[0,0.382683,0,0.92388]); foundry.animation.loop('idle_foundry');",seed:2});
const animation = await runFoundryKernel({sourceBytes:fixtureBytes,plan:animationPlan,domain:'animation'});
const animationInspect = await inspectGlbBytes(animation.glb);
assert.equal(animation.evidence.preservation.beforeHashes.meshes, animation.evidence.preservation.afterHashes.meshes, 'animation mutated geometry');
assert.equal(animation.evidence.preservation.beforeHashes.skins, animation.evidence.preservation.afterHashes.skins, 'animation mutated skin');
assert.equal(animationInspect.report.animations[0].name, 'idle_foundry');
assert.ok(Math.abs(animationInspect.report.animations[0].duration - 1.2) < 0.0001);

assert.throws(() => assertReviewImageNonBlank(reviewPng(true), 'blank.png'), (error) => error.code === 'foundry.review.blank_canvas');
assertReviewImageNonBlank(reviewPng(false), 'visible.png');

const admin = fakeAdmin();
const storage = new FakeStorage();
const owner = 'owner@example.com';
const sourceSha = digest(fixtureBytes), sourceObject = 'canonical/fixture-character.glb', artifactId = 'fixture-character';
storage.objects.set('home-center-generated/' + sourceObject, fixtureBytes);
storage.objects.set('home-center-generated/indexes/artifacts/v1/by-id/' + owner + '/' + artifactId + '.json', Buffer.from(JSON.stringify({source:{name:'fixture-character.glb',mimeType:'model/gltf-binary'},destination:{bucket:'home-center-generated',objectName:sourceObject,byteCount:fixtureBytes.length,sha256:sourceSha}})));
const enqueued = [], enqueue = async (payload) => enqueued.push(structuredClone(payload));
const user = {email:owner};
const baseArgs = {contractVersion:FOUNDRY_RUN_VERSION,domain:'hard_surface',script:{kind:'inline',version:FOUNDRY_SCRIPT_VERSION,filename:'specimen.js',text:hardScript},parameters:{},reviewPreset:'fixed-six-view',idempotencyKey:'mechanical-1',namespace:'specimen-a'};
const accepted = await queueFoundryRun({admin,storage,user,args:baseArgs,enqueue});
assert.equal(accepted.attached,false); assert.equal(enqueued.length,1);
const attached = await queueFoundryRun({admin,storage,user,args:baseArgs,enqueue});
assert.equal(attached.attached,true); assert.equal(attached.jobId,accepted.jobId); assert.equal(enqueued.length,1);
await assert.rejects(() => queueFoundryRun({admin,storage,user,args:{...baseArgs,parameters:{changed:true}},enqueue}), (error) => error.code === 'foundry.idempotency_conflict');
await assert.rejects(() => queueFoundryRun({admin,storage,user,args:{...baseArgs,idempotencyKey:'legacy',recipe:{version:'v1'}},enqueue}), (error) => error.code === 'foundry.contract.retired');

const inspectAccepted = await runFoundryOperation({operation:'foundry.asset.inspect',admin,storage,user,args:{source:{kind:'home_center_artifact',artifactId,sha256:sourceSha,byteLength:fixtureBytes.length},idempotencyKey:'inspect-1',namespace:'inspect-a'},enqueue});
assert.equal(inspectAccepted.accepted,true); assert.equal(enqueued.length,2);
const acceptedB = await queueFoundryRun({admin,storage,user,args:{...baseArgs,idempotencyKey:'mechanical-2',namespace:'specimen-b'},enqueue});
assert.notEqual(acceptedB.jobId,accepted.jobId); assert.notEqual(acceptedB.inputHash,accepted.inputHash);

const workerSpawn = fakeWorkerSpawn(hardA.glb);
const completedA = await executeFoundryJob(admin,enqueued[0],{storage,spawnImpl:workerSpawn});
const uploadsAfterA = storage.uploadCalls;
const replayA = await executeFoundryJob(admin,enqueued[0],{storage,spawnImpl:workerSpawn});
assert.equal(replayA.result.resultHash,completedA.result.resultHash); assert.equal(storage.uploadCalls,uploadsAfterA,'exact replay uploaded bytes');
const completedB = await executeFoundryJob(admin,enqueued[2],{storage,spawnImpl:workerSpawn});
assert.notEqual(completedA.result.cacheKey,completedB.result.cacheKey);
assert.ok(completedA.result.artifacts.every((item) => item.storageRef.includes('/specimen-a/')));
assert.ok(completedB.result.artifacts.every((item) => item.storageRef.includes('/specimen-b/')));
assert.ok(completedA.result.artifacts.every((item) => !item.storageRef.toLowerCase().includes('/latest')));
assert.equal(completedA.result.review.transportState,'review_ready');
assert.equal(completedA.result.review.humanAcceptance,'unreviewed');
assert.match(completedA.result.review.viewerUrl,/^https:\/\/valar05\.github\.io\/model-viewer-lab\/model-viewer\.html\?/);
assert.ok(Buffer.byteLength(JSON.stringify(completedA)) < 64*1024);

const concurrent = await queueFoundryRun({admin,storage,user,args:{...baseArgs,idempotencyKey:'concurrent',namespace:'specimen-concurrent'},enqueue});
const payload = enqueued.at(-1), beforeConcurrent = storage.uploadCalls;
const concurrentResults = await Promise.all([executeFoundryJob(admin,payload,{storage,spawnImpl:workerSpawn}),executeFoundryJob(admin,payload,{storage,spawnImpl:workerSpawn})]);
assert.ok(concurrentResults.some((item) => item.state === 'completed'));
assert.equal(storage.uploadCalls - beforeConcurrent, 14, 'concurrent attachment duplicated output or logs');
assert.equal((await foundryStatus({admin,user,args:{jobId:concurrent.jobId}})).state,'completed');

const timeoutAccepted = await queueFoundryRun({admin,storage,user,args:{...baseArgs,idempotencyKey:'timeout',namespace:'specimen-timeout'},enqueue});
await assert.rejects(() => executeFoundryJob(admin,enqueued.at(-1),{storage,timeoutMs:50,spawnImpl:(_command,_args) => {const child=new EventEmitter();child.pid=999998;child.stdout=new PassThrough();child.stderr=new PassThrough();child.kill=()=>{child.stdout.end();child.stderr.end();child.emit('close',null,'SIGKILL');};return child;}}), (error) => error.code === 'foundry.worker.timeout');
assert.equal((await foundryStatus({admin,user,args:{jobId:timeoutAccepted.jobId}})).execution.timedOut,true);
await assert.rejects(() => foundryStatus({admin,user:{email:'other@example.com'},args:{jobId:accepted.jobId}}), (error) => error.code === 'foundry.job_forbidden');

admin.db.store.set('artifactReviewRecords/review-accepted',{ownerEmail:owner,verdict:'accepted',result:{promotionAllowed:true,producer:{receiptId:accepted.jobId}}});
const promoted = await promoteFoundryResult({admin,user,args:{jobId:accepted.jobId,resultHash:completedA.result.resultHash,reviewRequestId:'review-accepted',requestId:'promote-1'}});
assert.equal(promoted.humanAcceptance,'accepted');
const promotedReplay = await promoteFoundryResult({admin,user,args:{jobId:accepted.jobId,resultHash:completedA.result.resultHash,reviewRequestId:'review-accepted',requestId:'promote-1'}});
assert.equal(promotedReplay.promotionId,promoted.promotionId);
await assert.rejects(() => promoteFoundryResult({admin,user,args:{jobId:accepted.jobId,resultHash:completedA.result.resultHash,reviewRequestId:'missing'} }), (error) => error.code === 'foundry.promotion.review_not_found');

const logRoot = await fsp.mkdtemp(path.join(os.tmpdir(),'foundry-log-'));
try {
  const result = await runChildProcess({requestPath:path.join(logRoot,'request.json'),outputDir:logRoot,stdoutPath:path.join(logRoot,'stdout.log'),stderrPath:path.join(logRoot,'stderr.log'),timeoutMs:2000,spawnImpl:(_command,_args,options) => require('node:child_process').spawn(process.execPath,['-e',"process.stdout.write('x'.repeat(100000));process.stderr.write('y'.repeat(100000))"],options)});
  assert.equal(result.code,0); assert.equal(result.stdout.truncated,true); assert.equal(result.stderr.truncated,true);
} finally { await fsp.rm(logRoot,{recursive:true,force:true}); }

for (const file of ['functions/foundry_capability.js','functions/foundry_kernel.mjs','functions/foundry_worker_process.mjs','functions/foundry_review_renderer.mjs','functions/foundry_script_runtime.mjs']) {
  const source = fs.readFileSync(path.join(root,file),'utf8');
  assert.doesNotMatch(source,/\bbpy\b|spawn\s*\([^\n]*blender|exec(?:File)?\s*\([^\n]*blender/i,file + ' invokes retired renderer');
  assert.doesNotMatch(source,/[\/'"]latest[\/'"]|globalLatest|latestArtifact/i,file + ' uses mutable latest');
}

console.log(JSON.stringify({ok:true,topLevelMcpHash:digest(currentTools),dynamicOperations:dynamic,mechanicalSha256:digest(hardA.glb),characterSha256:digest(setup.glb),animationSha256:digest(animation.glb),isolatedJobs:[completedA.jobId,completedB.jobId],duplicateUploadsOnReplay:0},null,2));
