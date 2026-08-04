const crypto = require('crypto');

const VENICE_APPLICATION_ID = '1534113573708763196';
const VENICE_GUILD_ID = '1534104765796192356';
const VENICE_ALLOWED_CHANNEL_IDS = Object.freeze([
  '1534104766643437620',
  '1534105192226623610',
]);
const VENICE_ALLOWED_CHANNEL_SET = new Set(VENICE_ALLOWED_CHANNEL_IDS);
const DISCORD_SEND_MESSAGES = 1n << 11n;
const DISCORD_VIEW_CHANNEL = 1n << 10n;
const DISCORD_EPHEMERAL = 1 << 6;
const SIGNATURE_MAX_AGE_MS = 5 * 60 * 1000;
const MAX_INTERACTION_BODY_BYTES = 256 * 1024;
const AUDIT_RETENTION_MS = 30 * 24 * 60 * 60 * 1000;
const ED25519_SPKI_PREFIX = Buffer.from('302a300506032b6570032100', 'hex');
const ROOM_STATES = new Set(['DORMANT', 'PRESENT', 'WITHDRAWN']);
const GLOBAL_STATES = new Set(['DORMANT', 'PRESENT', 'WITHDRAWN', 'CUT']);

const VENICE_COMMANDS = Object.freeze([
  {
    type: 1,
    name: 'venice',
    description: 'Invite or withdraw Venice in an assigned room.',
    dm_permission: false,
    options: [
      {type: 1, name: 'begin', description: 'Invite Venice into the current scene.'},
      {
        type: 1,
        name: 'ask',
        description: 'Address Venice through the explicit interaction carrier.',
        options: [
          {
            type: 3,
            name: 'prompt',
            description: 'The invitation or question for Venice.',
            required: true,
            min_length: 1,
            max_length: 1800,
          },
        ],
      },
      {type: 1, name: 'withdraw', description: 'Withdraw Venice from the current scene.'},
      {type: 1, name: 'status', description: 'Show the current consent state privately.'},
    ],
  },
  {
    type: 1,
    name: 'cut-the-cam',
    description: 'Immediately stop Venice across every assigned channel.',
    dm_permission: false,
  },
]);

const RESPONSE_TEXT = Object.freeze({
  begun: 'Venice is present. Explicit invitations only; `/cut-the-cam` remains live.',
  asked: 'Venice heard the invitation. The first carrier is live; generative dialogue remains gated.',
  dormant: 'Venice is not present. Use `/venice begin` to open the explicit carrier.',
  withdrawn: 'Venice has withdrawn. No further ordinary output will be produced until `/venice begin`.',
  cut: 'The camera is cut. Venice is silent across every assigned channel.',
  cut_locked: 'The camera remains cut. Recovery is available only through the Home Center control plane.',
  unavailable: 'Venice is unavailable on this route.',
  permissions: 'Venice cannot safely answer with the current channel permissions.',
});

function cloneState(value = {}) {
  const state = GLOBAL_STATES.has(value.state) ? value.state : 'DORMANT';
  const epoch = Number.isSafeInteger(value.epoch) && value.epoch >= 0 ? value.epoch : 0;
  const cutEpoch = Number.isSafeInteger(value.cutEpoch) && value.cutEpoch >= 0 ? value.cutEpoch : 0;
  const rooms = {};
  for (const channelId of VENICE_ALLOWED_CHANNEL_IDS) {
    const roomState = value.rooms?.[channelId];
    rooms[channelId] = ROOM_STATES.has(roomState) ? roomState : 'DORMANT';
  }
  return {state, epoch, cutEpoch, rooms};
}

function interactionContext(interaction, command) {
  return {
    interactionId: String(interaction.id || ''),
    applicationId: String(interaction.application_id || ''),
    guildId: String(interaction.guild_id || ''),
    channelId: String(interaction.channel_id || ''),
    userId: String(interaction.member?.user?.id || interaction.user?.id || ''),
    command,
  };
}

