'use strict';

const dns = require('node:dns/promises');
const net = require('node:net');

const MAX_REDIRECTS = 3;
const FILE_ID_PATTERN = /^[A-Za-z0-9._:-]{3,512}$/;

function fail(message, status = 400, code = 'host_file_invalid') {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  return error;
}

function openAiFileParamJsonSchema(description = 'Required top-level ChatGPT host file.') {
  return {
    type: 'object',
    properties: {
      download_url: {type: 'string'},
      file_id: {type: 'string'},
      mime_type: {type: 'string'},
      file_name: {type: 'string'},
    },
    required: ['download_url', 'file_id'],
    additionalProperties: false,
    description,
  };
}

function openAiFileParamZodSchema(z, description = 'Required top-level ChatGPT host file.') {
  return z.object({
    download_url: z.string(),
    file_id: z.string(),
    mime_type: z.string().optional(),
    file_name: z.string().optional(),
  }).strict().describe(description);
}

function normalizeFileParam(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw fail('file must be a top-level ChatGPT host file object; paths, handles, URLs, Base64 strings, and nested descriptors are rejected.', 400, 'host_file_required');
  }
  const keys = Object.keys(value);
  const allowed = new Set(['download_url', 'file_id', 'mime_type', 'file_name']);
  if (keys.some((key) => !allowed.has(key))) {
    throw fail('file contains unsupported fields and was not accepted as a ChatGPT host file.', 400, 'host_file_schema_invalid');
  }
  const downloadUrl = typeof value.download_url === 'string' ? value.download_url.trim() : '';
  const fileId = typeof value.file_id === 'string' ? value.file_id.trim() : '';
  if (!downloadUrl || !FILE_ID_PATTERN.test(fileId)) {
    throw fail('file is missing a valid ChatGPT file_id or download_url; the attachment may be malformed or expired.', 400, 'host_file_schema_invalid');
  }
  return {
    downloadUrl,
    fileId,
    mimeType: typeof value.mime_type === 'string' ? value.mime_type.trim().slice(0, 160) : '',
    fileName: typeof value.file_name === 'string' ? value.file_name.trim().slice(0, 240) : '',
  };
}

function ipv4IsPublic(address) {
  const octets = address.split('.').map(Number);
  if (octets.length !== 4 || octets.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) return false;
  const [a, b] = octets;
  if (a === 0 || a === 10 || a === 127 || a >= 224) return false;
  if (a === 100 && b >= 64 && b <= 127) return false;
  if (a === 169 && b === 254) return false;
  if (a === 172 && b >= 16 && b <= 31) return false;
  if (a === 192 && (b === 0 || b === 168)) return false;
  if (a === 198 && (b === 18 || b === 19 || b === 51)) return false;
  if (a === 203 && b === 0) return false;
  return true;
}

function ipIsPublic(address) {
  const clean = String(address || '').toLowerCase().replace(/^\[|\]$/g, '');
  const family = net.isIP(clean);
  if (family === 4) return ipv4IsPublic(clean);
  if (family !== 6) return false;
  if (clean === '::' || clean === '::1' || clean.startsWith('fc') || clean.startsWith('fd') || /^fe[89ab]/.test(clean) || clean.startsWith('ff') || clean.startsWith('2001:db8:')) return false;
  const mapped = clean.match(/::ffff:(\d+\.\d+\.\d+\.\d+)$/);
  if (mapped) return ipv4IsPublic(mapped[1]);
  if (clean.startsWith('::ffff:') || clean.includes('.')) return false;
  return true;
}

