const CARTESIA_VERSION = '2026-03-01';
const CARTESIA_DEFAULT_MODEL_ID = 'sonic-3.5';
const CARTESIA_KATIE_VOICE_ID = 'f786b574-daa5-4673-aa0c-cbe3e8534c02';
const CARTESIA_KATIE_VOICE_NAME = 'Katie - Friendly Fixer';
const CARTESIA_DEFAULT_VOICE_NAME = CARTESIA_KATIE_VOICE_NAME;
const CARTESIA_LEGACY_NARRATOR_ALIASES = new Set(['cartesia narrator', 'narrator', 'she-raw', 'sheraw']);

const CARTESIA_VOICE_PAGE_LIMIT_DEFAULT = 100;
const CARTESIA_VOICE_PAGE_LIMIT_MAX = 100;
const CARTESIA_VOICE_SUPPORTED_PROVIDER_FILTERS = Object.freeze([
  'q',
  'limit',
  'starting_after',
  'ending_before',
  'is_owner',
  'gender',
  'language',
  'expand[]',
]);
const CARTESIA_VOICE_METADATA_FIELDS = Object.freeze([
  'id',
  'name',
  'description',
  'gender',
  'language',
  'locale',
  'accent',
  'country',
  'is_owner',
  'is_public',
  'created_at',
  'updated_at',
  'preview_file_url',
]);

const cachedCartesiaVoiceCatalogs = new Map();

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function cartesiaApiKey(options = {}) {
  const supplied = safeText(options.apiKey, 500);
  if (supplied) return supplied;
  if (typeof options.apiKeyGetter === 'function') {
    const fromGetter = safeText(options.apiKeyGetter(), 500);
    if (fromGetter) return fromGetter;
  }
  return safeText(process.env.CARTESIA_API_KEY, 500);
}

function safeBool(value) {
  if (value === true || value === false) return value;
  const text = safeText(value, 20).toLowerCase();
  if (text === 'true' || text === '1' || text === 'yes') return true;
  if (text === 'false' || text === '0' || text === 'no') return false;
  return null;
}

function cartesiaVoicePageLimit(value, fallback = CARTESIA_VOICE_PAGE_LIMIT_DEFAULT) {
  const raw = Number(value || fallback);
  return Math.max(1, Math.min(CARTESIA_VOICE_PAGE_LIMIT_MAX, Number.isFinite(raw) ? Math.floor(raw) : fallback));
}

function cartesiaVoiceCatalogRequest(options = {}) {
  const q = safeText(options.q || options.query, 240);
  const language = safeText(options.language || options.locale, 40);
  const gender = safeText(options.gender, 40);
  const startingAfter = safeText(options.startingAfter || options.starting_after || options.pageToken || options.cursor, 160);
  const endingBefore = safeText(options.endingBefore || options.ending_before, 160);
  const includePreviewUrl = options.includePreviewUrl !== false;
  const params = new URLSearchParams();
  const limit = cartesiaVoicePageLimit(options.limit);
  params.set('limit', String(limit));
  if (q) params.set('q', q);
  if (language) params.set('language', language);
  if (gender) params.set('gender', gender);
  if (startingAfter) params.set('starting_after', startingAfter);
  if (endingBefore) params.set('ending_before', endingBefore);
  const ownerValue = options.isOwner !== undefined ? options.isOwner : options.is_owner;
  const isOwner = safeBool(ownerValue);
  if (isOwner !== null) params.set('is_owner', String(isOwner));
  if (includePreviewUrl) params.append('expand[]', 'preview_file_url');
  return {q, language, gender, startingAfter, endingBefore, isOwner, limit, includePreviewUrl, params};
}

function cartesiaVoiceRows(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload && payload.voices)) return payload.voices;
  if (Array.isArray(payload && payload.data)) return payload.data;
  return [];
}

function normalizeCartesiaPagination(payload, request) {
  const hasMore = Boolean(payload && (payload.has_more || payload.hasMore));
  const nextPage = safeText(payload && (payload.next_page || payload.nextPage || payload.next || payload.next_cursor), 160);
  return {
    limit: request.limit,
    startingAfter: request.startingAfter,
    endingBefore: request.endingBefore,
    nextPage: nextPage || null,
    nextPageToken: nextPage || null,
    hasMore,
  };
}

function cartesiaVoiceCatalogCacheKey(request) {
  return request.params.toString();
}

