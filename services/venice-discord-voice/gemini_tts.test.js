'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {SAMPLE_RATE, synthesizeGeminiPcm} = require('./gemini_tts');

function audiblePcm() {
  const frames = Math.floor(SAMPLE_RATE / 10);
  const pcm = Buffer.alloc(frames * 2);
  for (let index = 0; index < frames; index += 1) pcm.writeInt16LE(index % 2 ? 4000 : -4000, index * 2);
  return pcm;
}

test('whisper mode sends an intelligible whisper direction and governed voice', async () => {
  let requestBody;
  const speech = await synthesizeGeminiPcm({
    apiKey: 'test-key',
    text: 'Venice lowers her voice.',
    voiceMode: 'whisper',
    voiceName: 'Achernar',
    fetchImpl: async (_url, options) => {
      requestBody = JSON.parse(options.body);
      return {
        ok: true,
        json: async () => ({output_audio: {data: audiblePcm().toString('base64'), sample_rate: SAMPLE_RATE}}),
      };
    },
  });
  assert.match(requestBody.input, /fully intelligible whisper/i);
  assert.deepEqual(requestBody.generation_config.speech_config, [{voice: 'Achernar'}]);
  assert.equal(speech.voiceMode, 'whisper');
  assert.equal(speech.voiceName, 'Achernar');
});

test('unknown direction and voice fail safely to the chipper candidate', async () => {
  let requestBody;
  const speech = await synthesizeGeminiPcm({
    apiKey: 'test-key',
    text: 'Venice greets Drew.',
    voiceMode: 'untrusted',
    voiceName: 'NotARealVoice',
    fetchImpl: async (_url, options) => {
      requestBody = JSON.parse(options.body);
      return {
        ok: true,
        json: async () => ({output_audio: {data: audiblePcm().toString('base64'), sample_rate: SAMPLE_RATE}}),
      };
    },
  });
  assert.match(requestBody.input, /brightly, chipper/i);
  assert.deepEqual(requestBody.generation_config.speech_config, [{voice: 'Zephyr'}]);
  assert.equal(speech.voiceMode, 'chipper');
});
