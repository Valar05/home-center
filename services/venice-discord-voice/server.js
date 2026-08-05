'use strict';

const http = require('node:http');
const {initializeApp} = require('firebase-admin/app');
const {getFirestore} = require('firebase-admin/firestore');
const {
  AudioPlayerStatus,
  NoSubscriberBehavior,
  StreamType,
  VoiceConnectionStatus,
  createAudioPlayer,
  createAudioResource,
  entersState,
  joinVoiceChannel,
} = require('@discordjs/voice');
const {ChannelType, Client, Events, GatewayIntentBits, PermissionFlagsBits} = require('discord.js');
const {createDiscordOggStream} = require('./audio_pipeline');
const {publicError, stateAllowsSpeech, validateSpeakRequest} = require('./core');
const {SAMPLE_RATE, synthesizeGeminiPcm} = require('./gemini_tts');

const PORT = Math.max(1, Number(process.env.PORT || 8080));
const GUILD_ID = String(process.env.VENICE_DISCORD_GUILD_ID || '1534104765796192356');
const VOICE_NAME = String(process.env.VENICE_VOICE_NAME || 'Kore');
const IDLE_DISCONNECT_MS = Math.max(500, Number(process.env.VENICE_IDLE_DISCONNECT_MS || 1500));
const AUDIO_PREROLL_MS = Math.max(500, Number(process.env.VENICE_AUDIO_PREROLL_MS || 1200));
const MAX_BODY_BYTES = 12 * 1024;

initializeApp();
const consentRef = getFirestore().collection('veniceDiscord').doc('runtime');
const client = new Client({intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates]});
const active = new Map();
const pendingByGuild = new Map();
const delivered = new Map();
let consentState = null;
let consentReady = false;
let discordReady = false;

function contentFreeLog(level, event, fields = {}) {
  console[level](JSON.stringify({event, ...fields}));
}

function stopSession(guildId, reason) {
  const session = active.get(guildId);
  if (!session) return;
  active.delete(guildId);
  try { session.player.stop(true); } catch (_) {}
  try { session.connection.destroy(); } catch (_) {}
  contentFreeLog('info', 'venice_voice_stopped', {guildId, interactionId: session.task.interactionId, reason});
}

function reconcileConsent() {
  for (const [guildId, session] of active) {
    if (!stateAllowsSpeech(consentState, session.task)) stopSession(guildId, 'consent_state_changed');
  }
}

consentRef.onSnapshot((snapshot) => {
  consentState = snapshot.exists ? snapshot.data() : null;
  consentReady = true;
  reconcileConsent();
}, (error) => {
  consentReady = false;
  contentFreeLog('error', 'venice_voice_consent_watch_failed', {code: String(error && error.code || 'unknown')});
  for (const guildId of active.keys()) stopSession(guildId, 'consent_state_unavailable');
  setTimeout(() => process.exit(1), 1000);
});

client.once(Events.ClientReady, () => {
  discordReady = true;
  contentFreeLog('info', 'venice_voice_gateway_ready', {applicationId: client.user.id, guildId: GUILD_ID});
});
client.on('shardDisconnect', () => {
  discordReady = false;
  for (const guildId of active.keys()) stopSession(guildId, 'discord_disconnected');
});
client.on('error', (error) => {
  contentFreeLog('error', 'venice_voice_gateway_error', {code: String(error && error.code || 'unknown')});
});

