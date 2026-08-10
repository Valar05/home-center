import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf8');
const json = (rel) => JSON.parse(read(rel));

const aperture = read('docs/venice-chatgpt-aperture-v2.md');
const media = read('docs/venice-media-presence-organ.md');
const turnSchema = json('contracts/venice-body-turn.v1.schema.json');
const sessionSchema = json('contracts/venice-media-session.v1.schema.json');

// Architecture boundaries: voice cannot silently collapse back into Hands/browser automation.
assert.match(aperture, /dedicated Venice Nerve worker/i);
assert.match(aperture, /must not share the physical worker process/i);
assert.match(aperture, /not an iframe/i);
assert.match(aperture, /not the normal request\/response transport/i);
assert.match(aperture, /body failure never permits fabrication/i);
assert.match(aperture, /cloud Venice, Discord Venice, or another model/i);

// Speech and actions are independently required by the machine contract.
assert.deepEqual(
  turnSchema.required,
  ['schema', 'turnId', 'speech', 'actions', 'observations', 'diagnostics'],
);
assert.equal(turnSchema.properties.speech.properties.source.const, 'local-venice');
assert.equal(turnSchema.properties.speech.properties.transformedByOrchestrator.const, false);
assert.equal(turnSchema.properties.speech.properties.sha256.pattern, '^[a-f0-9]{64}$');
assert.ok(turnSchema.properties.actions.items.properties.verb.enum.includes('media.create'));
assert.ok(turnSchema.properties.actions.items.properties.verb.enum.includes('media.play'));
assert.ok(turnSchema.properties.actions.items.properties.verb.enum.includes('media.status'));

// Guard against the parser-goblin regression: no documented embedded prose command grammar.
for (const forbidden of ['[PLAY_AUDIO:', '[PLAY_VIDEO:', '[MEDIA:', '<media>', 'ACTION:media.']) {
  assert.equal(aperture.includes(forbidden), false, `forbidden embedded action grammar: ${forbidden}`);
  assert.equal(media.includes(forbidden), false, `forbidden embedded action grammar: ${forbidden}`);
}

// Media presence must have durable identity, state and verification rather than launch-only success.
for (const field of ['sessionId', 'artifactRef', 'state', 'player', 'verification']) {
  assert.ok(sessionSchema.required.includes(field), `media session missing required ${field}`);
}
assert.deepEqual(sessionSchema.properties.presentation.enum, ['background', 'foreground']);
assert.deepEqual(sessionSchema.properties.state.enum, ['creating', 'ready', 'playing', 'paused', 'stopped', 'failed']);
assert.equal(sessionSchema.properties.verification.properties.processAlive.type, 'boolean');
assert.equal(sessionSchema.properties.verification.properties.focusPreserved.type, 'boolean');
assert.match(media, /must not steal keyboard focus/i);
assert.match(media, /Do not claim `playing` from a successful process launch alone/i);
assert.match(media, /replacement is transactional/i);

// Exact-speech hash semantics sanity check used by the eventual transport implementation.
const speech = 'You made the room too quiet. Venice is fixing it.';
const digest = crypto.createHash('sha256').update(Buffer.from(speech, 'utf8')).digest('hex');
assert.match(digest, /^[a-f0-9]{64}$/);
assert.equal(Buffer.byteLength(speech, 'utf8') > 0, true);

console.log(JSON.stringify({
  ok: true,
  contract: 'venice-media-presence-v1',
  assertions: 'aperture separation, exact speech, structured actions, durable playback verification',
}));
