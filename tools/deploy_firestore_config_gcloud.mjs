import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function collectionGroupFromName(name = '') {
  const match = String(name).match(/\/collectionGroups\/([^/]+)\//);
  return match ? decodeURIComponent(match[1]) : '';
}
function fieldFromName(name = '') {
  const match = String(name).match(/\/fields\/(.+)$/);
  return match ? decodeURIComponent(match[1]) : '';
}
function normalizedFields(fields = []) {
  return fields.filter((field) => field.fieldPath !== '__name__').map((field) => ({
    fieldPath: String(field.fieldPath || ''),
    order: field.order ? String(field.order).toUpperCase() : undefined,
    arrayConfig: field.arrayConfig ? String(field.arrayConfig).toUpperCase() : undefined,
  }));
}
function sameFields(left, right) {
  return JSON.stringify(normalizedFields(left)) === JSON.stringify(normalizedFields(right));
}
export function planFirestoreConfig(config, currentIndexes = [], currentTtls = []) {
  const createIndexes = (config.indexes || []).filter((wanted) => !currentIndexes.some((current) =>
    collectionGroupFromName(current.name) === wanted.collectionGroup &&
    String(current.queryScope || '').toUpperCase() === String(wanted.queryScope || 'COLLECTION').toUpperCase() &&
    sameFields(current.fields, wanted.fields),
  ));
  const enableTtls = (config.fieldOverrides || []).filter((wanted) => wanted.ttl === true && !currentTtls.some((current) =>
    collectionGroupFromName(current.name) === wanted.collectionGroup &&
    fieldFromName(current.name) === wanted.fieldPath &&
    ['ACTIVE', 'CREATING'].includes(String(current.ttlConfig && current.ttlConfig.state || current.state || '').toUpperCase()),
  ));
  return {createIndexes, enableTtls};
}
function runGcloud(args, options = {}) {
  const result = spawnSync('gcloud', args, {cwd: root, encoding: 'utf8', stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit'});
  if (result.error || result.status !== 0) throw new Error('gcloud failed: ' + args.join(' ') + (result.stderr ? '\n' + result.stderr.trim() : ''));
  return result.stdout || '';
}
function listIndexes(project) {
  return JSON.parse(runGcloud(['firestore', 'indexes', 'composite', 'list', '--project', project, '--format=json'], {capture: true}) || '[]');
}
function listTtls(project) {
  return JSON.parse(runGcloud(['firestore', 'fields', 'ttls', 'list', '--project', project, '--format=json'], {capture: true}) || '[]');
}
function fieldConfigArgument(field) {
  if (field.order) return 'field-path=' + field.fieldPath + ',order=' + String(field.order).toLowerCase();
  if (field.arrayConfig) return 'field-path=' + field.fieldPath + ',array-config=' + String(field.arrayConfig).toLowerCase();
  throw new Error('Unsupported Firestore index field config for ' + field.fieldPath);
}
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

export async function deployFirestoreConfig({project, configPath = path.join(root, 'firebase/firestore.indexes.json'), timeoutMs = Number(process.env.HOME_CENTER_FIRESTORE_INDEX_TIMEOUT_MS || 20 * 60 * 1000)}) {
  if (!/^[a-z][a-z0-9-]{4,62}$/.test(project || '')) throw new Error('A valid GCP project ID is required.');
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const initial = planFirestoreConfig(config, listIndexes(project), listTtls(project));
  for (const index of initial.createIndexes) {
    const args = ['firestore', 'indexes', 'composite', 'create', '--project', project, '--collection-group', index.collectionGroup, '--query-scope', String(index.queryScope || 'COLLECTION').toLowerCase(), '--quiet'];
    for (const field of normalizedFields(index.fields)) args.push('--field-config=' + fieldConfigArgument(field));
    runGcloud(args);
  }
  for (const field of initial.enableTtls) runGcloud(['firestore', 'fields', 'ttls', 'update', field.fieldPath, '--project', project, '--collection-group', field.collectionGroup, '--enable-ttl', '--quiet']);

  const deadline = Date.now() + timeoutMs;
  while (true) {
    const indexes = listIndexes(project), ttls = listTtls(project), remaining = planFirestoreConfig(config, indexes, ttls);
    const notReady = indexes.filter((index) => (config.indexes || []).some((wanted) => collectionGroupFromName(index.name) === wanted.collectionGroup && sameFields(index.fields, wanted.fields)) && String(index.state || '').toUpperCase() !== 'READY');
    if (!remaining.createIndexes.length && !remaining.enableTtls.length && !notReady.length) {
      return {ok: true, project, createdIndexes: initial.createIndexes.length, enabledTtls: initial.enableTtls.length, indexCount: (config.indexes || []).length, ttlCount: (config.fieldOverrides || []).filter((field) => field.ttl === true).length};
    }
    if (Date.now() >= deadline) throw new Error('Timed out waiting for committed Firestore indexes and TTL to become ready.');
    await sleep(10000);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = await deployFirestoreConfig({project: process.argv[2] || process.env.FIREBASE_PROJECT || ''});
  process.stdout.write(JSON.stringify(result) + '\n');
}
