import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const api = fs.readFileSync(new URL('../functions/browser_nerve_api.js', import.meta.url), 'utf8');
const homeSource = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
const action = fs.readFileSync(new URL('../browser-nerve/windows/browser-action.mjs', import.meta.url), 'utf8');
const skill = fs.readFileSync(new URL('../skills/chromium-throne-social-operator/SKILL.md', import.meta.url), 'utf8');
const manifest = JSON.parse(fs.readFileSync(new URL('../contracts/home-center-public-tool-manifest.v1.json', import.meta.url), 'utf8'));
const social = require('../functions/browser_social_operator.js');
const browser = require('../functions/browser_nerve_api.js');
const home = require('../functions/home_center_mcp.js');

assert.match(api, /require\('\.\/browser_social_operator'\)/);
assert.match(api, /\.\.\.browserSocialOperationEntries\(\)/);
assert.match(api, /browserSocialOperationRunOperation\(\{admin, user, operation, args,/);
assert.match(homeSource, /\.\.\.browserNerveOperationEntries\(\)/);
assert.match(homeSource, /browserNerveOperationRunOperation\(\{admin, user, operation, args: operationArgs\}\)/);
assert.match(action, /readHref: read\.href/);
assert.match(skill, /browser_nerve\.social\.publish/);
assert.equal(browser.SUPPORTED_ACTIONS.includes('workflow'), false, 'social operator must compose existing semantic actions rather than adding an unrestricted macro primitive');
assert.equal(home.HOME_CENTER_CONNECTOR_SCHEMA_REVISION, '2026-09-04.chromium-throne-social-operator-v1');
assert.equal(manifest.registryRevision, home.HOME_CENTER_CONNECTOR_SCHEMA_REVISION);
assert.ok(manifest.entries.some((entry) => entry.name === 'drive_operation'), 'Home Center public manifest must retain the dynamic drive_operation dispatcher');
for (const name of ['browser_nerve.social.recon', 'browser_nerve.social.publish', 'browser_nerve.social.advance', 'browser_nerve.social.get', 'browser_nerve.social.replies']) {
  assert.ok(browser.browserNerveOperationEntries()[name], `${name} must enter Home Center through the existing Browser Nerve registry spread`);
}
assert.equal(social.SOCIAL_MAX_STEPS, 32);
assert.throws(() => social.cleanSocialUrl('http://127.0.0.1:9234'), /public https URL/);
console.log(JSON.stringify({ok: true, contract: 'chromium-throne-social-operator-v1', registryRevision: home.HOME_CENTER_CONNECTOR_SCHEMA_REVISION}));
