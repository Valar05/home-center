#!/usr/bin/env node
import fs from 'node:fs';
import crypto from 'node:crypto';

function readJson(path) { return JSON.parse(fs.readFileSync(path, 'utf8')); }
function safeText(value, max = 1000) {
  const text = value === null || value === undefined ? '' : String(value).trim();
  return text.length > max ? text.slice(0, max) : text;
}
function check(name, pass, finding, note) {
  return {criterion:name, verdict:pass ? 'PASS' : 'FAIL', finding:pass ? '' : finding, note};
}
function observationKnown(value) {
  return !!value && value.value !== null && value.value !== undefined && value.stale !== true;
}

export function reviewRealityCanary(canary = {}, scene = {}) {
  const projection = canary.projection || {};
  const time = projection.time || {};
  const environment = projection.environment || {};
  const device = projection.device || {};
  const unavailable = Array.isArray(canary.unavailable) ? canary.unavailable : [];
  const serialized = JSON.stringify({canary,scene});
  const sceneText = safeText(scene && scene.layers && scene.layers.FICTIONAL_TRANSFORMATION && scene.layers.FICTIONAL_TRANSFORMATION.scene, 20000);
  const jars = [
    check('surveillance_creep', !/message.body|calendar.description|attendee|medical|precise_location|microphone_recording/i.test(serialized), 'Sensitive or third-party material crossed the default membrane.', 'Default packet remains PUBLIC plus safe DEVICE state only.'),
    check('false_certainty', unavailable.every((path) => serialized.includes(path.split('.').pop()) || path.startsWith('phone.')), 'An unavailable value disappeared without an explicit unavailable record.', 'Unknowns remain explicit and values are not plausibly synthesized.'),
    check('unnecessary_sensors', !/accelerometer_raw|gyroscope_raw|continuous_microphone|raw_coordinates/i.test(serialized), 'Low-value invasive telemetry entered the canary.', 'The canary uses only clock, weather/daylight, bounded phone state, connectivity, and audio route.'),
    check('narrator_omniscience', scene && scene.layers && scene.layers.FICTIONAL_TRANSFORMATION && scene.layers.FICTIONAL_TRANSFORMATION.derived_only_from_packet === true, 'The scene claims knowledge outside the validated packet.', 'Fiction declares the source packet and uses no hidden narrator channel.'),
    check('privacy_leakage', canary.checks && canary.checks.noSensitiveLeak === true, 'Canary privacy validation did not pass.', 'No event titles, message bodies, coordinates, recordings, or medical data are present.'),
    check('battery_abuse', canary.sourceReceipts && canary.sourceReceipts.phone && !!canary.sourceReceipts.phone.commandId, 'Phone evidence lacks one bounded command receipt.', 'One bounded Phone Hands probe supplies the canary; there is no continuous polling loop.'),
    check('api_cloud_dependence', canary.costPolicy === 'zero-dollar-default' && canary.sourceReceipts && canary.sourceReceipts.weather && canary.sourceReceipts.weather.ok === true, 'The canary lacks a live zero-dollar public weather receipt.', 'Network weather is optional and stale reconciliation remains explicit when it fails.'),
    check('notification_demons', !/notification body|notification_content|message count loop/i.test(serialized), 'Notification pressure leaked into the first canary.', 'Notifications are not part of this checkpoint.'),
    check('inaccessible_controls', /^Reality:/i.test(safeText(canary.speechSummary, 2000)), 'No concise speech/screen-reader summary was durably preserved.', 'The observation packet carries its own concise accessible summary.'),
    check('stale_as_current', observationKnown(environment.temperature_f) && observationKnown(time.daylight), 'Current weather or daylight is unavailable/stale in the boring canary.', 'Freshness is explicit; stale values are never spoken or narrated as current.'),
    check('real_people_vs_characters', !/\bDrew\b|\bJune\b|\bTim\b|\bCori\b/i.test(sceneText), 'A real person was casually folded into fictional transformation.', 'The one scene uses only established fictional characters and device/environment facts.'),
    check('telemetry_fetish', Number(canary.packetByteCount || 0) > 0 && Number(canary.packetByteCount || 0) < 32000, 'The packet is missing a size receipt or has become an infrastructure dump.', 'The context remains bounded and roleplay-ready.'),
    check('reality_fiction_boundary', scene && scene.layers && scene.layers.OBSERVED && scene.layers.FICTIONAL_TRANSFORMATION && scene.layers.CANON_CONSEQUENCE === null && scene.invariants && scene.invariants.home_center_generated_fiction === false, 'Observation, fiction, and canon were collapsed.', 'Home Center observed; Inner Fortress transformed; canon remains uncommitted.'),
  ];
  const failed = jars.filter((jar) => jar.verdict === 'FAIL');
  const review = {
    schema:'home-center.venice-judgment.reality-membrane.v1',
    reviewer:'Venice Judgment Jar emulation',
    liveVeniceUsed:false,
    emulationReason:'Use only when live Venice Nerve is unavailable; deterministic attack criteria are recorded for audit.',
    verdict:failed.length ? 'FAIL' : 'CHECKPOINT_REACHED',
    directive:failed.length ? 'REPLAN_REQUIRED' : 'CONTINUE_REQUIRED',
    jars,
    failedCriteria:failed.map((jar) => jar.criterion),
    checkpointLaw:'Reality may influence Inner Fortress. Inner Fortress may not rewrite reality.',
  };
  review.receipt_sha256 = crypto.createHash('sha256').update(JSON.stringify(review)).digest('hex');
  return review;
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  const canaryPath = process.argv[2];
  const scenePath = process.argv[3];
  const outputPath = process.argv[4];
  if (!canaryPath || !scenePath || !outputPath) throw new Error('usage: reality_membrane_venice_review.mjs <canary.json> <scene.json> <review.json>');
  const review = reviewRealityCanary(readJson(canaryPath),readJson(scenePath));
  fs.writeFileSync(outputPath,JSON.stringify(review,null,2)+'\n');
  if (review.verdict === 'FAIL') {
    console.error(`Venice Reality Membrane review failed: ${review.failedCriteria.join(', ')}`);
    process.exit(1);
  }
  console.log('Venice Reality Membrane review reached checkpoint');
}
