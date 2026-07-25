import assert from 'node:assert/strict';
import {generateKeyPairSync} from 'node:crypto';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {githubAdminOperationEntries, githubAdminOperationRunOperation, createGitHubAppJwt} = require('../functions/home_center_mcp.js');

const registry = githubAdminOperationEntries();
for (const op of [
  'github_admin.auth_status',
  'github_admin.repos.create',
  'github_admin.repos.configure',
  'github_admin.branches.create',
  'github_admin.files.upsert',
  'github_admin.pull_requests.create',
  'github_admin.pull_requests.merge',
  'github_admin.workflows.dispatch',
]) {
  assert.ok(registry[op], `registry exposes ${op}`);
}
assert.equal(registry['github_admin.pull_requests.merge'].requiresRequestId, true);
assert.deepEqual(registry['github_admin.pull_requests.merge'].requiredPermissions, ['Contents: write']);

const originalEnabled = process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED;
const originalOwners = process.env.HOME_CENTER_GITHUB_ADMIN_OWNERS;
try {
  process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED = 'false';
  process.env.HOME_CENTER_GITHUB_ADMIN_OWNERS = 'Valar05,ExampleOrg';
  const status = await githubAdminOperationRunOperation({
    admin: null,
    user: {email: 'dclarke1005@gmail.com', authKind: 'test'},
    githubAdmin: {appId: () => '12345', installationId: () => '67890', privateKey: () => 'secret-private-key'},
    args: {operation: 'github_admin.auth_status', args: {}},
  });
  assert.equal(status.enabled, false);
  assert.equal(status.appConfigured, true);
  assert.equal(status.primaryCredential, 'github_app_installation');
  assert.deepEqual(status.allowedOwners, ['Valar05', 'ExampleOrg']);
  assert.equal(status.secretsExposed, false);

  await assert.rejects(
    githubAdminOperationRunOperation({
      admin: null,
      user: {email: 'dclarke1005@gmail.com', authKind: 'test'},
      githubAdmin: {},
      args: {operation: 'github_admin.repos.create', args: {owner: 'Valar05', name: 'blocked', requestId: 'blocked-create'}},
    }),
    /GitHub admin mutations are disabled/
  );

  const {privateKey} = generateKeyPairSync('rsa', {modulusLength: 2048});
  const pem = privateKey.export({type: 'pkcs8', format: 'pem'});
  const jwt = createGitHubAppJwt('12345', pem);
  const parts = jwt.split('.');
  assert.equal(parts.length, 3);
  assert.equal(JSON.parse(Buffer.from(parts[0], 'base64url').toString('utf8')).alg, 'RS256');
  const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
  assert.equal(payload.iss, '12345');
  assert.ok(payload.exp > payload.iat);
  assert.ok(!jwt.includes('PRIVATE KEY'));
} finally {
  if (originalEnabled === undefined) delete process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED;
  else process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED = originalEnabled;
  if (originalOwners === undefined) delete process.env.HOME_CENTER_GITHUB_ADMIN_OWNERS;
  else process.env.HOME_CENTER_GITHUB_ADMIN_OWNERS = originalOwners;
}

console.log('github_admin_contract_test passed');
