'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const {createCanary} = require('./server');

async function withServer(run) {
  const canary = createCanary({controlToken: 'local-test-token'});
  await new Promise((resolve) => canary.server.listen(0, '127.0.0.1', resolve));
  const address = canary.server.address();
  try { await run(`http://127.0.0.1:${address.port}`, canary); }
  finally { await new Promise((resolve) => canary.server.close(resolve)); }
}

test('status never exposes local paths or the control token', async () => {
  await withServer(async (base) => {
    const response = await fetch(`${base}/status`);
    const text = await response.text();
    assert.equal(response.status, 200);
    assert.doesNotMatch(text, /local-test-token/);
    assert.doesNotMatch(text, /filePath/);
  });
});

test('ordinary control requires authorization and cannot begin without verified art', async () => {
  await withServer(async (base) => {
    const denied = await fetch(`${base}/control`, {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({type: 'begin'}),
    });
    assert.equal(denied.status, 403);

    const unavailable = await fetch(`${base}/control`, {
      method: 'POST',
      headers: {'content-type': 'application/json', 'x-venice-control-token': 'local-test-token'},
      body: JSON.stringify({type: 'begin'}),
    });
    assert.equal(unavailable.status, 409);
    assert.match(await unavailable.text(), /portrait is unavailable/);
  });
});

test('CUT THE CAM remains available without authorization', async () => {
  await withServer(async (base) => {
    const response = await fetch(`${base}/cut`, {method: 'POST'});
    const body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.state, 'CUT');
    assert.equal(body.cutEpoch, 1);
    assert.equal(body.caption, '');
    assert.equal(body.speaking, false);
  });
});
