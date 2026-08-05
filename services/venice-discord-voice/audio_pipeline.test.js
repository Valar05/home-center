'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {createDiscordOggStream} = require('./audio_pipeline');

function sinePcm({sampleRate = 24000, seconds = 0.5, frequency = 440, amplitude = 0.2} = {}) {
  const frames = Math.floor(sampleRate * seconds);
  const pcm = Buffer.alloc(frames * 2);
  for (let index = 0; index < frames; index += 1) {
    pcm.writeInt16LE(Math.round(Math.sin(2 * Math.PI * frequency * index / sampleRate) * 32767 * amplitude), index * 2);
  }
  return pcm;
}

test('buffers PCM into a normalized Ogg/Opus stream with receive preroll', async () => {
  const encoded = createDiscordOggStream(sinePcm(), {prerollMs: 1200});
  const chunks = [];
  for await (const chunk of encoded.stream) chunks.push(chunk);
  const result = await encoded.done;
  const ogg = Buffer.concat(chunks);
  assert.equal(ogg.subarray(0, 4).toString('ascii'), 'OggS');
  assert.ok(ogg.length > 1000);
  assert.equal(result.outputBytes, ogg.length);
  assert.equal(result.prerollMs, 1200);
});
