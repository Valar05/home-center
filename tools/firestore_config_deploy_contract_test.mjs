import assert from 'node:assert/strict';
import fs from 'node:fs';
import {planFirestoreConfig} from './deploy_firestore_config_gcloud.mjs';

const config = JSON.parse(fs.readFileSync(new URL('../firebase/firestore.indexes.json', import.meta.url), 'utf8'));
const planned = planFirestoreConfig(config, [], []);
assert.equal(planned.createIndexes.length, config.indexes.length);
assert.equal(planned.enableTtls.length, 1);

const existingIndexes = config.indexes.map((index, position) => ({
  name: `projects/test/databases/(default)/collectionGroups/${index.collectionGroup}/indexes/${position}`,
  queryScope: index.queryScope,
  state: 'READY',
  fields: [...index.fields, {fieldPath: '__name__', order: 'ASCENDING'}],
}));
const ttl = config.fieldOverrides.find((field) => field.ttl === true);
const existingTtls = [{name: `projects/test/databases/(default)/collectionGroups/${ttl.collectionGroup}/fields/${ttl.fieldPath}`, ttlConfig: {state: 'ACTIVE'}}];
const replay = planFirestoreConfig(config, existingIndexes, existingTtls);
assert.equal(replay.createIndexes.length, 0, 'ready indexes must not be recreated');
assert.equal(replay.enableTtls.length, 0, 'active TTL must not be recreated');

const withoutFilesystem = existingIndexes.filter((index) => !index.name.includes('/gcsFilesystem'));
const repair = planFirestoreConfig(config, withoutFilesystem, []);
assert.equal(repair.createIndexes.length, 3);
assert.deepEqual(repair.createIndexes.map((index) => index.collectionGroup).sort(), ['gcsFilesystemPaths', 'gcsFilesystemTrashEntries', 'gcsFilesystemVersions']);
assert.equal(repair.enableTtls[0].collectionGroup, 'gcsFilesystemTrashEntries');

console.log('Firestore gcloud config deployment contract passed.');