async function listCartesiaVoiceCatalog(options = {}) {
  const request = cartesiaVoiceCatalogRequest(options);
  const cacheKey = cartesiaVoiceCatalogCacheKey(request);
  const now = Date.now();
  const cached = cachedCartesiaVoiceCatalogs.get(cacheKey);
  if (cached && now - cached.atMs < 5 * 60 * 1000) return cached.catalog;

  const apiKey = cartesiaApiKey(options);
  if (!apiKey) throw new Error('Cartesia API key is not configured');
  const url = `https://api.cartesia.ai/voices?${request.params.toString()}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'X-API-Key': apiKey,
      'Cartesia-Version': CARTESIA_VERSION,
      'Accept': 'application/json',
    },
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Cartesia voices HTTP ${response.status}${detail ? `: ${safeText(detail, 500)}` : ''}`);
  }
  const payload = await response.json();
  const catalog = {
    provider: 'cartesia',
    catalog: 'provider_live',
    filters: {
      query: request.q,
      language: request.language,
      locale: request.language,
      gender: request.gender,
      isOwner: request.isOwner,
    },
    supportedFilters: {
      providerQuery: [...CARTESIA_VOICE_SUPPORTED_PROVIDER_FILTERS],
      metadata: ['accent', 'country', 'locale'],
    },
    pagination: normalizeCartesiaPagination(payload, request),
    voices: cartesiaVoiceRows(payload),
  };
  cachedCartesiaVoiceCatalogs.set(cacheKey, {atMs: now, catalog});
  return catalog;
}

async function listCartesiaVoices(options = {}) {
  const catalog = await listCartesiaVoiceCatalog(options);
  return catalog.voices;
}
function cartesiaVoiceMetadata(voice, labels) {
  const metadata = {};
  for (const field of CARTESIA_VOICE_METADATA_FIELDS) {
    if (voice && voice[field] !== undefined && voice[field] !== null && typeof voice[field] !== 'object') metadata[field] = voice[field];
  }
  if (voice && voice.previewFileUrl && !metadata.preview_file_url) metadata.preview_file_url = voice.previewFileUrl;
  if (labels && Object.keys(labels).length) metadata.labels = labels;
  return metadata;
}

function normalizeCartesiaVoice(voice) {
  const labels = voice && voice.labels && typeof voice.labels === 'object' ? voice.labels : {};
  const id = voice && (voice.id || voice.voice_id);
  const name = voice && (voice.name || voice.display_name);
  const language = voice && (voice.language || voice.locale || labels.language || labels.locale);
  const locale = voice && (voice.locale || voice.language_locale || labels.locale || labels.language_locale || language);
  const gender = voice && (voice.gender || labels.gender);
  const accent = voice && (voice.accent || labels.accent);
  const country = voice && (voice.country || labels.country);
  const description = voice && (voice.description || voice.use_case || labels.description || gender || accent || country);
  const previewUrl = voice && (voice.preview_file_url || voice.previewFileUrl || voice.preview_url || voice.previewUrl);
  return {
    voiceId: safeText(id, 160),
    id: safeText(id, 160),
    name: safeText(name, 120),
    category: safeText((voice && (voice.category || voice.type || voice.use_case)) || 'cartesia', 80),
    description: safeText(description, 500),
    language: safeText(language, 40),
    locale: safeText(locale, 40),
    gender: safeText(gender, 40),
    accent: safeText(accent, 80),
    country: safeText(country, 80),
    isOwner: Boolean(voice && (voice.is_owner || voice.isOwner)),
    isPublic: Boolean(voice && (voice.is_public || voice.isPublic)),
    previewUrl: safeText(previewUrl, 500),
    labels,
    metadata: cartesiaVoiceMetadata(voice, labels),
  };
}

