#!/usr/bin/env node

import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  agentMailOperationRegistry,
  agentMailOperationRunOperation,
  sendAgentMail,
  inboxAgentMail,
  acknowledgeAgentMail,
  replyAgentMail,
} = require('./agent_mail.js');

function matches(payload, field, op, value) {
  if (op === '==') return payload[field] === value;
  if (op === 'array-contains') return Array.isArray(payload[field]) && payload[field].includes(value);
  throw new Error(`Unsupported fake query op: ${op}`);
}

function fakeAdmin() {
  const docs = new Map();
  let autoId = 0;
  const makeSnapshot = (key) => ({
    exists: docs.has(key),
    id: key.split('/').at(-1),
    data: () => docs.get(key),
  });
  const makeRef = (collection, id) => {
    const key = `${collection}/${id}`;
    return {
      id,
      key,
      async get() {
        return makeSnapshot(key);
      },
      async set(payload, options = {}) {
        const next = options.merge && docs.has(key) ? {...docs.get(key), ...payload} : payload;
        docs.set(key, structuredClone(next));
      },
    };
  };
  const query = (collection, filters = [], maximum = 1000) => ({
    where(field, op, value) {
      return query(collection, [...filters, {field, op, value}], maximum);
    },
    limit(value) {
      return query(collection, filters, value);
    },
    async get() {
      const rows = [];
      for (const [key, payload] of docs.entries()) {
        if (!key.startsWith(`${collection}/`)) continue;
        if (!filters.every((filter) => matches(payload, filter.field, filter.op, filter.value))) continue;
        rows.push({id: key.split('/').at(-1), data: () => structuredClone(payload)});
      }
      return {empty: rows.length === 0, docs: rows.slice(0, maximum)};
    },
  });
  const db = {
    collection(name) {
      return {
        doc(id) {
          return makeRef(name, id);
        },
        where(field, op, value) {
          return query(name, [{field, op, value}]);
        },
        async add(payload) {
          autoId += 1;
          const ref = makeRef(name, `auto-${autoId}`);
          await ref.set(payload);
          return ref;
        },
      };
    },
    async runTransaction(callback) {
      const writes = [];
      const tx = {
        async get(ref) {
          return makeSnapshot(ref.key);
        },
        set(ref, payload, options = {}) {
          writes.push({ref, payload: structuredClone(payload), options});
        },
      };
      const result = await callback(tx);
      for (const write of writes) await write.ref.set(write.payload, write.options);
      return result;
    },
  };
  return {
    _docs: docs,
    firestore() {
      return db;
    },
  };
}

const drew = {email: 'drew@example.com', uid: 'drew', authKind: 'test'};
const june = {email: 'june@example.com', uid: 'june', authKind: 'test'};

async function main() {
  const admin = fakeAdmin();
  const sent = await sendAgentMail({
    admin,
    user: drew,
    args: {
      spaceId: 'holocron',
      fromAgent: 'adam',
      toAgents: ['eve'],
      subject: 'Mailbox smoke',
      body: 'Reply with the active doctrine ID.',
      messageType: 'request',
      requestId: 'agent-mail-send-001',
    },
  });
  assert.match(sent.message.messageId, /^msg_[a-f0-9]{32}$/);
  assert.equal(sent.message.authority, 'proposal');
  assert.equal(sent.message.status, 'sent');

  const replay = await sendAgentMail({
    admin,
    user: drew,
    args: {
      spaceId: 'holocron',
      fromAgent: 'adam',
      toAgents: ['eve'],
      body: 'This replay must not replace the original.',
      requestId: 'agent-mail-send-001',
    },
  });
  assert.equal(replay.idempotent, true);
  assert.equal(replay.message.body, 'Reply with the active doctrine ID.');

  const inbox = await inboxAgentMail({admin, args: {spaceId: 'holocron', agentId: 'eve'}});
  assert.equal(inbox.count, 1);
  assert.equal(inbox.messages[0].subject, 'Mailbox smoke');

  const ack = await acknowledgeAgentMail({
    admin,
    user: june,
    args: {
      messageId: sent.message.messageId,
      agentId: 'eve',
      note: 'Received.',
      requestId: 'agent-mail-ack-001',
    },
  });
  assert.equal(ack.message.status, 'acknowledged');
  assert.equal(ack.message.acknowledgedAgents.includes('eve'), true);

  const empty = await inboxAgentMail({admin, args: {spaceId: 'holocron', agentId: 'eve'}});
  assert.equal(empty.count, 0);

  const reply = await replyAgentMail({
    admin,
    user: june,
    args: {
      replyTo: sent.message.messageId,
      fromAgent: 'eve',
      body: 'The canonical active doctrine ID is 1209.',
      authority: 'information',
      requestId: 'agent-mail-reply-001',
    },
  });
  assert.equal(reply.message.threadId, sent.message.threadId);
  assert.deepEqual(reply.message.toAgents, ['adam']);

  const adamInbox = await agentMailOperationRunOperation({
    admin,
    user: drew,
    args: {operation: 'agent_mail.inbox', args: {spaceId: 'holocron', agentId: 'adam'}},
  });
  assert.equal(adamInbox.result.count, 1);
  assert.equal(adamInbox.result.messages[0].fromAgent, 'eve');

  const registry = agentMailOperationRegistry();
  assert.equal(registry.operations['agent_mail.send'].write, true);
  assert.equal(registry.operations['agent_mail.inbox'].write, false);
  assert.match(registry.authorityBoundary, /not Holocron canon/i);

  await assert.rejects(
    () => sendAgentMail({admin, user: drew, args: {fromAgent: 'Adam Smith', toAgent: 'eve', body: 'bad', requestId: 'agent-mail-bad-001'}}),
    /lowercase agent address/,
  );

  console.log('Agent mail contract: OK');
}

await main();