async function playOne(task) {
  if (!discordReady) throw new Error('discord_not_ready');
  if (!consentReady) throw new Error('consent_state_unavailable');
  if (!stateAllowsSpeech(consentState, task)) throw new Error('consent_state_changed');

  const guild = await client.guilds.fetch(task.guildId);
  const member = await guild.members.fetch(task.userId);
  const voiceChannel = member.voice && member.voice.channel;
  if (!voiceChannel || ![ChannelType.GuildVoice, ChannelType.GuildStageVoice].includes(voiceChannel.type)) {
    throw new Error('user_not_in_voice');
  }
  const permissions = voiceChannel.permissionsFor(guild.members.me);
  if (!permissions || !permissions.has([PermissionFlagsBits.ViewChannel, PermissionFlagsBits.Connect, PermissionFlagsBits.Speak])) {
    throw new Error('voice_permissions_missing');
  }

  const speech = await synthesizeGeminiPcm({
    apiKey: process.env.GEMINI_API_KEY,
    text: task.text,
    voiceName: VOICE_NAME,
  });
  if (!stateAllowsSpeech(consentState, task)) throw new Error('consent_state_changed');

  const connection = joinVoiceChannel({
    channelId: voiceChannel.id,
    guildId: guild.id,
    adapterCreator: guild.voiceAdapterCreator,
    selfDeaf: true,
    selfMute: false,
  });
  try {
    await entersState(connection, VoiceConnectionStatus.Ready, 20000);
  } catch (_) {
    connection.destroy();
    throw new Error('voice_connection_failed');
  }
  if (!stateAllowsSpeech(consentState, task)) {
    connection.destroy();
    throw new Error('consent_state_changed');
  }

  const player = createAudioPlayer({behaviors: {noSubscriber: NoSubscriberBehavior.Pause}});
  player.on('error', (error) => {
    contentFreeLog('error', 'venice_voice_player_error', {
      guildId: task.guildId,
      interactionId: task.interactionId,
      code: String(error && error.code || 'unknown'),
    });
    stopSession(task.guildId, 'audio_player_error');
  });
  active.set(task.guildId, {connection, player, task});
  try {
    connection.subscribe(player);
    const encoded = createDiscordOggStream(speech.pcm, {
      sampleRate: SAMPLE_RATE,
      prerollMs: AUDIO_PREROLL_MS,
      logger: (fields) => contentFreeLog('error', fields.event, fields),
    });
    const encodingDone = encoded.done.catch((error) => {
      encoded.stream.destroy(error);
      throw error;
    });
    const resource = createAudioResource(encoded.stream, {inputType: StreamType.OggOpus});
    player.play(resource);
    await entersState(player, AudioPlayerStatus.Playing, 10000);
    await entersState(player, AudioPlayerStatus.Idle, 120000);
    const encoding = await encodingDone;
    const current = active.get(task.guildId);
    if (!current || current.task.interactionId !== task.interactionId || !stateAllowsSpeech(consentState, task)) {
      throw new Error('consent_state_changed');
    }
    await new Promise((resolve) => setTimeout(resolve, IDLE_DISCONNECT_MS));
    stopSession(task.guildId, 'single_reply_complete');
    delivered.set(task.interactionId, Date.now());
    contentFreeLog('info', 'venice_voice_reply_complete', {
      guildId: task.guildId,
      voiceChannelId: voiceChannel.id,
      interactionId: task.interactionId,
      voiceName: speech.voiceName,
      voiceIdentity: 'candidate_noncanonical',
      sourceDurationMs: speech.metrics.durationMs,
      sourcePeak: speech.metrics.peak,
      sourceRms: speech.metrics.rms,
      encodedBytes: encoding.outputBytes,
      prerollMs: encoding.prerollMs,
    });
    return {voiceChannelId: voiceChannel.id, voiceName: speech.voiceName};
  } catch (error) {
    stopSession(task.guildId, 'reply_failed');
    throw error;
  }
}

function enqueue(task) {
  const prior = pendingByGuild.get(task.guildId) || Promise.resolve();
  const next = prior.catch(() => {}).then(() => playOne(task));
  const tracked = next.finally(() => {
    if (pendingByGuild.get(task.guildId) === tracked) pendingByGuild.delete(task.guildId);
  });
  pendingByGuild.set(task.guildId, tracked);
  return next;
}

async function readJson(req) {
  const chunks = [];
  let total = 0;
  for await (const chunk of req) {
    total += chunk.length;
    if (total > MAX_BODY_BYTES) throw Object.assign(new Error('request_too_large'), {status: 413});
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch (_) { throw Object.assign(new Error('invalid_json'), {status: 400}); }
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method === 'GET' && req.url === '/health') {
    const ok = discordReady && consentReady;
    res.writeHead(ok ? 200 : 503, {'content-type': 'application/json'});
    res.end(JSON.stringify({ok, discordReady, consentReady, mode: 'explicit_single_reply', voiceIdentity: 'candidate_noncanonical'}));
    return;
  }
  if (req.method !== 'POST' || req.url !== '/speak') {
    res.writeHead(404).end('');
    return;
  }
  let task;
  try {
    task = validateSpeakRequest(await readJson(req), GUILD_ID);
    const deliveredAt = delivered.get(task.interactionId);
    if (deliveredAt && Date.now() - deliveredAt < 15 * 60 * 1000) {
      res.writeHead(200, {'content-type': 'application/json'});
      res.end(JSON.stringify({ok: true, idempotent: true, voiceIdentity: 'candidate_noncanonical'}));
      return;
    }
    const result = await enqueue(task);
    res.writeHead(200, {'content-type': 'application/json'});
    res.end(JSON.stringify({ok: true, ...result, voiceIdentity: 'candidate_noncanonical'}));
  } catch (error) {
    const status = Number(error && error.status) || (publicError(error) === 'voice_unavailable' ? 503 : 409);
    contentFreeLog('error', 'venice_voice_request_failed', {
      interactionId: task && task.interactionId || '',
      code: publicError(error),
    });
    res.writeHead(status, {'content-type': 'application/json'});
    res.end(JSON.stringify({ok: false, error: publicError(error)}));
  }
});

server.listen(PORT, () => contentFreeLog('info', 'venice_voice_http_ready', {port: PORT}));
client.login(process.env.DISCORD_BOT_TOKEN).catch((error) => {
  contentFreeLog('error', 'venice_voice_login_failed', {code: String(error && error.code || 'unknown')});
  process.exitCode = 1;
  setTimeout(() => process.exit(1), 1000);
});