async function assertPublicHttpsUrl(rawUrl, resolveHostname = dns.lookup) {
  let parsed;
  try { parsed = new URL(rawUrl); } catch { throw fail('ChatGPT host file download_url is invalid.', 400, 'host_file_url_invalid'); }
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password || (parsed.port && parsed.port !== '443')) {
    throw fail('ChatGPT host files require a credential-free HTTPS download_url.', 400, 'host_file_url_forbidden');
  }
  const hostname = parsed.hostname.replace(/^\[|\]$/g, '');
  let records;
  if (net.isIP(hostname)) records = [{address: hostname}];
  else {
    try { records = await resolveHostname(hostname, {all: true, verbatim: true}); }
    catch { throw fail('ChatGPT host file download host could not be resolved.', 502, 'host_file_download_unavailable'); }
  }
  if (!Array.isArray(records)) records = [records];
  if (!records.length || records.some((record) => !ipIsPublic(record && record.address))) {
    throw fail('ChatGPT host file download_url resolved to a forbidden network address.', 400, 'host_file_url_forbidden');
  }
  return parsed;
}

async function responseBytes(response, maxBytes) {
  const declared = Number(response.headers && response.headers.get && response.headers.get('content-length'));
  if (Number.isFinite(declared) && declared > maxBytes) {
    throw fail('file exceeds the configured Home Center ingest ceiling.', 413, 'host_file_too_large');
  }
  const chunks = [];
  let count = 0;
  if (response.body && typeof response.body[Symbol.asyncIterator] === 'function') {
    for await (const chunk of response.body) {
      const bytes = Buffer.from(chunk);
      count += bytes.length;
      if (count > maxBytes) throw fail('file exceeds the configured Home Center ingest ceiling.', 413, 'host_file_too_large');
      chunks.push(bytes);
    }
    return Buffer.concat(chunks, count);
  }
  const bytes = Buffer.from(await response.arrayBuffer());
  if (bytes.length > maxBytes) throw fail('file exceeds the configured Home Center ingest ceiling.', 413, 'host_file_too_large');
  return bytes;
}

async function materializeOpenAiHostFile(value, {maxBytes, fetchImpl = globalThis.fetch, resolveHostname = dns.lookup} = {}) {
  const file = normalizeFileParam(value);
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) throw new TypeError('maxBytes must be a positive safe integer.');
  if (typeof fetchImpl !== 'function') throw new TypeError('fetchImpl must be a function.');
  let currentUrl = file.downloadUrl;
  let response;
  for (let redirect = 0; redirect <= MAX_REDIRECTS; redirect += 1) {
    const parsed = await assertPublicHttpsUrl(currentUrl, resolveHostname);
    try {
      response = await fetchImpl(parsed.href, {method: 'GET', redirect: 'manual', headers: {accept: 'application/octet-stream'}});
    } catch {
      throw fail('ChatGPT host file download failed before bytes were received.', 502, 'host_file_download_unavailable');
    }
    if ([301, 302, 303, 307, 308].includes(Number(response.status))) {
      const location = response.headers && response.headers.get && response.headers.get('location');
      if (!location || redirect === MAX_REDIRECTS) throw fail('ChatGPT host file download redirect was invalid or excessive.', 502, 'host_file_download_unavailable');
      currentUrl = new URL(location, parsed).href;
      continue;
    }
    break;
  }
  if (!response || !response.ok) {
    const expired = response && [401, 403, 404, 410].includes(Number(response.status));
    throw fail(expired ? 'ChatGPT host file is unavailable or expired; attach the file again.' : 'ChatGPT host file download failed before bytes were received.', expired ? 400 : 502, expired ? 'host_file_expired' : 'host_file_download_unavailable');
  }
  const bytes = await responseBytes(response, maxBytes);
  if (!bytes.length) throw fail('file is empty.', 400, 'host_file_empty');
  const responseMime = response.headers && response.headers.get && response.headers.get('content-type') || '';
  const name = file.fileName || 'upload.bin';
  const type = file.mimeType || String(responseMime).split(';')[0].trim() || 'application/octet-stream';
  return {
    name,
    type,
    size: bytes.length,
    fileId: file.fileId,
    arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
  };
}

module.exports = {
  openAiFileParamJsonSchema,
  openAiFileParamZodSchema,
  normalizeFileParam,
  ipIsPublic,
  assertPublicHttpsUrl,
  materializeOpenAiHostFile,
};
