'use strict';

const {createHash} = require('node:crypto');

const VOICE_TIERS = Object.freeze(['utility', 'draft', 'canon']);
const TIER_RANK = Object.freeze({utility: 0, draft: 1, canon: 2});

const DEFAULT_CONFIG = Object.freeze({
  schemaVersion: 'home-center.voice-tier-policy.v1',
  revision: 'fortress-online-voice-tiers-2026-08-03',
  providers: {
    cartesia_utility: {
      provider: 'cartesia',
      modelId: 'sonic-3.5',
      enabled: true,
      configuredMarginalUsdPerSecond: 0,
      textInputUsdPerMillionTokens: 0,
      audioOutputUsdPerMillionTokens: 0,
      supportsDirection: false,
      voiceNamespace: 'cartesia',
    },
    gemini_flash: {
      provider: 'gemini',
      modelId: 'gemini-3.1-flash-tts-preview',
      enabled: true,
      configuredMarginalUsdPerSecond: 0.0005,
      textInputUsdPerMillionTokens: 1,
      audioOutputUsdPerMillionTokens: 20,
      supportsDirection: true,
      voiceNamespace: 'gemini',
    },
    gemini_pro: {
      provider: 'gemini',
      modelId: 'gemini-2.5-pro-preview-tts',
      enabled: true,
      configuredMarginalUsdPerSecond: 0.0005,
      textInputUsdPerMillionTokens: 1,
      audioOutputUsdPerMillionTokens: 20,
      supportsDirection: true,
      voiceNamespace: 'gemini',
    },
  },
  tiers: {
    utility: {purpose: ['ui', 'caption', 'captions', 'accessibility_prompt'], candidates: ['cartesia_utility', 'gemini_flash']},
    draft: {purpose: ['audition', 'auditions', 'dialogue', 'ordinary_dialogue'], primary: 'gemini_flash', fallback: ['utility']},
    canon: {purpose: ['canon', 'final', 'final_performance', 'final_performances'], primary: 'gemini_pro', fallback: ['draft', 'utility']},
  },
});

function stable(value) {
  if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + stable(value[key])).join(',') + '}';
  return JSON.stringify(value);
}

function clone(value) { return JSON.parse(JSON.stringify(value)); }

function clean(value, max = 2000) {
  return typeof value === 'string' ? value.trim().slice(0, max) : '';
}

function configError(message) {
  const error = new Error(message);
  error.status = 500;
  error.failureKind = 'voice_tier_config_invalid';
  return error;
}

function validateConfig(config) {
  if (!config || typeof config !== 'object' || Array.isArray(config)) throw configError('Voice tier configuration must be an object.');
  if (!config.providers || !config.tiers) throw configError('Voice tier configuration requires providers and tiers.');
  for (const [key, route] of Object.entries(config.providers)) {
    if (!route || !['cartesia', 'gemini'].includes(route.provider)) throw configError('Voice tier provider ' + key + ' is invalid.');
    if (!clean(route.modelId, 160)) throw configError('Voice tier provider ' + key + ' requires modelId.');
  }
  for (const tier of VOICE_TIERS) {
    if (!config.tiers[tier]) throw configError('Voice tier configuration is missing ' + tier + '.');
  }
  return config;
}

function loadVoiceTierConfig(env = process.env) {
  let config = clone(DEFAULT_CONFIG);
  const raw = clean(env.HOME_CENTER_VOICE_TIER_CONFIG_JSON, 64000);
  if (raw) {
    try { config = JSON.parse(raw); }
    catch { throw configError('HOME_CENTER_VOICE_TIER_CONFIG_JSON is not valid JSON.'); }
  }
  validateConfig(config);
  return {...config, configSha256: createHash('sha256').update(stable(config)).digest('hex')};
}

function requestedTier(args = {}, config = loadVoiceTierConfig()) {
  const explicit = clean(args.voiceTier || args.tier || args.qualityTier, 40).toLowerCase();
  if (explicit) {
    if (!VOICE_TIERS.includes(explicit)) {
      const error = new Error('voiceTier must be utility, draft, or canon.');
      error.status = 400;
      error.failureKind = 'voice_tier_invalid';
      throw error;
    }
    return explicit;
  }
  const useCase = clean(args.useCase || args.voiceUseCase || args.purpose, 80).toLowerCase();
  if (!useCase) return '';
  for (const tier of VOICE_TIERS) {
    if ((config.tiers[tier].purpose || []).map((value) => String(value).toLowerCase()).includes(useCase)) return tier;
  }
  const error = new Error('Unknown voice useCase: ' + useCase + '.');
  error.status = 400;
  error.failureKind = 'voice_tier_use_case_invalid';
  throw error;
}

function routeByKey(config, key, tier) {
  const raw = config.providers[key];
  if (!raw || raw.enabled === false) return null;
  return {...raw, key, tier};
}

