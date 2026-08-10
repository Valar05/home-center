import fs from 'node:fs';
import assert from 'node:assert/strict';

const helper = fs.readFileSync(new URL('./deploy_functions_termux.sh', import.meta.url), 'utf8');
const release = fs.readFileSync(new URL('./deploy_blender_workspace_release.sh', import.meta.url), 'utf8');

const releaseMatch = release.match(/deploy_functions_termux\.sh\" \"\$PROJECT\"\s+([^\n]+)/);
assert.ok(releaseMatch, 'umbrella release must invoke deploy_functions_termux.sh with explicit targets');
const requested = releaseMatch[1].trim().split(/\s+/);
assert.ok(requested.length > 0, 'umbrella release target list must not be empty');

const caseBlock = helper.match(/for fn in \$FUNCTIONS; do([\s\S]*?)done\s*$/);
assert.ok(caseBlock, 'deploy helper case dispatch was not found');
const supported = new Set([...caseBlock[1].matchAll(/^\s*([A-Za-z][A-Za-z0-9]*)\)\s+deploy_/gm)].map((match) => match[1]));

for (const target of requested) {
  assert.ok(supported.has(target), `umbrella release requests unsupported deploy target: ${target}`);
}

for (const target of ['computerHands', 'veniceNerve']) {
  assert.ok(requested.includes(target), `umbrella release must request ${target}`);
  assert.ok(supported.has(target), `deploy helper must support ${target}`);
  assert.match(helper, new RegExp(`deploy_${target === 'computerHands' ? 'computer_hands' : 'venice_nerve'}\\(\\) \\{[\\s\\S]*?gcloud functions deploy ${target}[\\s\\S]*?--runtime=nodejs22[\\s\\S]*?--entry-point=${target}`, 'm'));
}

assert.match(helper, /homeCenterMcp[\s\S]*computerHands[\s\S]*veniceNerve[\s\S]*assert_home_center_mcp_main_release\.sh/);
assert.match(helper, /HOME_CENTER_VENICE_NERVE_ORIGIN="https:\/\/\$\{REGION\}-\$\{PROJECT\}\.cloudfunctions\.net\/veniceNerve"/);

console.log(JSON.stringify({ok: true, requested, supported: [...supported].sort()}));
