const {createHash} = require('node:crypto');

const DEFAULT_LOCATION = process.env.MOTION_DOCS_WORKFLOW_LOCATION || 'us-central1';
const DEFAULT_WORKFLOW = process.env.MOTION_DOCS_WORKFLOW_NAME || 'motion-to-docs';
const DEFAULT_FOLDER_NAME = process.env.MOTION_DOCS_FOLDER_NAME || 'Motion Scans';
const WORKFLOW_SERVICE_ACCOUNT = process.env.MOTION_DOCS_WORKFLOW_SERVICE_ACCOUNT || '';

function text(value, max = 500) {
  const clean = typeof value === 'string' ? value.trim() : '';
  return clean.length > max ? clean.slice(0, max) : clean;
}

function requestId(value) {
  const clean = text(value, 180);
  if (!/^[A-Za-z0-9_.:-]{8,180}$/.test(clean)) throw Object.assign(new Error('requestId is required and must be a stable identifier.'), {status: 400, code: 'motion_docs_request_id_invalid'});
  return clean;
}

function sourceDescriptor(file) {
  const value = Array.isArray(file) ? file[0] : file;
  if (!value || typeof value !== 'object') throw Object.assign(new Error('A top-level Work Mode video file is required.'), {status: 400, code: 'motion_docs_file_required'});
  const sourceUrl = text(value.download_url || value.file_url || value.url || value.image_url, 4000);
  if (!sourceUrl) throw Object.assign(new Error('The uploaded file is missing its temporary download URL.'), {status: 400, code: 'motion_docs_file_url_missing'});
  return {sourceUrl, fileId: text(value.file_id || value.id, 240), name: text(value.file_name || value.filename || value.name, 500), mimeType: text(value.mime_type || value.mimeType || value.content_type, 160)};
}

function assertVideo(uploaded, descriptor) {
  const mimeType = text(uploaded.type || descriptor.mimeType, 160).toLowerCase();
  const name = text(uploaded.name || descriptor.name, 500).toLowerCase();
  if (!mimeType.startsWith('video/') && !/\.(mp4|mov|m4v|webm|avi|mkv)$/i.test(name)) {
    throw Object.assign(new Error('motion_to_docs_scan accepts a video upload.'), {status: 415, code: 'motion_docs_video_required'});
  }
}

function executionIdFor(value) {
  return 'scan-' + createHash('sha256').update(value).digest('hex').slice(0, 24);
}

async function findOrCreateFolder({google, auth, outputFolderId = ''}) {
  const drive = google.drive({version: 'v3', auth});
  if (outputFolderId) {
    const response = await drive.files.get({fileId: outputFolderId, fields: 'id,name,mimeType,webViewLink,parents', supportsAllDrives: true});
    if (response.data.mimeType !== 'application/vnd.google-apps.folder') throw Object.assign(new Error('outputFolderId is not a Google Drive folder.'), {status: 400, code: 'motion_docs_folder_invalid'});
    return response.data;
  }
  const found = await drive.files.list({
    q: "trashed=false and mimeType='application/vnd.google-apps.folder' and appProperties has { key='homeCenterMotionDocs' and value='root-v1' }",
    pageSize: 2,
    fields: 'files(id,name,mimeType,webViewLink,parents)',
    spaces: 'drive',
  });
  const matches = found.data.files || [];
  if (matches.length > 1) throw Object.assign(new Error('Multiple Motion Scans root folders exist; automatic routing is quarantined.'), {status: 409, code: 'motion_docs_folder_conflict'});
  if (matches.length === 1) return matches[0];
  const created = await drive.files.create({
    requestBody: {name: DEFAULT_FOLDER_NAME, mimeType: 'application/vnd.google-apps.folder', appProperties: {homeCenterMotionDocs: 'root-v1'}},
    fields: 'id,name,mimeType,webViewLink,parents',
  });
  return created.data;
}

