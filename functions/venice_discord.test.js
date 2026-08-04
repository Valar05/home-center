const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const test = require('node:test');

const {
  VENICE_APPLICATION_ID,
  VENICE_GUILD_ID,
  VENICE_ALLOWED_CHANNEL_IDS,
  createFirestoreStateStore,
  createVeniceDiscordHandler,
  createVeniceGenerationTaskHandler,
  dispatchVeniceInteraction,
  verifyDiscordRequest,
} = require('./venice_discord');

const APP_PERMISSIONS = '84992';

class MemoryStore {
  constructor() {
    this.state = {
      state: 'DORMANT',
      epoch: 0,
      cutEpoch: 0,
      rooms: Object.fromEntries(VENICE_ALLOWED_CHANNEL_IDS.map((channelId) => [channelId, 'DORMANT'])),
    };
    this.audit = new Map();
    this.guardHook = null;
  }

  async execute(context, reducer) {
    const replay = this.audit.get(context.interactionId);
    if (replay) return {...replay, replayed: true};
    const before = {...this.state};
    const reduced = reducer(before);
    const after = {...(reduced.nextState || before)};
    this.state = after;
    const result = {...reduced, before, after, replayed: false};
    this.audit.set(context.interactionId, result);
    return result;
  }

  async guard(cutEpoch, {channelId = '', stateEpoch = null} = {}) {
    if (this.guardHook) await this.guardHook();
    if (this.state.state === 'CUT' || this.state.cutEpoch !== cutEpoch) return false;
    if (channelId && this.state.rooms[channelId] !== 'PRESENT') return false;
    if (Number.isSafeInteger(stateEpoch) && this.state.epoch !== stateEpoch) return false;
    return true;
  }
}

function interaction({
  id,
  channelId = VENICE_ALLOWED_CHANNEL_IDS[0],
  guildId = VENICE_GUILD_ID,
  applicationId = VENICE_APPLICATION_ID,
  command = 'status',
  prompt = 'private prompt that must never enter the audit',
} = {}) {
  const data = command === 'cut-the-cam'
    ? {name: 'cut-the-cam'}
    : {
        name: 'venice',
        options: [{
          type: 1,
          name: command,
          ...(command === 'ask' ? {options: [{type: 3, name: 'prompt', value: prompt}]} : {}),
        }],
      };
  return {
    id: id || crypto.randomUUID(),
    token: 'transient-interaction-token',
    type: 2,
    application_id: applicationId,
    guild_id: guildId,
    channel_id: channelId,
    app_permissions: APP_PERMISSIONS,
    member: {user: {id: 'operator-1'}},
    data,
  };
}

function responseRecorder() {
  return {
    statusCode: 0,
    body: undefined,
    status(code) { this.statusCode = code; return this; },
    set() { return this; },
    type() { return this; },
    send(body) { this.body = body; return this; },
  };
}

function signedRequest(rawBody, privateKey, timestamp = String(Math.floor(Date.now() / 1000))) {
  const signature = crypto.sign(null, Buffer.concat([Buffer.from(timestamp), rawBody]), privateKey).toString('hex');
  return {
    method: 'POST',
    rawBody,
    get(name) {
      if (name === 'X-Signature-Ed25519') return signature;
      if (name === 'X-Signature-Timestamp') return timestamp;
      return '';
    },
  };
}

test('verifies a current Ed25519 Discord signature and rejects tampering', () => {
  const {publicKey, privateKey} = crypto.generateKeyPairSync('ed25519');
  const publicKeyHex = publicKey.export({format: 'der', type: 'spki'}).subarray(-32).toString('hex');
  const timestamp = String(Math.floor(Date.now() / 1000));
  const rawBody = Buffer.from(JSON.stringify({type: 1}), 'utf8');
  const signature = crypto.sign(null, Buffer.concat([Buffer.from(timestamp), rawBody]), privateKey).toString('hex');

  assert.equal(verifyDiscordRequest({signature, timestamp, rawBody, publicKeyHex}), true);
  assert.equal(verifyDiscordRequest({signature, timestamp, rawBody: Buffer.from('{"type":2}'), publicKeyHex}), false);
  assert.equal(verifyDiscordRequest({signature, timestamp: String(Number(timestamp) - 600), rawBody, publicKeyHex}), false);
});

