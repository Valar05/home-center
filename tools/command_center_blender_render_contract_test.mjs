#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const commandCenter = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
const homeCenter = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
const renderService = fs.readFileSync(new URL('../cloud-render/src/render_bundle.mjs', import.meta.url), 'utf8');
const server = fs.readFileSync(new URL('../cloud-render/src/server.mjs', import.meta.url), 'utf8');
const dockerfile = fs.readFileSync(new URL('../cloud-render/Dockerfile', import.meta.url), 'utf8');

assert(commandCenter.includes("server.registerTool('command_center.render.blender_glb'"));
assert(homeCenter.includes("'render.blender_glb'"));
assert(homeCenter.includes("server.registerTool('render_blender_glb'"));
assert(homeCenter.includes("nested dispatcher args cannot activate host file upload slots"));
assert(homeCenter.includes("'render.blender_glb': {summary:"));
assert(homeCenter.includes("commandCenterRenderBlenderGlb(admin, extra, operationArgs)"));
assert(homeCenter.includes("render_blender_glb accepts only top-level glbFile and scriptFile uploads"));
assert(commandCenter.includes("COMMAND_CENTER_RENDER_BUCKET"));
assert(server.includes("req.method === 'POST' && req.url === '/render/glb'"));
assert(dockerfile.includes('blender'));
assert(renderService.includes('CACHE_BUCKET'));
assert(renderService.includes('googleOAuthAccessToken'));
assert(renderService.includes('downloadDrive'));
assert(renderService.includes('bucketInputs'));
assert(renderService.includes('render_input_gcs_read_auth_failed'));
assert(renderService.includes('drive_input_download_auth_failed'));
assert(commandCenter.includes('cleanRenderStagedInputs'));
assert(commandCenter.includes('render_service_invocation_auth_failed'));
assert(homeCenter.includes('drive_input_download_auth_failed'));
assert(homeCenter.includes('materializeHomeCenterRenderDriveRefs'));
assert(commandCenter.includes('glbFile: z.file().optional()'));
assert(commandCenter.includes('scriptFile: z.file().optional()'));
assert(homeCenter.includes('glbFile: z.file().describe('));
assert(homeCenter.includes('scriptFile: z.file().describe('));
assert(!homeCenter.includes("glbRef: z.string().optional().describe('Existing drive://"));
assert(!homeCenter.includes("scriptText: z.string().optional().describe('Inline Blender Python script alternative"));
assert(commandCenter.includes('Exactly one GLB source is required'));
assert(commandCenter.includes('Exactly one Blender script source is required'));
assert(commandCenter.includes('stageRenderUpload'));
assert(commandCenter.includes('validateGlbBytes'));
assert(commandCenter.includes('validateScriptBytes'));
assert(homeCenter.includes("topLevelFileTool: 'render_blender_glb'"));
assert(homeCenter.includes('nested command_center_operation args cannot activate host file upload slots'));
assert(renderService.includes('decodeUploadObject'));
assert(renderService.includes('Network and process escape are disabled inside Command Center Blender render scripts'));
assert(renderService.includes("--python-exit-code', '88"));
assert(renderService.includes("_np.bool = bool"));
assert(renderService.includes("LIBGL_ALWAYS_SOFTWARE: '1'"));
assert(dockerfile.includes('libegl1'));
assert(dockerfile.includes('libgl1-mesa-dri'));
assert(renderService.includes('blenderExitCode'));
assert(renderService.includes('originalScriptRef'));
assert(!renderService.includes('fallback default renderer'));
assert(!renderService.includes('DEFAULT_SCRIPT'));
assert(renderService.includes('cachedManifest'));
assert(renderService.includes('framesAreInsufficient: true'));
for (const required of [
  'rendered_frames',
  'contact_sheet',
  'three_d_artifact',
  'native_pose_animation_data',
  'script_input_hashes',
  'blender_version_settings',
  'stdout_stderr',
  'fixed_camera_renders',
  'diagnostic_view_renders',
  'validation_manifest',
  'original_script',
]) {
  assert(commandCenter.includes(required), `Command Center missing ${required}`);
  assert(renderService.includes(required), `render service missing ${required}`);
}
for (const artifact of ['modifiedBlendRef', 'animatedGlbRef', 'nativeDataRefs', 'originalScriptRef', 'stdoutRef', 'stderrRef', 'fixedCameraRenderRefs', 'diagnosticRenderRefs', 'validationManifestRef']) {
  assert(commandCenter.includes(artifact), `Command Center result missing ${artifact}`);
}
assert(!renderService.includes('@openai/codex'));
assert(!renderService.includes('codex exec'));
assert(!renderService.includes('jobs.create'));
assert(!renderService.includes('agents.create_activation'));
console.log('Command Center Blender render contract test: OK');
