import {createHash} from 'node:crypto';
import {Readable} from 'node:stream';
import {createInflateRaw, gzipSync} from 'node:zlib';

const bucket = process.env.GCS_BUCKET || 'home-center-dclar-hyperbolic-corpus';
const archiveObject = process.env.GCS_ARCHIVE_OBJECT || 'source/huggingface.co/datasets/RyokoExtra/TvTroper/resolve/main/pages.zip';
const outputPrefix = (process.env.GCS_INDEX_PREFIX || 'index/v2/shards').replace(/\/+$/, '');
const startEntry = Math.max(0, Number(process.env.START_ENTRY || 0));
const endEntry = Number(process.env.END_ENTRY || 0);
const maxSearchChars = Math.max(10000, Number(process.env.MAX_SEARCH_CHARS || 50000));
const taskIndex = Math.max(0, Number(process.env.CLOUD_RUN_TASK_INDEX || 0));
const taskCount = Math.max(1, Number(process.env.CLOUD_RUN_TASK_COUNT || 1));
let tokenCache = {token: '', expiresAt: 0};

function fail(message) { throw new Error(message); }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function objectUrl(name, media = false) {
  const root = media ? 'https://storage.googleapis.com/download/storage/v1' : 'https://storage.googleapis.com/storage/v1';
  return root + '/b/' + encodeURIComponent(bucket) + '/o/' + encodeURIComponent(name) + (media ? '?alt=media' : '');
}

async function accessToken() {
  if (tokenCache.token && tokenCache.expiresAt > Date.now() + 60000) return tokenCache.token;
  const response = await fetch('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token', {headers: {'Metadata-Flavor': 'Google'}});
  if (!response.ok) fail('metadata_token_failed:' + response.status + ':' + await response.text());
  const payload = await response.json();
  tokenCache = {token: payload.access_token, expiresAt: Date.now() + Number(payload.expires_in || 300) * 1000};
  return tokenCache.token;
}

async function googleFetch(url, options = {}, retries = 5) {
  let last;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const headers = new Headers(options.headers || {});
    headers.set('Authorization', 'Bearer ' + await accessToken());
    const response = await fetch(url, {...options, headers});
    if (response.ok || response.status === 404) return response;
    last = new Error('google_fetch_failed:' + response.status + ':' + (await response.text()).slice(0, 1000));
    if (response.status < 500 && response.status !== 429) throw last;
    await sleep(Math.min(30000, 1000 * 2 ** attempt));
  }
  throw last;
}

async function objectMetadata(name) {
  const response = await googleFetch(objectUrl(name));
  return response.status === 404 ? null : response.json();
}

async function rangeRead(name, start, end) {
  const response = await googleFetch(objectUrl(name, true), {headers: {Range: 'bytes=' + start + '-' + end}});
  const bytes = Buffer.from(await response.arrayBuffer());
  const expected = end - start + 1;
  if (bytes.length !== expected) fail('range_read_length_mismatch:' + name + ':' + start + ':' + end + ':' + bytes.length + ':' + expected);
  return bytes;
}

async function uploadObject(name, bytes, contentType = 'application/octet-stream', contentEncoding = '') {
  const query = new URLSearchParams({uploadType: 'media', name});
  const headers = {'Content-Type': contentType};
  if (contentEncoding) headers['Content-Encoding'] = contentEncoding;
  const response = await googleFetch('https://storage.googleapis.com/upload/storage/v1/b/' + encodeURIComponent(bucket) + '/o?' + query, {method: 'POST', headers, body: bytes});
  if (!response.ok) fail('upload_failed:' + response.status + ':' + await response.text());
  return response.json();
}

function readU64(buffer, offset) {
  const value = buffer.readBigUInt64LE(offset);
  if (value > BigInt(Number.MAX_SAFE_INTEGER)) fail('zip64_value_too_large');
  return Number(value);
}

function zip64Values(extra, needed) {
  let p = 0;
  while (p + 4 <= extra.length) {
    const id = extra.readUInt16LE(p);
    const size = extra.readUInt16LE(p + 2);
    const body = extra.subarray(p + 4, p + 4 + size);
    if (id === 1) {
      let q = 0;
      const out = {};
      for (const key of ['uncompressedSize', 'compressedSize', 'localHeaderOffset', 'diskStart']) {
        if (!needed[key]) continue;
        if (key === 'diskStart') { out[key] = body.readUInt32LE(q); q += 4; }
        else { out[key] = readU64(body, q); q += 8; }
      }
      return out;
    }
    p += 4 + size;
  }
  return {};
}

