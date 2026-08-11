const {createHash, randomUUID} = require('node:crypto');

const COLLECTIONS = Object.freeze({
  devices: 'phoneHandsDevices',
  commands: 'phoneHandsCommands',
  idempotency: 'phoneHandsIdempotency',
  diagnosticStreams: 'phoneHandsDiagnosticStreams',
});

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}
function safeObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
function hashText(value) { return createHash('sha256').update(String(value || '')).digest('hex'); }
function canonicalJson(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key)=>`${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  throw Object.assign(new Error('non-canonical JSON value'), {status:400});
}
function diagnosticReceiptHash(receipt) {
  const body = {...receipt};
  delete body.receiptHash;
  return hashText(canonicalJson(body));
}
function diagnosticChunkHash(result) {
  const payload = {...result};
  delete payload.chunkHash;
  delete payload.status;
  delete payload.byteCount;
  return hashText(canonicalJson(payload));
}
function shortHash(value, n = 32) { return hashText(value).slice(0, n); }
function ownerKeyFromActor(actor) { return `owner_${shortHash(safeText(actor, 320).toLowerCase() || 'anonymous', 32)}`; }
function cleanDeviceId(value) {
  const id = safeText(value, 120).toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '');
  if (!id) throw Object.assign(new Error('deviceId is required'), {status: 400});
  return id;
}
const DIAGNOSTIC_KINDS = new Set([
  'capability_snapshot','tree_inventory','repo_status','toolchain_probe','cache_probe','file_manifest',
]);
const DIAGNOSTIC_KEYS = new Set([
  'action','schema','diagnosticKind','deviceId','packageId','workerId',
  'queueDocId','queueRevision','commissionHash','laneId','sessionId',
  'streamId','chunkIndex','rootId','watermark','previousChunkHash','maxEntries','maxBytes','extensions',
]);
const DIAGNOSTIC_EXTENSIONS = new Set([
  '.gd','.tscn','.tres','.godot','.md','.txt','.json','.toml','.yaml','.yml',
  '.xml','.cfg','.ini','.py','.js','.mjs','.ts','.tsx','.java','.kt','.kts',
  '.c','.cc','.cpp','.h','.hpp','.glsl','.vert','.frag','.shader','.sh','.ps1',
]);
function requiredDiagnosticText(body, key, max = 320) {
  const value = safeText(body[key], max);
  if (!value) throw Object.assign(new Error(`phone_diagnostics requires ${key}`), {status: 400});
  return value;
}
function cleanPhoneDiagnostics(body) {
  const unknown = Object.keys(body).filter((key) => !DIAGNOSTIC_KEYS.has(key));
  if (unknown.length) throw Object.assign(new Error(`phone_diagnostics rejects unknown field: ${unknown[0]}`), {status: 400});
  if (body.schema !== 'phone.diagnostics.request.v1') {
    throw Object.assign(new Error('phone_diagnostics schema must be phone.diagnostics.request.v1'), {status: 400});
  }
  const diagnosticKind = safeText(body.diagnosticKind, 80);
  if (!DIAGNOSTIC_KINDS.has(diagnosticKind)) {
    throw Object.assign(new Error(`unsupported diagnosticKind: ${diagnosticKind}`), {status: 400});
  }
  const deviceId = cleanDeviceId(body.deviceId);
  const packageId = requiredDiagnosticText(body, 'packageId', 160);
  if (packageId !== 'com.termux') throw Object.assign(new Error('phone_diagnostics packageId must be com.termux'), {status: 400});
  const workerId = requiredDiagnosticText(body, 'workerId', 160);
  if (workerId !== `phone-relay:${deviceId}`) {
    throw Object.assign(new Error('phone_diagnostics workerId does not match device'), {status: 400});
  }
  const queueDocId = requiredDiagnosticText(body, 'queueDocId', 200);
  const queueRevision = requiredDiagnosticText(body, 'queueRevision', 320);
  const commissionHash = requiredDiagnosticText(body, 'commissionHash', 64).toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(commissionHash)) {
    throw Object.assign(new Error('phone_diagnostics commissionHash must be SHA-256'), {status: 400});
  }
  const laneId = requiredDiagnosticText(body, 'laneId', 160);
  const sessionId = requiredDiagnosticText(body, 'sessionId', 200);
  const streamId = requiredDiagnosticText(body, 'streamId', 200);
  const chunkIndex = Number(body.chunkIndex);
  if (!Number.isSafeInteger(chunkIndex) || chunkIndex < 0) {
    throw Object.assign(new Error('phone_diagnostics chunkIndex must be a nonnegative integer'), {status: 400});
  }
  const rootKinds = new Set(['tree_inventory','repo_status','file_manifest']);
  const rootId = safeText(body.rootId, 80);
  if (rootKinds.has(diagnosticKind) && rootId !== 'GODOT_PROJECTS') {
    throw Object.assign(new Error('phone_diagnostics rootId must be GODOT_PROJECTS'), {status: 400});
  }
  if (!rootKinds.has(diagnosticKind) && rootId) {
    throw Object.assign(new Error('phone_diagnostics rootId is not valid for this diagnosticKind'), {status: 400});
  }
  const watermark = safeText(body.watermark, 1000);
  if (watermark.startsWith('/') || watermark.includes('..') || watermark.includes('\\')) {
    throw Object.assign(new Error('phone_diagnostics watermark must be a safe relative path'), {status: 400});
  }
  const previousChunkHash = safeText(body.previousChunkHash, 64).toLowerCase();
  if (previousChunkHash && !/^[0-9a-f]{64}$/.test(previousChunkHash)) {
    throw Object.assign(new Error('phone_diagnostics previousChunkHash must be SHA-256'), {status: 400});
  }
  if (chunkIndex === 0 && (watermark || previousChunkHash)) {
    throw Object.assign(new Error('phone_diagnostics first chunk cannot claim prior state'), {status: 400});
  }
  if (chunkIndex > 0 && !previousChunkHash) {
    throw Object.assign(new Error('phone_diagnostics resume requires previousChunkHash'), {status: 400});
  }
  const maxEntries = body.maxEntries == null ? 200 : Number(body.maxEntries);
  const maxBytes = body.maxBytes == null ? 524288 : Number(body.maxBytes);
  if (!Number.isInteger(maxEntries) || maxEntries < 1 || maxEntries > 500 ||
      !Number.isInteger(maxBytes) || maxBytes < 1024 || maxBytes > 2097152) {
    throw Object.assign(new Error('phone_diagnostics budgets must be bounded integers'), {status: 400});
  }
  const extensions = body.extensions == null ? undefined : body.extensions;
  if (extensions !== undefined && (!Array.isArray(extensions) || extensions.length > 64 ||
      extensions.some((value) => typeof value !== 'string' || value.length > 16 ||
        !DIAGNOSTIC_EXTENSIONS.has(value.toLowerCase())))) {
    throw Object.assign(new Error('phone_diagnostics extensions must be a bounded string array'), {status: 400});
  }
  return {
    action:'phone_diagnostics', schema:body.schema, diagnosticKind, deviceId, packageId, workerId,
    queueDocId, queueRevision, commissionHash, laneId, sessionId, streamId, chunkIndex,
    ...(rootId ? {rootId} : {}),
    ...(watermark ? {watermark} : {}),
    ...(previousChunkHash ? {previousChunkHash} : {}),
    maxEntries, maxBytes,
    ...(extensions === undefined ? {} : {extensions:[...extensions]}),
  };
}
function cleanAction(value) {
  const body = safeObject(value);
  const action = safeText(body.action, 80);
  const allowed = new Set([
    'observe','tap','swipe','text','keyevent','home','back','recents','launch','force_stop','dungeon_run','local_ask','phone_shell',
    'file_stat','file_hash','file_list','file_mkdir','file_copy','file_move','armory_inventory','armory_ingest','armory_doctor','armory_slice',
    'window_status','window_probe','window_compose','window_focus','window_swap',
    'status_tts_doctor','status_say',
    'operator_overlay_status','operator_overlay_start','operator_overlay_update','phone_diagnostics',
  ]);
  if (!allowed.has(action)) throw Object.assign(new Error(`unsupported phone action: ${action}`), {status: 400});
  if (action === 'phone_diagnostics') return cleanPhoneDiagnostics({...body, action});
  return {...body, action};
}
function ownerKey(caller = {}) {
  const key = safeText(caller.ownerKey, 120);
  if (!key) throw Object.assign(new Error('ownerKey is required'), {status: 401});
  return key;
}

async function callerFromBearer(admin, bearer) {
  const token = safeText(bearer, 4096);
  if (!token) throw Object.assign(new Error('missing bearer token'), {status:401});
  const snap = await admin.firestore().collection('mcpOAuthAccessTokens').doc(hashText(token)).get();
  if (!snap.exists) throw Object.assign(new Error('invalid Home Center bearer token'), {status:401});
  const data = snap.data() || {};
  if (data.revokedAtMs || Number(data.expiresAtMs || 0) <= Date.now()) throw Object.assign(new Error('expired Home Center bearer token'), {status:401});
  const email = safeText(data.email,320).toLowerCase();
  if (!email) throw Object.assign(new Error('bearer token has no owner email'), {status:401});
  return {actor:email, ownerKey:ownerKeyFromActor(email)};
}

async function enqueuePhoneCommand(admin, caller, args = {}) {
  const idem = safeText(args.idempotencyKey, 180);
  if (!idem) throw Object.assign(new Error('idempotencyKey is required'), {status: 400});
  const deviceId = cleanDeviceId(args.deviceId || 'primary-phone');
  const action = cleanAction(args.action);
  if (action.action === 'phone_diagnostics' && action.deviceId !== deviceId) {
    throw Object.assign(new Error('phone_diagnostics deviceId does not match command device'), {status: 400});
  }
  const owner = ownerKey(caller);
  const idemId = hashText(`${owner}:${idem}`);
  const idemRef = admin.firestore().collection(COLLECTIONS.idempotency).doc(idemId);
  if (action.action === 'phone_diagnostics') {
    const requestHash = hashText(canonicalJson(action));
    const streamScopeHash = hashText(canonicalJson({
      deviceId:action.deviceId,packageId:action.packageId,workerId:action.workerId,
      queueDocId:action.queueDocId,queueRevision:action.queueRevision,
      commissionHash:action.commissionHash,laneId:action.laneId,sessionId:action.sessionId,
      streamId:action.streamId,diagnosticKind:action.diagnosticKind,rootId:action.rootId || '',
    }));
    const commandId = safeText(args.commandId, 160) || `phc_${randomUUID()}`;
    const now = Date.now();
    const record = {
      commandId, deviceId, ownerKey: owner, action,
      status: 'queued', createdAtMs: now, updatedAtMs: now,
      expiresAtMs: now + Math.max(30000, Math.min(Number(args.ttlMs || 300000), 3600000)),
      requestedBy: safeText(caller.actor, 320), result: null, error: '', leaseOwner: '', leaseExpiresAtMs: 0,
    };
    const commandRef = admin.firestore().collection(COLLECTIONS.commands).doc(commandId);
    const deviceRef = admin.firestore().collection(COLLECTIONS.devices).doc(deviceId);
    const streamRef = admin.firestore().collection(COLLECTIONS.diagnosticStreams)
      .doc(hashText(`${owner}:${deviceId}:${action.streamId}`));
    return admin.firestore().runTransaction(async (transaction) => {
      const prior = await transaction.get(idemRef);
      if (prior.exists) {
        if (prior.data().requestHash !== requestHash) {
          throw Object.assign(new Error('phone_diagnostics idempotency key is bound to a different request'), {status:409});
        }
        const priorRef = admin.firestore().collection(COLLECTIONS.commands).doc(prior.data().commandId);
        const priorCommand = await transaction.get(priorRef);
        return priorCommand.exists ? priorCommand.data() : {commandId:prior.data().commandId,status:'unknown'};
      }
      const device = await transaction.get(deviceRef);
      const deviceData = device.exists ? (device.data() || {}) : {};
      if (!device.exists || deviceData.ownerKey !== owner ||
          !Array.isArray(deviceData.capabilities) || !deviceData.capabilities.includes('phone_diagnostics_readonly')) {
        throw Object.assign(new Error('phone_diagnostics device capability is not registered for this owner'), {status:409});
      }
      const stream = await transaction.get(streamRef);
      if (!stream.exists) {
        if (action.chunkIndex !== 0 || action.watermark || action.previousChunkHash) {
          throw Object.assign(new Error('phone_diagnostics stream must start at chunk zero'), {status: 409});
        }
      } else {
        const state = stream.data() || {};
        if (state.inflightCommandId) throw Object.assign(new Error('phone_diagnostics stream already has an inflight chunk'), {status: 409});
        if (state.streamScopeHash !== streamScopeHash || Number(state.nextChunkIndex) !== action.chunkIndex ||
            safeText(state.lastWatermark,1000) !== safeText(action.watermark,1000) ||
            safeText(state.lastChunkHash,64) !== safeText(action.previousChunkHash,64)) {
          throw Object.assign(new Error('phone_diagnostics stream CAS mismatch'), {status: 409});
        }
      }
      transaction.create(commandRef, record);
      transaction.create(idemRef, {commandId, ownerKey:owner, requestHash, createdAtMs:now});
      transaction.set(streamRef, {
        ownerKey:owner, deviceId, streamId:action.streamId,
        streamScopeHash,
        nextChunkIndex:action.chunkIndex, lastWatermark:safeText(action.watermark,1000),
        lastChunkHash:safeText(action.previousChunkHash,64), lastReceiptHash:'',
        inflightCommandId:commandId, updatedAtMs:now,
      }, {merge:true});
      return record;
    });
  }
  const prior = await idemRef.get();
  if (prior.exists) {
    const commandId = prior.data().commandId;
    const snap = await admin.firestore().collection(COLLECTIONS.commands).doc(commandId).get();
    return snap.exists ? snap.data() : {commandId, status: 'unknown'};
  }
  const commandId = safeText(args.commandId, 160) || `phc_${randomUUID()}`;
  const now = Date.now();
  const record = {
    commandId, deviceId, ownerKey: owner, action,
    status: 'queued', createdAtMs: now, updatedAtMs: now,
    expiresAtMs: now + Math.max(30000, Math.min(Number(args.ttlMs || 300000), 3600000)),
    requestedBy: safeText(caller.actor, 320), result: null, error: '', leaseOwner: '', leaseExpiresAtMs: 0,
  };
  const batch = admin.firestore().batch();
  batch.create(admin.firestore().collection(COLLECTIONS.commands).doc(commandId), record);
  batch.create(idemRef, {commandId, ownerKey: owner, createdAtMs: now});
  await batch.commit();
  return record;
}

async function getPhoneCommand(admin, caller, args = {}) {
  const commandId = safeText(args.commandId, 180);
  if (!commandId) throw Object.assign(new Error('commandId is required'), {status: 400});
  const snap = await admin.firestore().collection(COLLECTIONS.commands).doc(commandId).get();
  if (!snap.exists) throw Object.assign(new Error('phone command not found'), {status: 404});
  const record = snap.data() || {};
  if (record.ownerKey !== ownerKey(caller)) throw Object.assign(new Error('phone command not found'), {status: 404});
  return record;
}
async function listPhoneDevices(admin, caller) {
  const snap = await admin.firestore().collection(COLLECTIONS.devices).where('ownerKey','==',ownerKey(caller)).limit(20).get();
  return snap.docs.map((doc) => { const x=doc.data()||{}; return {...x, tokenHash: x.tokenHash ? '[stored-digest]' : ''}; });
}

async function devicePull(admin, {deviceId, deviceToken, leaseMs = 30000} = {}) {
  const id = cleanDeviceId(deviceId);
  const devRef = admin.firestore().collection(COLLECTIONS.devices).doc(id);
  const devSnap = await devRef.get();
  if (!devSnap.exists) throw Object.assign(new Error('device not registered'), {status: 404});
  const device = devSnap.data() || {};
  if (hashText(deviceToken) !== device.tokenHash) throw Object.assign(new Error('device unauthorized'), {status: 401});
  const now = Date.now();
  await devRef.set({lastSeenAtMs: now, status: 'online'}, {merge: true});
  const query = await admin.firestore().collection(COLLECTIONS.commands)
    .where('ownerKey','==',device.ownerKey).where('deviceId','==',id).where('status','==','queued').limit(10).get();
  const candidates = query.docs.map((d) => d.data()).filter((x) => Number(x.expiresAtMs || 0) > now).sort((a,b) => a.createdAtMs-b.createdAtMs);
  if (!candidates.length) return {ok: true, command: null};
  const chosen = candidates[0];
  const leaseOwner = `device:${id}`;
  await admin.firestore().collection(COLLECTIONS.commands).doc(chosen.commandId).set({status:'leased', leaseOwner, leaseExpiresAtMs: now + Math.max(5000, Math.min(Number(leaseMs), 120000)), updatedAtMs: now}, {merge:true});
  return {ok: true, command: {...chosen, status:'leased', leaseOwner}};
}
async function deviceComplete(admin, {deviceId, deviceToken, commandId, status, result, error} = {}) {
  const id = cleanDeviceId(deviceId);
  const devSnap = await admin.firestore().collection(COLLECTIONS.devices).doc(id).get();
  if (!devSnap.exists) throw Object.assign(new Error('device not registered'), {status: 404});
  const device = devSnap.data() || {};
  if (hashText(deviceToken) !== device.tokenHash) throw Object.assign(new Error('device unauthorized'), {status: 401});
  const ref = admin.firestore().collection(COLLECTIONS.commands).doc(safeText(commandId,180));
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('command not found'), {status:404});
  const record = snap.data() || {};
  if (record.ownerKey !== device.ownerKey || record.deviceId !== id) throw Object.assign(new Error('command not found'), {status:404});
  const finalStatus = status === 'completed' ? 'completed' : 'failed';
  const cleanResult = JSON.parse(JSON.stringify(result == null ? null : result));
  if (record.action && record.action.action === 'phone_diagnostics') {
    const action = record.action;
    const streamRef = admin.firestore().collection(COLLECTIONS.diagnosticStreams)
      .doc(hashText(`${record.ownerKey}:${id}:${action.streamId}`));
    await admin.firestore().runTransaction(async (transaction) => {
      const fresh = await transaction.get(ref);
      const stream = await transaction.get(streamRef);
      if (!fresh.exists || !stream.exists || stream.data().inflightCommandId !== record.commandId) {
        throw Object.assign(new Error('phone_diagnostics completion CAS mismatch'), {status:409});
      }
      const freshRecord = fresh.data() || {};
      if (freshRecord.status !== 'leased' || freshRecord.leaseOwner !== `device:${id}`) {
        throw Object.assign(new Error('phone_diagnostics completion requires the exact device lease'), {status:409});
      }
      const now = Date.now();
      if (finalStatus === 'completed') {
        if (!cleanResult || cleanResult.schema !== 'phone.diagnostics.receipt.v1' ||
            cleanResult.requestHash !== hashText(canonicalJson(action)) ||
            cleanResult.deviceId !== id || cleanResult.streamId !== action.streamId ||
            cleanResult.chunkIndex !== action.chunkIndex ||
            cleanResult.packageId !== action.packageId || cleanResult.workerId !== action.workerId ||
            cleanResult.queueDocId !== action.queueDocId || cleanResult.queueRevision !== action.queueRevision ||
            cleanResult.commissionHash !== action.commissionHash || cleanResult.laneId !== action.laneId ||
            cleanResult.sessionId !== action.sessionId || cleanResult.diagnosticKind !== action.diagnosticKind ||
            cleanResult.networkUsed !== false || cleanResult.writeUsed !== false ||
            cleanResult.subprocessUsed !== false || cleanResult.buildUsed !== false ||
            cleanResult.installUsed !== false || cleanResult.uiUsed !== false ||
            !cleanResult.result || cleanResult.result.previousChunkHash !== safeText(action.previousChunkHash,64) ||
            cleanResult.result.watermarkBefore !== safeText(action.watermark,1000) ||
            cleanResult.result.rootId !== safeText(action.rootId,80) ||
            !Array.isArray(cleanResult.result.entries) ||
            cleanResult.result.entryCount !== cleanResult.result.entries.length ||
            !/^[0-9a-f]{64}$/.test(safeText(cleanResult.result.chunkHash,64)) ||
            diagnosticChunkHash(cleanResult.result) !== cleanResult.result.chunkHash ||
            !/^[0-9a-f]{64}$/.test(safeText(cleanResult.receiptHash,64)) ||
            diagnosticReceiptHash(cleanResult) !== cleanResult.receiptHash) {
          throw Object.assign(new Error('phone_diagnostics receipt identity or hash is invalid'), {status:400});
        }
        transaction.set(streamRef, {
          nextChunkIndex:action.chunkIndex + 1,
          lastWatermark:safeText(cleanResult.result && cleanResult.result.watermarkAfter,1000),
          lastChunkHash:cleanResult.result.chunkHash,
          lastReceiptHash:cleanResult.receiptHash,
          inflightCommandId:'',
          updatedAtMs:now,
        }, {merge:true});
      } else {
        transaction.set(streamRef, {inflightCommandId:'',updatedAtMs:now}, {merge:true});
      }
      transaction.set(ref, {
        status:finalStatus, result:cleanResult, error:safeText(error,4000),
        completedAtMs:now, updatedAtMs:now, leaseExpiresAtMs:0,
      }, {merge:true});
    });
    return {ok:true, commandId:record.commandId, status:finalStatus};
  }
  await ref.set({status: finalStatus, result: cleanResult, error: safeText(error,4000), completedAtMs: Date.now(), updatedAtMs: Date.now(), leaseExpiresAtMs:0}, {merge:true});
  return {ok:true, commandId:record.commandId, status:finalStatus};
}
async function registerDevice(admin, caller, args = {}) {
  const id = cleanDeviceId(args.deviceId || 'primary-phone');
  const token = safeText(args.deviceToken, 500);
  if (token.length < 32) throw Object.assign(new Error('deviceToken must be at least 32 characters'), {status:400});
  const now = Date.now();
  const previous = await admin.firestore().collection(COLLECTIONS.devices).doc(id).get();
  if (previous.exists && previous.data().ownerKey !== ownerKey(caller)) throw Object.assign(new Error('deviceId belongs to another owner'), {status:409});
  const record = {deviceId:id, ownerKey:ownerKey(caller), label:safeText(args.label,200)||id, tokenHash:hashText(token), status:'registered', capabilities:Array.isArray(args.capabilities)?args.capabilities.slice(0,50):[], createdAtMs:previous.exists?(previous.data().createdAtMs||now):now, updatedAtMs:now, lastSeenAtMs:0};
  await admin.firestore().collection(COLLECTIONS.devices).doc(id).set(record,{merge:true});
  return {...record, tokenHash:'[stored-digest]'};
}

function createPhoneHandsRelayHandler(admin) {
  return async (req,res) => {
    try {
      let out;
      if (req.path === '/register') {
        const header=req.get('Authorization')||''; const match=header.match(/^Bearer\s+(.+)$/i);
        const caller=await callerFromBearer(admin,match&&match[1]); out=await registerDevice(admin,caller,req.body||{});
      } else if (req.path === '/pull') out=await devicePull(admin,req.body||{});
      else if (req.path === '/complete') out=await deviceComplete(admin,req.body||{});
      else { res.status(404).json({ok:false,error:'not_found'}); return; }
      res.set('Cache-Control','no-store').status(200).json(out);
    } catch (err) { res.status(err.status||500).json({ok:false,error:err.message||String(err)}); }
  };
}

function registerCommandCenterPhoneTools(server, {admin, z, textResult, callerFromExtra}) {
  server.registerTool('command_center.phone_hands.devices', {
    title:'List Android Phone Hands devices', description:'List owner-scoped Android Phone Hands relay devices and live last-seen state.', inputSchema:{}
  }, async (_args,extra)=>textResult(await listPhoneDevices(admin,await callerFromExtra(admin,extra))));
  server.registerTool('command_center.phone_hands.enqueue', {
    title:'Enqueue Android Phone Hands action', description:'Send a bounded action to an owner-scoped Android phone through the Home Center relay. The phone executes it locally through Phone Hands.',
    inputSchema:{idempotencyKey:z.string(),deviceId:z.string().optional(),commandId:z.string().optional(),action:z.record(z.string(),z.any()),ttlMs:z.number().optional()}
  }, async (args,extra)=>textResult(await enqueuePhoneCommand(admin,await callerFromExtra(admin,extra),args||{})));
  server.registerTool('command_center.phone_hands.get', {
    title:'Read Android Phone Hands command', description:'Read status, result, or failure for one owner-scoped phone action.', inputSchema:{commandId:z.string()}
  }, async (args,extra)=>textResult(await getPhoneCommand(admin,await callerFromExtra(admin,extra),args||{})));
}

module.exports = {COLLECTIONS, enqueuePhoneCommand, getPhoneCommand, listPhoneDevices, registerDevice, devicePull, deviceComplete, cleanAction, cleanPhoneDiagnostics, diagnosticChunkHash, diagnosticReceiptHash, hashText, createPhoneHandsRelayHandler, registerCommandCenterPhoneTools};