function interactionReply(content, {ephemeral = false} = {}) {
  const data = {
    content,
    allowed_mentions: {parse: []},
  };
  if (ephemeral) data.flags = DISCORD_EPHEMERAL;
  return {type: 4, data};
}

function statusText(state, channelId) {
  const roomState = state.rooms?.[channelId] || 'DORMANT';
  return `Venice global state: **${state.state}** · this room: **${roomState}** · epoch **${state.epoch}**.`;
}

function commandName(interaction) {
  if (interaction.data?.name === 'cut-the-cam') return 'cut-the-cam';
  if (interaction.data?.name !== 'venice') return '';
  const subcommand = interaction.data?.options?.find((option) => option?.type === 1)?.name;
  return subcommand ? `venice.${subcommand}` : '';
}

function hasRequiredAppPermissions(interaction) {
  try {
    const permissions = BigInt(interaction.app_permissions || '0');
    return (permissions & DISCORD_VIEW_CHANNEL) !== 0n && (permissions & DISCORD_SEND_MESSAGES) !== 0n;
  } catch (_) {
    return false;
  }
}

function globalStateForRooms(rooms) {
  const values = Object.values(rooms);
  if (values.includes('PRESENT')) return 'PRESENT';
  if (values.includes('WITHDRAWN')) return 'WITHDRAWN';
  return 'DORMANT';
}

function stateDecision(command, before, channelId, {canPublicReply = true} = {}) {
  if (command === 'cut-the-cam') {
    if (before.state === 'CUT') {
      return {nextState: before, outcome: 'already_cut', responseKey: 'cut', public: canPublicReply, controlPlane: true};
    }
    return {
      nextState: {...before, state: 'CUT', epoch: before.epoch + 1, cutEpoch: before.cutEpoch + 1},
      outcome: 'cut',
      responseKey: 'cut',
      public: canPublicReply,
      controlPlane: true,
    };
  }

  if (command === 'venice.status') {
    return {nextState: before, outcome: 'status', responseKey: 'status', public: false, controlPlane: true};
  }

  if (before.state === 'CUT') {
    return {nextState: before, outcome: 'blocked_cut', responseKey: 'cut_locked', public: false, controlPlane: true};
  }

  if (command === 'venice.begin') {
    const rooms = {...before.rooms, [channelId]: 'PRESENT'};
    return {
      nextState: {
        state: globalStateForRooms(rooms),
        epoch: before.epoch + 1,
        cutEpoch: before.cutEpoch,
        rooms,
      },
      outcome: before.rooms[channelId] === 'PRESENT' ? 'begin_idempotent' : 'begun',
      responseKey: 'begun',
      public: true,
      controlPlane: false,
    };
  }

  if (command === 'venice.withdraw') {
    const rooms = {...before.rooms, [channelId]: 'WITHDRAWN'};
    return {
      nextState: {
        state: globalStateForRooms(rooms),
        epoch: before.epoch + 1,
        cutEpoch: before.cutEpoch,
        rooms,
      },
      outcome: before.rooms[channelId] === 'WITHDRAWN' ? 'withdraw_idempotent' : 'withdrawn',
      responseKey: 'withdrawn',
      public: true,
      controlPlane: true,
    };
  }

  if (command === 'venice.ask') {
    if (before.rooms[channelId] !== 'PRESENT') {
      return {nextState: before, outcome: 'blocked_inactive', responseKey: 'dormant', public: false, controlPlane: true};
    }
    return {nextState: before, outcome: 'accepted_stub', responseKey: 'asked', public: true, controlPlane: false};
  }

  return {nextState: before, outcome: 'unknown_command', responseKey: 'unavailable', public: false, controlPlane: true};
}

function responseFromDecision(decision, channelId) {
  const content = decision.responseKey === 'status'
    ? statusText(decision.after, channelId)
    : RESPONSE_TEXT[decision.responseKey] || RESPONSE_TEXT.unavailable;
  return interactionReply(content, {ephemeral: !decision.public});
}

