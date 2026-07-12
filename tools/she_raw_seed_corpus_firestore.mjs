#!/usr/bin/env node
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {SHE_RAW_SEED_CASES} = require('../corpus/she-raw/seed_cases.js');
const PROJECT = process.env.FIREBASE_PROJECT || 'home-center-dclar';

function firestoreValue(value) {
  if (typeof value === 'string') return {stringValue: value};
  if (typeof value === 'number') return {doubleValue: value};
  if (typeof value === 'boolean') return {booleanValue: value};
  if (Array.isArray(value)) return {arrayValue: {values: value.map(firestoreValue)}};
  if (value && typeof value === 'object') return {mapValue: {fields: firestoreFields(value)}};
  return {nullValue: null};
}

function firestoreFields(obj) {
  return Object.fromEntries(Object.entries(obj).map(([key, value]) => [key, firestoreValue(value)]));
}

async function main() {
  const tokenResult = spawnSync('gcloud', ['auth', 'print-access-token'], {encoding: 'utf8'});
  if (tokenResult.status !== 0) throw new Error(`gcloud auth print-access-token failed: ${tokenResult.stderr || tokenResult.stdout}`);
  const token = tokenResult.stdout.trim();
  const written = [];
  for (const item of SHE_RAW_SEED_CASES) {
    const url = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/sheRawCorpusCases/${encodeURIComponent(item.id)}`;
    const response = await fetch(url, {
      method: 'PATCH',
      headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json'},
      body: JSON.stringify({fields: firestoreFields({...item, updatedAtMs: Date.now()})}),
    });
    const text = await response.text();
    if (!response.ok) throw new Error(`Firestore seed failed for ${item.id}: HTTP ${response.status} ${text.slice(0, 500)}`);
    written.push(item.id);
  }
  console.log(JSON.stringify({ok: true, project: PROJECT, collection: 'sheRawCorpusCases', written}, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
