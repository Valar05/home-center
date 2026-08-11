import http from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { ThroneState } from "./state.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const port = Number(process.env.CHROMIUM_THRONE_PORT ?? 4777);
const host = process.env.CHROMIUM_THRONE_HOST ?? "127.0.0.1";
const headless = process.env.CHROMIUM_THRONE_HEADLESS !== "false";
const profileRoot = process.env.CHROMIUM_THRONE_PROFILE_ROOT ?? join(root, ".profiles");
const captureRoot = process.env.CHROMIUM_THRONE_CAPTURE_ROOT ?? join(root, "generated", "captures");
const state = new ThroneState();
const sessions = new Map();
const pluginManifest = JSON.parse(await readFile(join(root, "plugins", "manifest.json"), "utf8"));

await mkdir(profileRoot, { recursive: true });
await mkdir(captureRoot, { recursive: true });

function json(res, status, value) {
  const body = JSON.stringify(value);
  res.writeHead(status, { "content-type": "application/json; charset=utf-8", "content-length": Buffer.byteLength(body) });
  res.end(body);
}

async function body(req, limit = 256_000) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > limit) throw Object.assign(new Error("BODY_TOO_LARGE"), { status: 413 });
    chunks.push(chunk);
  }
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {};
}

function route(url) {
  const parts = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  return parts;
}

async function launchThread(input) {
  if ((input.costClass === "CREDIT_BEARING_CODEX" || input.costClass === "PAID_PROVIDER") && input.explicitCostAuthority !== true) {
    throw Object.assign(new Error("EXPLICIT_COST_AUTHORITY_REQUIRED"), { status: 409 });
  }
  const thread = state.create(input);
  try {
    const context = await chromium.launchPersistentContext(join(profileRoot, thread.threadId.replace(/[:]/g, "_")), {
      headless,
      viewport: { width: 1440, height: 960 },
      args: ["--disable-background-timer-throttling", "--disable-renderer-backgrounding"],
    });
    const page = context.pages()[0] ?? await context.newPage();
    page.on("console", message => state.emit("TAB_CONSOLE", { threadId: thread.threadId, level: message.type(), text: message.text().slice(0, 500) }));
    page.on("crash", () => state.update(thread.threadId, { state: "FAILED", blocker: "TAB_CRASHED" }));
    await page.goto(thread.url, { waitUntil: "domcontentloaded", timeout: 45_000 });
    sessions.set(thread.threadId, { context, page });
    return state.update(thread.threadId, { state: "RUNNING", title: (await page.title()).slice(0, 120) || thread.title });
  } catch (error) {
    state.update(thread.threadId, { state: "FAILED", blocker: error.message });
    throw error;
  }
}

async function screenshot(threadId) {
  const session = sessions.get(threadId);
  if (!session) throw Object.assign(new Error("THREAD_NOT_LIVE"), { status: 404 });
  const at = new Date().toISOString().replace(/[:.]/g, "-");
  const path = join(captureRoot, `${threadId.replace(/[:]/g, "_")}-${at}.png`);
  await session.page.screenshot({ path, fullPage: false });
  state.update(threadId, { lastScreenshot: { path, capturedAt: new Date().toISOString() } });
  return path;
}

async function closeThread(threadId) {
  const session = sessions.get(threadId);
  if (session) await session.context.close();
  sessions.delete(threadId);
  return state.update(threadId, { state: "CLOSED" });
}

