import assert from 'node:assert/strict';
import {generateKeyPairSync} from 'node:crypto';
import {chmod, mkdtemp, readFile, readdir, rm, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const bootstrap = path.join(root, 'tools/github_admin_gh_bootstrap.sh');
const setup = path.join(root, 'tools/setup_github_admin_secrets.sh');
const bootstrapSource = await readFile(bootstrap, 'utf8');
const setupSource = await readFile(setup, 'utf8');

assert.doesNotMatch(bootstrapSource, /generated\/github_admin|github-app\.private-key\.pem|pem="\$\(/);
assert.match(bootstrapSource, /set_secret_from_file GITHUB_APP_PRIVATE_KEY/);
assert.match(bootstrapSource, /PRIVATE_STATE_DIR/);
assert.match(bootstrapSource, /trap cleanup EXIT HUP INT TERM/);
assert.match(setupSource, /GITHUB_APP_PRIVATE_KEY is intentionally not accepted through the environment/);

const directory = await mkdtemp(path.join(tmpdir(), 'home-center-key-custody-'));
try {
  const privateDir = path.join(directory, 'private');
  const binDir = path.join(directory, 'bin');
  const keyPath = path.join(directory, 'new-key.pem');
  const capturePath = path.join(directory, 'secret-version.pem');
  await import('node:fs/promises').then(({mkdir}) => Promise.all([mkdir(privateDir), mkdir(binDir)]));
  const {privateKey} = generateKeyPairSync('rsa', {modulusLength: 2048, privateKeyEncoding: {type: 'pkcs8', format: 'pem'}, publicKeyEncoding: {type: 'spki', format: 'pem'}});
  await writeFile(keyPath, privateKey, {mode: 0o600});
  const fakeGcloud = `#!/usr/bin/env node\nconst fs=require('node:fs');\nconst args=process.argv.slice(2);\nif(args[0]==='secrets'&&args[1]==='describe') process.exit(0);\nif(args[0]==='secrets'&&args[1]==='versions'&&args[2]==='add'){const file=args.find(x=>x.startsWith('--data-file='));fs.copyFileSync(file.slice(12),process.env.CAPTURE_PATH);process.exit(0);}\nprocess.exit(1);\n`;
  await writeFile(path.join(binDir, 'gcloud'), fakeGcloud, {mode: 0o700});
  await chmod(path.join(binDir, 'gcloud'), 0o700);
  const run = spawnSync('sh', [bootstrap, 'ingest-key', keyPath], {
    cwd: root,
    encoding: 'utf8',
    env: {...process.env, PATH: binDir + ':' + process.env.PATH, HOME_CENTER_GITHUB_ADMIN_PRIVATE_DIR: privateDir, CAPTURE_PATH: capturePath, FIREBASE_PROJECT: 'fixture-project'},
  });
  assert.equal(run.status, 0, run.stderr);
  assert.doesNotMatch(run.stdout + run.stderr, /BEGIN PRIVATE KEY/);
  assert.equal(await readFile(capturePath, 'utf8'), privateKey);
  assert.deepEqual(await readdir(privateDir), []);
  assert.equal(await import('node:fs/promises').then(({access}) => access(path.join(root, 'generated/github_admin/github-app.private-key.pem')).then(() => true, () => false)), false);
} finally {
  await rm(directory, {recursive: true, force: true});
}

console.log(JSON.stringify({ok: true, secretManagerFileIngress: true, repositoryPemWritten: false, temporaryKeyCleaned: true, privateKeyEnvironmentRejected: true}, null, 2));
