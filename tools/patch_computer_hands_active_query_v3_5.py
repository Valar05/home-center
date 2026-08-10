from pathlib import Path

p = Path('functions/computer_hands_api.js')
s = p.read_text(encoding='utf-8')
old_status = "  const pending = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', owner).limit(100).get();\n  const rows = pending.docs.map((doc) => doc.data() || {}).filter((item) => item.workerId === workerId && ['queued', 'leased', 'running'].includes(item.status));"
new_status = "  // Query active states before filtering owner/worker so completed ticket history can never starve new work beyond an arbitrary historical limit.\n  const pending = await admin.firestore().collection(COLLECTIONS.tickets).where('status', 'in', ['queued', 'leased', 'running']).limit(500).get();\n  const rows = pending.docs.map((doc) => doc.data() || {}).filter((item) => item.ownerKey === owner && item.workerId === workerId);"
old_lease = "  const query = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', worker.ownerKey).limit(100).get();\n  const eligible = query.docs.map((doc) => ({ref: doc.ref, row: doc.data() || {}})).filter((item) => {\n    if (item.row.workerId !== worker.workerId || item.row.cancelRequested === true || item.row.status === 'cancelled') return false;"
new_lease = "  // Active-state query avoids historical-ticket starvation while retaining terminal receipts indefinitely.\n  const query = await admin.firestore().collection(COLLECTIONS.tickets).where('status', 'in', ['queued', 'leased', 'running']).limit(500).get();\n  const eligible = query.docs.map((doc) => ({ref: doc.ref, row: doc.data() || {}})).filter((item) => {\n    if (item.row.ownerKey !== worker.ownerKey || item.row.workerId !== worker.workerId || item.row.cancelRequested === true || item.row.status === 'cancelled') return false;"
if old_status not in s:
    raise SystemExit('missing workerStatus active-query anchor')
if old_lease not in s:
    raise SystemExit('missing lease active-query anchor')
s = s.replace(old_status, new_status, 1)
s = s.replace(old_lease, new_lease, 1)
p.write_text(s, encoding='utf-8')
print('computer hands active-query v3.5 patch applied')