async function resolveCartesiaVoice(voiceName, voiceId, options = {}) {
  const explicitVoiceId = safeText(voiceId, 160);
  if (explicitVoiceId) return {voiceId: explicitVoiceId, voiceName: safeText(voiceName || CARTESIA_DEFAULT_VOICE_NAME, 120) || CARTESIA_DEFAULT_VOICE_NAME};
  const explicitVoiceName = safeText(voiceName, 120);
  const envVoiceId = safeText(process.env.CARTESIA_VOICE_ID || process.env.CARTESIA_DEFAULT_VOICE_ID, 160);
  if (!explicitVoiceName && envVoiceId) {
    return {voiceId: envVoiceId, voiceName: safeText(process.env.CARTESIA_VOICE_NAME || CARTESIA_DEFAULT_VOICE_NAME, 120) || CARTESIA_DEFAULT_VOICE_NAME};
  }
  const requestedLabel = explicitVoiceName || safeText(process.env.CARTESIA_VOICE_NAME || CARTESIA_DEFAULT_VOICE_NAME, 120) || CARTESIA_DEFAULT_VOICE_NAME;
  const requestedName = requestedLabel.toLowerCase();
  if (requestedName === CARTESIA_DEFAULT_VOICE_NAME.toLowerCase()) {
    return {voiceId: CARTESIA_KATIE_VOICE_ID, voiceName: CARTESIA_DEFAULT_VOICE_NAME};
  }
  if (CARTESIA_LEGACY_NARRATOR_ALIASES.has(requestedName)) {
    return {voiceId: CARTESIA_KATIE_VOICE_ID, voiceName: CARTESIA_DEFAULT_VOICE_NAME};
  }
  const voices = await listCartesiaVoices(options);
  const normalized = voices.map(normalizeCartesiaVoice).filter((voice) => voice.voiceId);
  const exact = normalized.find((voice) => voice.name.toLowerCase() === requestedName);
  if (exact) return {voiceId: exact.voiceId, voiceName: exact.name};
  if (explicitVoiceName) throw new Error(`cartesia_voice_not_found: ${requestedLabel}`);
  const defaultExact = normalized.find((voice) => voice.name.toLowerCase() === CARTESIA_DEFAULT_VOICE_NAME.toLowerCase());
  if (defaultExact) return {voiceId: defaultExact.voiceId, voiceName: defaultExact.name};
  throw new Error(`cartesia_voice_not_found: ${CARTESIA_DEFAULT_VOICE_NAME}`);
}

function cartesiaOutputFormat(options = {}) {
  const format = safeText(options.format || options.container || 'raw', 20).toLowerCase();
  const sampleRate = Math.max(8000, Math.min(48000, Math.floor(Number(options.sampleRate || 24000)) || 24000));
  if (format === 'wav' || format === 'wave') {
    return {container: 'wav', encoding: 'pcm_s16le', sample_rate: sampleRate};
  }
  if (format === 'raw' || format === 'pcm') {
    return {container: 'raw', encoding: 'pcm_s16le', sample_rate: sampleRate};
  }
  const err = new Error(`unsupported_cartesia_audio_format: ${format}`);
  err.status = 400;
  throw err;
}

async function openCartesiaStream(text, options = {}) {
  const apiKey = cartesiaApiKey(options);
  if (!apiKey) throw new Error('Cartesia API key is not configured');
  const requestedVoiceName = safeText(options.voiceName || process.env.CARTESIA_VOICE_NAME || CARTESIA_DEFAULT_VOICE_NAME, 120) || CARTESIA_DEFAULT_VOICE_NAME;
  const resolvedVoice = await resolveCartesiaVoice(requestedVoiceName, options.voiceId, {apiKey});
  const voiceName = resolvedVoice.voiceName || requestedVoiceName || CARTESIA_DEFAULT_VOICE_NAME;
  const voiceId = resolvedVoice.voiceId;
  const modelId = safeText(options.modelId || process.env.CARTESIA_MODEL_ID || CARTESIA_DEFAULT_MODEL_ID, 120) || CARTESIA_DEFAULT_MODEL_ID;
  const outputFormat = cartesiaOutputFormat(options.outputFormat || options);
  const generationConfig = options.generationConfig && typeof options.generationConfig === 'object' && !Array.isArray(options.generationConfig)
    ? Object.fromEntries(Object.entries(options.generationConfig).filter(([, value]) => value !== undefined && value !== null && value !== ''))
    : {};
  const body = {
    model_id: modelId,
    transcript: text,
    voice: {mode: 'id', id: voiceId},
    output_format: outputFormat,
  };
  if (Object.keys(generationConfig).length) body.generation_config = generationConfig;
  return {
    voiceName,
    voiceId,
    modelId,
    outputFormat,
    generationConfig,
    response: await fetch('https://api.cartesia.ai/tts/bytes', {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey,
        'Cartesia-Version': CARTESIA_VERSION,
        'Accept': 'application/octet-stream',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    }),
  };
}

module.exports = {
  CARTESIA_VERSION,
  CARTESIA_DEFAULT_MODEL_ID,
  CARTESIA_DEFAULT_VOICE_NAME,
  listCartesiaVoiceCatalog,
  listCartesiaVoices,
  normalizeCartesiaVoice,
  openCartesiaStream,
  resolveCartesiaVoice,
};