async function dispatchVeniceInteraction(interaction, store) {
  if (String(interaction.application_id || '') !== VENICE_APPLICATION_ID) {
    return {status: 200, body: interactionReply(RESPONSE_TEXT.unavailable, {ephemeral: true})};
  }
  if (String(interaction.guild_id || '') !== VENICE_GUILD_ID) {
    return {status: 200, body: interactionReply(RESPONSE_TEXT.unavailable, {ephemeral: true})};
  }
  if (!VENICE_ALLOWED_CHANNEL_SET.has(String(interaction.channel_id || ''))) {
    return {status: 200, body: interactionReply(RESPONSE_TEXT.unavailable, {ephemeral: true})};
  }

  const command = commandName(interaction);
  const canPublicReply = hasRequiredAppPermissions(interaction);
  if (command !== 'cut-the-cam' && !canPublicReply) {
    return {status: 200, body: interactionReply(RESPONSE_TEXT.permissions, {ephemeral: true})};
  }
  const context = interactionContext(interaction, command || 'unknown');
  const decision = await store.execute(context, (before) => stateDecision(
    command,
    before,
    context.channelId,
    {canPublicReply},
  ));

  if (decision.public && command !== 'cut-the-cam') {
    const stillCurrent = await store.guard(decision.after.cutEpoch);
    if (!stillCurrent) {
      return {status: 200, body: interactionReply(RESPONSE_TEXT.cut, {ephemeral: true})};
    }
  }

  return {status: 200, body: responseFromDecision(decision, context.channelId)};
}

function discordPublicKey(publicKeyHex) {
  if (!/^[0-9a-f]{64}$/i.test(publicKeyHex || '')) throw new Error('invalid_public_key');
  return crypto.createPublicKey({
    key: Buffer.concat([ED25519_SPKI_PREFIX, Buffer.from(publicKeyHex, 'hex')]),
    format: 'der',
    type: 'spki',
  });
}

function verifyDiscordRequest({signature, timestamp, rawBody, publicKeyHex, nowMs = Date.now()}) {
  if (!Buffer.isBuffer(rawBody)) return false;
  if (!/^[0-9a-f]{128}$/i.test(signature || '')) return false;
  if (!/^\d{10,13}$/.test(timestamp || '')) return false;
  const timestampMs = Number(timestamp) * 1000;
  if (!Number.isFinite(timestampMs) || Math.abs(nowMs - timestampMs) > SIGNATURE_MAX_AGE_MS) return false;
  try {
    return crypto.verify(
      null,
      Buffer.concat([Buffer.from(timestamp, 'utf8'), rawBody]),
      discordPublicKey(publicKeyHex),
      Buffer.from(signature, 'hex'),
    );
  } catch (_) {
    return false;
  }
}

