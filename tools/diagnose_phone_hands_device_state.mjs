#!/usr/bin/env node
import crypto from 'node:crypto';
import admin from 'firebase-admin';

const project = process.env.PROJECT || 'home-center-dclar';
const ownerEmail = String(process.env.OWNER_EMAIL || '').trim().toLowerCase();
if (!ownerEmail) throw new Error('OWNER_EMAIL is required');
const hash = (value) => crypto.createHash('sha256').update(String(value || '')).digest('hex');
const ownerKey = 'owner_' + hash(ownerEmail).slice(0, 32);

admin.initializeApp({projectId: project});
const snap = await admin.firestore().collection('phoneHandsDevices').where('ownerKey', '==', ownerKey).limit(20).get();
const now = Date.now();
const devices = snap.docs.map((doc) => {
  const row = doc.data() || {};
  const lastSeenAtMs = Number(row.lastSeenAtMs || 0);
  const heartbeatAgeMs = lastSeenAtMs ? now - lastSeenAtMs : null;
  return {
    deviceId: String(row.deviceId || ''),
    label: String(row.label || ''),
    status: String(row.status || 'unknown'),
    online: Boolean(lastSeenAtMs && heartbeatAgeMs >= 0 && heartbeatAgeMs < 45000),
    lastSeenAtMs,
    updatedAtMs: Number(row.updatedAtMs || 0),
    heartbeatAgeMs,
    capabilities: Array.isArray(row.capabilities) ? row.capabilities.map(String) : [],
  };
});
console.log(JSON.stringify({
  ok: true,
  source: 'production Firestore phoneHandsDevices',
  ownerPartition: ownerKey,
  observedAt: new Date(now).toISOString(),
  mutationPerformed: false,
  devices,
}, null, 2));
