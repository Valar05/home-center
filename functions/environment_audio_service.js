const {createHash} = require('node:crypto');
const {
  primitives: {
    decodeWav,
    encodeWav,
    trim,
    fade,
    gain,
    pan,
    biquadLike,
    limit,
    timeline,
    toChannels,
    measure,
  },
} = require('./audio_render_service');

const SCHEMA_VERSION = 'home-center.environment-audio.v1';
const ENGINE_VERSION = 'home-center-environment-audio-v1.0';

const ZONES = {
  open_beach: {exposure: 1, transmission: 1, interior: false, shelter: 0},
  shoreline: {exposure: 1, transmission: 1, interior: false, shelter: 0},
  dock: {exposure: 0.95, transmission: 1, interior: false, shelter: 0.05},
  covered_balcony: {exposure: 0.72, transmission: 1, interior: false, shelter: 0.45},
  covered_patio: {exposure: 0.68, transmission: 1, interior: false, shelter: 0.5},
  hotel_lobby: {exposure: 0, transmission: 0.16, interior: true, shelter: 1},
  hotel_room: {exposure: 0, transmission: 0.1, interior: true, shelter: 1},
  hotel_hallway: {exposure: 0, transmission: 0.035, interior: true, shelter: 1},
  bathroom: {exposure: 0, transmission: 0.015, interior: true, shelter: 1},
  vehicle: {exposure: 0, transmission: 0.07, interior: true, shelter: 1},
  sealed_interior: {exposure: 0, transmission: 0, interior: true, shelter: 1},
};

const WEATHER = {
  clear: {wind: 0.08, rain: 0, thunder: 0, storm: 0},
  windy: {wind: 0.48, rain: 0, thunder: 0, storm: 0.12},
  storm_building: {wind: 0.62, rain: 0.28, thunder: 0.16, storm: 0.56},
  storm: {wind: 0.9, rain: 0.9, thunder: 0.62, storm: 1},
  storm_passing: {wind: 0.54, rain: 0.42, thunder: 0.2, storm: 0.46},
  after_storm: {wind: 0.2, rain: 0.08, thunder: 0, storm: 0.12},
};

const OCEAN = {
  absent: {energy: 0, bedGainDb: -80, breakerGap: [999, 999], clusterChance: 0},
  calm: {energy: 0.18, bedGainDb: -25, breakerGap: [10, 24], clusterChance: 0.08},
  rolling: {energy: 0.38, bedGainDb: -20, breakerGap: [7, 17], clusterChance: 0.15},
  active: {energy: 0.58, bedGainDb: -16, breakerGap: [4.5, 12], clusterChance: 0.28},
  heavy: {energy: 0.78, bedGainDb: -12, breakerGap: [2.8, 8], clusterChance: 0.42},
  violent: {energy: 1, bedGainDb: -8, breakerGap: [1.6, 5.5], clusterChance: 0.62},
};

const DIRECT_OCEAN_ROLES = new Set([
  'ocean.far_surf',
  'ocean.breaker.small',
  'ocean.breaker.large',
  'ocean.foam',
]);

function environmentError(message, code = 'environment_audio_invalid') {
  const error = new Error(message);
  error.code = code;
  return error;
}

function stableJson(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + stableJson(value[key])).join(',') + '}';
  }
  return JSON.stringify(value);
}

function sha256Hex(value) {
  return createHash('sha256').update(value).digest('hex');
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Number(value)));
}

function hashSeed(seed) {
  const digest = createHash('sha256').update(String(seed || 'environment')).digest();
  return digest.readUInt32LE(0) || 1;
}

function createRng(seed) {
  let state = hashSeed(seed);
  return () => {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    return (state >>> 0) / 4294967296;
  };
}

function randomBetween(rng, range) {
  return range[0] + (range[1] - range[0]) * rng();
}

function choose(rng, values) {
  return values[Math.min(values.length - 1, Math.floor(rng() * values.length))];
}

