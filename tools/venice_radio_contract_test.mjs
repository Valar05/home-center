import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const {safeStationId, ownerKey, segmentObjectName, API_VERSION} = require('../functions/venice_radio_api.js');

assert.equal(API_VERSION, 'home-center.venice-radio.v1');
assert.equal(safeStationId('venice-asmr-primary'), 'venice-asmr-primary');
assert.throws(() => safeStationId('../oops'), /invalid_station_id/);
assert.equal(ownerKey('DCLARKE1005@GMAIL.COM'), ownerKey('dclarke1005@gmail.com'));
assert.equal(segmentObjectName('abc', 'venice-asmr-primary', 2, 7, 'ogg'), 'radio/abc/venice-asmr-primary/g2/s0000000007.ogg');
console.log('venice_radio_contract_test: ok');
