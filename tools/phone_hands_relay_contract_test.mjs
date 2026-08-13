#!/usr/bin/env node
import fs from 'node:fs';
const relay=fs.readFileSync('functions/phone_hands_relay.js','utf8');
const patcher=fs.readFileSync('tools/apply_phone_hands_relay_wiring.mjs','utf8');
const agent=fs.readFileSync('tools/android_phone_home_center_relay.py','utf8');
const shell=fs.readFileSync('tools/android_phone_termux_shell.py','utf8');
const diagnostics=fs.readFileSync('tools/android_phone_diagnostics.py','utf8');
const overlay=fs.readFileSync('tools/android_operator_overlay.py','utf8');
const overlayInstaller=fs.readFileSync('tools/setup_android_operator_overlay.sh','utf8');
const overlayWorkflow=fs.readFileSync('.github/workflows/operator-overlay-android.yml','utf8');
const overlaySignedBuilder=fs.readFileSync('tools/build_operator_overlay_signed.ps1','utf8');
const overlayManifest=fs.readFileSync('android/operator-overlay/app/src/main/AndroidManifest.xml','utf8');
const overlayService=fs.readFileSync('android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java','utf8');
const overlayState=fs.readFileSync('android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java','utf8');
const overlayProvider=fs.readFileSync('android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorStateProvider.java','utf8');
const overlayPolicy=fs.readFileSync('android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OverlayUiPolicy.java','utf8');
const overlayPolicyTest=fs.readFileSync('android/operator-overlay/app/src/test/java/com/homecenter/operatoroverlay/OverlayUiPolicyTest.java','utf8');
const factory=fs.readFileSync('tools/android_phone_factory_tools.py','utf8');
const armoryDriver=fs.readFileSync('tools/android_armory_driver.py','utf8');
const armoryBlender=fs.readFileSync('tools/fleshpunk_armory_blender.py','utf8');
const requiredRelay=['command_center.phone_hands.devices','command_center.phone_hands.enqueue','command_center.phone_hands.get','devicePull','deviceComplete','registerDevice'];
for (const s of requiredRelay) if (!relay.includes(s)) throw new Error('relay contract missing '+s);
for (const s of ["require('./phone_hands_relay')",'registerCommandCenterPhoneTools','exports.phoneHandsRelay']) if (!patcher.includes(s)) throw new Error('wiring patch missing '+s);
for (const s of ['termuxTokenRefresh','android_phone_hands_bridge','dungeon_run','local_ask','/pull','/complete','android_phone_factory_tools','android_armory_driver','FACTORY_ACTIONS','ARMORY_ACTIONS','android_phone_termux_shell','TERMUX_SHELL_ACTIONS','android_phone_diagnostics','DIAGNOSTIC_ACTIONS','phone_diagnostics_readonly','android_operator_overlay','OVERLAY_ACTIONS','overlay_control_gate','overlay_heartbeat']) if (!agent.includes(s)) throw new Error('phone agent contract missing '+s);
for (const s of ["'phone_shell'",'timeoutSeconds','MAX_OUTPUT_CHARS','SECRET_PATTERNS','subprocess.run']) if (!shell.includes(s)) throw new Error('Termux shell contract missing '+s);
if (!relay.includes("'phone_shell'")) throw new Error('relay action missing phone_shell');
for (const s of ["'phone_diagnostics'",'cleanPhoneDiagnostics','phone.diagnostics.request.v1','GODOT_PROJECTS','commissionHash','previousChunkHash']) if (!relay.includes(s)) throw new Error('typed phone diagnostics relay contract missing '+s);
for (const s of ['ROOTS','GODOT_PROJECTS','DiagnosticsEngine','capability_snapshot','tree_inventory','repo_status','toolchain_probe','cache_probe','file_manifest','PENDING_HOME_CENTER_POSTBACK','UNKNOWN_NO_EXEC','followlinks=False']) if (!diagnostics.includes(s)) throw new Error('phone diagnostics implementation contract missing '+s);
for (const forbidden of ['import subprocess','import urllib','import socket','import requests','shell=True','os.system','eval(','exec(']) {
  if (diagnostics.includes(forbidden)) throw new Error('phone diagnostics must not execute, write, or use network: '+forbidden);
}
if (agent.indexOf('if kind in DIAGNOSTIC_ACTIONS:') > agent.indexOf('gate=overlay_control_gate()')) throw new Error('typed diagnostics must not depend on the interaction overlay gate');

