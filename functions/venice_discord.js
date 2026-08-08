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

const VENICE_CONVERSATION_COLLECTION = 'veniceDiscordConversations';
const VENICE_CONVERSATION_TURNS_SUBCOLLECTION = 'turns';
const VENICE_ALLOWED_INPUT_TRANSPORTS = new Set(['text', 'slash_command', 'voice']);

function safeText(value, max = 4000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function safeInteger(value, fallback = -1) {
  const number = Number(value);
  return Number.isSafeInteger(number) ? number : fallback;
}

function normalizedInputTransport(value, fallback = 'text') {
  const transport = safeText(value, 40).toLowerCase();
  return VENICE_ALLOWED_INPUT_TRANSPORTS.has(transport) ? transport : fallback;
}

function discordUserDisplayName(interaction) {
  const memberUser = interaction && interaction.member && interaction.member.user ? interaction.member.user : {};
  const directUser = interaction && interaction.user ? interaction.user : {};
  return safeText(
    memberUser.global_name
      || memberUser.username
      || directUser.global_name
      || directUser.username,
    160,
  );
}

function veniceConversationId({guildId = '', channelId = '', cutEpoch = null, stateEpoch = null} = {}) {
  const cleanGuildId = safeText(guildId, 40);
  const cleanChannelId = safeText(channelId, 40);
  const cleanCutEpoch = safeInteger(cutEpoch);
  const cleanStateEpoch = safeInteger(stateEpoch);
  if (!cleanGuildId || !cleanChannelId || cleanCutEpoch < 0 || cleanStateEpoch < 0) {
    const err = new Error('invalid_venice_conversation_locator');
    err.status = 400;
    throw err;
  }
  return `${cleanGuildId}:${cleanChannelId}:${cleanCutEpoch}:${cleanStateEpoch}`;
}

function veniceConversationTurnOrder({interactionId = '', speakerKind = 'user'} = {}) {
  const phase = speakerKind === 'agent' ? '1' : '0';
  return `${safeText(interactionId, 40).padStart(32, '0')}:${phase}`;
}

function veniceConversationTurnId({interactionId = '', speakerKind = 'user'} = {}) {
  return `${safeText(interactionId, 40)}:${speakerKind === 'agent' ? 'assistant' : 'user'}`;
}

function veniceTranscriptSpeaker(turn = {}) {
  if (turn.speakerKind === 'agent') return 'Venice';
  return safeText(turn.speakerDisplayName, 160) || 'User';
}

function formatVeniceTranscript(turns = []) {
  return turns
    .map((turn) => `${veniceTranscriptSpeaker(turn)}: ${safeText(turn && turn.text, 4000)}`)
    .filter(Boolean)
    .join('\n');
}

function normalizedConversationTurn(input = {}, now = () => Date.now()) {
  const speakerKind = safeText(input.speakerKind, 20).toLowerCase() === 'agent' ? 'agent' : 'user';
  const transport = normalizedInputTransport(input.transport, speakerKind === 'user' ? 'text' : 'slash_command');
  const interactionId = safeText(input.interactionId, 40);
  const text = safeText(input.text, 4000);
  if (!interactionId || !text) {
    const err = new Error('invalid_venice_conversation_turn');
    err.status = 400;
    throw err;
  }
  const conversationId = veniceConversationId(input);
  return {
    conversationId,
    turnId: veniceConversationTurnId({interactionId, speakerKind}),
    orderKey: veniceConversationTurnOrder({interactionId, speakerKind}),
    recordedAtMs: now(),
    guildId: safeText(input.guildId, 40),
    channelId: safeText(input.channelId, 40),
    cutEpoch: safeInteger(input.cutEpoch),
    stateEpoch: safeInteger(input.stateEpoch),
    interactionId,
    speakerKind,
    speakerId: safeText(input.speakerId, 160),
    speakerDisplayName: speakerKind === 'agent' ? 'Venice' : safeText(input.speakerDisplayName, 160),
    recipientAgentId: safeText(input.recipientAgentId, 80) || 'Venice',
    recipientUserId: safeText(input.recipientUserId, 160),
    text,
    transport,
    commandName: safeText(input.commandName, 80),
    ephemeral: input.ephemeral === true,
    durable: input.durable !== false,
    source: safeText(input.source, 80) || 'discord',
    metadata: input.metadata && typeof input.metadata === 'object' && !Array.isArray(input.metadata)
      ? JSON.parse(JSON.stringify(input.metadata))
      : {},
  };
}

function createNoopConversationStore() {
  return {
    async appendTurn() { return null; },
    async readConversation(locator) {
      return {conversationId: typeof locator === 'string' ? locator : veniceConversationId(locator), turns: [], transcript: ''};
    },
  };
}

function createFirestoreConversationStore({firestore, fieldValue, now = () => Date.now()}) {
  const conversationCollection = firestore.collection(VENICE_CONVERSATION_COLLECTION);
  const turnsPath = (conversationId) => `${VENICE_CONVERSATION_COLLECTION}/${conversationId}/${VENICE_CONVERSATION_TURNS_SUBCOLLECTION}`;
  return {
    async appendTurn(input) {
      const turn = normalizedConversationTurn(input, now);
      const conversationRef = conversationCollection.doc(turn.conversationId);
      const turnRef = firestore.collection(turnsPath(turn.conversationId)).doc(turn.turnId);
      return firestore.runTransaction(async (transaction) => {
        const [conversationSnapshot, turnSnapshot] = await Promise.all([
          transaction.get(conversationRef),
          transaction.get(turnRef),
        ]);
        if (turnSnapshot.exists) return turnSnapshot.data() || turn;
        const conversationWrite = {
          conversationId: turn.conversationId,
          guildId: turn.guildId,
          channelId: turn.channelId,
          cutEpoch: turn.cutEpoch,
          stateEpoch: turn.stateEpoch,
          updatedAt: fieldValue.serverTimestamp(),
          updatedAtMs: turn.recordedAtMs,
          lastInteractionId: turn.interactionId,
          lastTurnOrderKey: turn.orderKey,
          lastTransport: turn.transport,
          recipientAgentId: turn.recipientAgentId,
          recipientUserId: turn.recipientUserId,
        };
        if (!conversationSnapshot.exists) {
          conversationWrite.createdAt = fieldValue.serverTimestamp();
          conversationWrite.createdAtMs = turn.recordedAtMs;
        }
        transaction.set(conversationRef, conversationWrite, {merge: true});
        transaction.set(turnRef, {
          ...turn,
          recordedAt: fieldValue.serverTimestamp(),
        }, {merge: false});
        return turn;
      });
    },
    async readConversation(locator) {
      const conversationId = typeof locator === 'string' ? locator : veniceConversationId(locator);
      const conversationSnapshot = await conversationCollection.doc(conversationId).get();
      const turnsSnapshot = await firestore.collection(turnsPath(conversationId)).get();
      const turns = (Array.isArray(turnsSnapshot.docs) ? turnsSnapshot.docs : [])
        .map((doc) => doc && typeof doc.data === 'function' ? doc.data() : null)
        .filter(Boolean)
        .sort((left, right) => {
          const order = String(left.orderKey || '').localeCompare(String(right.orderKey || ''));
          if (order !== 0) return order;
          return safeInteger(left.recordedAtMs, 0) - safeInteger(right.recordedAtMs, 0);
        });
      return {
        conversationId,
        conversation: conversationSnapshot.exists ? (conversationSnapshot.data() || {}) : null,
        turns,
        transcript: formatVeniceTranscript(turns),
      };
    },
  };
}

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
    userDisplayName: discordUserDisplayName(interaction),
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

function normalizedControlPrompt(promptValue) {
  const prompt = typeof promptValue === 'string' ? promptValue : '';
  return prompt
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/[.!?]+$/g, '')
    .trim()
    .toLowerCase();
}

