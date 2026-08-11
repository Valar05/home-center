const {createHash, randomUUID} = require('node:crypto');

const COLLECTIONS = Object.freeze({
  devices: 'phoneHandsDevices',
  commands: 'phoneHandsCommands',
  idempotency: 'phoneHandsIdempotency',
});

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}
function safeObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
function hashText(value) { return createHash('sha256').update(String(value || '')).digest('hex'); }
function shortHash(value, n = 32) { return hashText(value).slice(0, n); }
function ownerKeyFromActor(actor) { return `owner_${shortHash(safeText(actor, 320).toLowerCase() || 'anonymous', 32)}`; }
function cleanDeviceId(value) {
  const id = safeText(value, 120).toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '');
  if (!id) throw Object.assign(new Error('deviceId is required'), {status: 400});
  return id;
}
function cleanAction(value) {
  const body = safeObject(value);
  const action = safeText(body.action, 80);
  const allowed = new Set([
    'observe','tap','swipe','text','keyevent','home','back','recents','launch','force_stop','dungeon_run','local_ask','phone_shell',
    'file_stat','file_hash','file_list','file_mkdir','file_copy','file_move','armory_inventory','armory_ingest','armory_doctor','armory_slice',
    'window_status','window_probe','window_compose','window_focus','window_swap',
    'status_tts_doctor','status_say',
    'operator_overlay_status','operator_overlay_start','operator_overlay_update',
  ]);
  if (!allowed.has(action)) throw Object.assign(new Error(`unsupported phone action: ${action}`), {status: 400});
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
  const owner = ownerKey(caller);
  const idemId = hashText(`${owner}:${idem}`);
  const idemRef = admin.firestore().collection(COLLECTIONS.idempotency).doc(idemId);
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

module.exports = {COLLECTIONS, enqueuePhoneCommand, getPhoneCommand, listPhoneDevices, registerDevice, devicePull, deviceComplete, cleanAction, hashText, createPhoneHandsRelayHandler, registerCommandCenterPhoneTools};
