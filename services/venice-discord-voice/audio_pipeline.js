'use strict';

const {spawn} = require('node:child_process');
const {Readable} = require('node:stream');

const DEFAULT_PREROLL_MS = 1200;

function createDiscordOggStream(pcm, {
  sampleRate = 24000,
  prerollMs = DEFAULT_PREROLL_MS,
  spawnImpl = spawn,
  logger = () => {},
} = {}) {
  if (!Buffer.isBuffer(pcm) || !pcm.length || pcm.length % 2) throw new Error('voice_connection_failed');
  const boundedPreroll = Math.max(500, Math.min(5000, Math.round(Number(prerollMs) || DEFAULT_PREROLL_MS)));
  const filter = `adelay=${boundedPreroll}:all=1,loudnorm=I=-16:TP=-1.5:LRA=7`;
  const ffmpeg = spawnImpl('ffmpeg', [
    '-hide_banner', '-loglevel', 'error',
    '-f', 's16le', '-ar', String(sampleRate), '-ac', '1', '-i', 'pipe:0',
    '-af', filter,
    '-ar', '48000', '-ac', '2',
    '-c:a', 'libopus', '-b:a', '96k', '-vbr', 'on', '-application', 'voip', '-frame_duration', '20',
    '-f', 'ogg', 'pipe:1',
  ], {stdio: ['pipe', 'pipe', 'pipe']});
  let stderr = '';
  let outputBytes = 0;
  ffmpeg.stderr.on('data', (chunk) => { stderr = (stderr + chunk.toString('utf8')).slice(-500); });
  ffmpeg.stdout.on('data', (chunk) => { outputBytes += chunk.length; });
  const done = new Promise((resolve, reject) => {
    ffmpeg.once('error', () => reject(new Error('voice_connection_failed')));
    ffmpeg.once('close', (code) => {
      if (code) {
        logger({event: 'venice_voice_ffmpeg_failed', code, detailLength: stderr.length});
        reject(new Error('voice_connection_failed'));
        return;
      }
      resolve({outputBytes, prerollMs: boundedPreroll});
    });
  });
  Readable.from([pcm]).pipe(ffmpeg.stdin);
  return {stream: ffmpeg.stdout, done, prerollMs: boundedPreroll};
}

module.exports = {DEFAULT_PREROLL_MS, createDiscordOggStream};
