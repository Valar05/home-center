// Pure deterministic wire protocol between Ritsu cockpit and Chromium Throne.
// No audio and no Home Center account secret is managed here.
const ID = /^[A-Za-z0-9_.:-]{8,100}$/;
export const RITSU_TURN_VERSION = 'ritsu.chat.turn.v1';
export function validateRitsuTurn(value) {
  if (!value || typeof value !== 'object') throw new Error('turn_object_required');
  const sessionId = String(value.sessionId || '');
  const turnId = String(value.turnId || '');
  const channel = String(value.channel || 'dialogue');
  const prompt = value.prompt;
  if (!ID.test(sessionId) || !ID.test(turnId)) throw new Error('stable_session_and_turn_ids_required');
  if (!['control', 'dialogue'].includes(channel)) throw new Error('unsupported_chat_channel');
  if (typeof prompt !== 'string' || !prompt.trim() || prompt.length > 5000) throw new Error('bounded_nonempty_prompt_required');
  return Object.freeze({version: RITSU_TURN_VERSION, sessionId, turnId, channel, prompt});
}
export function toThroneCommand(turn, source = 'ritsu-cockpit') {
  const v = validateRitsuTurn(turn);
  return Object.freeze({commandId: `ritsu.${v.turnId}`, action: 'chat.turn', source, turn: v});
}
export function readRitsuResult(status, expected) {
  const turn = validateRitsuTurn(expected);
  if (!status || status.commandId !== `ritsu.${turn.turnId}`) throw new Error('command_id_mismatch');
  if (status.state === 'queued' || status.state === 'leased') return {state: 'pending'};
  if (status.state === 'uncertain') return {state: 'unknown', reason: 'unconfirmed_browser_dispatch_do_not_retry'};
  if (status.state !== 'completed') return {state: 'failed', reason: status.result?.error || status.state};
  const result = status.result;
  if (!result || result.ok !== true || result.sessionId !== turn.sessionId ||
      result.turnId !== turn.turnId || result.channel !== turn.channel ||
      !((Number.isInteger(result.tabId)&&result.tabId>0)||
        (typeof result.tabId==='string'&&/^[A-Fa-f0-9]{32}$/.test(result.tabId))) ||
      typeof result.text !== 'string' || !result.text.trim())
      throw new Error('reply_receipt_invalid');
  return {state: 'completed', sessionId: result.sessionId, turnId: result.turnId,
    channel: result.channel, tabId: result.tabId, text: result.text};
}
