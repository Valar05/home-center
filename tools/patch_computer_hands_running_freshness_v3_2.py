from pathlib import Path

path = Path('functions/computer_hands_api.js')
text = path.read_text(encoding='utf-8')

old = "const LEASE_TTL_MS = 2 * 60 * 1000;"
new = "const LEASE_TTL_MS = 3 * 60 * 1000;"
if text.count(old) != 1:
    raise SystemExit(f'lease TTL marker count was {text.count(old)}')
text = text.replace(old, new, 1)

old = "  const row = snap.data() || {};\n  const lastSeenAtMs = Number(row.lastSeenAtMs || 0);\n  const pending = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', owner).limit(100).get();"
new = "  const row = snap.data() || {};\n  const lastSeenAtMs = Number(row.lastSeenAtMs || 0);\n  const updatedAtMs = Number(row.updatedAtMs || 0);\n  const state = safeText(row.state, 80) || 'unknown';\n  const onlineFreshnessMs = ['running', 'leased'].includes(state) ? LEASE_TTL_MS + 15000 : 30000;\n  const heartbeatAtMs = Math.max(lastSeenAtMs, ['running', 'leased'].includes(state) ? updatedAtMs : 0);\n  const online = heartbeatAtMs > 0 && Date.now() - heartbeatAtMs < onlineFreshnessMs;\n  const pending = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', owner).limit(100).get();"
if text.count(old) != 1:
    raise SystemExit(f'worker-status setup marker count was {text.count(old)}')
text = text.replace(old, new, 1)

old = "  return {workerId, status: safeText(row.state, 80) || 'unknown', online: lastSeenAtMs > 0 && Date.now() - lastSeenAtMs < 30000, lastSeenAtMs, workerVersion: safeText(row.workerVersion, 120), machine: row.machine || null, capabilities: row.capabilities || SUPPORTED_ACTIONS, fileLayer: 'drive_sync', queueDepth: rows.length, activeLanes, lastServedLaneId: safeText(row.lastServedLaneId, 160)};"
new = "  return {workerId, status: state, online, lastSeenAtMs, updatedAtMs, onlineFreshnessMs, workerVersion: safeText(row.workerVersion, 120), machine: row.machine || null, capabilities: row.capabilities || SUPPORTED_ACTIONS, fileLayer: 'drive_sync', queueDepth: rows.length, activeLanes, lastServedLaneId: safeText(row.lastServedLaneId, 160)};"
if text.count(old) != 1:
    raise SystemExit(f'worker-status return marker count was {text.count(old)}')
text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
print('Computer Hands running freshness v3.2 patch applied')
