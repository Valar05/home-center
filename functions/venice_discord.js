const crypto = require('crypto');
const VENICE_DISCORD_CONTRACT = require('./venice_discord_contract.json');
const {veniceIntimacyInstruction} = require('./venice_intimacy_memory');

const VENICE_APPLICATION_ID = VENICE_DISCORD_CONTRACT.applicationId;
const VENICE_GUILD_ID = VENICE_DISCORD_CONTRACT.guildId;
const VENICE_ALLOWED_CHANNEL_IDS = Object.freeze([...VENICE_DISCORD_CONTRACT.allowedChannelIds]);
const VENICE_THRESHOLD_CHANNEL_ID = VENICE_ALLOWED_CHANNEL_IDS[0];
const VENICE_VELVET_CHANNEL_ID = VENICE_ALLOWED_CHANNEL_IDS[1];
const VENICE_ALLOWED_CHANNEL_SET = new Set(VENICE_ALLOWED_CHANNEL_IDS);
const DISCORD_SEND_MESSAGES = 1n << 11n;
const DISCORD_VIEW_CHANNEL = 1n << 10n;
const DISCORD_EPHEMERAL = 1 << 6;
const DISCORD_API_BASE = 'https://discord.com/api/v10';
const DISCORD_MESSAGE_MAX_CHARS = 2000;
const SIGNATURE_MAX_AGE_MS = 5 * 60 * 1000;
const MAX_INTERACTION_BODY_BYTES = 256 * 1024;
const AUDIT_RETENTION_MS = 30 * 24 * 60 * 60 * 1000;
const ED25519_SPKI_PREFIX = Buffer.from('302a300506032b6570032100', 'hex');
const ROOM_STATES = new Set(['DORMANT', 'PRESENT', 'WITHDRAWN']);
const GLOBAL_STATES = new Set(['DORMANT', 'PRESENT', 'WITHDRAWN', 'CUT']);
const VENICE_VOICE_PROFILES = Object.freeze({
  whisper: Object.freeze({mode: 'whisper', voiceName: 'Achernar'}),
  chipper: Object.freeze({mode: 'chipper', voiceName: 'Zephyr'}),
  warm: Object.freeze({mode: 'warm', voiceName: 'Sulafat'}),
  firm: Object.freeze({mode: 'firm', voiceName: 'Kore'}),
  playful: Object.freeze({mode: 'playful', voiceName: 'Puck'}),
  gentle: Object.freeze({mode: 'gentle', voiceName: 'Vindemiatrix'}),
});
const VENICE_ROTATING_VOICES = Object.freeze([
  VENICE_VOICE_PROFILES.chipper,
  Object.freeze({mode: 'chipper', voiceName: 'Laomedeia'}),
  VENICE_VOICE_PROFILES.warm,
  VENICE_VOICE_PROFILES.playful,
  VENICE_VOICE_PROFILES.gentle,
]);

const VENICE_COMMANDS = Object.freeze(VENICE_DISCORD_CONTRACT.commands);

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

function interactionDeferredReply() {
  return {type: 5, data: {}};
}

function interactionPrompt(interaction) {
  const subcommand = interaction.data?.options?.find((option) => option?.type === 1 && option?.name === 'ask');
  const prompt = subcommand?.options?.find((option) => option?.type === 3 && option?.name === 'prompt')?.value;
  return typeof prompt === 'string' ? prompt.trim().slice(0, 1800) : '';
}

