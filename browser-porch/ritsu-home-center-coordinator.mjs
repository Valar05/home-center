// Instance-scoped Home Center turn coordinator for ChatGPT/Chromium Throne.
// No global state, no singleton exports, no Android secret, no direct
// browser access except via injected authenticated adapter.
// Designed for one front CONTROL thread and one DIALOGUE thread now.
// A bounded WORKER result may be staged later; workers NEVER route commands.
import {validateRitsuTurn, toThroneCommand, readRitsuResult} from './ritsu-turn-protocol.mjs';

const ID = /^[A-Za-z0-9_.:-]{8,100}$/;
const MAX_TURNS = 128;
const MAX_WORKER_RESULTS = 32;
const MAX_EVENTS = 256;
const MAX_PROMPT = 5000;

function id(value, name) {
  if (!ID.test(String(value ?? ''))) throw new Error(name + '_invalid');
  return String(value);
}
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function boundedText(value, field) {
  if (typeof value !== 'string' || !value.trim() || value.length > MAX_PROMPT)
    throw new Error(field + '_invalid');
  return value;
}
function initial(namespace, controlSessionId, dialogueSessionId) {
  return {schema: 1, namespace, controlSessionId, dialogueSessionId,
    sequence: 0, turns: [], workerResults: [], timeline: []};
}
function receipt(state, type, fields={}) {
  const sequence = ++state.sequence;
  state.timeline.push({sequence, type, ...fields});
  if (state.timeline.length > MAX_EVENTS) state.timeline.shift();
  return sequence;
}
function validateState(s, namespace, controlId, dialogueId) {
  if (!s || s.schema !== 1 || s.namespace !== namespace ||
      s.controlSessionId !== controlId || s.dialogueSessionId !== dialogueId ||
      !Array.isArray(s.turns) || !Array.isArray(s.workerResults) ||
      !Array.isArray(s.timeline) || !Number.isSafeInteger(s.sequence))
    throw new Error('coordinator_state_incompatible_fail_closed');
}

/**
 * store: injected durable {load(namespace),save(namespace,snapshot)}.
 * transport: injected authorized {submit(command),readResult(commandId)}.
 * Both belong to Home Center deployment, NEVER the Android package.
 *
 * NOTE: pre-send 'dispatch_unknown' is persisted BEFORE network write.
 * On restart it is NEVER blindly dispatched again. A real production
 * store must serialize per namespace across processes and its event journal
 * must survive host crash. Inject a stronger storage backend as needed.
 */
