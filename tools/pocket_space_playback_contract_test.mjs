#!/usr/bin/env node
import fs from 'node:fs';

const manifest = fs.readFileSync('app/src/main/AndroidManifest.xml', 'utf8');
const activity = fs.readFileSync('app/src/main/java/com/dclar/homecenter/PocketTtsPlaybackActivity.java', 'utf8');
const reader = fs.readFileSync('tools/fortress_read_aloud.py', 'utf8');

for (const required of [
  'android.permission.READ_MEDIA_AUDIO',
  'android:name=".PocketTtsPlaybackActivity"',
  'android:exported="true"',
  'android:theme="@android:style/Theme.NoDisplay"',
]) {
  if (!manifest.includes(required)) throw new Error('Pocket Space manifest contract missing: ' + required);
}

for (const required of [
  'Documents/FortressAudio',
  'READ_MEDIA_AUDIO is not granted',
  'USAGE_ASSISTANCE_ACCESSIBILITY',
  'AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK',
  'new MediaPlayer()',
  'player.setDataSource',
  'play_start file=',
  'play_finish reason=',
  'focus_abandoned=true',
]) {
  if (!activity.includes(required)) throw new Error('Pocket Space Android playback contract missing: ' + required);
}

for (const forbidden of [
  'Environment.getExternalStorageDirectory()',
  'setDataSource(supplied)',
  'AUDIOFOCUS_GAIN',
]) {
  if (activity.includes(forbidden)) throw new Error('Pocket Space Android playback contract contains forbidden broad behavior: ' + forbidden);
}

for (const required of [
  "POCKET_PHONE=Path.home()/'bin/pocket-tts-phone'",
  "'engine':'pocket-tts-phone+home-center-playback+rish'",
  "component='com.dclar.homecenter/.PocketTtsPlaybackActivity'",
  "if provider=='termux': raise RuntimeError('BLOCKED: system TTS is not Adam')",
  "'provider':'pocket-home-center'",
  "'transport':'shizuku-rish'",
  'seconds+=play_home_center(wav)',
]) {
  if (!reader.includes(required)) throw new Error('Pocket Space end-to-end reader contract missing: ' + required);
}

const synthesisOnly = '$HOME/bin/pockettts-say --text';
if (reader.includes(synthesisOnly)) throw new Error('End-to-end reader must not delegate completion to the synthesis-only helper.');

console.log('Pocket Space synthesis -> Home Center Android playback -> audio focus -> completion contract: PASS');