test('the HTTPS handler acknowledges PING and rejects invalid or malformed requests', async () => {
  const {publicKey, privateKey} = crypto.generateKeyPairSync('ed25519');
  const publicKeyHex = publicKey.export({format: 'der', type: 'spki'}).subarray(-32).toString('hex');
  const handler = createVeniceDiscordHandler({
    publicKeyGetter: () => publicKeyHex,
    store: {execute: async () => { throw new Error('PING must not touch state'); }},
  });

  const pingResponse = responseRecorder();
  await handler(signedRequest(Buffer.from(JSON.stringify({type: 1})), privateKey), pingResponse);
  assert.equal(pingResponse.statusCode, 200);
  assert.deepEqual(pingResponse.body, {type: 1});

  const invalidResponse = responseRecorder();
  const invalidRequest = signedRequest(Buffer.from(JSON.stringify({type: 1})), privateKey);
  invalidRequest.get = (name) => name === 'X-Signature-Timestamp' ? String(Math.floor(Date.now() / 1000)) : '00';
  await handler(invalidRequest, invalidResponse);
  assert.equal(invalidResponse.statusCode, 401);

  const nullResponse = responseRecorder();
  await handler(signedRequest(Buffer.from('null'), privateKey), nullResponse);
  assert.equal(nullResponse.statusCode, 400);

  const oversizedResponse = responseRecorder();
  await handler({method: 'POST', rawBody: Buffer.alloc(256 * 1024 + 1), get: () => ''}, oversizedResponse);
  assert.equal(oversizedResponse.statusCode, 413);
});

test('routes only the exact application, guild, and two assigned channels', async () => {
  const store = new MemoryStore();
  for (const channelId of VENICE_ALLOWED_CHANNEL_IDS) {
    const result = await dispatchVeniceInteraction(interaction({channelId, command: 'status'}), store);
    assert.equal(result.status, 200);
    assert.equal(result.body.data.flags, 64);
  }

  for (const payload of [
    interaction({guildId: 'other-guild'}),
    interaction({channelId: 'other-channel'}),
    interaction({applicationId: 'other-app'}),
  ]) {
    const result = await dispatchVeniceInteraction(payload, store);
    assert.equal(result.status, 200);
    assert.equal(result.body.data.flags, 64);
  }
});

test('presence is scoped to the room that received /venice begin', async () => {
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'room-begin', channelId: VENICE_ALLOWED_CHANNEL_IDS[0], command: 'begin'}), store);

  const otherRoom = await dispatchVeniceInteraction(interaction({
    id: 'room-other-ask',
    channelId: VENICE_ALLOWED_CHANNEL_IDS[1],
    command: 'ask',
  }), store);
  const begunRoom = await dispatchVeniceInteraction(interaction({
    id: 'room-begun-ask',
    channelId: VENICE_ALLOWED_CHANNEL_IDS[0],
    command: 'ask',
  }), store);

  assert.equal(otherRoom.body.data.flags, 64);
  assert.match(otherRoom.body.data.content, /not present/i);
  assert.equal(begunRoom.body.data.flags, undefined);
});

test('begin and ask are explicit, public, and do not persist prompt content', async () => {
  const store = new MemoryStore();
  const begin = await dispatchVeniceInteraction(interaction({id: 'begin-1', command: 'begin'}), store);
  assert.equal(begin.status, 200);
  assert.equal(begin.body.data.flags, undefined);
  assert.equal(store.state.state, 'PRESENT');

  const secretPrompt = 'do not store this message body';
  const ask = await dispatchVeniceInteraction(interaction({id: 'ask-1', command: 'ask', prompt: secretPrompt}), store);
  assert.equal(ask.status, 200);
  assert.equal(ask.body.data.flags, undefined);
  assert.doesNotMatch(JSON.stringify([...store.audit.entries()]), new RegExp(secretPrompt));
});

