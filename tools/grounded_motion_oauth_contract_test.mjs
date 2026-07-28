#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  resolveOAuthGrant,
  GROUNDED_MOTION_MCP_RESOURCE,
  GROUNDED_MOTION_MCP_SCOPE,
} = require('../functions/home_center_mcp.js');

const grounded = resolveOAuthGrant(GROUNDED_MOTION_MCP_RESOURCE, GROUNDED_MOTION_MCP_SCOPE);
assert.equal(GROUNDED_MOTION_MCP_RESOURCE, 'https://grounded-motion-mcp-220218838446.us-central1.run.app/mcp');
assert.equal(grounded.resource, GROUNDED_MOTION_MCP_RESOURCE);
assert.deepEqual(grounded.scopes, [GROUNDED_MOTION_MCP_SCOPE]);
assert.deepEqual(grounded.googleScopes, ['openid', 'email']);
assert.deepEqual(grounded.allowedEmails, ['dclarke1005@gmail.com']);
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

console.log(JSON.stringify({
  ok: true,
  resource: GROUNDED_MOTION_MCP_RESOURCE,
  scope: GROUNDED_MOTION_MCP_SCOPE,
  googleScopes: grounded.googleScopes,
  allowedEmails: grounded.allowedEmails,
}));
