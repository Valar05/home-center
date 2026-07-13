import {runBrowserEpisode, writeEpisodeArtifact} from './browser_worker.mjs';

function arg(name, fallback = '') {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

const query = arg('query', 'scrambled eggs recipe');
const url = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
const episode = await runBrowserEpisode({
  sessionId: `google_search_${Date.now()}`,
  intent: `Search Google for ${query} in desktop Chrome mode and capture reusable browser-hands learning.`,
  startUrl: url,
  headless: process.env.HEADLESS !== '0',
  actions: [{type: 'wait', ms: 1500}],
});
const artifact = await writeEpisodeArtifact(episode);
console.log(JSON.stringify({ok: true, artifact, title: episode.title, origin: episode.origin, discoveries: episode.discoveryCandidates.length}, null, 2));
