import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.resolve(here, '..', 'web', 'swarm-failover-lights.html');
const html = fs.readFileSync(htmlPath, 'utf8');

assert.doesNotMatch(html, /http-equiv=["']refresh["']/i, 'continuity lights must not auto-refresh');
assert.doesNotMatch(html, /setInterval\s*\(/, 'continuity lights must not run a ticking status loop');
assert.doesNotMatch(html, /aria-live=/i, 'timing must not create unsolicited live-region pressure');
assert.match(html, /<details class="timing-evidence">[\s\S]*?<summary>Show receipt timing<\/summary>/, 'receipt timing must be operator-requested');
assert.match(html, /No countdown\./, 'the default scheduler surface must explicitly reject countdown pressure');
assert.match(html, /prefers-reduced-motion:\s*reduce/, 'the light show must preserve reduced-motion accessibility');
assert.match(html, /<div class="label">SCHEDULER<\/div>[\s\S]*?<div class="state">__TASK_STATE__<\/div>/, 'meaningful scheduler state must remain visible without elapsed-time telemetry');

console.log('swarm failover quiet timing contract: PASS');
