#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const target = path.join(root, 'functions', 'phone_hands_relay.js');
let source = fs.readFileSync(target, 'utf8');

const oldBlock = `  const query = await admin.firestore().collection(COLLECTIONS.commands)\n    .where('ownerKey','==',device.ownerKey).where('deviceId','==',id).where('status','==','queued').limit(10).get();\n  const candidates = query.docs.map((d) => d.data()).filter((x) => Number(x.expiresAtMs || 0) > now).sort((a,b) => a.createdAtMs-b.createdAtMs);\n  if (!candidates.length) return {ok: true, command: null};\n`;
const newBlock = `  const query = await admin.firestore().collection(COLLECTIONS.commands)\n    .where('ownerKey','==',device.ownerKey).where('deviceId','==',id).where('status','==','queued').limit(100).get();\n  const queued = query.docs.map((d) => d.data()).sort((a,b) => a.createdAtMs-b.createdAtMs);\n  const expired = queued.filter((x) => Number(x.expiresAtMs || 0) <= now);\n  if (expired.length) {\n    const batch = admin.firestore().batch();\n    for (const command of expired.slice(0, 80)) {\n      if (!command.commandId) continue;\n      batch.set(admin.firestore().collection(COLLECTIONS.commands).doc(command.commandId), {\n        status:'failed', error:'expired_before_lease', completedAtMs:now, updatedAtMs:now, leaseExpiresAtMs:0,\n      }, {merge:true});\n    }\n    await batch.commit();\n  }\n  const candidates = queued.filter((x) => Number(x.expiresAtMs || 0) > now);\n  if (!candidates.length) return {ok: true, command: null};\n`;

if (source.includes(newBlock)) {
  console.log('Phone Hands queue starvation fix already applied');
  process.exit(0);
}
if (!source.includes(oldBlock)) throw new Error('Phone Hands queue selection anchor not found');
source = source.replace(oldBlock, newBlock);
fs.writeFileSync(target, source);
console.log('Phone Hands queue starvation fix applied');
