import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';

export const ACTION_OPEN = '<THRONE_ACTION>';
export const ACTION_CLOSE = '</THRONE_ACTION>';
export const MAX_FILE_BYTES = 512 * 1024;
export const MAX_RESULT_CHARS = 24000;

export function safeText(value, max = MAX_RESULT_CHARS) {
  const text = value == null ? '' : String(value);
  return text.length > max ? `${text.slice(0, max)}\n[truncated]` : text;
}

export function extractAction(text) {
  const source = String(text || '');
  const start = source.lastIndexOf(ACTION_OPEN);
  const end = source.lastIndexOf(ACTION_CLOSE);
  if (start < 0 || end <= start) return null;
  const json = source.slice(start + ACTION_OPEN.length, end).trim();
  try {
    const parsed = JSON.parse(json);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
}

export function resolveInside(root, requested = '.') {
  const base = path.resolve(root);
  const target = path.resolve(base, String(requested || '.'));
  const relative = path.relative(base, target);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`Path escapes repository root: ${requested}`);
  }
  return target;
}

export function commandIsDangerous(command) {
  const value = String(command || '').toLowerCase();
  const blocked = [
    /\bshutdown\b/,
    /\brestart-computer\b/,
    /\bstop-computer\b/,
    /\bformat\s+[a-z]:/,
    /\bdiskpart\b/,
    /\bbcdedit\b/,
    /\breg\s+delete\b/,
    /\bremove-item\b[^\n]*-[^\n]*recurse[^\n]*(?:\\windows|\\users|\\program files|[a-z]:\\)/,
    /\brm\s+-rf\s+(?:\/|~|[a-z]:[\\/])/,
    /\bdel\s+\/s\s+\/q\s+[a-z]:\\/,
  ];
  return blocked.some((pattern) => pattern.test(value));
}

async function listFiles(root, requested = '.', depth = 2) {
  const start = resolveInside(root, requested);
  const rows = [];
  const walk = async (dir, level) => {
    if (rows.length >= 500) return;
    const entries = await fs.readdir(dir, {withFileTypes: true});
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      if (rows.length >= 500) break;
      if (['.git', 'node_modules', '.venv', 'venv', 'dist', 'build'].includes(entry.name)) continue;
      const full = path.join(dir, entry.name);
      const rel = path.relative(root, full) || '.';
      rows.push(`${entry.isDirectory() ? 'd' : 'f'} ${rel}`);
      if (entry.isDirectory() && level < depth) await walk(full, level + 1);
    }
  };
  await walk(start, 0);
  return rows.join('\n');
}

async function runShell(root, command, timeoutMs = 120000) {
  if (!command || typeof command !== 'string') throw new Error('shell requires command.');
  if (commandIsDangerous(command)) throw new Error('Command blocked by Chromium Throne host-safety guard.');
  const shell = process.platform === 'win32' ? process.env.ComSpec || 'cmd.exe' : process.env.SHELL || '/bin/sh';
  const args = process.platform === 'win32' ? ['/d', '/s', '/c', command] : ['-lc', command];
  return await new Promise((resolve, reject) => {
    const child = spawn(shell, args, {cwd: root, env: process.env, windowsHide: true});
    let stdout = '';
    let stderr = '';
    const limit = 256 * 1024;
    child.stdout.on('data', (chunk) => { if (stdout.length < limit) stdout += chunk; });
    child.stderr.on('data', (chunk) => { if (stderr.length < limit) stderr += chunk; });
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error(`Command timed out after ${timeoutMs} ms.`));
    }, Math.max(1000, Math.min(Number(timeoutMs) || 120000, 10 * 60 * 1000)));
    child.on('error', (error) => { clearTimeout(timer); reject(error); });
    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({code, stdout: safeText(stdout), stderr: safeText(stderr)});
    });
  });
}

export async function executeAction(repoRoot, action) {
  const root = path.resolve(repoRoot);
  const type = String(action?.type || '').toLowerCase();
  if (type === 'list_files') {
    return {ok: true, type, output: safeText(await listFiles(root, action.path || '.', Number(action.depth ?? 2)))};
  }
  if (type === 'read_file') {
    const target = resolveInside(root, action.path);
    const stat = await fs.stat(target);
    if (stat.size > MAX_FILE_BYTES) throw new Error(`File exceeds ${MAX_FILE_BYTES} bytes: ${action.path}`);
    return {ok: true, type, path: path.relative(root, target), output: safeText(await fs.readFile(target, 'utf8'))};
  }
  if (type === 'write_file') {
    const target = resolveInside(root, action.path);
    await fs.mkdir(path.dirname(target), {recursive: true});
    const content = String(action.content ?? '');
    if (Buffer.byteLength(content, 'utf8') > MAX_FILE_BYTES) throw new Error(`write_file exceeds ${MAX_FILE_BYTES} bytes.`);
    await fs.writeFile(target, content, 'utf8');
    const readback = await fs.readFile(target, 'utf8');
    if (readback !== content) throw new Error('write_file readback mismatch.');
    return {ok: true, type, path: path.relative(root, target), bytes: Buffer.byteLength(content, 'utf8'), readback: 'matched'};
  }
  if (type === 'shell') {
    return {ok: true, type, ...(await runShell(root, action.command, action.timeoutMs))};
  }
  if (type === 'finish') {
    return {ok: true, type, finished: true, summary: safeText(action.summary || 'Finished.')};
  }
  throw new Error(`Unsupported action type: ${type || '(empty)'}`);
}

export function workerInstruction({task, repoRoot}) {
  return `You are a coding worker controlled by Chromium Throne. Work on the user's repository until the requested task is genuinely usable and tested. Do not merely explain what to do.\n\nTASK:\n${task}\n\nREPOSITORY ROOT:\n${repoRoot}\n\nYou do not have direct filesystem or shell tools. Chromium Throne will execute exactly one action at a time for you. Reply with ordinary concise reasoning if useful, but ALWAYS end every response with exactly one machine action using this envelope:\n${ACTION_OPEN}\n{"type":"list_files","path":".","depth":2}\n${ACTION_CLOSE}\n\nAllowed actions: list_files, read_file, write_file, shell, finish. Paths must stay inside the repository. Use shell for tests and normal development commands. Inspect before editing. After every tool result, continue from that result. Do not use finish until the requested artifact exists and tests or direct verification have been run. Never ask the human to do work that the throne can do. If authentication, CAPTCHA, or another genuinely human-only browser gate is required, explain the exact gate and use finish with a summary beginning HUMAN_GATE:.`;
}

export function resultPrompt(result) {
  return `THRONE_RESULT\n${JSON.stringify(result, null, 2)}\nContinue the task. End with exactly one <THRONE_ACTION> JSON action.`;
}