test('the HTTPS handler defers an accepted ask only after a content-bounded task is enqueued', async () => {
  const {publicKey, privateKey} = crypto.generateKeyPairSync('ed25519');
  const publicKeyHex = publicKey.export({format: 'der', type: 'spki'}).subarray(-32).toString('hex');
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'generated-begin', command: 'begin'}), store);
  const secretPrompt = 'A private invitation that must remain transient';
  const payload = interaction({id: 'generated-ask', command: 'ask', prompt: secretPrompt});
  let queuedTask;
  const handler = createVeniceDiscordHandler({
    publicKeyGetter: () => publicKeyHex,
    store,
    enqueueGeneration: async (task) => { queuedTask = task; },
  });
  const response = responseRecorder();

  await handler(signedRequest(Buffer.from(JSON.stringify(payload)), privateKey), response);

  assert.equal(response.statusCode, 200);
  assert.deepEqual(response.body, {type: 5, data: {}});
  assert.equal(queuedTask.prompt, secretPrompt);
  assert.equal(queuedTask.interactionToken, 'transient-interaction-token');
  assert.equal(queuedTask.cutEpoch, 0);
  assert.equal(queuedTask.stateEpoch, 1);
  assert.doesNotMatch(JSON.stringify([...store.audit.entries()]), new RegExp(secretPrompt));
});

test('an authenticated generation task delivers one bounded reply without mentions or content persistence', async () => {
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'generation-task-begin', command: 'begin'}), store);
  const secretPrompt = 'A task prompt that remains outside Firestore';
  const webhookCalls = [];
  const handler = createVeniceGenerationTaskHandler({
    verifyTaskRequest: async () => true,
    store,
    generateReply: async (task) => task.prompt === secretPrompt ? 'Venice answers without pinging @everyone.' : '',
    webhookFetch: async (url, options) => {
      webhookCalls.push({url, options});
      return {ok: true, status: 200};
    },
  });
  const response = responseRecorder();
  await handler({body: {
    applicationId: VENICE_APPLICATION_ID,
    interactionToken: 'transient-interaction-token',
    interactionId: '1234567890',
    channelId: VENICE_ALLOWED_CHANNEL_IDS[0],
    userId: '1234567890',
    prompt: secretPrompt,
    cutEpoch: 0,
    stateEpoch: 1,
  }}, response);

  assert.equal(response.statusCode, 204);
  assert.equal(webhookCalls.length, 1);
  assert.equal(webhookCalls[0].options.method, 'PATCH');
  assert.deepEqual(JSON.parse(webhookCalls[0].options.body), {
    content: 'Venice answers without pinging @everyone.',
    allowed_mentions: {parse: []},
  });
  assert.doesNotMatch(JSON.stringify([...store.audit.entries()]), new RegExp(secretPrompt));
});

test('a global cut racing an authenticated generation task deletes the deferred response', async () => {
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'generation-cut-begin', command: 'begin'}), store);
  const webhookCalls = [];
  const handler = createVeniceGenerationTaskHandler({
    verifyTaskRequest: async () => true,
    store,
    generateReply: async () => {
      store.state = {...store.state, state: 'CUT', epoch: store.state.epoch + 1, cutEpoch: store.state.cutEpoch + 1};
      return 'This output must never be published.';
    },
    webhookFetch: async (url, options) => {
      webhookCalls.push({url, options});
      return {ok: true, status: 204};
    },
  });
  const response = responseRecorder();
  await handler({body: {
    applicationId: VENICE_APPLICATION_ID,
    interactionToken: 'transient-interaction-token',
    interactionId: '1234567891',
    channelId: VENICE_ALLOWED_CHANNEL_IDS[0],
    userId: '1234567890',
    prompt: 'Answer after a racing cut',
    cutEpoch: 0,
    stateEpoch: 1,
  }}, response);

  assert.equal(response.statusCode, 204);
  assert.deepEqual(webhookCalls.map((call) => call.options.method), ['DELETE']);
  assert.doesNotMatch(JSON.stringify(webhookCalls), /must never be published/i);
});

