import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { WorkstationStore } from '../src/workstation-store.mjs';
import { memoryRecordText, memoryRecordView, promoteMemoryInput } from '../src/durable-core/memory-policy.mjs';

test('manual user memory is high-authority typed durable memory with UI-compatible view', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'venice-memory-user-'));
  const store = new WorkstationStore(path.join(root, 'venice.db'));
  const record = promoteMemoryInput({ scope: 'global', key: 'tone', value: 'warm and direct', source: 'user', type: 'preference' }, { threadId: 'thread-1' });
  assert.equal(record.promotedBy, 'drew');
  assert.equal(record.authorityRank, 100);
  assert.equal(record.confidence, 1);
  store.putDurableMemory(record);
  const listed = store.listDurableMemories({ scopeKind: 'global' });
  assert.equal(listed.length, 1);
  const view = memoryRecordView(listed[0]);
  assert.equal(view.id, record.memoryId);
  assert.equal(view.key, 'tone');
  assert.equal(view.value, 'warm and direct');
  assert.equal(view.type, 'preference');
  assert.match(memoryRecordText(listed[0]), /tone: warm and direct/);
  store.close();
});

test('Venice-authored project memory has lower authority and concrete provenance', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'venice-memory-agent-'));
  const store = new WorkstationStore(path.join(root, 'venice.db'));
  const record = promoteMemoryInput({ scope: 'project', key: 'build', value: 'local first', source: 'venice' }, { projectId: 'project-1', threadId: 'thread-1', jobId: 'job-1' });
  assert.equal(record.type, 'project_fact');
  assert.equal(record.scope.kind, 'project');
  assert.equal(record.scope.id, 'project-1');
  assert.equal(record.promotedBy, 'venice_rule');
  assert.equal(record.authorityRank, 40);
  assert.equal(record.confidence, 0.75);
  assert.deepEqual(record.sourceRefs.includes('job:job-1'), true);
  store.putDurableMemory(record);
  assert.equal(store.listDurableMemories({ scopeKind: 'project', scopeId: 'project-1' }).length, 1);
  store.close();
});

test('retiring memory changes active status overlay without mutating immutable record bytes', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'venice-memory-retire-'));
  const store = new WorkstationStore(path.join(root, 'venice.db'));
  const record = promoteMemoryInput({ scope: 'global', key: 'old', value: 'value', source: 'user' }, { threadId: 'thread-1' });
  store.putDurableMemory(record);
  const beforeJson = store.db.prepare('SELECT memory_json FROM durable_memories WHERE memory_id=?').get(record.memoryId).memory_json;
  assert.equal(store.retireDurableMemory(record.memoryId, 'superseded'), true);
  assert.equal(store.listDurableMemories({ scopeKind: 'global' }).length, 0);
  const retired = store.getDurableMemory(record.memoryId);
  assert.equal(retired.status, 'superseded');
  const afterJson = store.db.prepare('SELECT memory_json FROM durable_memories WHERE memory_id=?').get(record.memoryId).memory_json;
  assert.equal(afterJson, beforeJson);
  store.close();
});