export function createRitsuHomeCenterCoordinator({
  namespace, controlSessionId, dialogueSessionId, store, transport,
} = {}) {
  namespace = id(namespace, 'namespace');
  controlSessionId = id(controlSessionId, 'control_session_id');
  dialogueSessionId = id(dialogueSessionId, 'dialogue_session_id');
  if (controlSessionId === dialogueSessionId)
    throw new Error('control_and_dialogue_must_be_distinct');
  if (!store || typeof store.load !== 'function' || typeof store.save !== 'function')
    throw new Error('durable_store_required');
  if (!transport || typeof transport.submit !== 'function' ||
      typeof transport.readResult !== 'function')
    throw new Error('authenticated_throne_adapter_required');

  // Serializes mutation within THIS instance only; nothing process-global.
  let previous = Promise.resolve();
  function exclusive(work) {
    // A single coordinator serializes itself. A file-backed Home Center CLI
    // also provides an inter-process namespace lock; multiple campaign IDs
    // remain independent and there is never a process-global singleton.
    const task = previous.then(() => typeof store.withNamespaceLock === 'function'
      ? store.withNamespaceLock(namespace, work) : work());
    previous = task.catch(() => {});
    return task;
  }
  async function load() {
    const saved = await store.load(namespace);
    const state = saved == null
      ? initial(namespace, controlSessionId, dialogueSessionId) : copy(saved);
    validateState(state, namespace, controlSessionId, dialogueSessionId);
    return state;
  }
  async function save(state) { await store.save(namespace, copy(state)); }
  const getTurn = (state, turnId) => state.turns.find(t => t.turn.turnId === turnId);
  const getWorker = (state, resultId) => state.workerResults.find(w => w.resultId === resultId);

  return Object.freeze({
    async status() {
      return exclusive(async () => copy(await load()));
    },

    async submitUserTurn({turnId, channel='dialogue', prompt}={}) {
      return exclusive(async () => {
        const sessionId = channel === 'control' ? controlSessionId : dialogueSessionId;
        const turn = validateRitsuTurn({sessionId, turnId, channel, prompt});
        const state = await load();
        const found = getTurn(state, turn.turnId);
        if (found) {
          if (JSON.stringify(found.turn) !== JSON.stringify(turn))
            throw new Error('turn_id_collision');
          return copy(found); // No duplicate network write, even after restart.
        }
        if (state.turns.length >= MAX_TURNS)
          throw new Error('coordinator_capacity_requires_checkpoint');
        // An earlier unverified dispatch cannot be replayed, even if another
        // submit request arrives with the same ID.
        const row = {turn, commandId: toThroneCommand(turn).commandId,
          state: 'dispatch_unknown', result: null, presented: false};
        state.turns.push(row);
        receipt(state, 'user_turn_prepared', {turnId, channel});
        await save(state);
        try {
          // POST is idempotent at the live relay; durable preparation also
          // prevents blind retries after a Home Center restart.
          const reply = await transport.submit(toThroneCommand(turn, 'home-center'));
          if (!reply || reply.commandId !== row.commandId ||
              reply.ok !== true || !['queued', 'leased', 'completed'].includes(reply.state))
            throw new Error('unverified_throne_submission');
          row.state = reply.state;
          receipt(state, 'throne_submission_ack', {turnId, channel, state: row.state});
        } catch (error) {
          row.state = 'dispatch_unknown';
          receipt(state, 'throne_submission_uncertain', {turnId, channel});
        }
        await save(state);
        return copy(row);
      });
    },

    async readOneTurn(turnId) {
      return exclusive(async () => {
        turnId = id(turnId, 'turn_id');
        const state = await load();
        const row = getTurn(state, turnId);
        if (!row) throw new Error('turn_not_found');
        if (row.state === 'completed' || row.state === 'failed' ||
            row.state === 'unknown') return copy(row);
        // Dispatch_unknown is not proof the command was accepted by relay.
        // Only status readback is permitted, NEVER another POST.
        let remote;
        try {
          remote = await transport.readResult(row.commandId);
        } catch {
          return copy(row);
        }
        if (!remote) return copy(row);
        let result;
        try { result = readRitsuResult(remote, row.turn); }
        catch {
          row.state = 'unknown';
          receipt(state, 'result_identity_rejected', {turnId, channel: row.turn.channel});
          await save(state);
          return copy(row);
        }
        if (result.state === 'pending') {
          // Keep uncertain local pre-send marker until a verifiable result.
          if (row.state !== 'dispatch_unknown') row.state = remote.state;
        } else if (result.state === 'completed') {
          row.state = 'completed';
          row.result = {text: result.text, tabId: result.tabId,
            sessionId: result.sessionId, turnId, channel: result.channel};
          // A DIALOGUE result is projected as a candidate, NOT automatically
          // merged as a main/control response. Main thread is presentation owner.
          receipt(state, 'result_staged_for_main_thread', {
            turnId, channel: row.turn.channel, tabId: result.tabId});
        } else {
          row.state = result.state === 'unknown' ? 'unknown' : 'failed';
          receipt(state, 'throne_completion_not_accepted', {
            turnId, channel: row.turn.channel, state: row.state});
        }
        await save(state);
        return copy(row);
      });
    },

    async stageWorkerResult({resultId, jobId, sessionId, text, receiptId}={}) {
      return exclusive(async () => {
        resultId = id(resultId, 'result_id');
        jobId = id(jobId, 'job_id');
        sessionId = id(sessionId, 'worker_session_id');
        receiptId = id(receiptId, 'receipt_id');
        text = boundedText(text, 'worker_text');
        const state = await load();
        const existing = getWorker(state, resultId);
        if (existing) {
          if (existing.jobId !== jobId || existing.sessionId !== sessionId ||
              existing.text !== text || existing.receiptId !== receiptId)
            throw new Error('worker_result_id_collision');
          return copy(existing);
        }
        if (state.workerResults.length >= MAX_WORKER_RESULTS)
          throw new Error('worker_result_capacity_requires_checkpoint');
        const row={resultId, jobId, sessionId, text, receiptId,
          published: false, review: 'pending'};
        row.arrivalSequence=receipt(state, 'worker_result_staged', {resultId,jobId,receiptId});
        state.workerResults.push(row);
        await save(state);
        return copy(row);
      });
    },

    /** Only an authenticated Home Center main-thread operation is allowed to
     * call this. A completed CONTROL conversation turn provides provenance,
     * not implicit permission to execute worker content as instructions. */
    async mainThreadPublish({controlTurnId, turnIds=[], resultIds=[]}={}) {
      return exclusive(async () => {
        controlTurnId = id(controlTurnId, 'control_turn_id');
        if (!Array.isArray(resultIds) || !Array.isArray(turnIds) ||
            resultIds.length + turnIds.length < 1 ||
            resultIds.length + turnIds.length > 8 ||
            new Set(resultIds).size !== resultIds.length ||
            new Set(turnIds).size !== turnIds.length)
          throw new Error('bounded_unique_merge_ids_required');
        const state = await load();
        const control = getTurn(state, controlTurnId);
        if (!control || control.turn.channel !== 'control' ||
            control.state !== 'completed')
          throw new Error('verified_main_control_turn_required');
        const selectedTurns = turnIds.map(turnId => {
          const row = getTurn(state, id(turnId, 'turn_id'));
          if (!row || row.turn.channel !== 'dialogue' ||
              row.state !== 'completed' || row.presented)
            throw new Error('dialogue_turn_not_staged');
          return row;
        });
        const selected = resultIds.map(resultId => {
          const row = getWorker(state, id(resultId, 'result_id'));
          if (!row || row.review !== 'pending') throw new Error('worker_result_not_pending');
          return row;
        }).sort((a,b)=>a.arrivalSequence-b.arrivalSequence);
        for (const row of selectedTurns) {
          row.presented = true;
          row.publishedByTurnId = controlTurnId;
          row.publicationSequence = receipt(state, 'dialogue_result_published_by_main', {
            turnId:row.turn.turnId,controlTurnId});
        }
        for (const row of selected) {
          row.review = 'published';
          row.published = true;
          row.publishedByTurnId = controlTurnId;
          row.publicationSequence = receipt(state, 'worker_result_published_by_main', {
            resultId:row.resultId, controlTurnId});
        }
        await save(state);
        return [...selectedTurns.map(row => ({
          type:'chat_result', channel:'dialogue',
          turnId:row.turn.turnId, text:row.result.text,
          publishedByTurnId:controlTurnId,
          sequence:row.publicationSequence,
        })), ...selected.map(row => ({
          type:'worker_result', resultId:row.resultId, text:row.text,
          publishedByTurnId:controlTurnId,sequence:row.publicationSequence,
        }))].sort((a,b)=>a.sequence-b.sequence);
      });
    },

    async projectedFeed() {
      return exclusive(async () => {
        const state=await load();
        const events=[];
        // Only CONTROL and explicitly approved dialogue/worker results are
        // projected to the outward merged feed. Other results stay private
        // staged data until a verified control turn authorizes publication.
        for (const row of state.turns) {
          if (row.state !== 'completed') continue;
          if (row.turn.channel === 'control') {
            events.push({
              type:'chat_result', channel:'control',turnId:row.turn.turnId,
              sessionId:row.turn.sessionId,tabId:row.result.tabId,
              text:row.result.text,disposition:'main_thread',
              sequence:state.timeline.find(e =>
                e.type==='result_staged_for_main_thread' &&
                e.turnId===row.turn.turnId)?.sequence || 0,
            });
          } else if (row.presented) {
            events.push({
              type:'chat_result',channel:'dialogue',turnId:row.turn.turnId,
              sessionId:row.turn.sessionId,tabId:row.result.tabId,
              text:row.result.text,publishedByTurnId:row.publishedByTurnId,
              sequence:row.publicationSequence,
            });
          }
        }
        for (const row of state.workerResults) {
          if (row.published) events.push({
            type:'worker_result', channel:'worker', resultId:row.resultId,
            jobId:row.jobId, receiptId:row.receiptId, text:row.text,
            publishedByTurnId:row.publishedByTurnId,
            sequence:row.publicationSequence});
        }
        return copy(events.sort((a,b)=>a.sequence-b.sequence));
      });
    },
  });
}
