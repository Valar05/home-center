'use strict';

const { ADAPTER_NAMES, READ_ONLY_OPERATIONS } = require('./contracts');

const adapterInterfaces = Object.freeze(Object.fromEntries(ADAPTER_NAMES.map(name => [name, Object.freeze({
  name,
  mode: 'read_only',
  operations: READ_ONLY_OPERATIONS,
  requiredIdentityFields: Object.freeze(['workerId', 'identityHash'])
})])));

function getAdapterInterface(name) {
  const descriptor = adapterInterfaces[name];
  if (!descriptor) throw new TypeError(`unsupported adapter: ${name}`);
  return descriptor;
}

module.exports = { adapterInterfaces, getAdapterInterface };
