import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const provider = require('../functions/hosted_speech_provider.js');
const {cartesiaVoicesOperation, createHomeCenterMcpServer, driveOperationRunOperation} = require('../functions/home_center_mcp.js');

const homeCenterSource = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
assert(homeCenterSource.includes("server.registerTool('cartesia_voices'"), 'top-level cartesia_voices tool is registered');
for (const field of ['pageToken', 'startingAfter', 'endingBefore', 'language', 'locale', 'gender', 'accent', 'country', 'includePreviewUrl']) {
  assert(homeCenterSource.includes(field), `cartesia_voices schema/capability includes ${field}`);
}
assert(!homeCenterSource.includes('CARTESIA_API_KEY.value() &&'), 'schema must not expose Cartesia API key material');

const server = createHomeCenterMcpServer({google: {}, admin: {}, googleClientId: () => '', googleClientSecret: () => '', cartesiaApiKey: () => 'test-cartesia-key'});
assert(server._registeredTools.cartesia_voices, 'MCP tool registry exposes cartesia_voices');

const oldFetch = globalThis.fetch;
const fetchCalls = [];
const catalogRows = Array.from({length: 12}, (_, index) => ({
  id: `ru-voice-${String(index + 1).padStart(2, '0')}`,
  name: `Russian Voice ${index + 1}`,
  description: 'Russian narration catalog voice',
  gender: index % 2 ? 'masculine' : 'feminine',
  language: 'ru',
  country: 'RU',
  accent: index % 2 ? 'Moscow' : 'Saint Petersburg',
  is_owner: false,
  is_public: true,
  created_at: '2026-03-31T17:37:05.961874Z',
  preview_file_url: `https://example.invalid/preview-${index + 1}.wav`,
}));

globalThis.fetch = async (url, options = {}) => {
  fetchCalls.push({url: String(url), options});
  assert.equal(options.method, 'GET');
  assert.equal(options.headers['Cartesia-Version'], '2026-03-01');
  assert.equal(options.headers['Accept'], 'application/json');
  assert.equal(options.headers.Authorization, 'Bearer test-cartesia-key');
  assert.equal(options.headers['X-API-Key'], 'test-cartesia-key');
  const parsed = new URL(String(url));
  assert.equal(parsed.origin + parsed.pathname, 'https://api.cartesia.ai/voices');
  assert.equal(parsed.searchParams.get('q'), 'Russian');
  assert.equal(parsed.searchParams.get('language'), 'ru');
  assert.equal(parsed.searchParams.get('gender'), 'feminine');
  assert.equal(parsed.searchParams.get('limit'), '100');
  assert.equal(parsed.searchParams.get('starting_after'), 'voice-page-0');
  assert.equal(parsed.searchParams.get('expand[]'), 'preview_file_url');
  return new Response(JSON.stringify({data: catalogRows, has_more: true, next_page: 'ru-voice-12'}), {status: 200, headers: {'content-type': 'application/json'}});
};

try {
  const catalog = await provider.listCartesiaVoiceCatalog({
    apiKeyGetter: () => 'test-cartesia-key',
    query: 'Russian',
    language: 'ru',
    gender: 'feminine',
    limit: 200,
    pageToken: 'voice-page-0',
  });
  assert.equal(catalog.catalog, 'provider_live');
  assert.equal(catalog.voices.length, 12, 'provider catalog is not capped to the previous ten curated voices');
  assert.equal(catalog.pagination.limit, 100, 'Cartesia provider page limit is capped to documented max');
  assert.equal(catalog.pagination.hasMore, true);
  assert.equal(catalog.pagination.nextPageToken, 'ru-voice-12');
  assert.deepEqual(catalog.supportedFilters.providerQuery, ['q', 'limit', 'starting_after', 'ending_before', 'is_owner', 'gender', 'language', 'expand[]']);

  const normalized = provider.normalizeCartesiaVoice(catalogRows[0]);
  assert.equal(normalized.id, 'ru-voice-01');
  assert.equal(normalized.voiceId, 'ru-voice-01');
  assert.equal(normalized.language, 'ru');
  assert.equal(normalized.locale, 'ru');
  assert.equal(normalized.gender, 'feminine');
  assert.equal(normalized.accent, 'Saint Petersburg');
  assert.equal(normalized.country, 'RU');
  assert.equal(normalized.metadata.preview_file_url, 'https://example.invalid/preview-1.wav');

  const result = await cartesiaVoicesOperation({
    cartesiaApiKey: () => 'test-cartesia-key',
    args: {query: 'Russian', language: 'ru', gender: 'feminine', limit: 200, pageToken: 'voice-page-0', country: 'RU'},
  });
  assert.equal(result.provider, 'cartesia');
  assert.equal(result.catalog, 'provider_live');
  assert.equal(result.voices.length, 12);
  assert.equal(result.pagination.nextPageToken, 'ru-voice-12');
  assert.equal(result.filters.language, 'ru');
  assert.equal(result.filters.country, 'RU');
  assert(result.voices.every((voice) => voice.country === 'RU'));
  assert(!JSON.stringify(result).includes('test-cartesia-key'), 'voice catalog response must not leak provider key');

  const routed = await driveOperationRunOperation({
    google: {},
    admin: {},
    auth: {},
    user: {email: 'dclarke1005@gmail.com', authKind: 'google_oauth_bearer'},
    cartesiaApiKey: () => 'test-cartesia-key',
    args: {operation: 'tts.voices', args: {query: 'Russian', language: 'ru', gender: 'feminine', limit: 200, pageToken: 'voice-page-0'}},
  });
  assert.equal(routed.completed, true);
  assert.equal(routed.result.catalog, 'provider_live');
  assert.equal(routed.result.voices.length, 12);
  assert.equal(fetchCalls.length, 1, 'same provider page uses catalog cache instead of repeated network calls');

  console.log('Cartesia voice catalog contract: OK');
} finally {
  globalThis.fetch = oldFetch;
}