function normalizeCard(input = {}) {
  const location = String(input.location || '').trim().toLowerCase();
  const weather = String(input.weather || 'clear').trim().toLowerCase();
  const oceanState = String(input.oceanState || (input.ocean && input.ocean.state) || 'rolling').trim().toLowerCase();
  if (!ZONES[location]) throw environmentError(`Unknown acoustic location: ${location || '(missing)'}.`);
  if (!WEATHER[weather]) throw environmentError(`Unknown weather state: ${weather}.`);
  if (!OCEAN[oceanState]) throw environmentError(`Unknown ocean state: ${oceanState}.`);
  const durationSeconds = clamp(input.durationSeconds || input.duration || 30, 1, 3600);
  const openings = input.openings && typeof input.openings === 'object' ? input.openings : {};
  const doorOpen = openings.door === 'open' || openings.doorOpen === true;
  const windowOpen = openings.window === 'open' || openings.windowOpen === true;
  const openingExposure = doorOpen || windowOpen ? clamp(input.openingExposure ?? 0.72, 0, 1) : 0;
  return {
    schemaVersion: SCHEMA_VERSION,
    sceneId: String(input.sceneId || 'vacation-scene'),
    seed: String(input.seed || input.sceneId || 'vacation-environment'),
    durationSeconds,
    location,
    weather,
    oceanState,
    openings: {doorOpen, windowOpen, openingExposure},
    oceanPresent: input.oceanPresent !== false && oceanState !== 'absent',
    dialogueSafe: input.dialogueSafe !== false,
    intensity: clamp(input.intensity ?? 1, 0, 1),
    transitions: Array.isArray(input.transitions) ? input.transitions : [],
  };
}

function effectiveZone(card) {
  const zone = ZONES[card.location];
  const open = card.openings.openingExposure;
  return {
    ...zone,
    exposure: clamp(zone.exposure + (1 - zone.exposure) * open, 0, 1),
    transmission: clamp(zone.transmission + (1 - zone.transmission) * open, 0, 1),
  };
}

function addEvent(events, role, at, options = {}) {
  events.push({
    eventId: `${role}-${String(events.length + 1).padStart(4, '0')}`,
    role,
    atSeconds: Number(Math.max(0, at).toFixed(4)),
    gainDb: Number((options.gainDb ?? 0).toFixed(3)),
    pan: Number((options.pan ?? 0).toFixed(3)),
    lowpassHz: options.lowpassHz || null,
    highpassHz: options.highpassHz || null,
    fadeInSeconds: options.fadeInSeconds || 0,
    fadeOutSeconds: options.fadeOutSeconds || 0,
    maxDurationSeconds: options.maxDurationSeconds || null,
    sourceOffsetRatio: options.sourceOffsetRatio ?? null,
    domain: options.domain || 'environment',
    directExterior: options.directExterior === true,
  });
}

function scheduleBed(events, rng, role, duration, gainDb, options = {}) {
  const chunk = options.chunkSeconds || 12;
  const overlap = options.overlapSeconds || 2.5;
  let at = 0;
  while (at < duration) {
    addEvent(events, role, at, {
      ...options,
      gainDb: gainDb + randomBetween(rng, [-1.2, 1.2]),
      pan: randomBetween(rng, [-0.12, 0.12]),
      fadeInSeconds: Math.min(1.5, overlap / 2),
      fadeOutSeconds: Math.min(2, overlap / 2),
      maxDurationSeconds: Math.min(chunk, duration - at + overlap),
      sourceOffsetRatio: rng(),
    });
    at += Math.max(1, chunk - overlap + randomBetween(rng, [-1.3, 1.3]));
  }
}

function scheduleBreakers(events, rng, card, zone, ocean, weather) {
  if (!card.oceanPresent || zone.exposure <= 0) return;
  let at = randomBetween(rng, [0.8, Math.min(4, ocean.breakerGap[1])]);
  while (at < card.durationSeconds) {
    const stormLift = weather.storm * 0.28;
    const largeChance = clamp(0.08 + ocean.energy * 0.38 + stormLift, 0, 0.82);
    const large = rng() < largeChance;
    const role = large ? 'ocean.breaker.large' : 'ocean.breaker.small';
    const gainDb = -15 + ocean.energy * 8 + weather.storm * 3 + randomBetween(rng, [-2.2, 1.8]);
    addEvent(events, role, at, {
      gainDb,
      pan: randomBetween(rng, [-0.7, 0.7]),
      domain: 'ocean',
      directExterior: true,
    });
    const foamDelay = randomBetween(rng, [0.18, large ? 0.65 : 0.42]);
    addEvent(events, 'ocean.foam', at + foamDelay, {
      gainDb: gainDb - randomBetween(rng, [4, 8]),
      pan: randomBetween(rng, [-0.8, 0.8]),
      maxDurationSeconds: randomBetween(rng, [1.3, large ? 4.6 : 3]),
      fadeOutSeconds: randomBetween(rng, [0.4, 1.4]),
      domain: 'ocean',
      directExterior: true,
    });
    if (rng() < ocean.clusterChance) {
      at += randomBetween(rng, [0.55, 1.8]);
    } else {
      const compressed = [
        ocean.breakerGap[0] * (1 - weather.storm * 0.35),
        ocean.breakerGap[1] * (1 - weather.storm * 0.28),
      ];
      at += randomBetween(rng, compressed);
    }
  }
}