test('room withdrawal before task execution deletes the deferred response without calling the provider', async () => {
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'generation-withdraw-begin', command: 'begin'}), store);
  await dispatchVeniceInteraction(interaction({id: 'generation-withdraw', command: 'withdraw'}), store);
  const webhookCalls = [];
  let generated = false;
  const handler = createVeniceGenerationTaskHandler({
    verifyTaskRequest: async () => true,
    store,
    generateReply: async () => { generated = true; return 'must not run'; },
    webhookFetch: async (url, options) => {
      webhookCalls.push({url, options});
      return {ok: true, status: 204};
    },
  });
  const response = responseRecorder();
  await handler({body: {
    applicationId: VENICE_APPLICATION_ID,
    interactionToken: 'transient-interaction-token',
    interactionId: '1234567893',
    channelId: VENICE_ALLOWED_CHANNEL_IDS[0],
    userId: '1234567890',
    prompt: 'This invitation was withdrawn before execution',
    cutEpoch: 0,
    stateEpoch: 1,
  }}, response);

  assert.equal(response.statusCode, 204);
  assert.equal(generated, false);
  assert.deepEqual(webhookCalls.map((call) => call.options.method), ['DELETE']);
});

test('generation task failure produces only a content-free safe follow-up and logs', async () => {
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'generation-failure-begin', command: 'begin'}), store);
  const secretPrompt = 'failure prompt that cannot enter logs';
  const webhookCalls = [];
  const logs = [];
  const handler = createVeniceGenerationTaskHandler({
    verifyTaskRequest: async () => true,
    store,
    generateReply: async () => { throw new Error(secretPrompt); },
    webhookFetch: async (url, options) => {
      webhookCalls.push({url, options});
      return {ok: true, status: 200};
    },
    logger: {error: (...args) => logs.push(args)},
  });
  const response = responseRecorder();
  await handler({body: {
    applicationId: VENICE_APPLICATION_ID,
    interactionToken: 'transient-interaction-token',
    interactionId: '1234567892',
    channelId: VENICE_ALLOWED_CHANNEL_IDS[0],
    userId: '1234567890',
    prompt: secretPrompt,
    cutEpoch: 0,
    stateEpoch: 1,
  }}, response);

  assert.equal(response.statusCode, 204);
  assert.equal(webhookCalls.length, 1);
  assert.equal(webhookCalls[0].options.method, 'PATCH');
  assert.match(JSON.parse(webhookCalls[0].options.body).content, /could not answer/i);
  assert.doesNotMatch(JSON.stringify(logs), new RegExp(secretPrompt));
  assert.doesNotMatch(JSON.stringify([...store.audit.entries()]), new RegExp(secretPrompt));
});

test('generation tasks fail closed without authenticated queue identity', async () => {
  const store = new MemoryStore();
  const handler = createVeniceGenerationTaskHandler({
    verifyTaskRequest: async () => false,
    store,
    generateReply: async () => { throw new Error('must not run'); },
  });
  const response = responseRecorder();
  await handler({body: {}}, response);
  assert.equal(response.statusCode, 401);
});

test('/cut-the-cam is global, durable in state, unilateral, and idempotent', async () => {
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'begin-2', command: 'begin'}), store);
  const cutPayload = interaction({id: 'cut-1', channelId: VENICE_ALLOWED_CHANNEL_IDS[1], command: 'cut-the-cam'});
  const first = await dispatchVeniceInteraction(cutPayload, store);
  const cutEpoch = store.state.epoch;
  const replay = await dispatchVeniceInteraction(cutPayload, store);

  assert.equal(first.status, 200);
  assert.equal(first.body.data.flags, undefined);
  assert.equal(store.state.state, 'CUT');
  assert.equal(replay.status, 200);
  assert.equal(store.state.epoch, cutEpoch);

  for (const channelId of VENICE_ALLOWED_CHANNEL_IDS) {
    const ask = await dispatchVeniceInteraction(interaction({channelId, command: 'ask'}), store);
    assert.equal(ask.status, 200);
    assert.equal(ask.body.data.flags, 64);
    assert.match(ask.body.data.content, /remains cut/i);
  }
});

