import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const write = (file, value) => fs.writeFileSync(path.join(root, file), value, 'utf8');

function replaceOnce(source, needle, replacement, label) {
  const count = source.split(needle).length - 1;
  if (count !== 1) throw new Error(`${label}: expected one exact match, found ${count}.`);
  return source.replace(needle, replacement);
}

const stagingDir = path.join(root, 'tools/social_operator_parts');
function materializeBase64Parts(target, prefix) {
  const targetPath = path.join(root, target);
  if (fs.existsSync(targetPath)) return;
  if (!fs.existsSync(stagingDir)) throw new Error(`${target} is missing and no staging parts exist.`);
  const parts = fs.readdirSync(stagingDir).filter((name) => name.startsWith(prefix + '.b64.')).sort();
  if (!parts.length) throw new Error(`No base64 staging parts found for ${target}.`);
  const encoded = parts.map((name) => fs.readFileSync(path.join(stagingDir, name), 'utf8').trim()).join('');
  fs.mkdirSync(path.dirname(targetPath), {recursive: true});
  fs.writeFileSync(targetPath, Buffer.from(encoded, 'base64'));
}
materializeBase64Parts('functions/browser_social_operator.js', 'browser_social_operator.js');
materializeBase64Parts('functions/browser_social_operator.test.js', 'browser_social_operator.test.js');

const socialModule = 'functions/browser_social_operator.js';

const apiPath = 'functions/browser_nerve_api.js';
let api = read(apiPath);
if (!api.includes("require('./browser_social_operator')")) {
  api = replaceOnce(
    api,
    "const {createHash, randomBytes} = require('node:crypto');",
    "const {createHash, randomBytes} = require('node:crypto');\nconst {browserSocialOperationEntries, browserSocialOperationRunOperation} = require('./browser_social_operator');",
    'Browser Social module import',
  );
}
if (!api.includes('...browserSocialOperationEntries()')) {
  const marker = "    'browser_nerve.worker.status': {summary: 'Read Browser Nerve worker heartbeat, selector capability, and queued browser work.', write: false, requiresRequestId: false, requiredScopes: [], input: {workerId: 'optional windows-browser-nerve-01'}},";
  api = replaceOnce(api, marker, `${marker}\n    ...browserSocialOperationEntries(),`, 'Browser Social operation registry spread');
}
if (!api.includes('browserSocialOperationRunOperation({admin, user, operation, args,')) {
  const marker = "  if (operation === 'browser_nerve.worker.status') return workerStatusOperation({admin, user, args});";
  const dispatch = "  if (browserSocialOperationEntries()[operation]) return browserSocialOperationRunOperation({admin, user, operation, args, dependencies: {ownerKey, collections: COLLECTIONS, ticketDocId, enqueueBrowserNerveTicket}});";
  api = replaceOnce(api, marker, `${marker}\n${dispatch}`, 'Browser Social operation dispatcher');
}
write(apiPath, api);

const homePath = 'functions/home_center_mcp.js';
let home = read(homePath);
const previousRevision = "const HOME_CENTER_CONNECTOR_SCHEMA_REVISION = '2026-09-04.browser-nerve-action-surface-v1';";
const socialRevision = "const HOME_CENTER_CONNECTOR_SCHEMA_REVISION = '2026-09-04.chromium-throne-social-operator-v1';";
if (!home.includes(socialRevision)) home = replaceOnce(home, previousRevision, socialRevision, 'Home Center connector revision');
write(homePath, home);

const actionPath = 'browser-nerve/windows/browser-action.mjs';
let action = read(actionPath);
if (!action.includes('readHref: read.href')) {
  action = replaceOnce(
    action,
    "const read = await handle.evaluate((el) => ({text: (el.innerText || el.textContent || '').trim().slice(0, 8000), value: 'value' in el ? String(el.value || '').slice(0, 8000) : ''}));",
    "const read = await handle.evaluate((el) => ({text: (el.innerText || el.textContent || '').trim().slice(0, 8000), value: 'value' in el ? String(el.value || '').slice(0, 8000) : '', href: el.href ? String(el.href).slice(0, 1000) : ''}));",
    'Browser Nerve semantic href readback',
  );
  action = replaceOnce(
    action,
    "actionResult = action === 'find' ? {found: true, hasText: !!read.text, hasValue: !!read.value} : {readText: read.text, readValue: read.value};",
    "actionResult = action === 'find' ? {found: true, hasText: !!read.text, hasValue: !!read.value, hasHref: !!read.href} : {readText: read.text, readValue: read.value, readHref: read.href};",
    'Browser Nerve href evidence envelope',
  );
}
write(actionPath, action);

const skillPath = 'skills/chromium-throne-social-operator/SKILL.md';
let skill = read(skillPath);
if (!skill.includes('## Callable Home Center operations')) {
  skill += `\n\n## Callable Home Center operations\n\nThe implementation surface is the existing Home Center \`drive_operation\` dispatcher. Do not create another transport.\n\n- \`browser_nerve.social.recon\`: queue public same-origin semantic reconnaissance.\n- \`browser_nerve.social.publish\`: queue one explicitly commissioned public post as a finite semantic step plan.\n- \`browser_nerve.social.advance\`: reconcile the current step, refuse blind mutation retries, and queue the next step.\n- \`browser_nerve.social.get\`: inspect the durable job, current Browser Nerve ticket, and watch without advancing.\n- \`browser_nerve.social.replies\`: inspect a previously verified public post and return only newly observed public reply fragments.\n\nA publication workflow must capture the authenticated account before mutation and capture the resulting post plus permalink after mutation. A submit/click receipt alone remains UNKNOWN. Reply workflows cannot type, select, submit, or enter messages, inbox, account, settings, billing, advertising, or payment surfaces.\n\n### Capability state\n\nRepository implementation and deterministic contract tests establish IMPLEMENTED/TESTED only. DEPLOYED requires the Home Center/Browser Nerve deployment receipt. CALLABLE requires a fresh worker heartbeat and successful operation canary. DELIVERED requires a verified public permalink or returned reply briefing. HUMAN-ACCEPTED remains Drew's decision.\n`;
}
write(skillPath, skill);

if (fs.existsSync(stagingDir)) fs.rmSync(stagingDir, {recursive: true, force: true});

console.log(JSON.stringify({ok: true, patched: [socialModule, 'functions/browser_social_operator.test.js', apiPath, homePath, actionPath, skillPath]}));
