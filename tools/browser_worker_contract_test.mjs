#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const packageJson = JSON.parse(fs.readFileSync(new URL('../browser-worker/package.json', import.meta.url), 'utf8'));
const workerSource = fs.readFileSync(new URL('../browser-worker/src/browser_worker.mjs', import.meta.url), 'utf8');
const chatgptDebugSource = fs.readFileSync(new URL('../browser-worker/src/chatgpt_plugin_debug.mjs', import.meta.url), 'utf8');
const cleanSlateSource = fs.readFileSync(new URL('../browser-worker/src/chatgpt_clean_slate_verify.mjs', import.meta.url), 'utf8');
const cleanSlateWrapper = fs.readFileSync(new URL('../tools/run_chatgpt_clean_slate_verify.sh', import.meta.url), 'utf8');
const docs = fs.readFileSync(new URL('../docs/BROWSER_HANDS.md', import.meta.url), 'utf8');

assert.equal(packageJson.dependencies.playwright, 'latest');
assert.equal(packageJson.type, 'module');
assert.match(packageJson.description, /first-class app function/i);
assert.match(workerSource, /from 'playwright'/);
assert.match(workerSource, /chromium\.launch/);
assert.match(workerSource, /HOME_CENTER_CHROMIUM_EXECUTABLE/);
assert.match(workerSource, /executablePath/);
assert.match(workerSource, /mode: 'desktop'/);
assert.match(workerSource, /record/);
assert.match(workerSource, /blocked_human_required/);
assert.match(workerSource, /detectPageBlockers/);

assert.match(workerSource, /buildSelectorLadderFromElementMeta/);
assert.match(workerSource, /runBrowserReplay/);
assert.match(workerSource, /selector_drift/);
assert.match(workerSource, /householdLearningContract/);
assert.match(workerSource, /learnedBy: safeText\(options\.learnedBy/);
assert.match(workerSource, /replayAudience: safeText\(options\.replayAudience/);
assert.match(workerSource, /html_id_data_testid_aria_role_label_first_no_pixel_coordinates/);
assert.doesNotMatch(workerSource, /pixel_coordinates'\s*,\s*\n\s*}\);/);
assert.match(workerSource, /not a robot/);
assert.match(workerSource, /redacted/);
assert.match(packageJson.scripts['debug:chatgpt-plugin'], /chatgpt_plugin_debug/);

assert.match(packageJson.scripts.check, /chatgpt_clean_slate_verify/);
assert.match(packageJson.scripts['verify:chatgpt-clean-slate'], /chatgpt_clean_slate_verify/);
assert.match(cleanSlateSource, /launchPersistentContext/);
assert.match(cleanSlateSource, /HOME_CENTER_CHATGPT_PROFILE_DIR/);
assert.match(cleanSlateSource, /SingletonLock/);
assert.match(cleanSlateSource, /connector_state_only_no_cloud_bucket_deletion/);
assert.match(cleanSlateSource, /bucket\.put_object/);
assert.match(cleanSlateSource, /bucket\.get_object/);
assert.match(cleanSlateSource, /blocked_chatgpt_auth/);
assert.match(cleanSlateSource, /blocked_chatgpt_ui/);
assert.match(cleanSlateSource, /Home Center/);
assert.match(cleanSlateSource, /Command Center/);
assert.match(cleanSlateWrapper, /proot-distro login debian/);
assert.match(cleanSlateWrapper, /HOME_CENTER_CHROMIUM_EXECUTABLE=\/usr\/bin\/chromium/);
assert.match(chatgptDebugSource, /chatgpt\.com/);
assert.match(chatgptDebugSource, /blocked_chatgpt_auth/);
assert.match(chatgptDebugSource, /blocked_chatgpt_ui/);
assert.match(docs, /Playwright is an essential Home Center app function/);
assert.match(docs, /Amazon is not prioritized/);
assert.match(docs, /Debian\/proot/);
assert.match(docs, /not the acceptance target/);
console.log('Browser worker contract test: OK');
