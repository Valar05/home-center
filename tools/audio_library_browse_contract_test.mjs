import assert from 'node:assert/strict';
import test from 'node:test';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {browseAudio, normalizeFolder} = require('../functions/audio_library_api.js');
const owner = 'dclarke1005@gmail.com';
const root = `indexes/audio/v1/catalog/${owner}/`;

function record({id, project, stage, name, bytes}) {
  return Buffer.from(JSON.stringify({
    schemaVersion: 'home-center.audio-index.v1',
    indexedAt: '2026-07-26T18:00:00.000Z',
    source: {fileId: id, name, mimeType: 'audio/ogg', sourcePath: `Generated/${project}/${stage}/${name}`},
    destination: {
      objectName: `audio/${owner}/drive-import/${project}/${stage}/${id}-${name}`,
      byteCount: bytes,
      sha256: id.padEnd(64, '0'),
      ownerEmail: owner,
      project,
      stage,
    },
    classification: {ownerEmail: owner, project, stage},
  }));
}

const objects = new Map([
  [`${root}vacation/finals/drive-1.json`, record({id: 'drive-1', project: 'vacation', stage: 'finals', name: 'final.ogg', bytes: 10})],
  [`${root}vacation/probes/drive-2.json`, record({id: 'drive-2', project: 'vacation', stage: 'probes', name: 'probe.ogg', bytes: 20})],
  [`${root}fortress/finals/drive-3.json`, record({id: 'drive-3', project: 'fortress', stage: 'finals', name: 'fortress.ogg', bytes: 30})],
]);

class FakeFile {
  constructor(name) { this.name = name; }
  async download() { return [objects.get(this.name)]; }
}

class FakeBucket {
  constructor() { this.calls = []; }
  async getFiles(query) {
    this.calls.push({...query});
    const names = [...objects.keys()].filter((name) => name.startsWith(query.prefix));
    const files = [];
    const prefixes = new Set();
    for (const name of names) {
      const remainder = name.slice(query.prefix.length);
      const slash = remainder.indexOf('/');
      if (slash >= 0) prefixes.add(query.prefix + remainder.slice(0, slash + 1));
      else files.push(new FakeFile(name));
    }
    return [files, {}, {prefixes: [...prefixes]}];
  }
}

test('folder depth is limited to project and stage', () => {
  assert.equal(normalizeFolder('vacation/finals'), 'vacation/finals');
  assert.throws(() => normalizeFolder('vacation/finals/deeper'), /project and stage only/);
});

test('root and project requests open only immediate index prefixes', async () => {
  const bucket = new FakeBucket();
  const rootResult = await browseAudio(bucket, {}, owner);
  assert.deepEqual(rootResult.folders.map((folder) => folder.path), ['fortress', 'vacation']);
  assert.equal(rootResult.items.length, 0);
  const projectResult = await browseAudio(bucket, {folder: 'vacation'}, owner);
  assert.deepEqual(projectResult.folders.map((folder) => folder.path), ['vacation/finals', 'vacation/probes']);
  assert.equal(projectResult.items.length, 0);
  assert.deepEqual(bucket.calls.map((call) => call.prefix), [root, `${root}vacation/`]);
});

test('stage requests open only the selected stage records', async () => {
  const bucket = new FakeBucket();
  const result = await browseAudio(bucket, {folder: 'vacation/finals'}, owner);
  assert.equal(result.items.length, 1);
  assert.equal(result.items[0].displayName, 'final.ogg');
  assert.equal(result.items[0].size, 10);
  assert.equal(bucket.calls.length, 1);
  assert.equal(bucket.calls[0].prefix, `${root}vacation/finals/`);
  assert.equal(bucket.calls[0].delimiter, '/');
});
