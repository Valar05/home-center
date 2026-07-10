#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import childProcess from 'node:child_process';

function parseArgs(argv) {
  const args = {repo: process.cwd(), out: 'generated/engineering_memory', workflow: 'manual-artifact-registration', type: 'artifact', generator: 'unknown', notes: '', selfTest: false, stdout: false};
  for (let i = 2; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === '--self-test') args.selfTest = true;
    else if (item === '--stdout') args.stdout = true;
    else if (item === '--artifact') args.artifact = argv[++i];
    else if (item === '--repo') args.repo = argv[++i];
    else if (item === '--out') args.out = argv[++i];
    else if (item === '--workflow') args.workflow = argv[++i];
    else if (item === '--type') args.type = argv[++i];
    else if (item === '--generator') args.generator = argv[++i];
    else if (item === '--notes') args.notes = argv[++i];
    else if (item === '--help' || item === '-h') args.help = true;
    else throw new Error(`Unknown argument: ${item}`);
  }
  return args;
}
function usage() { return 'Usage: node tools/home_center_artifact_register.mjs --artifact <path> --repo <path> --workflow <id> --type <kind>\n'; }
function nowIso() { return new Date().toISOString(); }
function sha256Buffer(buffer) { return crypto.createHash('sha256').update(buffer).digest('hex'); }
function shortHash(value) { return crypto.createHash('sha256').update(String(value)).digest('hex').slice(0, 16); }
function nodeId(type, identity) { return `${type}:${shortHash(identity)}`; }
function ensureDir(dir) { fs.mkdirSync(dir, {recursive: true}); }
function appendJsonl(file, record) { ensureDir(path.dirname(file)); fs.appendFileSync(file, JSON.stringify(record) + '\n'); }
function readText(file) { try { return fs.readFileSync(file, 'utf8'); } catch { return ''; } }
function run(cmd, cwd) {
  try { return {ok: true, stdout: childProcess.execFileSync(cmd[0], cmd.slice(1), {cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']}).trim()}; }
  catch (err) { return {ok: false, stdout: '', error: String((err.stderr && err.stderr.toString()) || err.message || err)}; }
}
function gitInfo(repo) {
  const inside = run(['git', 'rev-parse', '--is-inside-work-tree'], repo);
  if (!inside.ok || inside.stdout !== 'true') return {isGit: false};
  const branch = run(['git', 'branch', '--show-current'], repo).stdout || '';
  const commit = run(['git', 'rev-parse', 'HEAD'], repo).stdout || '';
  const root = run(['git', 'rev-parse', '--show-toplevel'], repo).stdout || repo;
  const statusShort = run(['git', 'status', '--short'], repo).stdout.split('\n').filter(Boolean);
  return {isGit: true, root, branch, commit, dirty: statusShort.length > 0, statusShort};
}
function registerArtifact(options) {
  if (!options.artifact) throw new Error('--artifact is required');
  const artifactPath = path.resolve(options.artifact);
  if (!fs.existsSync(artifactPath) || !fs.statSync(artifactPath).isFile()) throw new Error(`Artifact file not found: ${artifactPath}`);
  const repo = path.resolve(options.repo || process.cwd());
  if (!fs.existsSync(repo) || !fs.statSync(repo).isDirectory()) throw new Error(`Repo path is not a directory: ${repo}`);
  const out = path.resolve(options.out || 'generated/engineering_memory');
  const generatedAt = nowIso();
  const bytes = fs.readFileSync(artifactPath);
  const stat = fs.statSync(artifactPath);
  const hash = sha256Buffer(bytes);
  const git = gitInfo(repo);
  const repositoryNodeId = nodeId('engineering.repository', `${git.root || repo}|${git.commit || 'no-commit'}`);
  const artifactNodeId = nodeId('engineering.artifact', `${artifactPath}|${hash}`);
  const workflowNodeId = nodeId('engineering.workflow_run', `${options.workflow}|${artifactNodeId}`);
  const record = {
    type: 'engineering.artifact', nodeId: artifactNodeId, artifactType: options.type || 'artifact', path: artifactPath,
    relativePath: path.relative(repo, artifactPath).replace(/\\/g, '/'), sizeBytes: stat.size, sha256: hash,
    generatedAt, generator: options.generator || 'unknown', workflowId: options.workflow || 'manual-artifact-registration', notes: options.notes || '',
    repository: {path: repo, nodeId: repositoryNodeId, branch: git.branch || '', commit: git.commit || '', dirty: !!git.dirty},
  };
  appendJsonl(path.join(out, 'artifacts.jsonl'), record);
  appendJsonl(path.join(out, 'workflow_runs.jsonl'), {type: 'engineering.workflow_run', nodeId: workflowNodeId, workflowId: record.workflowId, status: 'completed', generatedAt, repositoryNodeId, outputNodeId: artifactNodeId});
  appendJsonl(path.join(out, 'edges.jsonl'), {type: 'engineering.edge', from: artifactNodeId, to: repositoryNodeId, relation: 'generated_from', generatedAt});
  appendJsonl(path.join(out, 'edges.jsonl'), {type: 'engineering.edge', from: workflowNodeId, to: artifactNodeId, relation: 'generated', generatedAt});
  return record;
}
function selfTest() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'hc-artifact-register-'));
  const repo = path.join(tmp, 'repo');
  fs.mkdirSync(repo);
  fs.writeFileSync(path.join(repo, 'README.md'), '# Fixture\n');
  childProcess.execFileSync('git', ['init'], {cwd: repo, stdio: 'ignore'});
  childProcess.execFileSync('git', ['config', 'user.email', 'fixture@example.com'], {cwd: repo, stdio: 'ignore'});
  childProcess.execFileSync('git', ['config', 'user.name', 'Fixture'], {cwd: repo, stdio: 'ignore'});
  childProcess.execFileSync('git', ['add', '.'], {cwd: repo, stdio: 'ignore'});
  childProcess.execFileSync('git', ['commit', '-m', 'fixture'], {cwd: repo, stdio: 'ignore'});
  const artifact = path.join(repo, 'report.txt');
  fs.writeFileSync(artifact, 'evidence\n');
  const out = path.join(tmp, 'memory');
  const record = registerArtifact({artifact, repo, out, workflow: 'self-test', type: 'report', generator: 'fixture'});
  if (!record.sha256 || record.sizeBytes <= 0) throw new Error('self-test expected hash and size');
  if (!readText(path.join(out, 'artifacts.jsonl')).includes(record.nodeId)) throw new Error('self-test expected artifact index');
  if (!readText(path.join(out, 'edges.jsonl')).includes('generated_from')) throw new Error('self-test expected graph edge');
  console.log('home_center_artifact_register self-test: OK');
}
function main() {
  const args = parseArgs(process.argv);
  if (args.help) { console.log(usage()); return; }
  if (args.selfTest) { selfTest(); return; }
  const record = registerArtifact(args);
  if (args.stdout) console.log(JSON.stringify(record, null, 2));
  else console.log(`Artifact registered: ${record.nodeId}`);
}
main();
