const assert = require('node:assert/strict');
const {uaplHash} = require('./uapl_pose_language');
const {buildMotionSpa, assertGifDataUri} = require('./uapl_motion_spa');

const uapl = `UAPL 1
NAME jab_fixture
AXES X=right Y=up Z=forward
RIG humanoid5
JOINT P ROOT
JOINT N P
JOINT H N
JOINT RE N
JOINT RW RE
POSE guard
P 0 0 0
N 0 2 0
H 0 4 0
RE 1 2 0
RW 0 3 0
ENDPOSE
POSE contact
P 1 0 0
N 2 2 0
H 2 4 0
RE 4 2 0
RW 6 2 0
ENDPOSE
POSE recoil
P 0 0 0
N 1 2 0
H 1 4 0
RE 2 2 0
RW 1 3 0
ENDPOSE
ORDER guard contact recoil
ENDUAPL
`;

const uat = `UAT 1
SOURCE ${uaplHash(uapl)}
FPS 60
STEP guard 4
STEP contact 1
STEP recoil 3
ENDUAT
`;

// Valid 1x1 GIF89a fixture. Worker acceptance requires a meaningful motion GIF;
// this tiny byte fixture tests the packaging contract only.
const gif = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==';

const htmlA = buildMotionSpa({uaplText: uapl, uatText: uat, gifDataUri: gif, title: 'Jab fixture'});
const htmlB = buildMotionSpa({uaplText: uapl, uatText: uat, gifDataUri: gif, title: 'Jab fixture'});

assert.equal(htmlA, htmlB, 'same source/timing/GIF must produce byte-identical HTML');
assert.match(htmlA, /^<!doctype html>/);
assert.match(htmlA, /viewport-fit=cover/);
assert.match(htmlA, /height:100dvh/);
assert.match(htmlA, /env\(safe-area-inset-top\)/);
assert.match(htmlA, /min-height:44px/);
assert.match(htmlA, /white-space:pre/);
assert.match(htmlA, /font-variant-ligatures:none/);
assert.match(htmlA, /data-uapl-motion-spa="1"/);
assert.match(htmlA, new RegExp(uaplHash(uapl)));
assert.match(htmlA, /ASCII pose contact sheet/);
assert.match(htmlA, /Canonical horizontal contact sheet/);
assert.match(htmlA, /UAT timing opinion/);
assert.match(htmlA, /data:image\/gif;base64,/);
assert.match(htmlA, /id="uaplSource"/);
assert.match(htmlA, /UAPL 1/);
assert.match(htmlA, /POSE contact/);
assert.match(htmlA, /id="uatSource"/);
assert.match(htmlA, /STEP contact 1/);
assert.match(htmlA, /__UAPL_MOTION_SPA_READY__/);
assert.doesNotMatch(htmlA, /https?:\/\//, 'canonical SPA must not depend on network resources');

assert.doesNotThrow(() => assertGifDataUri(gif));
assert.throws(
  () => buildMotionSpa({uaplText: uapl, uatText: uat, gifDataUri: ''}),
  (error) => error && error.code === 'UAPL_SPA_GIF',
  'final SPA must require an embedded GIF',
);
assert.throws(
  () => buildMotionSpa({uaplText: uapl, uatText: uat, gifDataUri: 'data:image/png;base64,AAAA'}),
  (error) => error && error.code === 'UAPL_SPA_GIF',
  'PNG or image-of-ASCII must not satisfy the GIF slot',
);

console.log('UAPL_MOTION_SPA_OK');
console.log(uaplHash(uapl));
