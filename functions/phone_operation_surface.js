const {
  enqueuePhoneCommand,
  getPhoneCommand,
  listPhoneDevices,
  ownerKeyFromActor,
} = require('./phone_hands_relay');

const DIAGNOSTIC_FIELDS = Object.freeze([
  'diagnosticKind','deviceId','packageId','workerId','queueDocId','queueRevision',
  'commissionHash','laneId','sessionId','streamId','chunkIndex','rootId',
  'watermark','previousChunkHash','maxEntries','maxBytes','extensions',
]);
const MAINTENANCE_FIELDS = Object.freeze([
  'deviceId','packageId','workerId','queueDocId','queueRevision','commissionHash',
  'laneId','sessionId','approvalId','leaseId','sourceRepository','sourceHead',
  'sourceSubdir','expectedVersionName','expectedSignerSha256','timeoutSeconds',
  'networkPolicy','rollbackPolicy',
]);

function operationEntries() {
  return {
    'phone.devices': {
      summary: 'List owner-scoped native Home Center phone devices and their explicitly registered capability planes.',
      write: false,
      input: {},
    },
    'phone.diagnostics.enqueue': {
      summary: 'Enqueue one typed, bounded, read-only diagnostic on primary-phone. No path, command, argv, network, write, build, install, or UI authority is accepted.',
      write: true,
      requiresRequestId: true,
      input: {
        idempotencyKey: 'string', commandId: 'optional string', ttlMs: 'optional number',
        diagnosticKind: 'capability_snapshot|tree_inventory|repo_status|toolchain_probe|cache_probe|file_manifest',
        deviceId: 'primary-phone', packageId: 'com.termux', workerId: 'phone-relay:primary-phone',
        queueDocId: 'string', queueRevision: 'string', commissionHash: 'SHA-256',
        laneId: 'string', sessionId: 'string', streamId: 'string', chunkIndex: 'nonnegative integer',
        rootId: 'GODOT_PROJECTS for rooted kinds only', watermark: 'optional safe relative path',
        previousChunkHash: 'optional SHA-256', maxEntries: '1..500', maxBytes: '1024..2097152',
        extensions: 'optional allowlisted text suffixes',
      },
    },
    'phone.maintenance.enqueue': {
      summary: 'Enqueue the single allowlisted anvil_shell.build_install.v1 maintenance operation on primary-phone. The operation has fixed repository, source subdirectory, build, package, install, and readback behavior and accepts no shell text, URL, arbitrary path, or argv.',
      write: true,
      requiresRequestId: true,
      input: {
        idempotencyKey: 'string', commandId: 'optional string', ttlMs: 'optional number',
        deviceId: 'primary-phone', packageId: 'com.continuecontinue.anvilshell',
        workerId: 'phone-relay:primary-phone', queueDocId: 'string', queueRevision: 'string',
        commissionHash: 'SHA-256', laneId: 'PHONE_MAINTENANCE', sessionId: 'string',
        approvalId: 'string', leaseId: 'string',
        sourceRepository: 'Valar05/continue-continue', sourceHead: '40-character commit SHA',
        sourceSubdir: 'edge/android-shell', expectedVersionName: '0.1.0-checkpoint',
        expectedSignerSha256: 'optional SHA-256', timeoutSeconds: '60..3600',
        networkPolicy: 'bootstrap-and-build', rollbackPolicy: 'retain_previous_apk_if_present',
      },
    },
    'phone.operation.get': {
      summary: 'Read one owner-scoped native Home Center phone diagnostic or maintenance operation and its terminal receipt.',
      write: false,
      input: {commandId: 'string'},
    },
  };
}

function callerFromUser(user = {}) {
  const actor = String(user.email || user.uid || '').trim().toLowerCase();
  if (!actor) throw Object.assign(new Error('Home Center phone operations require an authenticated owner identity.'), {status: 401});
  return {actor, ownerKey: ownerKeyFromActor(actor)};
}

function copyFields(args, names) {
  return Object.fromEntries(names.filter((name) => args[name] !== undefined).map((name) => [name, args[name]]));
}

async function runOperation({admin, user, operation, args = {}}) {
  const caller = callerFromUser(user);
  if (operation === 'phone.devices') return {devices: await listPhoneDevices(admin, caller)};
  if (operation === 'phone.operation.get') return getPhoneCommand(admin, caller, {commandId: args.commandId});
  if (operation === 'phone.diagnostics.enqueue') {
    const action = {
      action: 'phone_diagnostics',
      schema: 'phone.diagnostics.request.v1',
      ...copyFields(args, DIAGNOSTIC_FIELDS),
    };
    return enqueuePhoneCommand(admin, caller, {
      idempotencyKey: args.idempotencyKey,
      commandId: args.commandId,
      deviceId: args.deviceId || 'primary-phone',
      ttlMs: args.ttlMs,
      action,
    });
  }
  if (operation === 'phone.maintenance.enqueue') {
    const action = {
      action: 'anvil_shell_build_install',
      schema: 'phone.maintenance.anvil-shell.v1',
      automaticReplay: false,
      ...copyFields(args, MAINTENANCE_FIELDS),
    };
    return enqueuePhoneCommand(admin, caller, {
      idempotencyKey: args.idempotencyKey,
      commandId: args.commandId,
      deviceId: args.deviceId || 'primary-phone',
      ttlMs: args.ttlMs,
      action,
    });
  }
  throw Object.assign(new Error('Unsupported native phone operation: ' + operation), {status: 400});
}

module.exports = {operationEntries, runOperation, callerFromUser};