function scheduleStorm(events, rng, card, zone, weather) {
  const exteriorGain = -18 + zone.exposure * 11;
  const transmittedGain = -31 + zone.transmission * 13;
  if (weather.wind > 0.1) {
    scheduleBed(events, rng, 'weather.wind', card.durationSeconds, zone.interior ? transmittedGain : exteriorGain, {
      chunkSeconds: 14,
      overlapSeconds: 3.5,
      lowpassHz: zone.interior ? 950 : null,
      domain: 'weather',
      directExterior: !zone.interior,
    });
  }
  if (weather.rain > 0.05) {
    const role = zone.interior ? 'weather.rain.structure' : 'weather.rain.exterior';
    scheduleBed(events, rng, role, card.durationSeconds, (zone.interior ? -25 : -16) + weather.rain * 7, {
      chunkSeconds: 11,
      overlapSeconds: 2.8,
      lowpassHz: zone.interior ? 5200 : null,
      domain: 'weather',
      directExterior: !zone.interior,
    });
    if (zone.interior && weather.storm > 0.45) {
      let rattleAt = randomBetween(rng, [5, 14]);
      while (rattleAt < card.durationSeconds) {
        addEvent(events, 'architecture.window_rattle', rattleAt, {
          gainDb: -25 + weather.storm * 7 + randomBetween(rng, [-2, 2]),
          pan: randomBetween(rng, [-0.35, 0.35]),
          domain: 'architecture',
        });
        rattleAt += randomBetween(rng, [10, 31]);
      }
    }
  }
  if (weather.thunder > 0.05) {
    let thunderAt = randomBetween(rng, [5, 18]);
    while (thunderAt < card.durationSeconds) {
      addEvent(events, zone.interior ? 'weather.thunder.muffled' : 'weather.thunder.exterior', thunderAt, {
        gainDb: (zone.interior ? -24 : -13) + weather.thunder * 6 + randomBetween(rng, [-2, 2]),
        lowpassHz: zone.interior ? 900 : null,
        pan: randomBetween(rng, [-0.7, 0.7]),
        domain: 'weather',
        directExterior: !zone.interior,
      });
      thunderAt += randomBetween(rng, [14, 42]) / Math.max(0.4, weather.thunder);
    }
  }
}

function scheduleTransitions(events, card) {
  for (const transition of card.transitions) {
    const at = clamp(transition.atSeconds ?? transition.at ?? 0, 0, card.durationSeconds);
    const type = String(transition.type || '').toLowerCase();
    if (type === 'door_open' || type === 'window_open') {
      addEvent(events, 'transition.exterior_bloom', at, {gainDb: -8, fadeInSeconds: 0.18, domain: 'transition'});
    } else if (type === 'door_close' || type === 'window_close' || type === 'enter_interior') {
      addEvent(events, 'transition.exterior_cut', at, {gainDb: -10, fadeOutSeconds: 0.22, domain: 'transition'});
    }
  }
}

function planEnvironment(input = {}) {
  const card = normalizeCard(input);
  const zone = effectiveZone(card);
  const weather = WEATHER[card.weather];
  const ocean = OCEAN[card.oceanState];
  const rng = createRng(`${card.seed}:${stableJson(card)}`);
  const events = [];

  if (card.oceanPresent && zone.exposure > 0) {
    scheduleBed(events, rng, 'ocean.far_surf', card.durationSeconds, ocean.bedGainDb + (1 - zone.exposure) * -8, {
      chunkSeconds: 13,
      overlapSeconds: 3.2,
      lowpassHz: zone.exposure < 0.5 ? 1800 : null,
      domain: 'ocean',
      directExterior: true,
    });
    scheduleBreakers(events, rng, card, zone, ocean, weather);
  } else if (card.oceanPresent && zone.transmission > 0) {
    scheduleBed(events, rng, 'ocean.transmitted_rumble', card.durationSeconds, -34 + zone.transmission * 14 + ocean.energy * 5, {
      chunkSeconds: 16,
      overlapSeconds: 4,
      lowpassHz: 420 + zone.transmission * 500,
      domain: 'ocean',
      directExterior: false,
    });
  }

  scheduleStorm(events, rng, card, zone, weather);
  scheduleTransitions(events, card);
  events.sort((a, b) => a.atSeconds - b.atSeconds || a.eventId.localeCompare(b.eventId));

  if (zone.interior && card.openings.openingExposure === 0) {
    const illegal = events.filter((event) => DIRECT_OCEAN_ROLES.has(event.role));
    if (illegal.length) throw environmentError('Sealed interior plan leaked direct ocean events.', 'environment_audio_physics_violation');
  }

  const plan = {
    schemaVersion: SCHEMA_VERSION,
    engineVersion: ENGINE_VERSION,
    card,
    acousticTruth: {
      zone,
      directOceanAllowed: zone.exposure > 0,
      transmittedOceanAllowed: zone.transmission > 0,
      physicsAuthority: 'location_and_openings_before_emotional_direction',
    },
    events,
    unresolvedRoles: [],
    humanAcceptance: 'unreviewed',
  };
  plan.planSha256 = sha256Hex(Buffer.from(stableJson(plan), 'utf8'));
  return plan;
}

