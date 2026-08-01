import assert from 'node:assert/strict';
import {generateKeyPairSync} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {githubAdminOperationEntries, githubAdminOperationRunOperation, driveOperationRunOperation, createGitHubAppJwt} = require('../functions/home_center_mcp.js');

class FakeDoc {
  constructor(store, id) { this.store = store; this.id = id; }
  async get() { const value = this.store.get(this.id); return {exists: value !== undefined, data: () => value}; }
  async set(value) { this.store.set(this.id, value); }
}
class FakeCollection {
  constructor(store) { this.store = store; }
  doc(id) { return new FakeDoc(this.store, id); }
}
function fakeAdmin() {
  const collections = new Map();
  return {
    collections,
    firestore() {
      return {collection(name) { if (!collections.has(name)) collections.set(name, new Map()); return new FakeCollection(collections.get(name)); }};
    },
  };
}
function auditEntries(admin) {
  return Array.from((admin.collections.get('driveBridgeAudit') || new Map()).values());
}
function response(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 204 ? 'No Content' : 'OK',
    async text() { if (body === undefined || body === null) return ''; return typeof body === 'string' ? body : JSON.stringify(body); },
  };
}

const {privateKey} = generateKeyPairSync('rsa', {modulusLength: 2048});
const privateKeyPem = privateKey.export({type: 'pkcs8', format: 'pem'});
const user = {email: 'dclarke1005@gmail.com', authKind: 'test'};
const juneUser = {email: 'junewren28@gmail.com', authKind: 'test'};
const timUser = {email: 'timothypomeroy07@gmail.com', authKind: 'test'};
const githubAdmin = {
  appId: () => '12345',
  installationId: () => '67890',
  privateKey: () => privateKeyPem,
  bootstrapToken: () => 'bootstrap-token-for-tests',
  allowedOwners: () => 'Valar05',
};
const scopedProfilesB64 = Buffer.from(JSON.stringify({
  'junewren28@gmail.com': {owners: ['JuneGitHub'], installationId: '222'},
  'timothypomeroy07@gmail.com': {owners: ['TimGitHub'], installationId: '333'},
})).toString('base64');
const scopedGithubAdmin = {
  ...githubAdmin,
  userProfiles: () => scopedProfilesB64,
};
let installationTokenAttempts = 0;
let drewDispatchAttempts = 0;
let scopedDispatchAttempts = 0;
const originalFetch = global.fetch;
const originalEnabled = process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED;
const originalOwners = process.env.HOME_CENTER_GITHUB_ADMIN_OWNERS;
try {
  global.fetch = async (url, options = {}) => {
    const parsed = new URL(url);
    if (parsed.pathname === '/app/installations/67890/access_tokens') {
      installationTokenAttempts += 1;
      if (installationTokenAttempts === 1) return response(502, {message: 'transient gateway'});
      return response(201, {token: 'installation-token-for-tests'});
    }
    if (parsed.pathname === '/app/installations/222/access_tokens') return response(201, {token: 'june-installation-token'});
    if (parsed.pathname === '/app/installations/333/access_tokens') return response(201, {token: 'tim-installation-token'});
    if (parsed.pathname === '/repos/Valar05/home-center/actions/workflows/ci.yml/dispatches' && options.method === 'POST') {
      drewDispatchAttempts += 1;
      return response(204, null);
    }
    if (['/repos/JuneGitHub/june-project/actions/workflows/ci.yml/dispatches', '/repos/TimGitHub/tim-project/actions/workflows/ci.yml/dispatches'].includes(parsed.pathname) && options.method === 'POST') {
      scopedDispatchAttempts += 1;
      return response(204, null);
    }
    if (parsed.pathname === '/repos/Valar05/home-center/pulls/10') return response(200, {number: 10, draft: false, head: {ref: 'feature', sha: 'current-sha'}, base: {ref: 'main', sha: 'base-sha'}});
    if (parsed.pathname === '/repos/Valar05/home-center/pulls/11') return response(200, {number: 11, draft: false, head: {ref: 'feature', sha: 'ok-sha'}, base: {ref: 'main', sha: 'base-sha'}});
    if (parsed.pathname === '/repos/Valar05/home-center/commits/ok-sha/status') return response(200, {state: 'pending', statuses: [{context: 'ci'}], total_count: 1});
    throw new Error(`Unexpected GitHub mock route: ${options.method || 'GET'} ${parsed.pathname}`);
  };

  const registry = githubAdminOperationEntries();
  for (const op of ['github_admin.auth_status', 'github_admin.repos.create', 'github_admin.repos.configure', 'github_admin.branches.create', 'github_admin.files.upsert', 'github_admin.pull_requests.create', 'github_admin.pull_requests.merge', 'github_admin.workflows.dispatch']) {
    assert.ok(registry[op], `registry exposes ${op}`);
  }
  assert.equal(registry['github_admin.pull_requests.merge'].requiresRequestId, true);
  assert.deepEqual(registry['github_admin.pull_requests.merge'].requiredPermissions, ['Contents: write']);

  process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED = 'true';
  process.env.HOME_CENTER_GITHUB_ADMIN_OWNERS = 'Valar05';
  const liveStatus = await githubAdminOperationRunOperation({admin: fakeAdmin(), user, githubAdmin, args: {operation: 'github_admin.auth_status', args: {}}});
  assert.equal(liveStatus.enabled, true);
  assert.equal(installationTokenAttempts, 2, 'transient installation-token 502 is retried');
  const bridgeStatus = await driveOperationRunOperation({admin: fakeAdmin(), user, githubAdmin, args: {operation: 'github_admin.auth_status', args: {}}});
  assert.equal(bridgeStatus.completed, true);
  assert.equal(bridgeStatus.result.enabled, true);
  assert.equal(liveStatus.appConfigured, true);
  assert.equal(liveStatus.authenticated, true);
  assert.equal(liveStatus.providerReachable, true);
  assert.equal(liveStatus.primaryCredential, 'github_app_installation');
  assert.equal(liveStatus.credentialScope, 'legacy_drew', 'Drew keeps the existing installation binding');
  assert.equal(liveStatus.fallbackCredentialConfigured, true, 'Drew keeps the existing optional bootstrap authority');
  assert.deepEqual(liveStatus.allowedOwners, ['Valar05']);
  assert.equal(liveStatus.secretsExposed, false);

  const juneStatus = await githubAdminOperationRunOperation({admin: fakeAdmin(), user: juneUser, githubAdmin: scopedGithubAdmin, args: {operation: 'github_admin.auth_status', args: {}}});
  assert.equal(juneStatus.enabled, true);
  assert.equal(juneStatus.credentialScope, 'user_profile');
  assert.deepEqual(juneStatus.allowedOwners, ['JuneGitHub']);
  assert.equal(juneStatus.fallbackCredentialConfigured, false, 'June never inherits Drew bootstrap authority');
  assert.equal(juneStatus.requestIdOwnershipEnforced, true);

  const timStatus = await githubAdminOperationRunOperation({admin: fakeAdmin(), user: timUser, githubAdmin: scopedGithubAdmin, args: {operation: 'github_admin.auth_status', args: {}}});
  assert.equal(timStatus.enabled, true);
  assert.deepEqual(timStatus.allowedOwners, ['TimGitHub']);
  assert.equal(timStatus.fallbackCredentialConfigured, false);

  await assert.rejects(
    githubAdminOperationRunOperation({admin: fakeAdmin(), user: juneUser, githubAdmin: scopedGithubAdmin, args: {operation: 'github_admin.workflows.dispatch', args: {repo: 'Valar05/home-center', workflowId: 'ci.yml', ref: 'main', requestId: 'june-cross-owner'}}}),
    (err) => err && err.code === 'github_admin_owner_not_allowed'
  );
  await assert.rejects(
    githubAdminOperationRunOperation({admin: fakeAdmin(), user: juneUser, githubAdmin: scopedGithubAdmin, args: {operation: 'github_admin.repos.create', args: {owner: 'JuneGitHub', ownerType: 'user', name: 'new-repo', requestId: 'june-personal-create'}}}),
    (err) => err && err.code === 'github_admin_user_token_missing'
  );

  const scopedAuditAdmin = fakeAdmin();
  const juneDispatch = await githubAdminOperationRunOperation({admin: scopedAuditAdmin, user: juneUser, githubAdmin: scopedGithubAdmin, args: {operation: 'github_admin.workflows.dispatch', args: {repo: 'JuneGitHub/june-project', workflowId: 'ci.yml', ref: 'main', requestId: 'personal-dispatch-june'}}});
  const timDispatch = await githubAdminOperationRunOperation({admin: scopedAuditAdmin, user: timUser, githubAdmin: scopedGithubAdmin, args: {operation: 'github_admin.workflows.dispatch', args: {repo: 'TimGitHub/tim-project', workflowId: 'ci.yml', ref: 'main', requestId: 'personal-dispatch-tim'}}});
  assert.equal(juneDispatch.dispatched, true);
  assert.equal(timDispatch.dispatched, true);
  assert.equal(scopedDispatchAttempts, 2, 'each user dispatches only through the matching personal installation');
  await assert.rejects(
    githubAdminOperationRunOperation({admin: scopedAuditAdmin, user: timUser, githubAdmin: scopedGithubAdmin, args: {operation: 'github_admin.workflows.dispatch', args: {repo: 'TimGitHub/tim-project', workflowId: 'ci.yml', ref: 'main', requestId: 'personal-dispatch-june'}}}),
    (err) => err && err.code === 'github_admin_request_id_owner_conflict'
  );

  process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED = 'false';
  const disabledStatus = await githubAdminOperationRunOperation({admin: fakeAdmin(), user, githubAdmin, args: {operation: 'github_admin.auth_status', args: {}}});
  assert.equal(disabledStatus.enabled, false);
  assert.ok(disabledStatus.disabledReasons.some((reason) => reason.code === 'runtime_flag_disabled'));
  assert.equal(disabledStatus.diagnostics.installationProbe.code, 'not_applicable');

  process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED = 'true';
  const inaccessibleStatus = await githubAdminOperationRunOperation({
    admin: fakeAdmin(),
    user,
    githubAdmin: {...githubAdmin, privateKey: () => { throw new Error('private-key-payload-should-not-leak'); }},
    args: {operation: 'github_admin.auth_status', args: {}},
  });
  assert.equal(inaccessibleStatus.enabled, false);
  assert.equal(inaccessibleStatus.secretsExposed, false);
  assert.doesNotMatch(JSON.stringify(inaccessibleStatus), /private-key-payload-should-not-leak|installation-token-for-tests|bootstrap-token-for-tests/);

  await assert.rejects(
    githubAdminOperationRunOperation({admin: fakeAdmin(), user, githubAdmin, args: {operation: 'github_admin.branches.create', args: {repo: 'OtherOwner/home-center', branch: 'blocked', fromBranch: 'main', requestId: 'owner-blocked'}}}),
    /outside this Home Center user's GitHub Admin profile/
  );

  await assert.rejects(
    githubAdminOperationRunOperation({admin: fakeAdmin(), user, githubAdmin, args: {operation: 'github_admin.workflows.dispatch', args: {repo: 'Valar05/home-center', workflowId: 'ci.yml', ref: 'main'}}}),
    /requestId is required/
  );

  const admin = fakeAdmin();
  const dispatchArgs = {repo: 'Valar05/home-center', workflowId: 'ci.yml', ref: 'main', inputs: {nonce: 'github-admin-contract'}, requestId: 'dispatch-contract-1'};
  const dispatch = await githubAdminOperationRunOperation({admin, user, githubAdmin, args: {operation: 'github_admin.workflows.dispatch', args: dispatchArgs}});
  assert.equal(dispatch.dispatched, true);
  assert.equal(drewDispatchAttempts, 1, 'workflow dispatch POST is never blindly retried');
  assert.equal(dispatch.authMode, 'github_app_installation');
  const replay = await githubAdminOperationRunOperation({admin, user, githubAdmin, args: {operation: 'github_admin.workflows.dispatch', args: dispatchArgs}});
  assert.equal(replay.idempotent, true);
  assert.equal(auditEntries(admin).length, 1);
  const auditText = JSON.stringify(auditEntries(admin)[0]);
  assert.match(auditText, /github\.admin\.workflows\.dispatch/);
  assert.match(auditText, /dispatch-contract-1/);
  assert.doesNotMatch(auditText, /installation-token-for-tests|bootstrap-token-for-tests|PRIVATE KEY/);

  await assert.rejects(
    githubAdminOperationRunOperation({admin: fakeAdmin(), user, githubAdmin, args: {operation: 'github_admin.pull_requests.merge', args: {repo: 'Valar05/home-center', pullNumber: 10, expectedHeadSha: 'stale-sha', requestId: 'merge-head-mismatch'}}}),
    /PR head SHA changed/
  );
  await assert.rejects(
    githubAdminOperationRunOperation({admin: fakeAdmin(), user, githubAdmin, args: {operation: 'github_admin.pull_requests.merge', args: {repo: 'Valar05/home-center', pullNumber: 11, expectedHeadSha: 'ok-sha', requestId: 'merge-checks-not-green'}}}),
    /Required commit statuses are not green/
  );

  const jwt = createGitHubAppJwt('12345', privateKeyPem);
  const parts = jwt.split('.');
  assert.equal(parts.length, 3);
  assert.equal(JSON.parse(Buffer.from(parts[0], 'base64url').toString('utf8')).alg, 'RS256');
  const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
  assert.equal(payload.iss, '12345');
  assert.ok(payload.exp > payload.iat);
  assert.ok(!jwt.includes('PRIVATE KEY'));

  const source = readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
  assert.match(source, /server\.registerTool\('github_get_repo'/, 'existing authenticated GitHub read tool remains registered');
  assert.match(source, /function githubRequest\(githubToken/, 'existing authenticated GitHub read request path remains present');
} finally {
  global.fetch = originalFetch;
  if (originalEnabled === undefined) delete process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED;
  else process.env.HOME_CENTER_GITHUB_ADMIN_ENABLED = originalEnabled;
  if (originalOwners === undefined) delete process.env.HOME_CENTER_GITHUB_ADMIN_OWNERS;
  else process.env.HOME_CENTER_GITHUB_ADMIN_OWNERS = originalOwners;
}

console.log('github_admin_contract_test passed');