function createFirestoreStateStore({firestore, fieldValue, now = () => Date.now()}) {
  const stateRef = firestore.collection('veniceDiscord').doc('runtime');
  const auditCollection = firestore.collection('veniceDiscordAudit');
  return {
    async execute(context, reducer) {
      return firestore.runTransaction(async (transaction) => {
        const auditRef = auditCollection.doc(context.interactionId);
        const stateSnapshot = await transaction.get(stateRef);
        const auditSnapshot = await transaction.get(auditRef);

        if (auditSnapshot.exists) {
          const saved = auditSnapshot.data() || {};
          return {
            after: cloneState({
              state: saved.stateAfter,
              epoch: saved.epochAfter,
              cutEpoch: saved.cutEpochAfter,
              rooms: {[context.channelId]: saved.roomStateAfter},
            }),
            outcome: String(saved.outcome || 'replayed'),
            responseKey: String(saved.responseKey || 'unavailable'),
            public: saved.public === true,
            controlPlane: saved.controlPlane === true,
            replayed: true,
          };
        }

        const before = cloneState(stateSnapshot.exists ? stateSnapshot.data() : {});
        const reduced = reducer(before);
        const after = cloneState(reduced.nextState || before);
        if (
          after.state !== before.state ||
          after.epoch !== before.epoch ||
          after.cutEpoch !== before.cutEpoch ||
          !stateSnapshot.exists
        ) {
          transaction.set(stateRef, {
            state: after.state,
            epoch: after.epoch,
            cutEpoch: after.cutEpoch,
            rooms: after.rooms,
            updatedAt: fieldValue.serverTimestamp(),
            updatedByUserId: context.userId,
            lastInteractionId: context.interactionId,
          }, {merge: true});
        }
        transaction.set(auditRef, {
          interactionId: context.interactionId,
          applicationId: context.applicationId,
          guildId: context.guildId,
          channelId: context.channelId,
          userId: context.userId,
          command: context.command,
          outcome: reduced.outcome,
          responseKey: reduced.responseKey,
          public: reduced.public === true,
          controlPlane: reduced.controlPlane === true,
          stateBefore: before.state,
          epochBefore: before.epoch,
          stateAfter: after.state,
          roomStateAfter: after.rooms[context.channelId],
          epochAfter: after.epoch,
          cutEpochAfter: after.cutEpoch,
          recordedAt: fieldValue.serverTimestamp(),
          expireAt: new Date(now() + AUDIT_RETENTION_MS),
        }, {merge: false});
        return {...reduced, before, after, replayed: false};
      });
    },
    async guard(cutEpoch) {
      const snapshot = await stateRef.get();
      if (!snapshot.exists) return false;
      const current = cloneState(snapshot.data());
      return current.state !== 'CUT' && current.cutEpoch === cutEpoch;
    },
  };
}

function createVeniceDiscordHandler({publicKeyGetter, store, now = () => Date.now(), logger = console}) {
  return async function veniceDiscordHandler(req, res) {
    if (req.method !== 'POST') {
      res.status(405).set('Allow', 'POST').send('');
      return;
    }

    const rawBody = Buffer.isBuffer(req.rawBody) ? req.rawBody : null;
    if (!rawBody || rawBody.length > MAX_INTERACTION_BODY_BYTES) {
      res.status(rawBody ? 413 : 400).send('');
      return;
    }
    const signature = req.get('X-Signature-Ed25519') || '';
    const timestamp = req.get('X-Signature-Timestamp') || '';
    let verified = false;
    try {
      verified = verifyDiscordRequest({
        signature,
        timestamp,
        rawBody,
        publicKeyHex: publicKeyGetter(),
        nowMs: now(),
      });
    } catch (_) {
      res.status(503).send('');
      return;
    }
    if (!verified) {
      res.status(401).send('');
      return;
    }

    let interaction;
    try {
      interaction = JSON.parse(rawBody.toString('utf8'));
    } catch (_) {
      res.status(400).send('');
      return;
    }
    if (!interaction || typeof interaction !== 'object' || Array.isArray(interaction)) {
      res.status(400).send('');
      return;
    }

    if (interaction.type === 1) {
      res.status(200).type('application/json').send({type: 1});
      return;
    }
    if (interaction.type !== 2) {
      res.status(204).send('');
      return;
    }

    try {
      const result = await dispatchVeniceInteraction(interaction, store);
      if (!result.body) {
        res.status(result.status).send('');
        return;
      }
      res.status(result.status).type('application/json').send(result.body);
    } catch (_) {
      logger.error('venice_discord_interaction_failed', {
        interactionId: String(interaction.id || ''),
        outcome: 'fail_closed',
      });
      res.status(503).send('');
    }
  };
}

module.exports = {
  VENICE_APPLICATION_ID,
  VENICE_GUILD_ID,
  VENICE_ALLOWED_CHANNEL_IDS,
  VENICE_COMMANDS,
  cloneState,
  commandName,
  createFirestoreStateStore,
  createVeniceDiscordHandler,
  dispatchVeniceInteraction,
  stateDecision,
  verifyDiscordRequest,
};
