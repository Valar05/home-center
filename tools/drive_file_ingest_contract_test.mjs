import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');

const required = [
  "HOME_CENTER_DRIVE_INGEST_MAX_BYTES",
  "server.registerTool('drive_ingest_file'",
  "openAiFileParamZodSchema(z",
  "'openai/fileParams': ['file']",
  "materializeOpenAiHostFile",
  "await uploaded.arrayBuffer()",
  "expectedSha256",
  "drive_ingest_idempotency_conflict",
  "homeCenterRequestId",
  "homeCenterSha256",
  "appProperties has",
  "drive.files.create",
  "Readable.from([bytes])",
  "responseType: 'arraybuffer'",
  "readbackSha256",
  "verified: true",
  "inputSha256: sha256",
  "driveIngestFileCatalogInputSchema",
  "required: ['download_url', 'file_id']",
];

assert.match(source, /HOME_CENTER_DIRECT_FILE_TOOLS = Object\.freeze\(\[[^\]]*'drive_ingest_file'/);

for (const marker of required) {
  assert.equal(source.includes(marker), true, 'missing Drive file ingress contract marker: ' + marker);
}

assert.match(source, /if \(bytes\.length > HOME_CENTER_DRIVE_INGEST_MAX_BYTES\)/);
assert.match(source, /if \(expectedSha256 && expectedSha256 !== sha256\)/);
assert.match(source, /readbackBytes\.length === bytes\.length && readbackSha256 === sha256/);
assert.match(source, /if \(matches\.length > 1\).*quarantined/);
assert.match(source, /assertDriveIngestIdentity\(existing\.result, identity\)/);
assert.match(source, /parentFolderId: \(metadata\.parents \|\| \[\]\)\[0\] \|\| parentFolderId/);

console.log('Drive file ingress contract passed.');

