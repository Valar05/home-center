'use strict';

const dns = require('node:dns/promises');
const net = require('node:net');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {createHash, randomUUID} = require('node:crypto');
const {Readable, Transform} = require('node:stream');
const {pipeline} = require('node:stream/promises');

const MAX_REDIRECTS = 3;
const FILE_ID_PATTERN = /^[A-Za-z0-9._:-]{3,512}$/;

function fail(message, status = 400, code = 'host_file_invalid') {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  return error;
}

function openAiFileParamJsonSchema(description = 'Required top-level ChatGPT host file.') {
  const objectSchema = {
    type: 'object',
    properties: {
      download_url: {type: 'string'},
      file_url: {type: 'string'},
      image_url: {type: 'string'},
      url: {type: 'string'},
      file_id: {type: 'string'},
      id: {type: 'string'},
      mime_type: {type: 'string'},
      mimeType: {type: 'string'},
      content_type: {type: 'string'},
      file_name: {type: 'string'},
      filename: {type: 'string'},
      name: {type: 'string'},
      type: {type: 'string'},
      detail: {type: 'string'},
      size: {type: 'number'},
      bytes: {type: 'number'},
    },
    anyOf: [{required: ['download_url']}, {required: ['file_url']}, {required: ['image_url']}, {required: ['url']}],
    additionalProperties: false,
  };
  return {anyOf: [objectSchema, {type: 'array', minItems: 1, maxItems: 1, items: objectSchema}], description};
}

function openAiFileParamZodSchema(z, description = 'Required top-level ChatGPT host file.') {
  const object = z.object({
    download_url: z.string().optional(),
    file_url: z.string().optional(),
    image_url: z.string().optional(),
    url: z.string().optional(),
    file_id: z.string().optional(),
    id: z.string().optional(),
    mime_type: z.string().optional(),
    mimeType: z.string().optional(),
    content_type: z.string().optional(),
    file_name: z.string().optional(),
    filename: z.string().optional(),
    name: z.string().optional(),
    type: z.string().optional(),
    detail: z.string().optional(),
    size: z.number().optional(),
    bytes: z.number().optional(),
  }).strict().refine((value) => Boolean(value.download_url || value.file_url || value.image_url || value.url), {message: 'A host file URL is required.'});
  return z.union([object, z.array(object).length(1)]).describe(description);
}

function normalizeFileParam(value) {
  if (Array.isArray(value) && value.length === 1) value = value[0];
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw fail('file must be a top-level ChatGPT host file object; paths, handles, URLs, Base64 strings, and nested descriptors are rejected.', 400, 'host_file_required');
  }
  const keys = Object.keys(value);
  const allowed = new Set(['download_url', 'file_url', 'image_url', 'url', 'file_id', 'id', 'mime_type', 'mimeType', 'content_type', 'file_name', 'filename', 'name', 'type', 'detail', 'size', 'bytes']);
  if (keys.some((key) => !allowed.has(key))) {
    throw fail('file contains unsupported fields and was not accepted as a ChatGPT host file.', 400, 'host_file_schema_invalid');
  }
  const downloadUrl = [value.download_url, value.file_url, value.image_url, value.url].find((candidate) => typeof candidate === 'string' && candidate.trim()) || '';
  const suppliedFileId = [value.file_id, value.id].find((candidate) => typeof candidate === 'string' && candidate.trim()) || '';
  const fileId = suppliedFileId.trim() || ('url-' + createHash('sha256').update(String(downloadUrl).trim()).digest('hex').slice(0, 32));
  if (!downloadUrl.trim() || !FILE_ID_PATTERN.test(fileId)) {
    throw fail('file is missing a valid ChatGPT file URL or file identifier; the attachment may be malformed or expired.', 400, 'host_file_schema_invalid');
  }
  const discriminator = typeof value.type === 'string' ? value.type.trim() : '';
  const typeMime = discriminator.includes('/') ? discriminator : '';
  return {
    downloadUrl: downloadUrl.trim(),
    fileId,
    mimeType: String(value.mime_type || value.mimeType || value.content_type || typeMime || '').trim().slice(0, 160),
    fileName: String(value.file_name || value.filename || value.name || '').trim().slice(0, 240),
    inputKind: discriminator === 'input_image' ? 'photo' : discriminator === 'input_file' ? 'binary' : 'host_file',
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

async function openHostFileResponse(value, {maxBytes, fetchImpl = globalThis.fetch, resolveHostname = dns.lookup} = {}) {
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
  const declared = Number(response.headers && response.headers.get && response.headers.get('content-length'));
  if (Number.isFinite(declared) && declared > maxBytes) {
    throw fail('file exceeds the configured Home Center ingest ceiling.', 413, 'host_file_too_large');
  }
  return {file, response};
}

async function materializeOpenAiHostFile(value, options = {}) {
  const {maxBytes} = options;
  const {file, response} = await openHostFileResponse(value, options);
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

async function materializeOpenAiHostFileToTemp(value, options = {}) {
  const {maxBytes, tempDir = os.tmpdir()} = options;
  const {file, response} = await openHostFileResponse(value, options);
  const tempPath = path.join(tempDir, 'home-center-host-file-' + randomUUID() + '.part');
  const hash = createHash('sha256');
  let count = 0;
  const source = response.body && typeof response.body[Symbol.asyncIterator] === 'function'
    ? Readable.from(response.body)
    : Readable.from([Buffer.from(await response.arrayBuffer())]);
  const verifier = new Transform({
    transform(chunk, encoding, callback) {
      const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk, encoding);
      count += bytes.length;
      if (count > maxBytes) return callback(fail('file exceeds the configured Home Center ingest ceiling.', 413, 'host_file_too_large'));
      hash.update(bytes);
      callback(null, bytes);
    },
  });
  try {
    await pipeline(source, verifier, fs.createWriteStream(tempPath, {flags: 'wx', mode: 0o600}));
    if (!count) throw fail('file is empty.', 400, 'host_file_empty');
    const responseMime = response.headers && response.headers.get && response.headers.get('content-type') || '';
    const name = file.fileName || 'upload.bin';
    const type = file.mimeType || String(responseMime).split(';')[0].trim() || 'application/octet-stream';
    let cleaned = false;
    return {
      name,
      type,
      size: count,
      sha256: hash.digest('hex'),
      fileId: file.fileId,
      tempPath,
      createReadStream: () => fs.createReadStream(tempPath),
      cleanup: async () => {
        if (cleaned) return;
        cleaned = true;
        await fsp.unlink(tempPath).catch((error) => {
          if (!error || error.code !== 'ENOENT') throw error;
        });
      },
    };
  } catch (error) {
    await fsp.unlink(tempPath).catch(() => {});
    throw error;
  }
}

module.exports = {
  openAiFileParamJsonSchema,
  openAiFileParamZodSchema,
  normalizeFileParam,
  ipIsPublic,
  assertPublicHttpsUrl,
  materializeOpenAiHostFile,
  materializeOpenAiHostFileToTemp,
};
