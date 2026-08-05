'use strict';

const SAMPLE_RATE = 24000;
const DEFAULT_MODEL = 'gemini-3.1-flash-tts-preview';
const ALLOWED_VOICES = new Set(['Kore', 'Achernar', 'Vindemiatrix', 'Sulafat', 'Zephyr', 'Laomedeia', 'Puck']);
const VOICE_DIRECTIONS = Object.freeze({
  whisper: 'Perform in a close, controlled, fully intelligible whisper. Keep the volume present enough to hear clearly; do not become breath-only.',
  chipper: 'Perform brightly, chipper and conversational, with warm forward energy and crisp articulation.',
  warm: 'Perform with relaxed warmth, gentle emotional presence, and unhurried clarity.',
  firm: 'Perform with composed authority, precision, and calm confidence.',
  playful: 'Perform playfully and lightly, with clean comic timing and lively articulation.',
  gentle: 'Perform gently and softly, with reassuring clarity and no urgency.',
});

function timeoutSignal(milliseconds) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), milliseconds);
  return {signal: controller.signal, clear: () => clearTimeout(timer)};
}

function safeProviderDetail(value) {
  return String(value || '')
    .replace(/(?:AIza|sk-|Bearer\s+)[A-Za-z0-9._-]+/gi, '[REDACTED]')
    .slice(0, 240);
}

function validatePcm(pcm) {
  if (!Buffer.isBuffer(pcm) || pcm.length < SAMPLE_RATE / 10 || pcm.length % 2) {
    throw new Error('tts_unavailable');
  }
  let peak = 0;
  let sumSquares = 0;
  for (let index = 0; index < pcm.length; index += 2) {
    const sample = pcm.readInt16LE(index);
    peak = Math.max(peak, Math.abs(sample));
    sumSquares += sample * sample;
  }
  if (!peak) throw new Error('tts_unavailable');
  const frames = pcm.length / 2;
  return {
    byteCount: pcm.length,
    durationMs: Math.round(frames / SAMPLE_RATE * 1000),
    peak: Number((peak / 32768).toFixed(4)),
    rms: Number((Math.sqrt(sumSquares / frames) / 32768).toFixed(4)),
  };
}

async function synthesizeGeminiPcm({apiKey, text, voiceName = 'Zephyr', voiceMode = 'chipper', fetchImpl = fetch}) {
  const key = String(apiKey || '').trim();
  const transcript = String(text || '').trim();
  const selectedVoice = ALLOWED_VOICES.has(voiceName) ? voiceName : 'Zephyr';
  const selectedMode = VOICE_DIRECTIONS[voiceMode] ? voiceMode : 'chipper';
  if (!key || !transcript || transcript.length > 1800) throw new Error('tts_unavailable');
  const model = String(process.env.VENICE_TTS_MODEL || DEFAULT_MODEL).trim();
  const timer = timeoutSignal(55000);
  try {
    const response = await fetchImpl('https://generativelanguage.googleapis.com/v1beta/interactions', {
      method: 'POST',
      headers: {'content-type': 'application/json', 'x-goog-api-key': key},
      body: JSON.stringify({
        model,
        input: [
          `Director notes (do not speak): Candidate, noncanonical carrier voice. ${VOICE_DIRECTIONS[selectedMode]} Do not imitate a real person.`,
          'Speak the transcript exactly as supplied. Do not add, remove, or paraphrase words.',
          `Transcript:\n${transcript}`,
        ].join('\n'),
        response_format: {type: 'audio'},
        generation_config: {speech_config: [{voice: selectedVoice}]},
      }),
      signal: timer.signal,
    });
    if (!response.ok) {
      const detail = safeProviderDetail(await response.text().catch(() => ''));
      const error = new Error('tts_unavailable');
      error.providerStatus = response.status;
      error.providerDetail = detail;
      throw error;
    }
    const payload = await response.json();
    const audio = payload && payload.output_audio
      || (Array.isArray(payload && payload.steps)
        ? payload.steps.flatMap((step) => Array.isArray(step && step.content) ? step.content : [])
          .filter((content) => content && content.type === 'audio').pop()
        : null);
    if (!audio || typeof audio.data !== 'string') throw new Error('tts_unavailable');
    if (audio.sample_rate !== undefined && Number(audio.sample_rate) !== SAMPLE_RATE) throw new Error('tts_unavailable');
    const pcm = Buffer.from(audio.data, 'base64');
    return {pcm, metrics: validatePcm(pcm), voiceName: selectedVoice, voiceMode: selectedMode, model};
  } catch (error) {
    if (error && error.message === 'tts_unavailable') throw error;
    throw new Error('tts_unavailable');
  } finally {
    timer.clear();
  }
}

module.exports = {ALLOWED_VOICES, DEFAULT_MODEL, SAMPLE_RATE, VOICE_DIRECTIONS, synthesizeGeminiPcm, validatePcm};
