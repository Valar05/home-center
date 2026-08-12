import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const registry = fs.readFileSync('app/src/main/java/com/dclar/homecenter/ToolRegistry.java', 'utf8');
const gateway = fs.readFileSync('functions/index.js', 'utf8');
const regression = fs.readFileSync('tools/home_center_regression_tests.py', 'utf8');
const doctrine = fs.readFileSync('docs/HOME_CENTER_DOCTRINE.md', 'utf8');

test('Drive metadata tool explicitly exposes rename and move', () => {
  assert.match(registry, /drive\.update_metadata/);
  assert.match(registry, /Rename or move a Google Drive file or folder/);
  assert.match(registry, /Arrays\.asList\("fileId", "name", "addParentId", "removeParentId"\)/);
});

test('planner palette exposes confirmation-friendly destination names', () => {
  assert.match(gateway, /drive\.update_metadata[^\n]*addParentName/);
  assert.match(gateway, /folderName[^\n]*parentName[^\n]*addParentName/);
  assert.match(gateway, /driveItemLabel/);
  assert.match(gateway, /confirmationSpokenTarget/);
  assert.match(gateway, /confirmationSummary/);
});

test('remembered document and folder references resolve before mutation', () => {
  assert.match(gateway, /resolveToolArgsFromWorkingMemory/);
  assert.match(gateway, /toolName === 'drive\.update_metadata'\) args\.addParentId = memory\.lastFolder\.fileId/);
  assert.match(gateway, /When resolving a remembered document, include fileId, name, and folderName when known/);
});

test('writing workflow regression retains natural move route', () => {
  assert.match(regression, /Move HomeCenter into that folder\./);
  assert.match(regression, /rememberEntity\(\\"lastFolder\\", toolName/);
  assert.match(regression, /drive\.update_metadata/);
});

test('writing doctrine requires safe rename move and provider proof', () => {
  assert.match(doctrine, /safe rename, move, split, and extraction workflows with confirmation and provider proof/);
});

test('user-facing confirmation is name-oriented, not raw-id oriented', () => {
  const start = gateway.indexOf('function confirmationSpokenTarget');
  const end = gateway.indexOf('function confirmationAction', start);
  const confirmation = gateway.slice(start, end);
  assert.match(confirmation, /driveItemLabel/);
  assert.doesNotMatch(confirmation, /a\.fileId|args\.fileId/);
});
