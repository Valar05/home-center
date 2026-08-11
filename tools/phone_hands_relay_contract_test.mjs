#!/usr/bin/env node
import fs from 'node:fs';
const relay=fs.readFileSync('functions/phone_hands_relay.js','utf8');
const patcher=fs.readFileSync('tools/apply_phone_hands_relay_wiring.mjs','utf8');
const agent=fs.readFileSync('tools/android_phone_home_center_relay.py','utf8');
const shell=fs.readFileSync('tools/android_phone_termux_shell.py','utf8');
const overlay=fs.readFileSync('tools/android_operator_overlay.py','utf8');
const overlayManifest=fs.readFileSync('android/operator-overlay/app/src/main/AndroidManifest.xml','utf8');
const overlayService=fs.readFileSync('android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java','utf8');
const factory=fs.readFileSync('tools/android_phone_factory_tools.py','utf8');
const armoryDriver=fs.readFileSync('tools/android_armory_driver.py','utf8');
const armoryBlender=fs.readFileSync('tools/fleshpunk_armory_blender.py','utf8');
const requiredRelay=['command_center.phone_hands.devices','command_center.phone_hands.enqueue','command_center.phone_hands.get','devicePull','deviceComplete','registerDevice'];
for (const s of requiredRelay) if (!relay.includes(s)) throw new Error('relay contract missing '+s);
for (const s of ["require('./phone_hands_relay')",'registerCommandCenterPhoneTools','exports.phoneHandsRelay']) if (!patcher.includes(s)) throw new Error('wiring patch missing '+s);
for (const s of ['termuxTokenRefresh','android_phone_hands_bridge','dungeon_run','local_ask','/pull','/complete','android_phone_factory_tools','android_armory_driver','FACTORY_ACTIONS','ARMORY_ACTIONS','android_phone_termux_shell','TERMUX_SHELL_ACTIONS','android_operator_overlay','OVERLAY_ACTIONS','overlay_control_gate','overlay_heartbeat']) if (!agent.includes(s)) throw new Error('phone agent contract missing '+s);
for (const s of ["'phone_shell'",'timeoutSeconds','MAX_OUTPUT_CHARS','SECRET_PATTERNS','subprocess.run']) if (!shell.includes(s)) throw new Error('Termux shell contract missing '+s);
if (!relay.includes("'phone_shell'")) throw new Error('relay action missing phone_shell');

const overlayActions=['operator_overlay_status','operator_overlay_start','operator_overlay_update'];
for (const s of overlayActions) {
  if (!relay.includes(`'${s}'`)) throw new Error('relay overlay action missing '+s);
  if (!overlay.includes(`'${s}'`)) throw new Error('phone overlay action missing '+s);
}
for (const forbidden of ['operator_overlay_enable','operator_overlay_disable','operator_overlay_set_control']) {
  if (relay.includes(forbidden) || overlay.includes(forbidden)) throw new Error('remote control-toggle mutation must not exist: '+forbidden);
}
for (const s of ['controlEnabled','muted','control_gate','STATE_URI','content query','ACTION_UPDATE','ACTION_HEARTBEAT']) if (!overlay.includes(s)) throw new Error('operator overlay enforcement contract missing '+s);
for (const s of ['SYSTEM_ALERT_WINDOW','FOREGROUND_SERVICE_SPECIAL_USE','RECEIVE_BOOT_COMPLETED','android.permission.DUMP','OperatorOverlayService','OperatorStateProvider','BootReceiver']) if (!overlayManifest.includes(s)) throw new Error('operator overlay Android manifest missing '+s);
for (const s of ['Confirm disable','Disable control','Enable control','Mute','Unmute','HOME CENTER • ON','HOME CENTER • OFFLINE','CONTROL OFF','setMaxLines(30)','setMaxLines(2)','touchGuard','MATCH_PARENT','FLAG_NOT_TOUCHABLE','syncTouchGuard','setOnTouchListener((view, event) -> true)']) if (!overlayService.includes(s)) throw new Error('operator overlay visible/guard UI contract missing '+s);
if (!agent.includes("if kind=='status_say' and gate.get('muted')")) throw new Error('mute must suppress status speech at the relay');
if (!agent.includes("if kind in OVERLAY_ACTIONS")) throw new Error('overlay status/update actions must remain reachable when control is disabled');
if (!agent.includes('gate=overlay_control_gate()')) throw new Error('ordinary remote phone actions must pass the user-owned overlay control gate');

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
console.log('phone hands relay + operator overlay guard + Termux shell + deterministic factory + Armory slicer contract: PASS');
