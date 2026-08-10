import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { WorkstationStore } from "../src/workstation-store.mjs";
import { VeniceDurableRuntime } from "../src/durable-core/durable-runtime.mjs";

test("durable runtime snapshots survive process reopen and reconcile open loops", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "venice-durable-runtime-"));
  const database = path.join(root, "venice.db");

  let store = new WorkstationStore(database);
  const project = store.createProject({ title: "Durable project" });
  const thread = store.createThread({ projectId: project.id, title: "Restart me" });
  const runtime = new VeniceDurableRuntime({ store });
  const first = runtime.initialize();
  assert.equal(first.state.stateVersion, 1);
  assert.equal(first.coherence.status, "ready");
  assert.equal(store.durableEventCount(), 1);
  assert.equal(store.loadDurableWorkingState().derivedThroughEventId, first.event.eventId);

  const job = store.createJob({ threadId: thread.id, kind: "work", prompt: "Finish after restart" });
  store.updateJob(job.id, { status: "running", progress: { stage: "thinking" } });
  const second = runtime.refresh({ eventKind: "runtime.test.running_job", reason: "test running job" });
  assert.equal(second.state.stateVersion, 2);
  assert.equal(second.state.openLoops.length, 1);
  assert.equal(second.state.openLoops[0].jobId, job.id);
  store.close();

  store = new WorkstationStore(database);
  const afterRestart = new VeniceDurableRuntime({ store });
  const loaded = afterRestart.initialize();
  assert.equal(loaded.bootstrapped, false);
  assert.equal(loaded.state.stateVersion, 2);
  assert.equal(loaded.state.openLoops.length, 1);
  assert.equal(loaded.coherence.status, "ready");
  assert.equal(store.durableEventCount(), 2);

  store.updateJob(job.id, { status: "completed", result: { text: "done" } });
  const third = afterRestart.refresh({ eventKind: "runtime.test.job_complete", reason: "test completed job" });
  assert.equal(third.state.stateVersion, 3);
  assert.equal(third.state.openLoops.length, 0);
  assert.equal(store.durableEventCount(), 3);
  store.close();
});

test("durable transition is idempotent but rejects state regression", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "venice-durable-idempotent-"));
  const store = new WorkstationStore(path.join(root, "venice.db"));
  const runtime = new VeniceDurableRuntime({ store });
  const first = runtime.initialize();
  const committed = store.commitDurableTransition(first.event, first.state);
  assert.equal(committed.state.stateVersion, 1);
  assert.equal(store.durableEventCount(), 1);
  assert.throws(() => store.commitDurableTransition(
    { ...first.event, eventId: "evt:regression", stateVersionBefore: 1, stateVersionAfter: 0 },
    { ...first.state, stateVersion: 0, derivedThroughEventId: "evt:regression" },
  ), /regression|version/i);
  store.close();
});
