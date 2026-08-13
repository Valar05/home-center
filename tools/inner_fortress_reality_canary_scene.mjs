#!/usr/bin/env node
import fs from 'node:fs';
import crypto from 'node:crypto';

function safeText(value, max = 1000) {
  const text = value === null || value === undefined ? '' : String(value).trim();
  return text.length > max ? text.slice(0, max) : text;
}
function readJson(path) { return JSON.parse(fs.readFileSync(path, 'utf8')); }
function observation(group, key) {
  const value = group && group[key];
  return value && typeof value === 'object' ? value : null;
}
function known(observationValue) {
  return !!observationValue && observationValue.value !== null && observationValue.value !== undefined && observationValue.stale !== true;
}
function humanTime(value) {
  const text = safeText(value, 80);
  const match = text.match(/T(\d{2}):(\d{2})(?::\d{2})?/);
  if (!match) return text || 'an unknown hour';
  const hour24 = Number(match[1]);
  const minute = match[2];
  const suffix = hour24 >= 12 ? 'PM' : 'AM';
  const hour12 = hour24 % 12 || 12;
  return `${hour12}:${minute} ${suffix}`;
}
function daylightSentence(value) {
  if (value === 'dark_before_sunrise') return 'The kitchen window was still black with the hour before sunrise.';
  if (value === 'dark_after_sunset') return 'Night had already closed over the kitchen window.';
  if (value === 'daylight') return 'Daylight had reached the kitchen window.';
  return 'The membrane would not claim whether the window held daylight or darkness.';
}
function weatherSentence(environment = {}) {
  const temp = observation(environment, 'temperature_f');
  const feels = observation(environment, 'feels_like_f');
  const precipitation = observation(environment, 'precipitation');
  const pieces = [];
  if (known(temp)) pieces.push(`${safeText(temp.value, 40)} degrees Fahrenheit outside`);
  if (known(feels) && String(feels.value) !== String(temp && temp.value)) pieces.push(`feeling like ${safeText(feels.value, 40)}`);
  if (known(precipitation)) {
    const kind = safeText(precipitation.value, 80).toLowerCase();
    if (kind === 'rain') pieces.push('rain in the current observation');
    else if (kind === 'snow') pieces.push('snow in the current observation');
    else if (kind === 'none') pieces.push('no current precipitation');
    else if (kind) pieces.push(`${kind} in the current observation`);
  }
  return pieces.length ? `The membrane reported ${pieces.join(', ')}.` : 'The weather source remained honestly unavailable.';
}
function deviceSentence(device = {}, unavailable = []) {
  const battery = observation(device, 'battery_pct');
  const charging = observation(device, 'charging');
  const connectivity = observation(device, 'connectivity');
  const audioRoute = observation(device, 'audio_route');
  const pieces = [];
  if (known(battery)) pieces.push(`the phone at ${safeText(battery.value, 40)} percent`);
  else if (unavailable.includes('phone.battery_pct')) pieces.push('the phone battery unobserved');
  if (known(charging)) pieces.push(charging.value === true ? 'charging' : 'not charging');
  else if (unavailable.includes('phone.charging')) pieces.push('its charging state unknown');
  if (known(connectivity)) pieces.push(`connected by ${safeText(connectivity.value, 80).replace(/_/g, ' ')}`);
  else if (unavailable.includes('phone.connectivity')) pieces.push('its connection class unknown');
  if (known(audioRoute)) pieces.push(`audio routed through ${safeText(audioRoute.value, 80).replace(/_/g, ' ')}`);
  else if (unavailable.includes('phone.audio_route')) pieces.push('its audio route unknown');
  return pieces.length ? `On the table: ${pieces.join('; ')}.` : 'The phone offered no usable observation, and the scene did not counterfeit one.';
}
function rainAction(environment = {}) {
  const precipitation = observation(environment, 'precipitation');
  if (!known(precipitation)) return 'He left the weather without an adjective.';
  if (precipitation.value === 'rain') return 'Android 67 listened for rain against the glass, and only then let April hear it too.';
  if (precipitation.value === 'snow') return 'Android 67 watched the pale weather beyond the glass and left the coat hook occupied.';
  if (precipitation.value === 'none') return 'Android 67 left the coat where it hung; the sky had made no wet demand.';
  return 'Android 67 accepted the reported weather without pretending it was prophecy.';
}

export function buildCanaryScene(canaryReceipt) {
  const projection = canaryReceipt && canaryReceipt.projection || {};
  const time = projection.time || {};
  const environment = projection.environment || {};
  const device = projection.device || {};
  const unavailable = Array.isArray(canaryReceipt && canaryReceipt.unavailable) ? canaryReceipt.unavailable : [];
  const now = observation(time, 'now');
  const daylight = observation(time, 'daylight');
  const observed = {
    packet_receipt_id:safeText(canaryReceipt && canaryReceipt.packetReceiptId, 200),
    observed_at:safeText(canaryReceipt && canaryReceipt.observedAt, 100),
    time:now,
    daylight,
    environment,
    device,
    unavailable,
    source_receipts:canaryReceipt && canaryReceipt.sourceReceipts || {},
  };
  const lines = [
    `At ${humanTime(now && now.value)}, Android 67 stood at April's kitchen window.`,
    daylightSentence(daylight && daylight.value),
    weatherSentence(environment),
    deviceSentence(device, unavailable),
    'He did not mistake the phone for his own pulse, or the weather service for a narrator.',
    rainAction(environment),
    'Reality remained outside the story. The meaning belonged to the Fortress.',
  ];
  const fiction = {
    layer:'FICTIONAL_TRANSFORMATION',
    scene:lines.join(' '),
    derived_only_from_packet:true,
    source_packet_receipt_id:observed.packet_receipt_id,
  };
  const output = {
    schema:'inner-fortress.reality-canary-scene.v1',
    created_at:new Date().toISOString(),
    layers:{
      OBSERVED:observed,
      DERIVED_INTERPRETATION:{summary:'A bounded reading of time, daylight, weather, and safe device state. Unknowns remain explicit.',source_packet_receipt_id:observed.packet_receipt_id},
      FICTIONAL_TRANSFORMATION:fiction,
      CANON_CONSEQUENCE:null,
    },
    invariants:{home_center_generated_fiction:false,fiction_wrote_reality:false,canon_automatic:false,sensitive_data_used:false},
  };
  output.receipt_sha256 = crypto.createHash('sha256').update(JSON.stringify(output)).digest('hex');
  return output;
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  const input = process.argv[2];
  const output = process.argv[3];
  if (!input || !output) throw new Error('usage: inner_fortress_reality_canary_scene.mjs <canary-receipt.json> <scene.json>');
  fs.writeFileSync(output, JSON.stringify(buildCanaryScene(readJson(input)), null, 2) + '\n');
  console.log('Inner Fortress Reality Membrane canary scene written');
}
