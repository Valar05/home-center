#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const capability=require('../functions/blender_workspace_capability.js');
const expected=['blender.workspace.create','blender.workspace.export','blender.workspace.history','blender.workspace.inspect','blender.workspace.mutate','blender.workspace.render','blender.workspace.restore','blender.workspace.status'];
assert.deepEqual(Object.keys(capability.operationEntries()).sort(),expected);
assert.equal(capability.RECIPE_VERSION,'home-center.blender-workspace-recipe.v1');
for(const [name,entry] of Object.entries(capability.operationEntries())){
 assert.match(name,/^blender\.workspace\./);assert.ok(entry.summary);if(entry.write)assert.equal(entry.requiresRequestId,true);
}
const retired=capability.retiredFoundryError('foundry.asset.run');assert.equal(retired.code,'CAPABILITY_RETIRED');assert.equal(retired.status,410);assert.equal(retired.details.dispatched,false);assert.ok(retired.details.replacement.includes('blender.workspace.mutate'));
const control=fs.readFileSync(new URL('../functions/blender_workspace_capability.js',import.meta.url),'utf8');
for(const marker of ['baseRevisionId','currentRevisionId','pendingOperationId','revision_conflict','blenderWorkspaceRevisions','getSignedUrl','CloudTasksClient']) assert.ok(control.toLowerCase().includes(marker.toLowerCase()),'control plane missing '+marker);
assert.match(control,/recipe\.operations/);assert.match(control,/recipeJson: JSON\.stringify/);assert.doesNotMatch(control,/eval\(|new Function|child_process/);
const executor=fs.readFileSync(new URL('../blender_workspace/executor.py',import.meta.url),'utf8');
for(const marker of ['import bpy','import bmesh','mesh.vertex_move','mesh.loop_cut','mesh.inset','mesh.extrude','mesh.bridge','mesh.bevel','mesh.boolean','constraint.add','animation.keyframes','uv.smart_project','export_scene.gltf','save_as_mainfile','Review_World']) assert.ok(executor.includes(marker),'executor missing '+marker);
assert.ok(executor.includes("'hc_vertex_id'"));assert.ok(executor.includes("'hc_face_id'"));assert.ok(executor.includes("'hc_edge_id'"));
const service=fs.readFileSync(new URL('../blender_workspace/service.py',import.meta.url),'utf8');
for(const marker of ['record_recipe','json.loads(raw)','if_generation_match=0','source revision is not completed','workspace mutation lease lost','revisionIds','humanAcceptance','unreviewed','Blender completed without required outputs','animation preview was not produced']) assert.ok(service.includes(marker),'service missing '+marker);
const docker=fs.readFileSync(new URL('../blender_workspace/Dockerfile',import.meta.url),'utf8');assert.match(docker,/BLENDER_VERSION=4\.5\.12/);assert.match(docker,/95e3a2dfedba3bd32ca54fc355eac6b15a11986954ccb02815a07535d0120a25/);
assert.match(service,/--disable-autoexec/);assert.doesNotMatch(executor,/requests|urllib|socket|subprocess/);
console.log(JSON.stringify({ok:true,operations:expected,typedGrammar:true,immutableRevisions:true,staleWriteGuard:true,userPython:false,blender:'4.5.12'}));
