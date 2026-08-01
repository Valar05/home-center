import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const home = require('../functions/home_center_mcp.js');
const commandCenter = require('../functions/command_center_mcp.js');

const drew = 'dclarke1005@gmail.com';
const june = 'junewren28@gmail.com';
const tim = 'timothypomeroy07@gmail.com';
const approvedCreditUsers = [drew, june, tim];

assert.deepEqual(home.CREDIT_GATED_EMAILS, approvedCreditUsers);
assert.deepEqual(commandCenter.COMMAND_CENTER_ALLOWED_EMAILS, approvedCreditUsers);
assert.deepEqual(home.GITHUB_ADMIN_ALLOWED_EMAILS, approvedCreditUsers);

for (const email of approvedCreditUsers) {
  assert.equal(home.requireCreditGatedEmail(email), email);
  assert.equal(commandCenter.requireCommandCenterAllowedEmail(email), email);
}
for (const email of ['', 'outsider@example.com', 'drew@example.com']) {
  assert.throws(() => home.requireCreditGatedEmail(email), /restricted to approved Home Center accounts/);
  assert.throws(() => commandCenter.requireCommandCenterAllowedEmail(email), /restricted to approved Home Center accounts/);
}

for (const email of approvedCreditUsers) {
  assert.equal(home.requireGitHubAdminUser({email}), email);
}
for (const email of ['outsider@example.com', '']) {
  assert.throws(
    () => home.requireGitHubAdminUser({email}),
    (err) => err && err.status === 403 && err.code === 'github_admin_forbidden_email'
  );
}
for (const email of [june, tim]) {
  const status = await home.githubAdminOperationRunOperation({
    admin: {},
    user: {email},
    githubAdmin: {},
    args: {operation: 'github_admin.auth_status', args: {}},
  });
  assert.equal(status.enabled, false);
  assert.equal(status.profileConfigured, false);
  assert.ok(status.disabledReasons.some((reason) => reason.code === 'github_admin_user_profile_missing'));
}

const source = readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
assert.doesNotMatch(source, /server\.registerTool\('render_blender_glb'/);
assert.match(source, /capability_retired\.use_blender_workspace/);
assert.match(source, /async function githubAdminOperationRunOperation\([^)]*\) \{\n  requireGitHubAdminUser\(user\);/);

const hostedSource = readFileSync(new URL('../functions/index.js', import.meta.url), 'utf8');
assert.match(hostedSource, /const HOSTED_TTS_ALLOWED_EMAILS = CREDIT_GATED_EMAILS;/);
for (const [endpoint, verifier] of [
  ['creativePromptSmoke', 'requireSmokeUser'],
  ['turnContractSmoke', 'requireSmokeUser'],
  ['metalPromptSmoke', 'requireSmokeUser'],
  ['agentToolTurn', 'requireUser'],
  ['agentTurn', 'requireUser'],
]) {
  assert.match(hostedSource, new RegExp("requireCreditBackedUser\\(await " + verifier + "\\(req\\), '" + endpoint + "'\\)"));
}
assert.match(hostedSource, /return requireCreditBackedUser\(await requireGoogleOAuthAction\(req\), 'hosted TTS'\);/);
assert.doesNotMatch(hostedSource, /stack: String\(err\.stack/);

console.log('Home Center authorization contract: OK');
