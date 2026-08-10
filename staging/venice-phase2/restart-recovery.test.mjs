import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { WorkstationRunner } from "../src/workstation-runner.mjs";
import { WorkstationStore } from "../src/workstation-store.mjs";

test("restart recovery resumes safe early work and holds possibly side-effecting work for review", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "venice-restart-recovery-"));
  const store = new WorkstationStore(path.join(root, "venice.db"));
  const project = store.createProject({ title: "Recovery" });
  const thread = store.createThread({ projectId: project.id, title: "Jobs" });

  const safe = store.createJob({ threadId: thread.id, kind: "work", prompt: "Explain something after restart" });
  store.updateJob(safe.id, { status: "running", progress: { stage: "thinking" } });

  const unsafe = store.createJob({ threadId: thread.id, kind: "work", prompt: "Potential side effect" });
  store.updateJob(unsafe.id, { status: "running", progress: { stage: "tool" } });
  store.addToolEvent(unsafe.id, "function", { name: "write_file" });

  let release;
  const blocked = new Promise((resolve) => { release = resolve; });
  const routing = {
    orient: async () => null,
    createInitial: async () => {
      await blocked;
      return { provider: "local", model: "recovery-test", client: null, response: { id: "recovered", output_text: "Recovered safely.", output: [] } };
    },
  };
  const tools = {
    definitions: () => [],
    attachmentContent: async () => ({ type: "input_text", text: "" }),
    execute: async () => { throw new Error("no tool execution expected"); },
  };
  const runner = new WorkstationRunner({
    store,
    tools,
    client: null,
    routing,
    projectRoot: root,
    connectorPath: path.join(root, "none.json"),
    publish: () => {},
    confirm: async () => false,
  });

  const report = runner.recoverPendingJobs();
  assert.equal(report.recovered.length, 1);
  assert.equal(report.recovered[0].jobId, safe.id);
  assert.equal(report.heldForReview.length, 1);
  assert.equal(report.heldForReview[0].jobId, unsafe.id);
  assert.equal(store.getJob(safe.id).status, "queued");
  assert.equal(store.getJob(unsafe.id).status, "failed");
  assert.equal(store.getJob(unsafe.id).progress.stage, "recovery_required");

  release();
  const deadline = Date.now() + 3000;
  let safeJob;
  do {
    await new Promise((resolve) => setTimeout(resolve, 20));
    safeJob = store.getJob(safe.id);
  } while (!['completed', 'failed'].includes(safeJob.status) && Date.now() < deadline);
  assert.equal(safeJob.status, "completed");
  assert.match(store.listMessages(thread.id).at(-1).content, /Recovered safely/);
  store.close();
});

test("waiting approval is never auto-replayed after restart", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "venice-restart-approval-"));
  const store = new WorkstationStore(path.join(root, "venice.db"));
  const project = store.createProject({ title: "Approval" });
  const thread = store.createThread({ projectId: project.id, title: "Approval job" });
  const job = store.createJob({ threadId: thread.id, kind: "computer", prompt: "Send something" });
  store.updateJob(job.id, { status: "waiting_approval", progress: { stage: "waiting_approval" } });
  const runner = new WorkstationRunner({
    store,
    tools: { definitions: () => [] },
    client: null,
    routing: { orient: async () => null },
    projectRoot: root,
    connectorPath: path.join(root, "none.json"),
    publish: () => {},
    confirm: async () => false,
  });
  const report = runner.recoverPendingJobs();
  assert.equal(report.recovered.length, 0);
  assert.equal(report.heldForReview.length, 1);
  assert.equal(store.getJob(job.id).status, "failed");
  assert.equal(store.getJob(job.id).progress.stage, "recovery_required");
  store.close();
});
