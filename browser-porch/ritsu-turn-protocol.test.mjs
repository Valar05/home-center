import test from 'node:test';
import assert from 'node:assert/strict';
import {validateRitsuTurn, toThroneCommand, readRitsuResult} from './ritsu-turn-protocol.mjs';
const input = {sessionId:'session-ritsu-0001', turnId:'turn-ritsu-0001', channel:'dialogue', prompt:'Say hello exactly once.'};
test('Ritsu turns preserve bounded user text and durable session identity', () => {
  const cmd = toThroneCommand(input);
  assert.equal(cmd.action, 'chat.turn');
  assert.equal(cmd.commandId, 'ritsu.turn-ritsu-0001');
  assert.equal(cmd.turn.prompt, input.prompt);
  assert.equal(cmd.turn.channel, 'dialogue');
  assert.equal(cmd.turn.sessionId, input.sessionId);
});
test('control and dialogue channels are segregated', () => {
  assert.equal(validateRitsuTurn({...input,channel:'control'}).channel,'control');
  assert.throws(()=>validateRitsuTurn({...input,channel:'swarm'}),/unsupported_chat_channel/);
});
test('blank, oversized and malformed turns cannot enter the browser lane', () => {
  for (const prompt of ['', '  ', 'x'.repeat(5001)])
    assert.throws(()=>toThroneCommand({...input,prompt}),/bounded_nonempty_prompt_required/);
  assert.throws(()=>toThroneCommand({...input,turnId:'%'}),/stable_session_and_turn_ids_required/);
});
test('successful response must match command, channel, turn and session', () => {
  const result={ok:true,sessionId:input.sessionId,turnId:input.turnId,channel:input.channel,tabId:12,text:'Hello.'};
  const status={commandId:'ritsu.turn-ritsu-0001',state:'completed',result};
  assert.equal(readRitsuResult(status,input).text,'Hello.');
  assert.throws(()=>readRitsuResult({...status,result:{...result,sessionId:'other-session'}},input),/reply_receipt_invalid/);
  assert.throws(()=>readRitsuResult({...status,commandId:'ritsu.wrong'},input),/command_id_mismatch/);
});
test('uncertain completion is never converted into permission to resend', () => {
  const result=readRitsuResult({commandId:'ritsu.turn-ritsu-0001',state:'uncertain'},input);
  assert.equal(result.state,'unknown');
  assert.match(result.reason,/do_not_retry/);
});