function decodeAsset(value, role) {
  if (!value) return null;
  if (Buffer.isBuffer(value)) return decodeWav(value);
  if (value.bytes && Buffer.isBuffer(value.bytes)) return decodeWav(value.bytes);
  if (value.channels && value.sampleRate) return value;
  throw environmentError(`Asset ${role} must be a WAV Buffer or decoded clip.`, 'environment_audio_asset_invalid');
}

function materializeEvent(event, source, outputSampleRate) {
  let clip = toChannels(source, 2);
  const maxDuration = event.maxDurationSeconds || clip.duration;
  const wanted = Math.min(maxDuration, clip.duration);
  const maxStart = Math.max(0, clip.duration - wanted);
  const offset = event.sourceOffsetRatio === null ? 0 : maxStart * event.sourceOffsetRatio;
  clip = trim(clip, offset, wanted);
  if (clip.sampleRate !== outputSampleRate) {
    throw environmentError(`Asset sample rate ${clip.sampleRate} does not match ${outputSampleRate}.`, 'environment_audio_sample_rate_mismatch');
  }
  if (event.lowpassHz) clip = biquadLike(clip, 'lowpass', event.lowpassHz);
  if (event.highpassHz) clip = biquadLike(clip, 'highpass', event.highpassHz);
  if (event.fadeInSeconds) clip = fade(clip, Math.min(event.fadeInSeconds, clip.duration / 2), 'in');
  if (event.fadeOutSeconds) clip = fade(clip, Math.min(event.fadeOutSeconds, clip.duration / 2), 'out');
  clip = gain(clip, event.gainDb);
  if (event.pan) clip = pan(clip, event.pan);
  return clip;
}

function renderEnvironment(input = {}) {
  const plan = input.plan || planEnvironment(input.card || input);
  const assets = input.assets && typeof input.assets === 'object' ? input.assets : {};
  const decoded = new Map();
  for (const [role, value] of Object.entries(assets)) decoded.set(role, decodeAsset(value, role));
  const sampleRate = input.sampleRate || [...decoded.values()][0]?.sampleRate || 48000;
  const items = [];
  const unresolvedRoles = new Set();
  for (const event of plan.events) {
    const source = decoded.get(event.role);
    if (!source) {
      unresolvedRoles.add(event.role);
      continue;
    }
    const clip = materializeEvent(event, source, sampleRate);
    items.push({clip, at: event.atSeconds, gainDb: 0, pan: 0});
  }
  if (input.requireAllAssets === true && unresolvedRoles.size) {
    throw environmentError(`Missing source-backed environment assets: ${[...unresolvedRoles].sort().join(', ')}`, 'environment_audio_assets_missing');
  }
  let mixed = timeline({
    duration: plan.card.durationSeconds,
    sampleRate,
    channels: 2,
    items,
  });
  mixed = limit(mixed, input.ceilingDb ?? -1);
  const wavBytes = encodeWav(mixed);
  const metrics = measure(mixed);
  const manifest = {
    schemaVersion: SCHEMA_VERSION,
    engineVersion: ENGINE_VERSION,
    planSha256: plan.planSha256,
    renderedEventCount: items.length,
    plannedEventCount: plan.events.length,
    unresolvedRoles: [...unresolvedRoles].sort(),
    durationSeconds: mixed.duration,
    sampleRate: mixed.sampleRate,
    channels: mixed.channelCount,
    peak: metrics.peak,
    clippingCount: metrics.clippingCount,
    silent: metrics.silent,
    outputSha256: sha256Hex(wavBytes),
    sourceBackedOnly: true,
    oscillatorMaterialIdentityUsed: false,
    humanAcceptance: 'unreviewed',
  };
  return {plan: {...plan, unresolvedRoles: manifest.unresolvedRoles}, manifest, wavBytes};
}

module.exports = {
  SCHEMA_VERSION,
  ENGINE_VERSION,
  ZONES,
  WEATHER,
  OCEAN,
  planEnvironment,
  renderEnvironment,
  internals: {
    stableJson,
    createRng,
    normalizeCard,
    effectiveZone,
    DIRECT_OCEAN_ROLES,
  },
};
