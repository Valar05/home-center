#!/usr/bin/env node
import fs from 'node:fs';
const relay=fs.readFileSync('functions/phone_hands_relay.js','utf8');
const patcher=fs.readFileSync('tools/apply_phone_hands_relay_wiring.mjs','utf8');
const agent=fs.readFileSync('tools/android_phone_home_center_relay.py','utf8');
const factory=fs.readFileSync('tools/android_phone_factory_tools.py','utf8');
const armoryDriver=fs.readFileSync('tools/android_armory_driver.py','utf8');
const armoryBlender=fs.readFileSync('tools/fleshpunk_armory_blender.py','utf8');
const requiredRelay=['command_center.phone_hands.devices','command_center.phone_hands.enqueue','command_center.phone_hands.get','devicePull','deviceComplete','registerDevice'];
for (const s of requiredRelay) if (!relay.includes(s)) throw new Error('relay contract missing '+s);
for (const s of ["require('./phone_hands_relay')",'registerCommandCenterPhoneTools','exports.phoneHandsRelay']) if (!patcher.includes(s)) throw new Error('wiring patch missing '+s);
for (const s of ['termuxTokenRefresh','android_phone_hands_bridge','dungeon_run','local_ask','/pull','/complete','android_phone_factory_tools','android_armory_driver','FACTORY_ACTIONS','ARMORY_ACTIONS']) if (!agent.includes(s)) throw new Error('phone agent contract missing '+s);
const factoryActions=['file_stat','file_hash','file_list','file_mkdir','file_copy','file_move','armory_inventory','armory_ingest'];
for (const s of factoryActions) {
  if (!relay.includes(`'${s}'`)) throw new Error('relay action missing '+s);
  if (!factory.includes(`'${s}'`)) throw new Error('factory action missing '+s);
}
for (const s of ['armory_doctor','armory_slice']) {
  if (!relay.includes(`'${s}'`)) throw new Error('relay action missing '+s);
  if (!agent.includes(`'${s}'`)) throw new Error('agent action missing '+s);
  if (!armoryDriver.includes(`'${s}'`)) throw new Error('armory driver action missing '+s);
}
for (const s of ['ALLOWED_ROOTS','verified_copy','sha256_file','glb_inventory','source_manifest.json','source_inventory.json']) if (!factory.includes(s)) throw new Error('factory safety/evidence contract missing '+s);
for (const s of ['--background','slice_receipt.json','blender_path','timeoutSeconds']) if (!armoryDriver.includes(s)) throw new Error('armory driver contract missing '+s);
for (const s of ['separate(type=\'LOOSE\')','parts.json','contact_sheet_all_parts.png','reassembled.glb','semanticCategory']) if (!armoryBlender.includes(s)) throw new Error('armory Blender contract missing '+s);
if (relay.includes('deviceToken:'+' token')) throw new Error('device token must not be returned by MCP');
console.log('phone hands relay + deterministic factory + Armory slicer contract: PASS');
