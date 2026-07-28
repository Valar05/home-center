#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const artifactTransport = fs.readFileSync(new URL('../functions/artifact_transport.js', import.meta.url), 'utf8');
const commandCenter = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
const homeCenter = fs.readFileSync(new URL('../functions/home_center_mcp.js', import.meta.url), 'utf8');
const renderService = fs.readFileSync(new URL('../cloud-render/src/render_bundle.mjs', import.meta.url), 'utf8');
const server = fs.readFileSync(new URL('../cloud-render/src/server.mjs', import.meta.url), 'utf8');
const dockerfile = fs.readFileSync(new URL('../cloud-render/Dockerfile', import.meta.url), 'utf8');
const functionsIndex = fs.readFileSync(new URL('../functions/index.js', import.meta.url), 'utf8');

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
assert(homeCenter.includes('materializeHomeCenterRenderSources'));
assert(homeCenter.includes('stageHomeCenterGitHubRenderInput'));
assert(homeCenter.includes("githubToken = () => ''"));
assert(homeCenter.includes('googleClientSecret, githubToken, extra'));
assert(homeCenter.includes('github_input_download_auth_failed'));
assert(homeCenter.includes('glbSource.provider=github'));
assert(homeCenter.includes("' source is required for render.blender_glb: provide '"));
assert(homeCenter.includes("sourceKind: 'github-cache'"));
assert(homeCenter.includes('readCachedGitHubRenderInput'));
assert(homeCenter.includes('writeCachedGitHubRenderInput'));
assert(homeCenter.includes('GitHubSourceCache'));
assert(homeCenter.includes('verifiedRenderGifMcpContent'), 'Home Center stable operation must verify private GCS GIF readback');
assert(homeCenter.includes('uploadVerifiedArtifact'), 'Home Center stable operation must attach audio-style resource_link via the verified upload helper');
assert(homeCenter.includes("mimeType: 'image/gif'"), 'Home Center stable operation must attach image/gif resource_link media');
assert(!homeCenter.includes("type: 'image', data: buffer.toString('"), 'Home Center render GIF delivery must not use MCP ImageContent');
assert(!homeCenter.includes("type: 'resource',\n    resource:"), 'Home Center render GIF delivery must not use embedded resource bytes');
assert(homeCenter.includes('HOME_CENTER_RENDER_INLINE_GIF_MAX_BYTES'), 'Home Center stable operation must enforce inline GIF ceiling');
assert(homeCenter.includes('renderReceiptWithoutInlinePayload'), 'Home Center receipt must avoid Base64 media pollution');
assert(!homeCenter.includes('getSignedUrl'), 'Home Center render delivery must not use signed URLs');
assert(!homeCenter.includes('https://storage.googleapis.com'), 'Home Center render delivery must not use public GCS URLs');
assert(commandCenter.includes('renderRequiredBundleKindsForOptions'), 'Command Center must derive lightweight bundle requirements through one helper');
assert(commandCenter.includes('const effectiveOptions'), 'Queued worker must derive completion from effective render options');
assert(commandCenter.includes("status: completed ? 'completed' : 'failed'"), 'Queued worker must persist terminal completion state');
assert(commandCenter.includes('render_provider_outcome_ambiguous'), 'Ambiguous renderer outcomes must be quarantined');
assert(commandCenter.includes("operation: 'render.status'"), 'Accepted receipts must expose bounded status lookup');
assert(commandCenter.includes("resolution !== 'retry_safe'"), 'Ambiguous retries must require explicit reconciliation');
assert(functionsIndex.includes('onTaskDispatched'), 'Blender execution must run through a durable task queue');
assert(functionsIndex.includes('maxAttempts: 1'), 'Renderer task delivery must not automatically retry ambiguous mutations');
assert(homeCenter.includes('githubStreamAndValidateMs'));
assert(homeCenter.includes('cacheLookupMs'));
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
assert(renderService.includes('Network and process escape are disabled inside Command Center Blender scripts'));
assert(renderService.includes("--python-exit-code', '88"));
assert(renderService.includes("_np.bool = bool"));
assert(renderService.includes("LIBGL_ALWAYS_SOFTWARE: '1'"));
assert(dockerfile.includes('libegl1'));
assert(dockerfile.includes('libgl1-mesa-dri'));
const deployScript = fs.readFileSync(new URL('../tools/deploy_command_center_blender_render.sh', import.meta.url), 'utf8');
assert(deployScript.includes('validate-resolved command-center-blender-render'));
assert(!deployScript.includes('COMMAND_CENTER_RENDER_MIN_INSTANCES'));
assert(deployScript.includes('--min-instances "$WORKER_MIN_INSTANCES"'));
assert(deployScript.includes('--cpu-boost'));
assert(deployScript.includes('RENDER_TIMEOUT_MS=${COMMAND_CENTER_RENDER_TIMEOUT_MS:-1200000}'), 'Renderer deploy must preserve the measured 20-minute subprocess ceiling');
assert(renderService.includes('blenderExitCode'));
assert(renderService.includes('loopingGifRef'));
assert(renderService.includes('gifPlaybackContractRef'));
assert(renderService.includes('makeLoopingGif'));
assert(renderService.includes('frameDurationsMs'));
assert(renderService.includes('buildGifPlaybackContract'));
assert(renderService.includes('gifFrames'));
assert(renderService.includes('gifTimingMs'));
assert(renderService.includes("'-dispose', 'Background'"));
assert(renderService.includes('gif-playback-contract.json'));
assert(renderService.includes('GIF assembly requires compatible PNG dimensions'));
assert(renderService.includes('artifactHashes'));
assert(renderService.includes('timings'));
assert(renderService.includes('timedPhase'));
assert(renderService.includes('renderBundleOptions'));
assert(renderService.includes('includeBlend'));
assert(renderService.includes('includeDiagnostics'));
assert(commandCenter.includes('timings'));
assert(commandCenter.includes('renderOptions'));
assert(commandCenter.includes('includeBlend'));
assert(commandCenter.includes('return normalizeRendererSettings(value)'));
assert(artifactTransport.includes('samples: Math.max(1, Math.min(Number(src.samples || src.renderSamples || 64) || 64, 128))'));
assert(artifactTransport.includes('gifFrames'));
assert(renderService.includes('PUBLISH_CONCURRENCY'));
assert(renderService.includes('Promise.all(['));
assert(commandCenter.includes("kind) => resolved.includeDiagnostics || kind !== 'diagnostic_view_renders'"));
assert(renderService.includes("if (ext === '.gif') return 'image/gif';"));
assert(commandCenter.includes('loopingGifRef'));
assert(commandCenter.includes('artifactHashes'));
assert(renderService.includes('originalScriptRef'));
assert(!renderService.includes('fallback default renderer'));
assert(!renderService.includes('DEFAULT_SCRIPT'));
assert(renderService.includes('cachedManifest'));
assert(renderService.includes('cacheLookupMs'));
assert(renderService.includes("timedPhase(timings, 'uploadArtifacts'"));
assert(renderService.includes("timedSyncPhase(timings, 'blenderExecution'"));
assert(renderService.includes('totalMs'));
assert(renderService.includes('requiredBundleKindsFor'));
assert(renderService.includes("options.includeBlend) required.push('three_d_artifact')"));
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
