const assert = require('node:assert/strict');
const test = require('node:test');

const {
  parseDueAt,
  captureReminder,
  listOpenReminders,
  closeReminder,
  rescheduleReminder,
} = require('../functions/headcrab_reminder_store');

function fakeAdmin() {
  const docs = new Map();
  function docRef(path) {
    return {
      id: path.split('/').pop(),
      collection(name) { return collectionRef(path + '/' + name); },
      async get() { return {exists: docs.has(path), data: () => docs.get(path)}; },
      async set(value, opts = {}) {
        docs.set(path, opts.merge ? {...(docs.get(path) || {}), ...value} : {...value});
      },
    };
  }
  function collectionRef(path) {
    return {
      doc(id) {
        const realId = id || ('r' + String(docs.size + 1));
        return docRef(path + '/' + realId);
      },
      limit() {
        return {
          async get() {
            const prefix = path + '/';
            const rows = [...docs.entries()].filter(([key]) => key.startsWith(prefix) && !key.slice(prefix.length).includes('/'));
            return {forEach(fn) { for (const [key, value] of rows) fn({id: key.slice(prefix.length), data: () => value}); }};
          },
        };
      },
    };
  }
  return {firestore() { return {collection: collectionRef}; }};
}

const user = {email: 'dclarke1005@gmail.com'};

test('untimed reminders persist without inventing a schedule', async () => {
  const admin = fakeAdmin();
  const created = await captureReminder({admin, user, label: 'Call credit cards about hardship'});
  assert.equal(created.created, true);
  assert.equal(created.reminder.dueAt, null);
  const open = await listOpenReminders({admin, user});
  assert.equal(open.length, 1);
  assert.equal(open[0].label, 'Call credit cards about hardship');
});

test('same open label and due time is idempotent', async () => {
  const admin = fakeAdmin();
  const dueAt = '2026-10-02T18:30:00-05:00';
  const a = await captureReminder({admin, user, label: 'Call Cori', dueAt});
  const b = await captureReminder({admin, user, label: 'Call Cori', dueAt});
  assert.equal(a.created, true);
  assert.equal(b.created, false);
  assert.equal(a.reminder.reminderId, b.reminder.reminderId);
});

test('close removes reminder from open stack', async () => {
  const admin = fakeAdmin();
  const item = await captureReminder({admin, user, label: 'Get psychiatrist records'});
  await closeReminder({admin, user, reminderId: item.reminder.reminderId, status: 'done'});
  assert.deepEqual(await listOpenReminders({admin, user}), []);
});

test('reschedule changes state but creates no external schedule', async () => {
  const admin = fakeAdmin();
  const item = await captureReminder({admin, user, label: 'Get records'});
  const updated = await rescheduleReminder({
    admin,
    user,
    reminderId: item.reminder.reminderId,
    dueAt: '2026-10-02T11:00:00-05:00',
  });
  assert.equal(updated.dueAt, '2026-10-02T16:00:00.000Z');
  const open = await listOpenReminders({admin, user});
  assert.equal(open[0].dueAt, '2026-10-02T16:00:00.000Z');
});

test('dueAt must be timezone-aware', () => {
  assert.throws(() => parseDueAt('2026-10-02T11:00:00'), /timezone/);
});