function primaryRoute(tier, config = loadVoiceTierConfig()) {
  const definition = config.tiers[tier];
  if (tier === 'utility') {
    const routes = (definition.candidates || []).map((key) => routeByKey(config, key, tier)).filter(Boolean);
    routes.sort((a, b) => Number(a.configuredMarginalUsdPerSecond || 0) - Number(b.configuredMarginalUsdPerSecond || 0) || a.key.localeCompare(b.key));
    if (!routes.length) throw configError('No utility TTS provider is enabled.');
    return routes[0];
  }
  const route = routeByKey(config, definition.primary, tier);
  if (!route) throw configError('No ' + tier + ' TTS provider is enabled.');
  return route;
}

function downwardRoutes(tier, config = loadVoiceTierConfig()) {
  if (!VOICE_TIERS.includes(tier)) return [];
  const keys = [tier, ...(config.tiers[tier].fallback || [])];
  const routes = [];
  for (const candidateTier of keys) {
    if (TIER_RANK[candidateTier] > TIER_RANK[tier]) continue;
    const route = primaryRoute(candidateTier, config);
    if (!routes.some((item) => item.provider === route.provider && item.modelId === route.modelId)) routes.push(route);
  }
  return routes;
}

function isQuotaError(error) {
  const code = clean(error && (error.failureKind || error.code), 160).toLowerCase();
  const status = Number(error && error.status || 0);
  return status === 429 || /quota|rate_limit|rate-limited|budget_exceeded/.test(code);
}

function acceptedLocks(args = {}) {
  const accepted = args.humanAcceptance === 'accepted' || args.accepted === true || args.acceptedVoice === true || args.voiceAccepted === true;
  const direction = clean(args.direction || args.naturalLanguageDirection, 2000);
  return {
    acceptedVoice: accepted || args.lockVoice === true,
    acceptedDirection: accepted || args.lockDirection === true,
    voiceName: clean(args.voiceName, 160),
    voiceId: clean(args.voiceId, 200),
    direction,
  };
}

function routePreservesLocks(from, to, locks) {
  if (!locks) return {ok: true};
  if (locks.acceptedVoice && from.voiceNamespace !== to.voiceNamespace) return {ok: false, reason: 'accepted_voice_namespace_mismatch'};
  if (locks.acceptedDirection && locks.direction && to.supportsDirection !== true) return {ok: false, reason: 'accepted_direction_unsupported'};
  return {ok: true};
}

function estimateCost(route, {duration = 0, usage = null, text = ''} = {}) {
  const inputTokens = Number(usage && (usage.total_input_tokens || usage.promptTokenCount) || 0);
  const outputTokens = Number(usage && (usage.total_output_tokens || usage.candidatesTokenCount) || 0);
  const tokenCost = inputTokens * Number(route.textInputUsdPerMillionTokens || 0) / 1000000 + outputTokens * Number(route.audioOutputUsdPerMillionTokens || 0) / 1000000;
  const durationCost = Math.max(0, Number(duration || 0)) * Number(route.configuredMarginalUsdPerSecond || 0);
  return {
    estimatedUsd: Number((tokenCost || durationCost).toFixed(8)),
    basis: tokenCost ? 'provider_reported_tokens' : 'configured_marginal_usd_per_second',
    inputTokens,
    outputTokens,
    textCharacterCount: typeof text === 'string' ? text.length : 0,
  };
}

function tierReceipt({requested, rendered, config, attempts = [], queue = null}) {
  const degraded = requested !== rendered;
  return {
    schemaVersion: config.schemaVersion,
    configRevision: config.revision,
    configSha256: config.configSha256,
    requestedTier: requested,
    renderedTier: rendered,
    degraded,
    canon: requested === 'canon' && rendered === 'canon' && !degraded,
    canonEligible: requested === 'canon' && rendered === 'canon' && !degraded,
    overwriteCanonAllowed: false,
    attempts,
    canonRerenderQueue: queue,
  };
}

function publicPolicy(config = loadVoiceTierConfig()) {
  return {
    schemaVersion: config.schemaVersion,
    revision: config.revision,
    configSha256: config.configSha256,
    hierarchy: VOICE_TIERS,
    tiers: Object.fromEntries(VOICE_TIERS.map((tier) => {
      const route = primaryRoute(tier, config);
      return [tier, {purpose: config.tiers[tier].purpose || [], provider: route.provider, modelId: route.modelId, routeKey: route.key, configuredMarginalUsdPerSecond: route.configuredMarginalUsdPerSecond, downwardFallbackOnly: true}];
    })),
    safeguards: {quotaOnlyFallback: true, downwardOnly: true, degradedFallback: true, fallbackCanBeCanon: false, overwriteCanonAllowed: false, preserveAcceptedVoiceAndDirection: true, queueCanonRerender: true},
  };
}

module.exports = {
  VOICE_TIERS,
  TIER_RANK,
  DEFAULT_CONFIG,
  loadVoiceTierConfig,
  requestedTier,
  primaryRoute,
  downwardRoutes,
  isQuotaError,
  acceptedLocks,
  routePreservesLocks,
  estimateCost,
  tierReceipt,
  publicPolicy,
};
