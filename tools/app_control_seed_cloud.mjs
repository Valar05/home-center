#!/usr/bin/env node
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const admin = require('../functions/node_modules/firebase-admin');
const {APP_CONTROL_DEFAULT_SEEDS, appControlProfileObjectId, appControlProfilePath} = require('../functions/app_control_cloud');

function parseArgs(argv) {
  const args = {projectId: process.env.FIREBASE_PROJECT || 'home-center-dclar', rest: false};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--rest') args.rest = true;
    else if (arg === '--project') args.projectId = argv[++i];
    else if (!arg.startsWith('-')) args.projectId = arg;
    else throw new Error(`Unknown arg: ${arg}`);
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));
const projectId = args.projectId;

function fullHash(value) {
  return createHash('sha256').update(String(value || '')).digest('hex');
}

function bucketObjectForProfile(profile) {
  const body = JSON.stringify(profile, null, 2);
  return {
    objectId: appControlProfileObjectId(profile),
    bucketId: 'command-center',
    kind: 'app_control.profile',
    lane: 'app-control/profiles',
    path: appControlProfilePath(profile),
    title: `App control profile ${profile.profileId}`,
    summary: (profile.source && profile.source.summary) || `Cloud app-control profile for ${profile.packageName}.`,
    body,
    objectUri: '',
    contentHash: fullHash(body),
    projectId: 'home-center',
    repository: 'Valar05/home-center',
    jobId: '',
    sourceRefs: [`firestore://appControlProfiles/${profile.profileId}`],
    evidenceRefs: profile.source && profile.source.evidencePath ? [profile.source.evidencePath] : [],
    tags: ['app-control', profile.packageName, profile.status || 'candidate'],
    promotionState: 'active',
    supersedes: [],
    createdBy: 'tools/app_control_seed_cloud.mjs',
    updatedBy: 'tools/app_control_seed_cloud.mjs',
    provenance: {actor: 'tools/app_control_seed_cloud.mjs', source: 'app_control_seed_cloud', noSecrets: true},
  };
}


function firestoreValue(value) {
  if (value === null || value === undefined) return {nullValue: null};
  if (typeof value === 'string') return {stringValue: value};
  if (typeof value === 'boolean') return {booleanValue: value};
  if (typeof value === 'number') return Number.isInteger(value) ? {integerValue: String(value)} : {doubleValue: value};
  if (Array.isArray(value)) return {arrayValue: {values: value.map(firestoreValue)}};
  if (typeof value === 'object') return {mapValue: {fields: firestoreFields(value)}};
  return {stringValue: String(value)};
}

function firestoreFields(object) {
  return Object.fromEntries(Object.entries(object || {}).filter(([, value]) => value !== undefined).map(([key, value]) => [key, firestoreValue(value)]));
}

async function firestorePatch(projectId, collection, docId, data, token) {
  const url = `https://firestore.googleapis.com/v1/projects/${encodeURIComponent(projectId)}/databases/(default)/documents/${encodeURIComponent(collection)}/${encodeURIComponent(docId)}`;
  const response = await fetch(url, {
    method: 'PATCH',
    headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json'},
    body: JSON.stringify({fields: firestoreFields(data)}),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`Firestore REST ${collection}/${docId} HTTP ${response.status}: ${text.slice(0, 1000)}`);
  return JSON.parse(text);
}

async function seedWithRest(projectId) {
  const {execFileSync} = await import('node:child_process');
  const token = String(execFileSync('gcloud', ['auth', 'print-access-token'], {encoding: 'utf8'})).trim();
  const nowMs = Date.now();
  const written = [];
  for (const seed of APP_CONTROL_DEFAULT_SEEDS) {
    const profile = {...seed, createdAtMs: nowMs, updatedAtMs: nowMs, createdBy: 'tools/app_control_seed_cloud.mjs', updatedBy: 'tools/app_control_seed_cloud.mjs'};
    await firestorePatch(projectId, 'appControlProfiles', profile.profileId, profile, token);
    const object = {...bucketObjectForProfile(profile), createdAtMs: nowMs, updatedAtMs: nowMs};
    await firestorePatch(projectId, 'commandCenterBucketObjects', object.objectId, object, token);
    written.push({profileId: profile.profileId, bucketObjectId: object.objectId});
  }
  return {ok: true, mode: 'firestore-rest', projectId, written};
}

if (args.rest) {
  console.log(JSON.stringify(await seedWithRest(projectId), null, 2));
  process.exit(0);
}

if (!admin.apps.length) {
  admin.initializeApp({projectId, credential: admin.credential.applicationDefault()});
}
const db = admin.firestore();
const nowMs = Date.now();
const written = [];
for (const seed of APP_CONTROL_DEFAULT_SEEDS) {
  const profile = {...seed, updatedAtMs: nowMs};
  const profileRef = db.collection('appControlProfiles').doc(profile.profileId);
  const existingProfile = await profileRef.get();
  await profileRef.set({
    ...profile,
    createdAtMs: existingProfile.exists ? (existingProfile.data().createdAtMs || nowMs) : nowMs,
    createdBy: existingProfile.exists ? (existingProfile.data().createdBy || 'tools/app_control_seed_cloud.mjs') : 'tools/app_control_seed_cloud.mjs',
    updatedBy: 'tools/app_control_seed_cloud.mjs',
  }, {merge: true});

  const object = {...bucketObjectForProfile(profile), createdAtMs: nowMs, updatedAtMs: nowMs};
  const bucketRef = db.collection('commandCenterBucketObjects').doc(object.objectId);
  const existingBucket = await bucketRef.get();
  await bucketRef.set({
    ...object,
    createdAtMs: existingBucket.exists ? (existingBucket.data().createdAtMs || nowMs) : nowMs,
    createdBy: existingBucket.exists ? (existingBucket.data().createdBy || object.createdBy) : object.createdBy,
  }, {merge: true});
  written.push({profileId: profile.profileId, bucketObjectId: object.objectId});
}
console.log(JSON.stringify({ok: true, projectId, written}, null, 2));
await admin.app().delete();
