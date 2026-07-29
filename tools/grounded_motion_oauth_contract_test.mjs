#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  resolveOAuthGrant,
  GROUNDED_MOTION_MCP_RESOURCE,
  GROUNDED_MOTION_MCP_SCOPE,
  createHomeCenterMcpApp,
} = require('../functions/home_center_mcp.js');

const grounded = resolveOAuthGrant(GROUNDED_MOTION_MCP_RESOURCE, GROUNDED_MOTION_MCP_SCOPE);
assert.equal(GROUNDED_MOTION_MCP_RESOURCE, 'https://grounded-motion-mcp-220218838446.us-central1.run.app/mcp');
assert.equal(grounded.resource, GROUNDED_MOTION_MCP_RESOURCE);
assert.deepEqual(grounded.scopes, [GROUNDED_MOTION_MCP_SCOPE]);
assert.deepEqual(grounded.googleScopes, ['openid', 'email']);
assert.deepEqual(grounded.allowedEmails, ['dclarke1005@gmail.com']);
const groundedOffline = resolveOAuthGrant(
  GROUNDED_MOTION_MCP_RESOURCE,
  `${GROUNDED_MOTION_MCP_SCOPE} offline_access`,
);
assert.deepEqual(groundedOffline.scopes, [GROUNDED_MOTION_MCP_SCOPE, 'offline_access']);
assert.deepEqual(groundedOffline.googleScopes, ['openid', 'email']);
assert.throws(
  () => resolveOAuthGrant(GROUNDED_MOTION_MCP_RESOURCE, 'https://www.googleapis.com/auth/drive'),
  /invalid_scope/,
);
assert.throws(
  () => resolveOAuthGrant('https://unregistered.example/mcp', GROUNDED_MOTION_MCP_SCOPE),
  /invalid_target/,
);

const home = resolveOAuthGrant('', '');
assert(home.googleScopes.includes('https://www.googleapis.com/auth/drive'));
assert.equal(home.allowedEmails, null);

const app = createHomeCenterMcpApp({
  google: {},
  admin: {firestore() { return {}; }},
  googleClientId: () => 'configured-client',
  googleClientSecret: () => 'configured-secret',
});
const listener = app.listen(0, '127.0.0.1');
await new Promise((resolve, reject) => {
  listener.once('listening', resolve);
  listener.once('error', reject);
});
try {
  const address = listener.address();
  for (const pathname of ['/.well-known/oauth-authorization-server', '/.well-known/openid-configuration']) {
    const response = await fetch(`http://127.0.0.1:${address.port}${pathname}`);
    assert.equal(response.status, 200);
    const metadata = await response.json();
    assert(metadata.scopes_supported.includes('offline_access'), `${pathname} must advertise offline_access`);
    assert(metadata.grant_types_supported.includes('refresh_token'), `${pathname} must advertise refresh_token`);
  }
} finally {
  await new Promise((resolve) => listener.close(resolve));
}

console.log(JSON.stringify({
  ok: true,
  resource: GROUNDED_MOTION_MCP_RESOURCE,
  scope: GROUNDED_MOTION_MCP_SCOPE,
  googleScopes: grounded.googleScopes,
  allowedEmails: grounded.allowedEmails,
}));