async function ensureWorkflowFolderAccess({google, auth, folderId, workflowServiceAccount = WORKFLOW_SERVICE_ACCOUNT}) {
  if (!workflowServiceAccount) {
    const projectId = process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT || '';
    workflowServiceAccount = projectId ? `motion-docs-workflow@${projectId}.iam.gserviceaccount.com` : '';
  }
  if (!workflowServiceAccount) throw Object.assign(new Error('MOTION_DOCS_WORKFLOW_SERVICE_ACCOUNT is not configured.'), {status: 503, code: 'motion_docs_workflow_identity_missing'});
  const drive = google.drive({version: 'v3', auth});
  const listed = await drive.permissions.list({fileId: folderId, fields: 'permissions(id,emailAddress,role,type)', supportsAllDrives: true});
  const existing = (listed.data.permissions || []).find((permission) => text(permission.emailAddress, 320).toLowerCase() === workflowServiceAccount.toLowerCase());
  if (existing && ['writer', 'fileOrganizer', 'organizer', 'owner'].includes(existing.role)) return {permission: existing, reused: true};
  const created = await drive.permissions.create({
    fileId: folderId,
    requestBody: {type: 'user', role: 'writer', emailAddress: workflowServiceAccount},
    sendNotificationEmail: false,
    supportsAllDrives: true,
    fields: 'id,emailAddress,role,type',
  });
  return {permission: created.data, reused: false};
}

async function defaultWorkflowClient(google) {
  const auth = new google.auth.GoogleAuth({scopes: ['https://www.googleapis.com/auth/cloud-platform']});
  return auth.getClient();
}

async function runWorkflow({google, workflowClient = null, projectId = process.env.GOOGLE_CLOUD_PROJECT || process.env.GCLOUD_PROJECT || '', location = DEFAULT_LOCATION, workflow = DEFAULT_WORKFLOW, idempotencyKey, argument, sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))}) {
  if (!projectId) throw Object.assign(new Error('Google Cloud project is not configured.'), {status: 503, code: 'motion_docs_project_missing'});
  const client = workflowClient || await defaultWorkflowClient(google);
  const parent = `projects/${projectId}/locations/${location}/workflows/${workflow}`;
  const executionId = executionIdFor(idempotencyKey);
  const createUrl = `https://workflowexecutions.googleapis.com/v1/${parent}/executions`;
  let execution;
  try {
    const created = await client.request({url: createUrl, method: 'POST', params: {executionId}, data: {argument: JSON.stringify(argument)}});
    execution = created.data;
  } catch (error) {
    if (Number(error && error.response && error.response.status) !== 409) throw error;
    execution = (await client.request({url: `${createUrl}/${executionId}`, method: 'GET'})).data;
  }
  const deadline = Date.now() + 14 * 60 * 1000;
  let delay = 2000;
  while (execution.state === 'ACTIVE' && Date.now() < deadline) {
    await sleep(delay);
    execution = (await client.request({url: `https://workflowexecutions.googleapis.com/v1/${execution.name}`, method: 'GET'})).data;
    delay = Math.min(delay * 2, 30000);
  }
  if (execution.state === 'ACTIVE') throw Object.assign(new Error('Motion-to-Docs workflow is still running; reuse the same requestId to resume.'), {status: 504, code: 'motion_docs_workflow_active', executionName: execution.name});
  if (execution.state !== 'SUCCEEDED') throw Object.assign(new Error(`Motion-to-Docs workflow ended in ${execution.state}: ${text(execution.error && execution.error.payload, 1000)}`), {status: 502, code: 'motion_docs_workflow_failed', executionName: execution.name});
  let result;
  try {
    result = JSON.parse(execution.result);
  } catch (_) {
    throw Object.assign(new Error('Motion-to-Docs workflow returned invalid JSON.'), {status: 502, code: 'motion_docs_workflow_result_invalid'});
  }
  return {executionName: execution.name, result};
}