test('a cut racing an ordinary response cancels that response at the pre-send guard', async () => {
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'begin-3', command: 'begin'}), store);
  store.guardHook = async () => {
    store.state = {
      ...store.state,
      state: 'CUT',
      epoch: store.state.epoch + 1,
      cutEpoch: store.state.cutEpoch + 1,
    };
  };
  const result = await dispatchVeniceInteraction(interaction({id: 'ask-race', command: 'ask'}), store);
  assert.equal(result.status, 200);
  assert.equal(result.body.data.flags, 64);
  assert.match(result.body.data.content, /camera is cut/i);
});

test('a cut racing a public withdrawal cancels the queued withdrawal response', async () => {
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'begin-withdraw-race', command: 'begin'}), store);
  store.guardHook = async () => {
    store.state = {
      ...store.state,
      state: 'CUT',
      epoch: store.state.epoch + 1,
      cutEpoch: store.state.cutEpoch + 1,
    };
  };
  const result = await dispatchVeniceInteraction(interaction({id: 'withdraw-race', command: 'withdraw'}), store);
  assert.equal(result.status, 200);
  assert.equal(result.body.data.flags, 64);
  assert.match(result.body.data.content, /camera is cut/i);
});

test('/cut-the-cam commits CUT even when reply permissions were removed', async () => {
  const store = new MemoryStore();
  const payload = interaction({id: 'cut-no-permissions', command: 'cut-the-cam'});
  payload.app_permissions = '0';
  const result = await dispatchVeniceInteraction(payload, store);
  assert.equal(store.state.state, 'CUT');
  assert.equal(result.status, 200);
  assert.equal(result.body.data.flags, 64);
});

test('a normal room-state change does not masquerade as a global cut', async () => {
  const store = new MemoryStore();
  await dispatchVeniceInteraction(interaction({id: 'begin-race-source', command: 'begin'}), store);
  store.guardHook = async () => {
    const otherChannel = VENICE_ALLOWED_CHANNEL_IDS[1];
    store.state = {
      ...store.state,
      state: 'PRESENT',
      epoch: store.state.epoch + 1,
      rooms: {...store.state.rooms, [otherChannel]: 'PRESENT'},
    };
  };
  const result = await dispatchVeniceInteraction(interaction({id: 'ask-non-cut-race', command: 'ask'}), store);
  assert.equal(result.status, 200);
  assert.equal(result.body.data.flags, undefined);
  assert.doesNotMatch(result.body.data.content, /camera is cut/i);
});

class FakeSnapshot {
  constructor(value) {
    this.value = value;
    this.exists = value !== undefined;
  }
  data() { return this.value === undefined ? undefined : structuredClone(this.value); }
}

class FakeFirestore {
  constructor() {
    this.documents = new Map();
    this.queue = Promise.resolve();
  }
  collection(name) {
    return {
      doc: (id) => {
        const key = `${name}/${id}`;
        return {
          key,
          get: async () => new FakeSnapshot(this.documents.get(key)),
        };
      },
    };
  }
  runTransaction(callback) {
    const run = this.queue.then(async () => {
      const writes = [];
      const transaction = {
        get: async (reference) => new FakeSnapshot(this.documents.get(reference.key)),
        set: (reference, value, options) => writes.push({reference, value, options}),
      };
      const result = await callback(transaction);
      for (const write of writes) {
        const existing = this.documents.get(write.reference.key) || {};
        this.documents.set(
          write.reference.key,
          write.options?.merge ? {...existing, ...structuredClone(write.value)} : structuredClone(write.value),
        );
      }
      return result;
    });
    this.queue = run.catch(() => {});
    return run;
  }
}