async function watchVeniceReply(threadId, beforeCount) {
  const session = sessions.get(threadId);
  if (!session) return;
  const replies = session.page.locator('[data-message-author-role="assistant"]');
  const deadline = Date.now() + 120_000;
  let last = "", stable = 0;
  while (Date.now() < deadline) {
    const count = await replies.count().catch(() => 0);
    const text = count > beforeCount ? (await replies.nth(count - 1).innerText().catch(() => "")).trim() : "";
    if (text && text === last) stable += 1; else stable = 0;
    last = text;
    if (last && stable >= 2) {
      state.addMessage(threadId, { speaker: "Venice", kind: "SOCIAL", text: last });
      state.update(threadId, { state: "RUNNING", summary: last.slice(0, 240) });
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  state.update(threadId, { state: "BLOCKED", blocker: "VENICE_REPLY_TIMEOUT" });
}

async function sendToConversation(threadId, input) {
  const thread = state.get(threadId);
  const session = sessions.get(threadId);
  if (!thread || !session) throw Object.assign(new Error("THREAD_NOT_LIVE"), { status: 404 });
  if (thread.conversationEngine !== "Venice") throw Object.assign(new Error("VENICE_ENGINE_REQUIRED"), { status: 409 });
  if (input.humanInitiated !== true) throw Object.assign(new Error("HUMAN_INITIATION_REQUIRED"), { status: 409 });
  if (!['SOCIAL', 'COMMAND'].includes(input.kind)) throw Object.assign(new Error("INVALID_MESSAGE_KIND"), { status: 400 });
  const text = String(input.text ?? "").trim();
  if (!text) throw Object.assign(new Error("EMPTY_MESSAGE"), { status: 400 });
  const replies = session.page.locator('[data-message-author-role="assistant"]');
  const beforeCount = await replies.count().catch(() => 0);
  const composer = session.page.locator('[data-testid="prompt-textarea"], #prompt-textarea, textarea').first();
  await composer.waitFor({ state: "visible", timeout: 15_000 });
  await composer.fill(text);
  const send = session.page.locator('[data-testid="send-button"], button[aria-label*="Send" i]').first();
  await send.click({ timeout: 10_000 });
  const message = state.addMessage(threadId, { speaker: "Drew", kind: input.kind, text });
  state.update(threadId, { state: "WAITING", summary: input.kind === "COMMAND" ? "Command carried along the nerve." : "Venice is listening." });
  void watchVeniceReply(threadId, beforeCount);
  return message;
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host ?? `${host}:${port}`}`);
    const parts = route(url);
    if (req.method === "GET" && url.pathname === "/") {
      const page = await readFile(join(root, "public", "index.html"));
      res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      return res.end(page);
    }
    if (req.method === "GET" && url.pathname === "/api/health") return json(res, 200, { ok: true, service: "chromium-throne", version: "0.1.0", headless, frontend: true });
    if (req.method === "GET" && url.pathname === "/api/plugins") return json(res, 200, pluginManifest);
    if (req.method === "GET" && url.pathname === "/api/threads") return json(res, 200, { threads: state.list() });
    if (req.method === "POST" && url.pathname === "/api/threads") return json(res, 201, await launchThread(await body(req)));
    if (req.method === "GET" && url.pathname === "/api/events") {
      res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache", connection: "keep-alive" });
      for (const event of state.events(Number(url.searchParams.get("after") ?? 0))) res.write(`id: ${event.sequence}\ndata: ${JSON.stringify(event)}\n\n`);
      const unsubscribe = state.subscribe(event => res.write(`id: ${event.sequence}\ndata: ${JSON.stringify(event)}\n\n`));
      req.on("close", unsubscribe);
      return;
    }
    if (parts[0] === "api" && parts[1] === "threads" && parts[2]) {
      const threadId = parts[2];
      if (req.method === "GET" && parts.length === 3) return json(res, state.get(threadId) ? 200 : 404, state.get(threadId) ?? { error: "THREAD_NOT_FOUND" });
      if (req.method === "GET" && parts[3] === "messages") return json(res, 200, { messages: state.messages(threadId) });
      if (req.method === "POST" && parts[3] === "messages") return json(res, 202, await sendToConversation(threadId, await body(req)));
      if (req.method === "POST" && parts[3] === "screenshot") return json(res, 200, { threadId, path: await screenshot(threadId) });
      if (req.method === "POST" && parts[3] === "pause") return json(res, 200, state.update(threadId, { state: "PAUSED" }));
      if (req.method === "POST" && parts[3] === "resume") return json(res, 200, state.update(threadId, { state: "RUNNING" }));
      if (req.method === "DELETE" && parts.length === 3) return json(res, 200, await closeThread(threadId));
    }
    json(res, 404, { error: "NOT_FOUND" });
  } catch (error) {
    json(res, error.status ?? 500, { error: error.message });
  }
});

async function shutdown() {
  await Promise.allSettled([...sessions.values()].map(session => session.context.close()));
  server.close(() => process.exit(0));
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
server.listen(port, host, () => console.log(JSON.stringify({ ok: true, url: `http://${host}:${port}`, headless })));
