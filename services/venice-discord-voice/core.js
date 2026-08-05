'use strict';

const DISCORD_ID = /^\d{1,32}$/;
const MAX_SPEECH_CHARS = 1800;

function validateSpeakRequest(value, expectedGuildId) {
  const body = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const guildId = String(body.guildId || '');
  const userId = String(body.userId || '');
  const roomChannelId = String(body.roomChannelId || '');
  const interactionId = String(body.interactionId || '');
  const text = typeof body.text === 'string' ? body.text.trim() : '';
  const cutEpoch = Number(body.cutEpoch);
  const stateEpoch = Number(body.stateEpoch);
  if (
    guildId !== expectedGuildId
    || !DISCORD_ID.test(userId)
    || !DISCORD_ID.test(roomChannelId)
    || !DISCORD_ID.test(interactionId)
    || !text
    || text.length > MAX_SPEECH_CHARS
    || !Number.isSafeInteger(cutEpoch)
    || cutEpoch < 0
    || !Number.isSafeInteger(stateEpoch)
    || stateEpoch < 0
  ) throw Object.assign(new Error('invalid_speak_request'), {status: 400});
  return {guildId, userId, roomChannelId, interactionId, text, cutEpoch, stateEpoch};
}

function normalizedConsentState(value) {
  const state = value && typeof value === 'object' ? value : {};
  const rooms = state.rooms && typeof state.rooms === 'object' && !Array.isArray(state.rooms)
    ? state.rooms
    : {};
  return {
    state: String(state.state || 'DORMANT'),
    epoch: Number.isSafeInteger(Number(state.epoch)) ? Number(state.epoch) : -1,
    cutEpoch: Number.isSafeInteger(Number(state.cutEpoch)) ? Number(state.cutEpoch) : -1,
    rooms,
  };
}

function stateAllowsSpeech(stateValue, task) {
  const state = normalizedConsentState(stateValue);
  return state.state !== 'CUT'
    && state.cutEpoch === task.cutEpoch
    && state.epoch === task.stateEpoch
    && state.rooms[task.roomChannelId] === 'PRESENT';
}

function publicError(error) {
  const code = String(error && (error.code || error.message) || 'voice_unavailable');
  const allow = new Set([
    'discord_not_ready',
    'consent_state_unavailable',
    'consent_state_changed',
    'user_not_in_voice',
    'voice_permissions_missing',
    'voice_connection_failed',
    'tts_unavailable',
  ]);
  return allow.has(code) ? code : 'voice_unavailable';
}

module.exports = {
  MAX_SPEECH_CHARS,
  normalizedConsentState,
  publicError,
  stateAllowsSpeech,
  validateSpeakRequest,
};
