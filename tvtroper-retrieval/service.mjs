import http from 'node:http';
import {randomUUID} from 'node:crypto';

const project = process.env.GCP_PROJECT || 'home-center-dclar';
const bucket = process.env.GCS_BUCKET || 'home-center-dclar-hyperbolic-corpus';
const archiveObject = process.env.GCS_ARCHIVE_OBJECT || 'source/huggingface.co/datasets/RyokoExtra/TvTroper/resolve/main/pages.zip';
const dataset = process.env.BQ_DATASET || 'hyperbolic_corpus';
const table = process.env.BQ_TABLE || 'tvtroper_records';
const port = Number(process.env.PORT || 8080);
const bootId = randomUUID();
const bootedAt = new Date().toISOString();
let tokenCache = {token: '', expiresAt: 0};

function safeInteger(value, fallback, min, max) { const n = Math.floor(Number(value)); return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback; }
function json(res, status, payload) { const body = JSON.stringify(payload); res.writeHead(status, {'content-type': 'application/json; charset=utf-8', 'content-length': Buffer.byteLength(body), 'cache-control': 'no-store'}); res.end(body); }
async function readBody(req) { const chunks = []; let size = 0; for await (const chunk of req) { size += chunk.length; if (size > 1024 * 1024) throw Object.assign(new Error('request_too_large'), {status: 413}); chunks.push(chunk); } return chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {}; }

async function accessToken() {
  if (tokenCache.token && tokenCache.expiresAt > Date.now() + 60000) return tokenCache.token;
  const response = await fetch('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token', {headers: {'Metadata-Flavor': 'Google'}});
  if (!response.ok) throw new Error('metadata_token_failed:' + response.status);
  const payload = await response.json();
  tokenCache = {token: payload.access_token, expiresAt: Date.now() + Number(payload.expires_in || 300) * 1000};
  return tokenCache.token;
}

async function googleFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set('Authorization', 'Bearer ' + await accessToken());
  const response = await fetch(url, {...options, headers});
  if (!response.ok) throw new Error('google_fetch_failed:' + response.status + ':' + (await response.text()).slice(0, 1000));
  return response;
}

async function bqQuery(query, parameters = {}) {
  const queryParameters = Object.entries(parameters).map(([name, value]) => typeof value === 'number' ? {name, parameterType: {type: 'INT64'}, parameterValue: {value: String(value)}} : {name, parameterType: {type: 'STRING'}, parameterValue: {value: String(value)}});
  const response = await googleFetch('https://bigquery.googleapis.com/bigquery/v2/projects/' + encodeURIComponent(project) + '/queries', {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({query, useLegacySql: false, parameterMode: 'NAMED', queryParameters, timeoutMs: 30000, useQueryCache: true})});
  const payload = await response.json();
  if (!payload.jobComplete) throw new Error('bigquery_query_timeout');
  const fields = payload.schema?.fields || [];
  return (payload.rows || []).map((row) => Object.fromEntries(fields.map((field, index) => [field.name, row.f[index]?.v ?? null])));
}

const qualified = String.fromCharCode(96) + project + '.' + dataset + '.' + table + String.fromCharCode(96);
async function search(query, limit) {
  const sql = 'SELECT record_id, source_url, title, namespace, page_name, zip_entry, line_number, LEFT(search_text, 700) AS snippet FROM ' + qualified + ' WHERE SEARCH(search_text, @query) ORDER BY CASE WHEN LOWER(title)=LOWER(@query) THEN 0 WHEN STARTS_WITH(LOWER(title), LOWER(@query)) THEN 1 ELSE 2 END, title LIMIT @limit';
  const rows = await bqQuery(sql, {query, limit});
  return rows.map((row) => ({...row, line_number: Number(row.line_number), snippet: String(row.snippet || '').replace(/\s+/g, ' ').trim()}));
}

async function getRecord(recordId) {
  if (!/^[a-f0-9]{32}$/.test(recordId)) throw Object.assign(new Error('invalid_record_id'), {status: 400});
  const sql = 'SELECT record_id, source_url, title, namespace, page_name, zip_entry, line_number, crc32, archive_generation, html FROM ' + qualified + ' WHERE record_id=@recordId LIMIT 1';
  const rows = await bqQuery(sql, {recordId});
  if (!rows.length) throw Object.assign(new Error('record_not_found'), {status: 404});
  const record = rows[0];
  return {record_id: record.record_id, title: record.title, source_url: record.source_url, html: record.html, provenance: {archive: 'gs://' + bucket + '/' + archiveObject, archive_generation: record.archive_generation, zip_entry: record.zip_entry, line_number: Number(record.line_number), crc32: record.crc32, full_record_store: 'BigQuery loaded from GCS index/v2 shards'}};
}

const server = http.createServer(async (req, res) => {
  const requestId = req.headers['x-cloud-trace-context']?.split('/')[0] || randomUUID();
  try {
    const url = new URL(req.url, 'http://localhost');
    if (req.method === 'GET' && url.pathname === '/health') return json(res, 200, {ok: true, service: 'tvtroper-retrieval', boot_id: bootId, booted_at: bootedAt, archive: 'gs://' + bucket + '/' + archiveObject, table: project + '.' + dataset + '.' + table});
    if (req.method === 'POST' && url.pathname === '/search') {
      const body = await readBody(req);
      const query = String(body.query || '').trim();
      if (query.length < 2 || query.length > 500) throw Object.assign(new Error('query_must_be_2_to_500_characters'), {status: 400});
      const results = await search(query, safeInteger(body.limit, 8, 1, 20));
      return json(res, 200, {query, count: results.length, results, request_id: requestId, boot_id: bootId});
    }
    if (req.method === 'POST' && url.pathname === '/get') {
      const body = await readBody(req);
      const result = await getRecord(String(body.record_id || '').trim());
      return json(res, 200, {...result, request_id: requestId, boot_id: bootId});
    }
    return json(res, 404, {error: 'not_found', request_id: requestId});
  } catch (error) {
    console.error(JSON.stringify({event: 'request_failed', request_id: requestId, message: error.message, stack: error.stack}));
    return json(res, error.status || 500, {error: error.message || 'internal_error', request_id: requestId, boot_id: bootId});
  }
});
server.listen(port, '0.0.0.0', () => console.log(JSON.stringify({event: 'service_started', port, boot_id: bootId, booted_at: bootedAt})));