async function runMotionToDocsScan({google, admin, auth, user, args = {}, uploaded, workflowClient = null, sleep}) {
  const stableId = requestId(args.requestId);
  const descriptor = sourceDescriptor(args.file);
  assertVideo(uploaded, descriptor);
  const inputSha256 = text(uploaded.sha256, 64).toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(inputSha256)) throw Object.assign(new Error('Host-file materialization did not produce a SHA-256 receipt.'), {status: 502, code: 'motion_docs_input_receipt_invalid'});
  const receiptRef = admin.firestore().collection('motionToDocsScans').doc(stableId);
  const prior = await receiptRef.get();
  if (prior.exists) {
    const data = prior.data() || {};
    if (data.inputSha256 !== inputSha256) throw Object.assign(new Error('requestId was reused with different video bytes.'), {status: 409, code: 'motion_docs_idempotency_conflict'});
    if (data.status === 'success' && data.result) return {...data.result, idempotent: true};
  }
  const mode = args.mode === 'exact' ? 'exact' : 'perceptual';
  const threshold = mode === 'exact' ? 0 : Math.max(0, Math.min(64, Number.isInteger(args.distanceThreshold) ? args.distanceThreshold : 6));
  const folder = await findOrCreateFolder({google, auth, outputFolderId: text(args.outputFolderId, 220)});
  const access = await ensureWorkflowFolderAccess({google, auth, folderId: folder.id});
  await receiptRef.set({requestId: stableId, owner: text(user && user.email, 320).toLowerCase(), inputSha256, inputBytes: Number(uploaded.size || 0), inputName: text(uploaded.name || descriptor.name, 500), mode, distanceThreshold: threshold, outputFolderId: folder.id, status: 'running', updatedAt: new Date().toISOString()}, {merge: true});
  const workflowRun = await runWorkflow({google, workflowClient, idempotencyKey: stableId, argument: {sourceUrl: descriptor.sourceUrl, outputFolderId: folder.id, scanId: executionIdFor(stableId), mode, distanceThreshold: threshold}, sleep});
  if (text(workflowRun.result.sourceSha256, 64).toLowerCase() !== inputSha256) throw Object.assign(new Error('Scanner source SHA-256 did not match the uploaded video.'), {status: 502, code: 'motion_docs_source_hash_mismatch'});
  const documentId = text(workflowRun.result.document && workflowRun.result.document.documentId, 220);
  if (!documentId) throw Object.assign(new Error('Workflow did not return a Google Document ID.'), {status: 502, code: 'motion_docs_document_missing'});
  const drive = google.drive({version: 'v3', auth});
  const verified = (await drive.files.get({fileId: documentId, fields: 'id,name,mimeType,parents,webViewLink,modifiedTime', supportsAllDrives: true})).data;
  if (verified.mimeType !== 'application/vnd.google-apps.document' || !(verified.parents || []).includes(folder.id)) throw Object.assign(new Error('Google Document readback did not match the workflow destination.'), {status: 502, code: 'motion_docs_document_readback_failed'});
  const result = {requestId: stableId, input: {name: text(uploaded.name || descriptor.name, 500), byteCount: Number(uploaded.size || 0), sha256: inputSha256}, scan: {scanId: workflowRun.result.scanId, mode: workflowRun.result.mode, totalFrames: workflowRun.result.totalFrames, uniqueFrames: workflowRun.result.uniqueFrames, duplicateFrames: workflowRun.result.duplicateFrames}, document: verified, outputFolder: folder, workflow: {executionName: workflowRun.executionName}, workflowFolderAccess: {emailAddress: access.permission.emailAddress, role: access.permission.role, reused: access.reused}, idempotent: false};
  await receiptRef.set({status: 'success', result, completedAt: new Date().toISOString()}, {merge: true});
  return result;
}

module.exports = {executionIdFor, sourceDescriptor, findOrCreateFolder, ensureWorkflowFolderAccess, runWorkflow, runMotionToDocsScan};
