import test from 'node:test';
import assert from 'node:assert/strict';
import { extractVoiceImagePrompt, requestsVeniceIdentity } from '../src/image-identity-intent.mjs';

test('underspecified voice image requests do not invent Venice', () => {
  for (const text of ['make me a picture', 'show me an image', 'create a portrait', 'draw me a scene']) {
    assert.equal(extractVoiceImagePrompt(text), null);
  }
});

test('voice image requests preserve explicit subjects', () => {
  assert.equal(extractVoiceImagePrompt('make me a picture of a tank crossing a flooded street'), 'a tank crossing a flooded street');
  assert.equal(extractVoiceImagePrompt('show me a portrait of Venice wearing a red coat'), 'Venice wearing a red coat');
});

test('Venice identity intent distinguishes the woman from the city', () => {
  assert.equal(requestsVeniceIdentity('portrait of Venice wearing a red coat'), true);
  assert.equal(requestsVeniceIdentity('show Venice standing beside the tank'), true);
  assert.equal(requestsVeniceIdentity('the flooded city of Venice with gondolas and canals'), false);
  assert.equal(requestsVeniceIdentity('Venice canals at sunrise in Italy'), false);
  assert.equal(requestsVeniceIdentity('a tank crossing a flooded street'), false);
});
