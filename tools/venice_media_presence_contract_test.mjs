import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (relative) => fs.readFileSync(path.join(root, relative), 'utf8');
const json = (relative) => JSON.parse(read(relative));
const prose = (text) => text.replace(/[*`]/g, '');

const aperture = read('docs/venice-chatgpt-aperture-v2.md');
const media = read('docs/venice-media-presence-organ.md');
const mediaProse = prose(media);
const turn = json('contracts/venice-body-turn.v1.schema.json');
const session = json('contracts/venice-media-session.v1.schema.json');
const nerve = read('functions/venice_nerve_api.js');
const worker = read('venice-nerve/windows/home-center-venice-nerve.ps1');

assert.match(aperture, /dedicated Venice Nerve worker/i);
assert.match(aperture, /not an iframe/i);
assert.match(aperture, /must not share the physical worker process/i);
assert.doesNotMatch(nerve, /computer_hands_api|computerHandsOperation|windows-hands-01/);
assert.match(worker, /venice-aperture\.ps1/);

assert.deepEqual(turn.required, ['schema', 'turnId', 'speech', 'actions', 'observations', 'diagnostics']);
assert.equal(turn.properties.speech.properties.source.const, 'local-venice');
assert.equal(turn.properties.speech.properties.transformedByOrchestrator.const, false);
assert.equal(turn.properties.speech.properties.sha256.pattern, '^[a-f0-9]{64}$');
assert.match(nerve, /speech SHA-256 did not match exact UTF-8 speech bytes/);

for (const field of ['sessionId', 'artifactRef', 'state', 'player', 'verification']) {
  assert.ok(session.required.includes(field), `media session missing ${field}`);
}
assert.deepEqual(session.properties.presentation.enum, ['background', 'foreground']);
assert.deepEqual(session.properties.state.enum, ['creating', 'ready', 'playing', 'paused', 'stopped', 'failed']);
assert.ok(session.properties.verification.required.includes('processAlive'));
assert.ok(session.properties.verification.required.includes('focusPreserved'));
assert.match(mediaProse, /must not steal keyboard focus/i);
assert.match(mediaProse, /replacement is transactional/i);
assert.match(mediaProse, /Do not claim playing from a successful process launch alone/i);
assert.match(mediaProse, /pause\/resume\/volume\/stop/i);
assert.match(mediaProse, /venice_body\.action is the spinal router/i);
assert.match(mediaProse, /not sufficient evidence for Media Presence/i);

console.log(JSON.stringify({
  ok: true,
  contract: 'venice-media-presence-v1',
  guarantees: [
    'dedicated speech transport',
    'exact speech hashing',
    'structured actions',
    'durable media session identity',
    'focus and liveness verification'
  ]
}));