async function centralEntries(meta) {
  const size = Number(meta.size);
  const tailStart = Math.max(0, size - 1024 * 1024);
  const tail = await rangeRead(archiveObject, tailStart, size - 1);
  const zip64Index = tail.lastIndexOf(Buffer.from([0x50, 0x4b, 0x06, 0x06]));
  if (zip64Index < 0) fail('zip64_eocd_not_found');
  const count = readU64(tail, zip64Index + 32);
  const centralSize = readU64(tail, zip64Index + 40);
  const centralOffset = readU64(tail, zip64Index + 48);
  const central = await rangeRead(archiveObject, centralOffset, centralOffset + centralSize - 1);
  const entries = [];
  let p = 0;
  while (p < central.length) {
    if (central.readUInt32LE(p) !== 0x02014b50) fail('bad_central_signature_at:' + p);
    const flags = central.readUInt16LE(p + 8);
    const method = central.readUInt16LE(p + 10);
    const crc32 = central.readUInt32LE(p + 16);
    let compressedSize = central.readUInt32LE(p + 20);
    let uncompressedSize = central.readUInt32LE(p + 24);
    const nameLength = central.readUInt16LE(p + 28);
    const extraLength = central.readUInt16LE(p + 30);
    const commentLength = central.readUInt16LE(p + 32);
    let localHeaderOffset = central.readUInt32LE(p + 42);
    const name = central.subarray(p + 46, p + 46 + nameLength).toString('utf8');
    const extra = central.subarray(p + 46 + nameLength, p + 46 + nameLength + extraLength);
    const needed = {uncompressedSize: uncompressedSize === 0xffffffff, compressedSize: compressedSize === 0xffffffff, localHeaderOffset: localHeaderOffset === 0xffffffff, diskStart: false};
    const z64 = zip64Values(extra, needed);
    if (needed.uncompressedSize) uncompressedSize = z64.uncompressedSize;
    if (needed.compressedSize) compressedSize = z64.compressedSize;
    if (needed.localHeaderOffset) localHeaderOffset = z64.localHeaderOffset;
    if (!name.endsWith('/')) entries.push({name, flags, method, crc32, compressedSize, uncompressedSize, localHeaderOffset});
    p += 46 + nameLength + extraLength + commentLength;
  }
  console.log(JSON.stringify({event: 'zip_directory', eocdCount: count, fileEntries: entries.length, centralSize, centralOffset}));
  return entries;
}

function decodeEntities(text) {
  const named = {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' '};
  return text.replace(/&(#x[0-9a-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, (_, entity) => {
    if (entity[0] !== '#') return named[entity.toLowerCase()] || ' ';
    const hex = entity[1].toLowerCase() === 'x';
    const value = Number.parseInt(entity.slice(hex ? 2 : 1), hex ? 16 : 10);
    return Number.isFinite(value) && value > 0 && value <= 0x10ffff ? String.fromCodePoint(value) : ' ';
  });
}

function titleFrom(html, pageName) {
  const match = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const raw = match ? decodeEntities(match[1].replace(/<[^>]+>/g, ' ')) : pageName.replace(/([a-z])([A-Z])/g, '$1 $2');
  return raw.replace(/\s*[-/]\s*TV Tropes\s*$/i, '').replace(/\s+/g, ' ').trim().slice(0, 500) || pageName;
}