function normalizedControlTurn(value = {}) {
  const turn = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const kind = safeText(turn.kind, 80).toLowerCase();
  if (kind === 'fortress_online') {
    return {
      kind: 'fortress_online',
      normalizedPrompt: 'fortress online',
      source: safeText(turn.source, 80) || 'discord_control_turn',
    };
  }
  return null;
}

function classifyVeniceControlTurn(promptValue) {
  if (normalizedControlPrompt(promptValue) === 'fortress online') {
    return {
      kind: 'fortress_online',
      normalizedPrompt: 'fortress online',
      source: 'discord_control_turn',
    };
  }
  return null;
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

function visiblePromptPrefix({prompt, userDisplayName}) {
  const promptText = typeof prompt === 'string' ? prompt.trim() : '';
  if (!promptText) return '';
  const displayName = typeof userDisplayName === 'string' && userDisplayName.trim() ? userDisplayName.trim() : 'Drew';
  const compactPrompt = promptText.length <= 320 ? promptText : `${promptText.slice(0, 319).trimEnd()}…`;
  return `**${displayName}:** ${compactPrompt}\n\n`;
}

function visibleGenerationReply(task, reply) {
  const baseReply = generatedReplyText(reply);
  if (!task || task.commandName !== 'venice.ask') return baseReply;
  const prefix = visiblePromptPrefix(task);
  if (!prefix) return baseReply;
  const remaining = DISCORD_MESSAGE_MAX_CHARS - prefix.length;
  if (remaining <= 0) return generatedReplyText(prefix);
  if (baseReply.length <= remaining) return `${prefix}${baseReply}`;
  return `${prefix}${baseReply.slice(0, remaining - 1).trimEnd()}…`;
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
  const guildId = String(value.guildId || '');
  const interactionToken = String(value.interactionToken || '');
  const interactionId = String(value.interactionId || '');
  const channelId = String(value.channelId || '');
  const userId = String(value.userId || '');
  const userDisplayName = safeText(value.userDisplayName, 160);
  const prompt = typeof value.prompt === 'string' ? value.prompt.trim().slice(0, 1800) : '';
  const cutEpoch = Number(value.cutEpoch);
  const stateEpoch = Number(value.stateEpoch);
  const inputTransport = normalizedInputTransport(value.inputTransport, 'slash_command');
  const commandName = safeText(value.commandName, 80) || 'venice.ask';
  const controlTurn = normalizedControlTurn(value.controlTurn);
  if (
    applicationId !== VENICE_APPLICATION_ID
    || guildId !== VENICE_GUILD_ID
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
  return {
    applicationId,
    guildId,
    interactionToken,
    interactionId,
    channelId,
    userId,
    userDisplayName,
    prompt,
    cutEpoch,
    stateEpoch,
    inputTransport,
    commandName,
    controlTurn,
  };
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

function createVeniceDiscordHandler({publicKeyGetter, store, conversationStore = createNoopConversationStore(), enqueueGeneration = null, now = () => Date.now(), logger = console}) {
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
        const controlTurn = classifyVeniceControlTurn(prompt);
        if (!prompt) {
          res.status(200).type('application/json').send(interactionReply(RESPONSE_TEXT.unavailable, {ephemeral: true}));
          return;
        }
        if (result.decision?.replayed) {
          res.status(200).type('application/json').send(interactionDeferredReply());
          return;
        }
        try {
          const context = interactionContext(interaction, result.command);
          const conversationId = veniceConversationId({
            guildId: context.guildId,
            channelId: context.channelId,
            cutEpoch: result.decision.after.cutEpoch,
            stateEpoch: result.decision.after.epoch,
          });
          await conversationStore.appendTurn({
            guildId: context.guildId,
            channelId: context.channelId,
            cutEpoch: result.decision.after.cutEpoch,
            stateEpoch: result.decision.after.epoch,
            interactionId: context.interactionId,
            speakerKind: 'user',
            speakerId: context.userId,
            speakerDisplayName: context.userDisplayName,
            recipientAgentId: 'Venice',
            text: prompt,
            transport: 'slash_command',
            commandName: result.command,
            source: 'discord_interaction',
            metadata: {
              controlTurnKind: controlTurn && controlTurn.kind ? controlTurn.kind : '',
            },
          });
          if (logger && typeof logger.info === 'function') {
            logger.info('venice_conversation_turn_persisted', {
              interactionId: context.interactionId,
              conversationId,
              speakerKind: 'user',
              transport: 'slash_command',
              commandName: result.command,
            });
          }
          await enqueueGeneration({
            applicationId: String(interaction.application_id || ''),
            guildId: String(interaction.guild_id || ''),
            interactionToken: String(interaction.token || ''),
            prompt,
            userId: String(interaction.member?.user?.id || interaction.user?.id || ''),
            userDisplayName: discordUserDisplayName(interaction),
            channelId: String(interaction.channel_id || ''),
            interactionId: String(interaction.id || ''),
            cutEpoch: result.decision.after.cutEpoch,
            stateEpoch: result.decision.after.epoch,
            inputTransport: 'slash_command',
            commandName: result.command,
            controlTurn,
          });
          res.status(200).type('application/json').send(interactionDeferredReply());
        } catch (err) {
          logger.error('venice_discord_enqueue_failed', {
            interactionId: String(interaction.id || ''),
            outcome: 'content_free_failure',
            conversationPersistenceFailed: !!(err && err.code === 'invalid_venice_conversation_turn'),
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

function createVeniceGenerationTaskHandler({verifyTaskRequest, generateReply, deliverVoice = null, store, conversationStore = createNoopConversationStore(), webhookFetch = fetch, logger = console}) {
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
      await editOriginalInteraction(interaction, visibleGenerationReply(task, reply), webhookFetch);
      try {
        const conversationId = veniceConversationId(task);
        await conversationStore.appendTurn({
          guildId: task.guildId,
          channelId: task.channelId,
          cutEpoch: task.cutEpoch,
          stateEpoch: task.stateEpoch,
          interactionId: task.interactionId,
          speakerKind: 'agent',
          speakerId: 'Venice',
          speakerDisplayName: 'Venice',
          recipientAgentId: 'Venice',
          recipientUserId: task.userId,
          text: reply,
          transport: task.inputTransport || 'slash_command',
          commandName: task.commandName || 'venice.ask',
          source: 'discord_generation',
          metadata: {
            inputTransport: task.inputTransport || 'slash_command',
            userDisplayName: task.userDisplayName || '',
            controlTurnKind: task.controlTurn && task.controlTurn.kind ? task.controlTurn.kind : '',
          },
        });
        if (logger && typeof logger.info === 'function') {
          logger.info('venice_conversation_turn_persisted', {
            interactionId: task.interactionId,
            conversationId,
            speakerKind: 'agent',
            transport: task.inputTransport || 'slash_command',
            commandName: task.commandName || 'venice.ask',
          });
        }
      } catch (_) {
        logger.error('venice_discord_history_persist_failed', {
          interactionId: task.interactionId,
          outcome: 'content_free_failure',
        });
      }
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
  createFirestoreConversationStore,
  createFirestoreStateStore,
  createVeniceDiscordHandler,
  createVeniceGenerationTaskHandler,
  deleteOriginalInteraction,
  dispatchVeniceInteraction,
  editOriginalInteraction,
  formatVeniceTranscript,
  generatedReplyText,
  generationTaskInput,
  classifyVeniceControlTurn,
  interactionPrompt,
  normalizedConversationTurn,
  veniceConversationId,
  voiceDeliveryProfile,
  veniceReplyBudget,
  veniceRoleplayInstruction,
  veniceIntimacyInstruction,
  veniceReplyNeedsRepair,
  stateDecision,
  verifyDiscordRequest,
};