const overlayActions=['operator_overlay_status','operator_overlay_start','operator_overlay_update'];
for (const s of overlayActions) {
  if (!relay.includes(`'${s}'`)) throw new Error('relay overlay action missing '+s);
  if (!overlay.includes(`'${s}'`)) throw new Error('phone overlay action missing '+s);
}
for (const forbidden of ['operator_overlay_enable','operator_overlay_disable','operator_overlay_set_control']) {
  if (relay.includes(forbidden) || overlay.includes(forbidden)) throw new Error('remote control-toggle mutation must not exist: '+forbidden);
}
for (const s of ['controlEnabled','muted','control_gate','STATE_URI','content query','ACTION_UPDATE','ACTION_HEARTBEAT','ACTION_SCREEN_ACTIVITY','screen_activity','screenActiveUntilMs','screenYieldUntilMs','panelCollapsed','overlayHidden','STATE_READ_ATTEMPTS','_read_state','operator state provider returned an incomplete row','dumpsys package','Home Center operator overlay is required; refusing remote phone control',"integer('control_enabled', 0)"]) if (!overlay.includes(s)) throw new Error('operator overlay fail-closed/active-screen enforcement contract missing '+s);
if (overlay.includes("if not state.get('installed'):\n        return state")) throw new Error('missing overlay state must never bypass the user control gate');
for (const s of ['/data/local/tmp/home-center-operator-overlay.apk','STAGED_SHA','pm install -r',"grep -qx 'Success'",'pm list packages $PACKAGE','SYSTEM_ALERT_WINDOW: allow','control_enabled=']) if (!overlayInstaller.includes(s)) throw new Error('operator overlay installer verification contract missing '+s);
if (overlayInstaller.includes("pm install -r '$OUT'")) throw new Error('installer must not pass shared-storage Termux path directly to system_server');
for (const s of ['build_operator_overlay_signed.ps1','origin/generated/operator-overlay-apk','ExpectedSourceSha','operator-overlay-debug.apk','operator-overlay-receipt.json','git worktree add','refs/heads/generated/operator-overlay-apk']) if (!overlayWorkflow.includes(s)) throw new Error('operator overlay durable signing workflow missing '+s);
for (const s of ['ExpectedSourceSha','Source SHA mismatch','GeneratedSigningRef','operator-overlay-debug.keystore','git','archive','Get-CertificateSha256','Find-ApkSigner','APK signer mismatch','signingCertificateSha256','signingKeySha256','signingSourceRef','durableSigningKey = $true','installed = $false','deploymentEvidence = $false','phoneTouched = $false','screenInteractionUsed = $false','ExportKeystore','versionNameMatch','versionCodeMatch','app/build.gradle','finally','debugBackup','localPropertiesBackup']) if (!overlaySignedBuilder.includes(s)) throw new Error('operator overlay signed builder contract missing '+s);
if (!overlaySignedBuilder.includes('if ($ExpectedSourceSha -and $sourceSha -ne $ExpectedSourceSha)')) throw new Error('signed overlay build must bind to the exact expected source');
if (!overlaySignedBuilder.includes('if ($apkCertificateSha -ne $signingCertificateSha)')) throw new Error('signed overlay build must verify APK/key certificate equality');
if (/^\s*\$home\s*=/mi.test(overlaySignedBuilder)) throw new Error('signed overlay builder must not overwrite PowerShell read-only HOME');
if (!overlaySignedBuilder.includes('$userHome =')) throw new Error('signed overlay builder must use a non-reserved user-home variable');
for (const forbidden of ['keytool -genkeypair','keytool -genkey','genkeypair']) {
  if (overlayWorkflow.includes(forbidden) || overlaySignedBuilder.includes(forbidden)) throw new Error('workflow/builder must never generate or rotate a signing key: '+forbidden);
}
if (overlayWorkflow.includes('git switch --orphan') || overlayWorkflow.includes('git push --force')) throw new Error('artifact publication must preserve the existing private signing branch history');
for (const text of [overlayWorkflow,overlaySignedBuilder]) {
  if (/versionName\s*[:=]\s*['"]1\.(?:0|2)(?:\.[0-9]+)?['"]/.test(text)) throw new Error('overlay version must be derived from current Gradle metadata');
}
for (const s of ['SYSTEM_ALERT_WINDOW','FOREGROUND_SERVICE_SPECIAL_USE','RECEIVE_BOOT_COMPLETED','android.permission.DUMP','OperatorOverlayService','OperatorStateProvider','BootReceiver']) if (!overlayManifest.includes(s)) throw new Error('operator overlay Android manifest missing '+s);
for (const s of ['ACTION_SCREEN_ACTIVITY','ACTION_RESTORE','REMOTE INPUT • ACTIVE','REMOTE INPUT • local screen input temporarily reserved','REMOTE INPUT • action pulse','Hide overlay','panelCollapsed','screenActiveUntilMs','screenYieldUntilMs','Confirm disable','Disable control','Enable control','Mute speech','Unmute speech','HOME CENTER • ON','HOME CENTER • OFFLINE','CONTROL OFF','setMaxLines(30)','setMaxLines(2)','touchGuard','MATCH_PARENT','FLAG_NOT_TOUCHABLE','syncTouchGuard','setOnTouchListener((view, event) -> true)','ScrollingMovementMethod','setVerticalScrollBarEnabled(true)','ViewConfiguration','getScaledTouchSlop','MIN_TOUCH_TARGET_DP','setOverlayPosition','onConfigurationChanged','addOnLayoutChangeListener','WindowInsets.Type.displayCutout','touchGuardActive']) if (!overlayService.includes(s)) throw new Error('operator overlay polished active-screen/draggable/compact UI contract missing '+s);
if (overlayService.includes('syncTouchGuard(enabled && online);')) throw new Error('enabled+online must never by itself block local input');
for (const s of ['KEY_SCREEN_ACTIVE_UNTIL_MS','KEY_SCREEN_YIELD_UNTIL_MS','KEY_PANEL_COLLAPSED','KEY_OVERLAY_HIDDEN','KEY_OVERLAY_X','KEY_OVERLAY_Y','clearScreenActivity','setScreenActivity','setOverlayPosition',"getBoolean(KEY_CONTROL_ENABLED, false)"]) if (!overlayState.includes(s)) throw new Error('operator overlay fail-closed persistent-state contract missing '+s);
if (overlayState.includes('getBoolean(KEY_CONTROL_ENABLED, true)')) throw new Error('fresh install must never default remote control on');
for (const s of ['screen_active_until_ms','screen_yield_until_ms','panel_collapsed','overlay_hidden']) if (!overlayProvider.includes(s)) throw new Error('operator state provider bounded state contract missing '+s);
for (const s of ['MIN_TOUCH_TARGET_DP = 48','touchGuardActive','controlEnabled && online && screenActive && !screenYield','clampPosition','isDrag','nextHidden']) if (!overlayPolicy.includes(s)) throw new Error('operator overlay pure policy contract missing '+s);
for (const s of ['gestureThresholdSeparatesTapFromDrag','dragArbitrationWorksInBothAxes','hideAndRestoreAreExplicitTransitions','guardNeedsEveryLeasePrecondition','positionClampsToInsetsAndEveryEdge','oversizedPanelStillLeavesLocalEscapeCornerReachable']) if (!overlayPolicyTest.includes(s)) throw new Error('operator overlay policy regression coverage missing '+s);
if (!agent.includes("if k=='status_say' and gate.get('muted')")) throw new Error('mute must suppress status speech at the relay');
if (!agent.includes("if k in OVERLAY_ACTIONS")) throw new Error('overlay status/update actions must remain reachable when control is disabled');
if (!agent.includes('gate=overlay_control_gate()')) throw new Error('ordinary remote phone actions must pass the user-owned overlay control gate');
for (const s of ['overlay_screen_activity','SCREEN_DIRECT_ACTIONS','SCREEN_WINDOW_ACTIONS','_screen_profile','screen=_screen_profile(a)',"if k in TERMUX_SHELL_ACTIONS:return termux_shell_execute(a)","return {'leaseMs':2500,'yieldMs':0}","return {'leaseMs':2500,'yieldMs':900}"]) if (!agent.includes(s)) throw new Error('phone relay active-screen lease contract missing '+s);
if (agent.includes("SCREEN_DIRECT_ACTIONS={'phone_shell'")) throw new Error('background phone_shell must never activate the screen guard');

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
for (const s of ["separate(type='LOOSE')",'parts.json','contact_sheet_all_parts.png','reassembled.glb','semanticCategory']) if (!armoryBlender.includes(s)) throw new Error('armory Blender contract missing '+s);
if (relay.includes('deviceToken:'+' token')) throw new Error('device token must not be returned by MCP');
console.log('phone hands relay + exact durable APK signer + active-screen-only guard + 48dp touch-slop drag + compact/persistent overlay + safe-area clamp + local hide/restore + fail-closed state + verified install + background Termux shell + deterministic factory + Armory slicer contract: PASS');