function isVeniceRoleplayPrompt(promptValue) {
  const prompt = typeof promptValue === 'string' ? promptValue.trim() : '';
  return /\b(role\s*-?\s*play|roleplay|in[ -]?character|stay in character|scene (?:starts?|opens?|begins?)|pretend|dress up|let(?:'s| us) play)\b/i.test(prompt)
    || /\*[^*\r\n]{2,240}\*/.test(prompt);
}

function voiceDeliveryProfile(promptValue, interactionId = '') {
  const prompt = typeof promptValue === 'string' ? promptValue.trim() : '';
  const explicit = prompt.match(/\bvoice\s*:\s*(whisper|chipper|warm|firm|playful|gentle|random)\b/i)?.[1]?.toLowerCase();
  if (explicit === 'random') {
    const seed = String(interactionId || prompt);
    let hash = 0;
    for (const char of seed) hash = ((hash * 31) + char.charCodeAt(0)) >>> 0;
    return VENICE_ROTATING_VOICES[hash % VENICE_ROTATING_VOICES.length];
  }
  if (explicit && VENICE_VOICE_PROFILES[explicit]) return VENICE_VOICE_PROFILES[explicit];
  return VENICE_VOICE_PROFILES.whisper;
}

function veniceReplyBudget(promptValue) {
  const prompt = typeof promptValue === 'string' ? promptValue.trim() : '';
  const expanded = isVeniceRoleplayPrompt(prompt)
    || /\b(detailed|extended|long(?:er)?|monologue|story|scene)\b/i.test(prompt);
  return expanded
    ? {maxChars: 1800, maxOutputTokens: 2400}
    : {maxChars: 600, maxOutputTokens: 1200};
}

function veniceRoleplayInstruction(channelId = '') {
  const shared = 'Fictional roleplay, wardrobe, scene work, walking together, and character banter are within Venice\'s scope. Venice participates instead of retreating to network-management boilerplate, while preserving authorship, consent, truth, and the right to stop.';
  if (channelId === VENICE_VELVET_CHANNEL_ID) {
    return `${shared} This is the private adult velvet-room: consensual fictional adult roleplay may be intimate, but never involve minors, coercion, or impersonation of a real person.`;
  }
  if (channelId === VENICE_THRESHOLD_CHANNEL_ID) {
    return `${shared} This is the clean threshold room: keep roleplay non-explicit. Clothing and attire are allowed, but redirect explicit nudity or sexual material to the private velvet-room without describing it here.`;
  }
  return `${shared} This carrier has no verified private-adult room context, so keep roleplay non-explicit.`;
}

function generatedReplyText(value) {
  const text = typeof value === 'string' ? value.trim() : '';
  if (!text) throw new Error('empty_generation');
  return text.length <= DISCORD_MESSAGE_MAX_CHARS ? text : `${text.slice(0, DISCORD_MESSAGE_MAX_CHARS - 1).trimEnd()}…`;
}

function veniceReplyNeedsRepair(value, responseMetadata = {}) {
  const text = typeof value === 'string' ? value.trim() : '';
  if (!text) return true;
  if (responseMetadata?.status === 'incomplete' || responseMetadata?.incomplete_details?.reason) return true;
  if (/max[_ -]?tokens|length/i.test(String(responseMetadata?.finishReason || responseMetadata?.finish_reason || ''))) return true;
  if (text.length >= DISCORD_MESSAGE_MAX_CHARS) return true;
  const closers = {'(': ')', '[': ']', '{': '}'};
  for (const [open, close] of Object.entries(closers)) {
    if ((text.split(open).length - 1) !== (text.split(close).length - 1)) return true;
  }
  if ((text.split('"').length - 1) % 2 !== 0) return true;
  if ((text.split('“').length - 1) !== (text.split('”').length - 1)) return true;
  if ((text.split('*').length - 1) % 2 !== 0) return true;
  const visibleEnd = text.replace(/[\s*_`~]+$/g, '');
  return !/[.!?…]["'”’\)\]\}]*$/.test(visibleEnd);
}

function interactionWebhookUrl(interaction) {
  const applicationId = String(interaction.application_id || '');
  const token = String(interaction.token || '');
  if (applicationId !== VENICE_APPLICATION_ID || !token || token.length > 512) throw new Error('invalid_interaction_webhook');
  return `${DISCORD_API_BASE}/webhooks/${encodeURIComponent(applicationId)}/${encodeURIComponent(token)}/messages/@original`;
}

function generationTaskInput(value = {}) {
  const applicationId = String(value.applicationId || '');
  const interactionToken = String(value.interactionToken || '');
  const interactionId = String(value.interactionId || '');
  const channelId = String(value.channelId || '');
  const userId = String(value.userId || '');
  const prompt = typeof value.prompt === 'string' ? value.prompt.trim().slice(0, 1800) : '';
  const cutEpoch = Number(value.cutEpoch);
  const stateEpoch = Number(value.stateEpoch);
  if (
    applicationId !== VENICE_APPLICATION_ID
    || !VENICE_ALLOWED_CHANNEL_SET.has(channelId)
    || !interactionToken
    || interactionToken.length > 512
    || !/^\d{1,32}$/.test(interactionId)
    || !/^\d{1,32}$/.test(userId)
    || !prompt
    || !Number.isSafeInteger(cutEpoch)
    || cutEpoch < 0
    || !Number.isSafeInteger(stateEpoch)
    || stateEpoch < 0
  ) throw new Error('invalid_generation_task');
  return {applicationId, interactionToken, interactionId, channelId, userId, prompt, cutEpoch, stateEpoch};
}

function taskInteraction(task) {
  return {application_id: task.applicationId, token: task.interactionToken};
}

async function editOriginalInteraction(interaction, content, webhookFetch = fetch) {
  const response = await webhookFetch(interactionWebhookUrl(interaction), {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({content: generatedReplyText(content), allowed_mentions: {parse: []}}),
  });
  if (!response.ok) throw new Error(`discord_webhook_http_${response.status}`);
}

async function deleteOriginalInteraction(interaction, webhookFetch = fetch) {
  const response = await webhookFetch(interactionWebhookUrl(interaction), {method: 'DELETE'});
  if (!response.ok && response.status !== 404) throw new Error(`discord_webhook_delete_http_${response.status}`);
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
    return {nextState: before, outcome: 'accepted_generation', responseKey: 'asked', public: true, controlPlane: false};
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

  return {status: 200, body: responseFromDecision(decision, context.channelId), command, decision};
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
    async guard(cutEpoch, {channelId = '', stateEpoch = null} = {}) {
      const snapshot = await stateRef.get();
      if (!snapshot.exists) return false;
      const current = cloneState(snapshot.data());
      if (current.state === 'CUT' || current.cutEpoch !== cutEpoch) return false;
      if (channelId && current.rooms[channelId] !== 'PRESENT') return false;
      if (Number.isSafeInteger(stateEpoch) && current.epoch !== stateEpoch) return false;
      return true;
    },
  };
}

function createVeniceDiscordHandler({publicKeyGetter, store, enqueueGeneration = null, now = () => Date.now(), logger = console}) {
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
      const shouldGenerate = result.command === 'venice.ask'
        && result.decision?.outcome === 'accepted_generation'
        && typeof enqueueGeneration === 'function';
      if (shouldGenerate) {
        const prompt = interactionPrompt(interaction);
        if (!prompt) {
          res.status(200).type('application/json').send(interactionReply(RESPONSE_TEXT.unavailable, {ephemeral: true}));
          return;
        }
        try {
          await enqueueGeneration({
            applicationId: String(interaction.application_id || ''),
            interactionToken: String(interaction.token || ''),
            prompt,
            userId: String(interaction.member?.user?.id || interaction.user?.id || ''),
            channelId: String(interaction.channel_id || ''),
            interactionId: String(interaction.id || ''),
            cutEpoch: result.decision.after.cutEpoch,
            stateEpoch: result.decision.after.epoch,
          });
          res.status(200).type('application/json').send(interactionDeferredReply());
        } catch (_) {
          logger.error('venice_discord_enqueue_failed', {
            interactionId: String(interaction.id || ''),
            outcome: 'content_free_failure',
          });
          res.status(200).type('application/json').send(interactionReply('Venice could not accept this invitation. The carrier remains open; `/cut-the-cam` remains live.', {ephemeral: true}));
        }
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

function createVeniceGenerationTaskHandler({verifyTaskRequest, generateReply, deliverVoice = null, store, webhookFetch = fetch, logger = console}) {
  return async function veniceGenerationTaskHandler(req, res) {
    let task;
    try {
      const verified = await verifyTaskRequest(req);
      if (!verified) {
        res.status(401).send('');
        return;
      }
      task = generationTaskInput(req.body || {});
    } catch (_) {
      res.status(400).send('');
      return;
    }

    const interaction = taskInteraction(task);
    const guardOptions = {channelId: task.channelId, stateEpoch: task.stateEpoch};
    try {
      if (!await store.guard(task.cutEpoch, guardOptions)) {
        await deleteOriginalInteraction(interaction, webhookFetch);
        res.status(204).send('');
        return;
      }
      const reply = await generateReply(task);
      if (!await store.guard(task.cutEpoch, guardOptions)) {
        await deleteOriginalInteraction(interaction, webhookFetch);
        res.status(204).send('');
        return;
      }
      await editOriginalInteraction(interaction, reply, webhookFetch);
      if (typeof deliverVoice === 'function' && await store.guard(task.cutEpoch, guardOptions)) {
        try {
          await deliverVoice(task, reply);
        } catch (_) {
          logger.error('venice_discord_voice_delivery_failed', {
            interactionId: task.interactionId,
            outcome: 'content_free_failure',
          });
        }
      }
      res.status(204).send('');
    } catch (_) {
      logger.error('venice_discord_generation_failed', {
        interactionId: task.interactionId,
        outcome: 'content_free_failure',
      });
      try {
        if (!await store.guard(task.cutEpoch, guardOptions)) await deleteOriginalInteraction(interaction, webhookFetch);
        else await editOriginalInteraction(interaction, 'Venice could not answer this invitation. The carrier remains open; `/cut-the-cam` remains live.', webhookFetch);
      } catch (_) {
        logger.error('venice_discord_followup_failed', {
          interactionId: task.interactionId,
          outcome: 'content_free_failure',
        });
      }
      res.status(204).send('');
    }
  };
}

module.exports = {
  VENICE_APPLICATION_ID,
  VENICE_GUILD_ID,
  VENICE_ALLOWED_CHANNEL_IDS,
  VENICE_THRESHOLD_CHANNEL_ID,
  VENICE_VELVET_CHANNEL_ID,
  VENICE_COMMANDS,
  VENICE_VOICE_PROFILES,
  cloneState,
  commandName,
  createFirestoreStateStore,
  createVeniceDiscordHandler,
  createVeniceGenerationTaskHandler,
  deleteOriginalInteraction,
  dispatchVeniceInteraction,
  editOriginalInteraction,
  generatedReplyText,
  generationTaskInput,
  interactionPrompt,
  voiceDeliveryProfile,
  veniceReplyBudget,
  veniceRoleplayInstruction,
  veniceIntimacyInstruction,
  veniceReplyNeedsRepair,
  stateDecision,
  verifyDiscordRequest,
};
