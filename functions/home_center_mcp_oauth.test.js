const assert = require('node:assert/strict');
const test = require('node:test');
const {
  isFullHomeCenterGoogleGrant,
  loadMcpAccessContext,
  selectHomeCenterGoogleTokens,
  storeHomeCenterGoogleGrant,
} = require('./home_center_mcp');

const scopes = [
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/spreadsheets',
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/calendar.events',
].join(' ');
const full = {access_token: 'new-access', refresh_token: 'new-refresh', scope: scopes};
const old = {access_token: 'old-access', refresh_token: 'old-refresh', scope: scopes};
const home = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';

test('fresh canonical Home Center grant supersedes a stale embedded connector grant', () => {
  const selected = selectHomeCenterGoogleTokens(old, {source: 'home_center_mcp_oauth', tokens: full});
  assert.deepEqual(selected, full);
  assert.deepEqual(old, {access_token: 'old-access', refresh_token: 'old-refresh', scope: scopes});
});

test('partial or unrelated grants cannot replace the Google credential', () => {
  assert.equal(isFullHomeCenterGoogleGrant(home, full), true);
  assert.equal(isFullHomeCenterGoogleGrant(home, {...full, refresh_token: ''}), false);
  assert.equal(isFullHomeCenterGoogleGrant(home, {...full, scope: 'openid email'}), false);
  assert.equal(isFullHomeCenterGoogleGrant('https://grounded-motion.invalid/mcp', full), false);
  assert.deepEqual(selectHomeCenterGoogleTokens(old, {source: 'android_sign_in', tokens: full}), old);
  assert.deepEqual(selectHomeCenterGoogleTokens(old, {source: 'home_center_mcp_oauth', tokens: full}, 'https://grounded-motion.invalid/mcp'), old);
  assert.deepEqual(selectHomeCenterGoogleTokens(old, {source: 'home_center_mcp_oauth', tokens: {...full, scope: 'openid email'}}), old);
});

test('authorized full Google callback saves canonical grant, not partial resource grant', async () => {
  const writes = [];
  const firestore = () => ({collection: (name) => ({doc: (email) => ({set: async (data, options) => writes.push({name, email, data, options})})})});
  firestore.FieldValue = {serverTimestamp: () => 'server-time'};
  const admin = {firestore};
  assert.equal(await storeHomeCenterGoogleGrant(admin, 'dclarke1005@gmail.com', 'https://grounded-motion.invalid/mcp', full), false);
  assert.equal(await storeHomeCenterGoogleGrant(admin, 'dclarke1005@gmail.com', home, {...full, scope: 'openid email'}), false);
  assert.equal(writes.length, 0);
  assert.equal(await storeHomeCenterGoogleGrant(admin, 'dclarke1005@gmail.com', home, full), true);
  assert.equal(writes.length, 2);
  assert.deepEqual(writes.map((write) => write.name), ['mcpGoogleGrants', 'googleToolTokens']);
  assert.equal(writes[0].email, 'dclarke1005@gmail.com');
  assert.deepEqual(writes[0].data.tokens, full);
});

test('MCP bearer remains required while its Google calls use the refreshed canonical grant', async () => {
  let selected;
  const google = {auth: {OAuth2: class {
    setCredentials(tokens) { selected = tokens; }
    on() {}
  }}};
  const accessData = {
    email: 'dclarke1005@gmail.com',
    resource: home,
    scopes: scopes.split(' '),
    googleTokens: old,
    expiresAtMs: Date.now() + 60000,
  };
  const firestore = () => ({collection: (name) => ({doc: () => ({
    get: async () => name === 'mcpOAuthAccessTokens'
      ? {exists: true, data: () => accessData, ref: {set: async () => {}}}
      : {exists: true, data: () => ({source: 'home_center_mcp_oauth', tokens: full})},
  })})});
  const context = await loadMcpAccessContext({firestore}, google, 'client', 'secret', 'opaque-mcp-token');
  assert.equal(context.user.email, 'dclarke1005@gmail.com');
  assert.deepEqual(selected, full);
  accessData.revokedAtMs = Date.now();
  await assert.rejects(() => loadMcpAccessContext({firestore}, google, 'client', 'secret', 'opaque-mcp-token'), /revoked/);
});
