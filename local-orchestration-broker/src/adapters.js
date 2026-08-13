'use strict';

const { ADAPTER_NAMES, READ_ONLY_OPERATIONS } = require('./contracts');

const requiredIdentityFields = Object.freeze(['commissionId', 'commissionHash', 'queueDocumentId', 'queueFolderId', 'queueRevision', 'stateOwner', 'laneId', 'laneOwner', 'workerId', 'identityHash']);
const adapterInterfaces = Object.freeze(Object.fromEntries(ADAPTER_NAMES.map(name => [name, Object.freeze(name === 'venice_mobile' ? {
  name,
  mode: 'descriptor_only',
  operations: Object.freeze(['venice.command.v1', 'venice.dispatch.v1', 'venice.receipt_projection.v1', 'DEVICE_TTS_STATUS.v1']),
  primaryCommandSurface: true,
  uiTypingAllowed: false,
  requiredIdentityFields: Object.freeze([...requiredIdentityFields, 'deviceId', 'appId', 'buildId', 'accountId', 'mobileSessionId', 'conversationId', 'turnId', 'eventSequence', 'eventHash', 'idempotencyKey'])
} : {
  name,
  mode: 'read_only',
  operations: READ_ONLY_OPERATIONS,
  requiredIdentityFields
})])));

function getAdapterInterface(name) {
  const descriptor = adapterInterfaces[name];
  if (!descriptor) throw new TypeError(`unsupported adapter: ${name}`);
  return descriptor;
}

module.exports = { adapterInterfaces, getAdapterInterface };

