const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, 'home_center_mcp.js'), 'utf8');
const packageJson = JSON.parse(fs.readFileSync(path.join(__dirname, 'package.json'), 'utf8'));

test('Sites source materialization and Drive folder sharing are stable drive operations', () => {
  assert.match(source, /'sites\.source_version\.materialize_drive':\s*\{/);
  assert.match(source, /'drive\.share_folder':\s*\{/);
  assert.match(source, /operation === 'sites\.source_version\.materialize_drive'/);
  assert.match(source, /operation === 'drive\.share_folder'/);
  assert.match(source, /HOME_CENTER_CONNECTOR_SCHEMA_REVISION = '2026-08-02\.sites-source-drive-share-v1'/);
});

test('Sites source credential is short-lived input and excluded from results', () => {
  assert.match(source, /credentialPersisted: false/);
  assert.match(source, /credentialReturned: false/);
  assert.match(source, /repositoryToken\.length < 20/);
  const resultBlock = source.slice(source.indexOf("const result = {\n      operation: 'sites.source_version.materialize_drive'"), source.indexOf("const audit = await auditWrite", source.indexOf("const result = {\n      operation: 'sites.source_version.materialize_drive'")));
  assert.ok(resultBlock.length > 0);
  assert.doesNotMatch(resultBlock, /repositoryToken/);
});

test('materialization requires exact commit, bounded source, and per-file readback', () => {
  assert.match(source, /sourceCommit must be an exact 40-character Git commit SHA/);
  assert.match(source, /trackedPaths\.length > HOME_CENTER_SITES_SOURCE_MAX_FILES/);
  assert.match(source, /totalSourceBytes > HOME_CENTER_SITES_SOURCE_MAX_BYTES/);
  assert.match(source, /readbackBytes\.length !== bytes\.length \|\| readbackSha256 !== expectedSha256/);
  assert.equal(packageJson.dependencies['isomorphic-git'], '^1.40.0');
});

test('folder sharing verifies recipient and effective role after mutation', () => {
  assert.match(source, /drive\.permissions\.list/);
  assert.match(source, /safeText\(item\.emailAddress, 320\)\.toLowerCase\(\) === email && shareRoleSatisfies\(item\.role, role\)/);
  assert.match(source, /Drive permission readback did not confirm the requested recipient and role/);
});