function visibleText(html) {
  return decodeEntities(html
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<(script|style|noscript|svg|template)[^>]*>[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim());
}

function locator(url) {
  try {
    const parts = new URL(url).pathname.split('/').filter(Boolean);
    const marker = parts.findIndex((part) => part.toLowerCase() === 'pmwiki.php');
    return {namespace: marker >= 0 ? (parts[marker + 1] || '') : '', pageName: marker >= 0 ? (parts[marker + 2] || '') : (parts.at(-1) || '')};
  } catch { return {namespace: '', pageName: ''}; }
}

function shardBase(entry, index) {
  const digest = createHash('sha256').update(entry.name).digest('hex').slice(0, 16);
  const base = entry.name.split('/').at(-1).replace(/[^A-Za-z0-9_.-]+/g, '-').slice(0, 120);
  return outputPrefix + '/' + String(index).padStart(4, '0') + '-' + digest + '-' + base;
}

function markerName(entry, index) {
  return outputPrefix.replace(/\/shards$/, '/markers') + '/' + String(index).padStart(4, '0') + '-' + createHash('sha256').update(entry.name).digest('hex').slice(0, 16) + '.json';
}

async function entryStream(entry) {
  const header = await rangeRead(archiveObject, entry.localHeaderOffset, entry.localHeaderOffset + 65535);
  if (header.readUInt32LE(0) !== 0x04034b50) fail('bad_local_header:' + entry.name);
  const dataOffset = entry.localHeaderOffset + 30 + header.readUInt16LE(26) + header.readUInt16LE(28);
  const chunkSize = 8 * 1024 * 1024;
  async function* compressedChunks() {
    const end = dataOffset + entry.compressedSize;
    for (let cursor = dataOffset; cursor < end; cursor += chunkSize) {
      yield await rangeRead(archiveObject, cursor, Math.min(end - 1, cursor + chunkSize - 1));
    }
  }
  const source = Readable.from(compressedChunks());
  if (entry.method === 0) return source;
  if (entry.method === 8) return source.pipe(createInflateRaw());
  fail('unsupported_zip_method:' + entry.method + ':' + entry.name);
}

async function* entryLines(entry) {
  const stream = await entryStream(entry);
  let carry = Buffer.alloc(0);
  for await (const chunk of stream) {
    const data = carry.length ? Buffer.concat([carry, chunk]) : Buffer.from(chunk);
    let cursor = 0;
    while (cursor < data.length) {
      const newline = data.indexOf(10, cursor);
      if (newline < 0) break;
      yield data.subarray(cursor, newline).toString('utf8').trim();
      cursor = newline + 1;
    }
    carry = cursor < data.length ? Buffer.from(data.subarray(cursor)) : Buffer.alloc(0);
  }
  if (carry.length) yield carry.toString('utf8').trim();
}

async function processEntry(entry, index, archiveGeneration) {
  const marker = markerName(entry, index);
  if (await objectMetadata(marker)) return {target: marker, skipped: true, records: 0, parts: 0};
  const base = shardBase(entry, index);
  const maxBatchBytes = 64 * 1024 * 1024;
  let batch = [];
  let batchBytes = 0;
  let part = 0;
  let compressedBytes = 0;
  let lineNumber = 0;
  async function flush() {
    if (!batch.length) return;
    const target = base + '-part-' + String(part).padStart(4, '0') + '.jsonl.gz';
    const gz = gzipSync(Buffer.concat(batch), {level: 6});
    await uploadObject(target, gz, 'application/x-ndjson', 'gzip');
    compressedBytes += gz.length;
    part++;
    batch = [];
    batchBytes = 0;
  }
  for await (const line of entryLines(entry)) {
    if (!line) continue;
    lineNumber++;
    const parsed = JSON.parse(line);
    if (!Array.isArray(parsed) || typeof parsed[0] !== 'string' || typeof parsed[1] !== 'string') fail('invalid_record:' + entry.name + ':' + lineNumber);
    const [sourceUrl, html] = parsed;
    const {namespace, pageName} = locator(sourceUrl);
    const title = titleFrom(html, pageName);
    const text = visibleText(html).slice(0, maxSearchChars);
    const row = Buffer.from(JSON.stringify({record_id: createHash('sha256').update(sourceUrl).digest('hex').slice(0, 32), source_url: sourceUrl, title, namespace, page_name: pageName, zip_entry: entry.name, line_number: lineNumber, local_header_offset: entry.localHeaderOffset, compressed_size: entry.compressedSize, uncompressed_size: entry.uncompressedSize, crc32: (entry.crc32 >>> 0).toString(16).padStart(8, '0'), archive_generation: String(archiveGeneration || ''), search_text: (title + ' ' + namespace + ' ' + pageName + ' ' + text).slice(0, maxSearchChars), html}) + '\n');
    if (batch.length && batchBytes + row.length > maxBatchBytes) await flush();
    batch.push(row);
    batchBytes += row.length;
    if (batchBytes >= maxBatchBytes) await flush();
  }
  await flush();
  const receipt = {schemaVersion: 2, entry: entry.name, index, records: lineNumber, parts: part, compressedBytes, archiveGeneration: String(archiveGeneration || ''), completedAt: new Date().toISOString()};
  await uploadObject(marker, Buffer.from(JSON.stringify(receipt, null, 2) + '\n'), 'application/json');
  return {target: marker, skipped: false, records: lineNumber, parts: part, compressedBytes};
}

async function main() {
  const meta = await objectMetadata(archiveObject);
  if (!meta) fail('archive_not_found:gs://' + bucket + '/' + archiveObject);
  const entries = await centralEntries(meta);
  const stop = endEntry > 0 ? Math.min(entries.length, endEntry) : entries.length;
  let records = 0;
  console.log(JSON.stringify({event: 'index_start', archive: 'gs://' + bucket + '/' + archiveObject, archiveGeneration: meta.generation, entries: entries.length, startEntry, endEntry: stop, outputPrefix, maxSearchChars}));
  for (let index = startEntry + taskIndex; index < stop; index += taskCount) {
    const result = await processEntry(entries[index], index, meta.generation);
    records += result.records;
    console.log(JSON.stringify({event: 'entry_complete', index, entry: entries[index].name, ...result, records}));
  }
  const manifest = {schemaVersion: 2, status: 'complete', archive: 'gs://' + bucket + '/' + archiveObject, archiveGeneration: meta.generation, sourceSize: Number(meta.size), entryCount: entries.length, processedEntries: Math.max(0, Math.ceil((stop - startEntry - taskIndex) / taskCount)), emittedRecords: records, range: {startEntry, endEntry: stop, taskIndex, taskCount}, outputPrefix, maxSearchChars, completedAt: new Date().toISOString()};
  await uploadObject(outputPrefix.replace(/\/shards$/, '') + '/manifest-' + startEntry + '-' + stop + '-task-' + taskIndex + '-of-' + taskCount + '.json', Buffer.from(JSON.stringify(manifest, null, 2) + '\n'), 'application/json');
  console.log(JSON.stringify({event: 'index_complete', ...manifest}));
}

main().catch((error) => { console.error(JSON.stringify({event: 'index_failed', message: error.message, stack: error.stack})); process.exitCode = 1; });
