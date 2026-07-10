#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import childProcess from 'node:child_process';

function parseArgs(argv) {
  const args = {repo: process.cwd(), out: 'generated/engineering_memory', workflow: 'engineering-orientation-v1', selfTest: false, stdout: false};
  for (let i = 2; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === '--self-test') args.selfTest = true;
    else if (item === '--stdout') args.stdout = true;
    else if (item === '--repo') args.repo = argv[++i];
    else if (item === '--out') args.out = argv[++i];
    else if (item === '--workflow') args.workflow = argv[++i];
    else if (item === '--help' || item === '-h') args.help = true;
    else throw new Error(`Unknown argument: ${item}`);
  }
  return args;
}

function usage() {
  return `Usage: node tools/home_center_engineering_orient.mjs --repo <path> --out generated/engineering_memory\n\nCreates a durable repository orientation report and JSONL engineering-memory records.\n`;
}

function nowIso() { return new Date().toISOString(); }
function sha256(value) { return crypto.createHash('sha256').update(String(value)).digest('hex'); }
function shortHash(value) { return sha256(value).slice(0, 16); }
function safeSlug(value) {
  return String(value || 'repo').toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80) || 'repo';
}
function nodeId(type, identity) { return `${type}:${shortHash(identity)}`; }
function ensureDir(dir) { fs.mkdirSync(dir, {recursive: true}); }
function readText(file, max = 20000) {
  try { return fs.readFileSync(file, 'utf8').slice(0, max); } catch { return ''; }
}
function exists(file) { return fs.existsSync(file); }
function rel(root, file) { return path.relative(root, file).replace(/\\/g, '/'); }
function walk(root, maxDepth = 3, maxFiles = 600) {
  const out = [];
  const ignore = new Set(['.git', 'node_modules', 'build', '.gradle', '.godot', '__pycache__', '.cache']);
  function visit(dir, depth) {
    if (out.length >= maxFiles || depth > maxDepth) return;
    let entries = [];
    try { entries = fs.readdirSync(dir, {withFileTypes: true}); } catch { return; }
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      if (out.length >= maxFiles) return;
      if (ignore.has(entry.name)) continue;
      const full = path.join(dir, entry.name);
      out.push(full);
      if (entry.isDirectory()) visit(full, depth + 1);
    }
  }
  visit(root, 0);
  return out;
}
function run(cmd, cwd) {
  try {
    return {ok: true, stdout: childProcess.execFileSync(cmd[0], cmd.slice(1), {cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']}).trim()};
  } catch (err) {
    return {ok: false, stdout: '', error: String((err.stderr && err.stderr.toString()) || err.message || err)};
  }
}
function gitInfo(repo) {
  const inside = run(['git', 'rev-parse', '--is-inside-work-tree'], repo);
  if (!inside.ok || inside.stdout !== 'true') return {isGit: false};
  const branch = run(['git', 'branch', '--show-current'], repo).stdout || '';
  const commit = run(['git', 'rev-parse', 'HEAD'], repo).stdout || '';
  const root = run(['git', 'rev-parse', '--show-toplevel'], repo).stdout || repo;
  const remote = run(['git', 'remote', '-v'], repo).stdout.split('\n').filter(Boolean).slice(0, 8);
  const statusShort = run(['git', 'status', '--short'], repo).stdout.split('\n').filter(Boolean);
  const recent = run(['git', 'log', '--oneline', '-n', '8'], repo).stdout.split('\n').filter(Boolean);
  return {isGit: true, root, branch, commit, dirty: statusShort.length > 0, statusShort, remotes: remote, recentCommits: recent};
}
function discoverDocs(repo, files) {
  const wanted = files.filter((file) => {
    const r = rel(repo, file);
    return /(^|\/)(README|AGENTS|PROJECT_ORIENTATION|PROJECT_MANIFEST|CHANGELOG|CONTRIBUTING|STEERING)\.md$/i.test(r)
      || /^docs\/.*\.md$/i.test(r)
      || /^\.github\/.*\.md$/i.test(r);
  }).slice(0, 80);
  return wanted.map((file) => ({path: rel(repo, file), title: firstMarkdownTitle(file)}));
}
function firstMarkdownTitle(file) {
  const text = readText(file, 4000);
  const line = text.split(/\r?\n/).find((item) => item.startsWith('# '));
  return line ? line.replace(/^#\s+/, '').trim() : '';
}
function discoverBuildSystems(repo) {
  const checks = [
    ['node', 'package.json'], ['gradle', 'build.gradle'], ['gradle-settings', 'settings.gradle'], ['android', 'app/build.gradle'],
    ['python-pyproject', 'pyproject.toml'], ['python-requirements', 'requirements.txt'], ['godot', 'project.godot'],
    ['firebase', 'firebase.json'], ['docker', 'Dockerfile'], ['github-actions', '.github/workflows'],
  ];
  return checks.filter(([, p]) => exists(path.join(repo, p))).map(([kind, p]) => ({kind, path: p}));
}
function discoverValidation(repo) {
  const commands = [];
  const add = (command, reason) => commands.push({command, reason});
  if (exists(path.join(repo, 'tools/run_regression_tests.sh'))) add('sh tools/run_regression_tests.sh', 'project regression harness');
  if (exists(path.join(repo, 'package.json'))) add('npm test', 'package.json present');
  if (exists(path.join(repo, 'build.gradle'))) add('gradle test --no-daemon', 'Gradle project present');
  if (exists(path.join(repo, 'pyproject.toml')) || exists(path.join(repo, 'requirements.txt'))) add('python -m pytest', 'Python project indicators present');
  if (exists(path.join(repo, 'project.godot'))) add('godot --headless --path . --quit', 'Godot project present');
  if (exists(path.join(repo, 'tools/check_no_secrets.sh'))) add('sh tools/check_no_secrets.sh', 'secret hygiene check');
  return commands;
}
function discoverArtifactDirs(repo, files) {
  const dirs = new Set();
  for (const file of files) {
    const r = rel(repo, file);
    if (/^(generated|reports|release|dist|tools\/.*evidence|build\/reports|app\/build\/outputs)(\/|$)/.test(r)) {
      const top = r.split('/').slice(0, r.startsWith('tools/') ? 2 : 1).join('/');
      dirs.add(top);
    }
  }
  return [...dirs].sort().slice(0, 80);
}
function appendJsonl(file, record) {
  ensureDir(path.dirname(file));
  fs.appendFileSync(file, JSON.stringify(record) + '\n');
}
function writeJson(file, record) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, JSON.stringify(record, null, 2) + '\n');
}
function writeMarkdown(file, text) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, text);
}
function orientationMarkdown(report) {
  const g = report.git;
  return `# Repository Orientation: ${report.repository.name}\n\n` +
    `Generated: ${report.generatedAt}\n\n` +
    `## Repository\n\n- Path: ${report.repository.path}\n- Node: ${report.repository.nodeId}\n- Git: ${g.isGit ? 'yes' : 'no'}\n- Branch: ${g.branch || 'n/a'}\n- Commit: ${g.commit || 'n/a'}\n- Dirty: ${g.dirty ? 'yes' : 'no'}\n\n` +
    `## Build Systems\n\n${bullet(report.buildSystems.map((b) => `${b.kind}: ${b.path}`))}\n\n` +
    `## Validation Commands\n\n${bullet(report.validationCommands.map((v) => `${v.command} (${v.reason})`))}\n\n` +
    `## Important Docs\n\n${bullet(report.docs.map((d) => d.title ? `${d.path} - ${d.title}` : d.path))}\n\n` +
    `## Artifact Dirs\n\n${bullet(report.artifactDirs)}\n\n` +
    `## Recent Commits\n\n${bullet(g.recentCommits || [])}\n\n` +
    `## Dirty Files\n\n${bullet(g.statusShort || [])}\n\n` +
    `## Unknowns\n\n${bullet(report.unknowns)}\n`;
}
function bullet(items) { return items && items.length ? items.map((x) => `- ${x}`).join('\n') : '- none found'; }
function orient(options) {
  const repo = path.resolve(options.repo || process.cwd());
  if (!exists(repo) || !fs.statSync(repo).isDirectory()) throw new Error(`Repo path is not a directory: ${repo}`);
  const out = path.resolve(options.out || 'generated/engineering_memory');
  const generatedAt = nowIso();
  const files = walk(repo);
  const git = gitInfo(repo);
  const repoName = path.basename(git.root || repo);
  const repoIdentity = `${git.root || repo}|${git.commit || 'no-commit'}`;
  const repository = {type: 'engineering.repository', nodeId: nodeId('engineering.repository', repoIdentity), name: repoName, path: repo, gitRoot: git.root || '', branch: git.branch || '', commit: git.commit || '', dirty: !!git.dirty, discoveredAt: generatedAt};
  const orientationId = nodeId('engineering.orientation', `${repo}|${generatedAt}|${git.commit || ''}`);
  const slug = `${generatedAt.replace(/[:.]/g, '-').replace('T', '_').replace('Z', 'Z')}_${safeSlug(repoName)}`;
  const report = {
    type: 'engineering.orientation', nodeId: orientationId, generatedAt, workflowId: options.workflow,
    repository, git, docs: discoverDocs(repo, files), buildSystems: discoverBuildSystems(repo),
    validationCommands: discoverValidation(repo), artifactDirs: discoverArtifactDirs(repo, files),
    unsupportedCapabilities: [],
    unknowns: ['Open issues, pull requests, cloud workflow state, and provider credentials require connected service queries.'],
  };
  const jsonPath = path.join(out, 'orientations', `${slug}.json`);
  const mdPath = path.join(out, 'orientations', `${slug}.md`);
  report.artifacts = {json: path.relative(out, jsonPath).replace(/\\/g, '/'), markdown: path.relative(out, mdPath).replace(/\\/g, '/')};
  writeJson(jsonPath, report);
  writeMarkdown(mdPath, orientationMarkdown(report));
  appendJsonl(path.join(out, 'repositories.jsonl'), repository);
  appendJsonl(path.join(out, 'orientations.jsonl'), {nodeId: orientationId, type: 'engineering.orientation', generatedAt, repositoryNodeId: repository.nodeId, repoPath: repo, branch: git.branch || '', commit: git.commit || '', dirty: !!git.dirty, jsonPath: report.artifacts.json, markdownPath: report.artifacts.markdown});
  appendJsonl(path.join(out, 'workflow_runs.jsonl'), {type: 'engineering.workflow_run', nodeId: nodeId('engineering.workflow_run', `${options.workflow}|${orientationId}`), workflowId: options.workflow, status: 'completed', generatedAt, repositoryNodeId: repository.nodeId, outputNodeId: orientationId});
  appendJsonl(path.join(out, 'edges.jsonl'), {type: 'engineering.edge', from: orientationId, to: repository.nodeId, relation: 'belongs_to', generatedAt});
  appendJsonl(path.join(out, 'edges.jsonl'), {type: 'engineering.edge', from: orientationId, to: repository.nodeId, relation: 'generated_from', generatedAt});
  return report;
}
function selfTest() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'hc-engineering-orient-'));
  const repo = path.join(tmp, 'repo');
  fs.mkdirSync(repo);
  fs.writeFileSync(path.join(repo, 'README.md'), '# Fixture Repo\n');
  fs.mkdirSync(path.join(repo, 'tools'));
  fs.writeFileSync(path.join(repo, 'tools', 'run_regression_tests.sh'), '#!/bin/sh\necho ok\n');
  childProcess.execFileSync('git', ['init'], {cwd: repo, stdio: 'ignore'});
  childProcess.execFileSync('git', ['config', 'user.email', 'fixture@example.com'], {cwd: repo, stdio: 'ignore'});
  childProcess.execFileSync('git', ['config', 'user.name', 'Fixture'], {cwd: repo, stdio: 'ignore'});
  childProcess.execFileSync('git', ['add', '.'], {cwd: repo, stdio: 'ignore'});
  childProcess.execFileSync('git', ['commit', '-m', 'fixture'], {cwd: repo, stdio: 'ignore'});
  fs.writeFileSync(path.join(repo, 'scratch.txt'), 'dirty\n');
  const out = path.join(tmp, 'memory');
  const report = orient({repo, out, workflow: 'self-test'});
  if (!report.git.isGit || !report.git.dirty) throw new Error('self-test expected dirty git repo');
  if (!report.docs.some((d) => d.path === 'README.md')) throw new Error('self-test expected README discovery');
  if (!exists(path.join(out, report.artifacts.json))) throw new Error('self-test expected json artifact');
  if (!readText(path.join(out, 'orientations.jsonl')).includes(report.nodeId)) throw new Error('self-test expected orientation index');
  console.log('home_center_engineering_orient self-test: OK');
}
function main() {
  const args = parseArgs(process.argv);
  if (args.help) { console.log(usage()); return; }
  if (args.selfTest) { selfTest(); return; }
  const report = orient(args);
  if (args.stdout) console.log(JSON.stringify(report, null, 2));
  else console.log(`Orientation written: ${report.artifacts.markdown}`);
}
main();