test('Firestore state survives store instances, serializes cuts, and expires content-free audit metadata', async () => {
  const firestore = new FakeFirestore();
  const fieldValue = {serverTimestamp: () => ({serverTimestamp: true})};
  const nowMs = Date.UTC(2026, 7, 4, 12, 0, 0);
  const firstStore = createFirestoreStateStore({firestore, fieldValue, now: () => nowMs});
  const secondStore = createFirestoreStateStore({firestore, fieldValue, now: () => nowMs});
  const beginContext = {
    interactionId: 'persisted-begin',
    applicationId: VENICE_APPLICATION_ID,
    guildId: VENICE_GUILD_ID,
    channelId: VENICE_ALLOWED_CHANNEL_IDS[0],
    userId: 'operator-1',
    command: 'venice.begin',
  };
  await firstStore.execute(beginContext, (before) => ({
    nextState: {
      ...before,
      state: 'PRESENT',
      epoch: before.epoch + 1,
      cutEpoch: before.cutEpoch,
      rooms: {...before.rooms, [beginContext.channelId]: 'PRESENT'},
    },
    outcome: 'begun',
    responseKey: 'begun',
    public: true,
    controlPlane: false,
  }));
  assert.equal(await secondStore.guard(0), true);

  const cutReducer = (before) => ({
    nextState: before.state === 'CUT'
      ? before
      : {...before, state: 'CUT', epoch: before.epoch + 1, cutEpoch: before.cutEpoch + 1},
    outcome: before.state === 'CUT' ? 'already_cut' : 'cut',
    responseKey: 'cut',
    public: true,
    controlPlane: true,
  });
  await Promise.all([
    firstStore.execute({...beginContext, interactionId: 'persisted-cut-1', command: 'cut-the-cam'}, cutReducer),
    secondStore.execute({...beginContext, interactionId: 'persisted-cut-2', command: 'cut-the-cam'}, cutReducer),
  ]);
  const persistedState = firestore.documents.get('veniceDiscord/runtime');
  assert.equal(persistedState.state, 'CUT');
  assert.equal(persistedState.epoch, 2);
  assert.equal(persistedState.cutEpoch, 1);

  const replay = await secondStore.execute({...beginContext, interactionId: 'persisted-cut-1', command: 'cut-the-cam'}, cutReducer);
  assert.equal(replay.replayed, true);
  assert.equal(firestore.documents.get('veniceDiscord/runtime').epoch, 2);

  const audit = firestore.documents.get('veniceDiscordAudit/persisted-begin');
  assert.equal(audit.expireAt.toISOString(), new Date(nowMs + 30 * 24 * 60 * 60 * 1000).toISOString());
  assert.doesNotMatch(JSON.stringify([...firestore.documents.entries()]), /private prompt|message body/i);
});

test('the HTTPS handler fails closed when state storage fails', async () => {
  const {publicKey, privateKey} = crypto.generateKeyPairSync('ed25519');
  const publicKeyHex = publicKey.export({format: 'der', type: 'spki'}).subarray(-32).toString('hex');
  const timestamp = String(Math.floor(Date.now() / 1000));
  const payload = interaction({id: 'store-failure', command: 'status'});
  const rawBody = Buffer.from(JSON.stringify(payload));
  const signature = crypto.sign(null, Buffer.concat([Buffer.from(timestamp), rawBody]), privateKey).toString('hex');
  const logs = [];
  const handler = createVeniceDiscordHandler({
    publicKeyGetter: () => publicKeyHex,
    store: {execute: async () => { throw new Error('store unavailable'); }},
    logger: {error: (...args) => logs.push(args)},
  });
  const response = responseRecorder();
  await handler({
    method: 'POST',
    rawBody,
    get(name) {
      if (name === 'X-Signature-Ed25519') return signature;
      if (name === 'X-Signature-Timestamp') return timestamp;
      return '';
    },
  }, response);

  assert.equal(response.statusCode, 503);
  assert.equal(response.body, '');
  assert.deepEqual(logs, [[
    'venice_discord_interaction_failed',
    {interactionId: 'store-failure', outcome: 'fail_closed'},
  ]]);
  assert.doesNotMatch(JSON.stringify(logs), /private prompt|message body/i);
});
