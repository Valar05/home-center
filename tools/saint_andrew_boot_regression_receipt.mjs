#!/usr/bin/env node
import crypto from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {buildBootCapsule} from './fortress_online_v2_boot.mjs';

const SCRIPT_DIR=path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT=path.resolve(SCRIPT_DIR,'..');
const TEST_FILE=path.join(SCRIPT_DIR,'fortress_online_v2_boot.test.mjs');
const expectedHead=String(process.argv[2]||'').trim();
const sha256=text=>crypto.createHash('sha256').update(String(text||'')).digest('hex');
const fail=(code,message,extra={})=>{
  process.stdout.write(JSON.stringify({kind:'red-build.saint-andrew-boot-regression.v1',ok:false,message,...extra})+'\n');
  process.exit(code);
};

if(!/^[0-9a-f]{40}$/i.test(expectedHead)) fail(2,'EXPECTED_HEAD_REQUIRED',{usage:'node tools/saint_andrew_boot_regression_receipt.mjs <40-char-head-sha>'});

const git=spawnSync('git',['-C',REPO_ROOT,'rev-parse','HEAD'],{encoding:'utf8'});
if(git.status!==0) fail(3,'GIT_HEAD_UNAVAILABLE',{gitExitCode:git.status,gitStderr:String(git.stderr||'').trim()});
const actualHead=String(git.stdout||'').trim();
if(actualHead.toLowerCase()!==expectedHead.toLowerCase()) fail(4,'EXACT_HEAD_MISMATCH',{expectedHead,actualHead});

const test=spawnSync(process.execPath,['--test',TEST_FILE],{cwd:REPO_ROOT,encoding:'utf8'});
const testStdout=String(test.stdout||'');
const testStderr=String(test.stderr||'');
if(test.status!==0) fail(5,'BOOT_REGRESSION_FAILED',{
  expectedHead,actualHead,testExitCode:test.status,
  testStdoutSha256:sha256(testStdout),testStderrSha256:sha256(testStderr),
  testStdoutTail:testStdout.slice(-4000),testStderrTail:testStderr.slice(-4000)
});

const capsule=buildBootCapsule({configOptions:{userPath:null,envPath:null}});
const saintAndrew=capsule.loadedSkills.filter(x=>x.id==='saint-andrew-default');
if(saintAndrew.length!==1) fail(6,'SAINT_ANDREW_CARDINALITY_INVALID',{expectedHead,actualHead,count:saintAndrew.length});
const organ=saintAndrew[0];
if(organ.source!=='bootstrap-contract'||organ.required!==true||capsule.saintAndrewDefault?.loaded!==true) {
  fail(7,'SAINT_ANDREW_BOOTSTRAP_INVARIANT_FAILED',{expectedHead,actualHead,source:organ.source,required:organ.required,loaded:capsule.saintAndrewDefault?.loaded});
}
if(!capsule.bootPrompt.includes('FORTRESS SKILL saint-andrew-default | bootstrap-contract')) {
  fail(8,'SAINT_ANDREW_BOOT_PROMPT_MARKER_MISSING',{expectedHead,actualHead});
}

process.stdout.write(JSON.stringify({
  kind:'red-build.saint-andrew-boot-regression.v1',
  ok:true,
  expectedHead,
  actualHead,
  testExitCode:test.status,
  testStdoutSha256:sha256(testStdout),
  testStderrSha256:sha256(testStderr),
  bootPromptSha256:capsule.bootPromptSha256,
  saintAndrewDefault:{
    source:organ.source,
    required:organ.required,
    sha256:organ.sha256,
    loaded:capsule.saintAndrewDefault.loaded
  }
})+'\n');
