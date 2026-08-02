#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const [project,region,commit,serviceUrl]=process.argv.slice(2);
if(!project||!region||!/^[a-f0-9]{40}$/.test(commit)||!serviceUrl) throw new Error('usage: publish_foundry_retirement_record.mjs project region commit serviceUrl');
const record={contractVersion:'home-center.foundry-retirement.v1',decision:'Foundry is retired and cannot author or modify geometry.',reason:'The egg-like D78461 and z-fighting failures demonstrated that receipts and a distant custom mesh contract did not provide close, truthful authoring control.',historicalArtifacts:'preserved read-only with original status and hashes',replacement:{architecture:'Home Center persistent revision control with Blender as geometry and animation kernel',operations:['blender.workspace.create','blender.workspace.inspect','blender.workspace.history','blender.workspace.mutate','blender.workspace.restore','blender.workspace.export','blender.workspace.status'],deprecatedCompatibilityOperations:['blender.workspace.render'],serviceUrl},deployedCommit:commit,deployedFrom:'refs/heads/main',deployedAt:new Date().toISOString(),region,project};
const tmp=path.join(os.tmpdir(),`foundry-retirement-${commit}.json`);fs.writeFileSync(tmp,JSON.stringify(record,null,2)+'\n');
const target=`gs://home-center-generated/retirement/foundry/${commit}.json`;let r=spawnSync('gcloud',['storage','cp',tmp,target],{stdio:'inherit'});if(r.status)process.exit(r.status);r=spawnSync('gcloud',['storage','cat',target],{encoding:'utf8'});if(r.status)process.exit(r.status);const read=JSON.parse(r.stdout);if(read.deployedCommit!==commit)throw new Error('retirement record readback mismatch');console.log(JSON.stringify({ok:true,target,record:read}));fs.rmSync(tmp,{force:true});
