#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';

process.env.HOME_CENTER_ARTIFACT_BUCKET_TEST_FAKE = '1';
const require = createRequire(import.meta.url);
const {uploadGeneratedArtifact} = require('../functions/artifact_bucket.js');
const {
  analyzeSourceOperation,
  transcribeSlateOperation,
  segmentSourceOperation,
  renderSourceConditionedOperation,
  sfxForgeStatusOperation,
  ENGINE_VERSION,
  SCHEMA_VERSION,
} = require('../functions/sfx_forge_service.js');
const {primitives} = require('../functions/audio_render_service.js');
const {noise, silence, timeline, gain, limit, encodeWav} = primitives;

function fixtureSource() {
  const sampleRate = 48000;
  const hitA = gain(noise({duration: 0.09, sampleRate, channels: 2, gain: 0.52, seed: 'hit-a', color: 'brown'}), 0);
  const hitB = gain(noise({duration: 0.12, sampleRate, channels: 2, gain: 0.44, seed: 'hit-b', color: 'pink'}), -1);
  const room = noise({duration: 1.2, sampleRate, channels: 2, gain: 0.003, seed: 'room'});
  return limit(timeline({
    duration: 1.2,
    sampleRate,
    channels: 2,
    items: [
      {clip: room, at: 0},
      {clip: hitA, at: 0.2},
      {clip: hitB, at: 0.65},
    ],
  }), -1);
}

const sourceBytes = encodeWav(fixtureSource());
const source = await uploadGeneratedArtifact({
  bytes: sourceBytes,
  name: 'fixture-heavy-bag-source.wav',
  mimeType: 'audio/wav',
  owner: 'drew',
  ownerEmail: 'dclarke1005@gmail.com',
  project: 'sfx-armory',
  stage: 'sources',
  artifactType: 'audio',
  requestId: 'sfx-fixture-source',
  prefix: 'audio/drew/sfx-armory/sources',
});

const audits = new Map();
const helpers = {
  createRequestId(value) {
    assert.ok(value);
    return String(value);
  },
  async existingAudit(_admin, requestId) {
    return audits.get(requestId) || null;
  },
  async auditWrite(_admin, entry) {
    audits.set(entry.requestId, entry);
    return {idempotent: false, audit: entry};
  },
};
const user = {email: 'dclarke1005@gmail.com', authKind: 'contract-test'};
const speechClient = {
  async longRunningRecognize(request) {
    assert.equal(request.audio.uri.startsWith('gs://'), true);
    assert.equal(request.config.encoding, 'FLAC');
    assert.equal(request.config.sampleRateHertz, 16000);
    assert.equal(request.config.enableWordTimeOffsets, true);
    return [{
      async promise() {
        return [{
          results: [
            {
              alternatives: [{
                transcript: 'room tone',
                confidence: 0.96,
                words: [
                  {word: 'room', startTime: {seconds: 0, nanos: 100000000}, endTime: {seconds: 0, nanos: 350000000}, confidence: 0.97},
                  {word: 'tone', startTime: {seconds: 0, nanos: 360000000}, endTime: {seconds: 0, nanos: 620000000}, confidence: 0.95},
                ],
              }],
            },
            {
              alternatives: [{
                transcript: 'clean body punch take one',
                confidence: 0.91,
                words: [
                  {word: 'clean', startTime: {seconds: 0, nanos: 700000000}, endTime: {seconds: 0, nanos: 820000000}, confidence: 0.93},
                  {word: 'body', startTime: {seconds: 0, nanos: 830000000}, endTime: {seconds: 0, nanos: 930000000}, confidence: 0.92},
                  {word: 'punch', startTime: {seconds: 0, nanos: 940000000}, endTime: {seconds: 1, nanos: 50000000}, confidence: 0.91},
                  {word: 'take', startTime: {seconds: 1, nanos: 60000000}, endTime: {seconds: 1, nanos: 130000000}, confidence: 0.9},
                  {word: 'one', startTime: {seconds: 1, nanos: 140000000}, endTime: {seconds: 1, nanos: 200000000}, confidence: 0.89},
                ],
              }],
            },
          ],
        }];
      },
    }];
  },
};

const analyzed = await analyzeSourceOperation({
  admin: {},
  user,
  helpers,
  args: {
    sourceRef: source.storageRef,
    expectedSha256: source.sha256,
    requestId: 'sfx-forge-analyze-contract',
    approved: true,
    owner: 'drew',
    ownerEmail: user.email,
    family: 'heavy-bag',
    transcription: {enabled: false},
  },
});
assert.equal(analyzed.ok, true);
assert.equal(analyzed.status, 'completed');
assert.equal(analyzed.executionAuthorized, true);
assert.equal(analyzed.humanAcceptance, 'unreviewed');
assert.equal(analyzed.canonicalSourceReplaced, false);
assert.equal(analyzed.source.sha256, source.sha256);
assert.equal(analyzed.decode.sampleRate, 48000);
assert.equal(analyzed.decode.channels, 2);
assert.equal(analyzed.decode.normalized, false);
assert.equal(analyzed.measurements.standards.standard, 'EBU R128 / ITU-R BS.1770 via FFmpeg ebur128');
assert.ok(Number.isFinite(analyzed.measurements.rms));
assert.ok(Number.isFinite(analyzed.measurements.crestFactorDb));
assert.ok(Number.isFinite(analyzed.measurements.standards.truePeakDbtp));
assert.ok(analyzed.transientAnalysis.candidates.length >= 2);
assert.ok(analyzed.artifacts.every((artifact) => artifact.verified && artifact.sha256 === artifact.readbackSha256));
assert.equal(analyzed.noCommandCenter, true);
assert.equal(analyzed.noCodexWorker, true);

await assert.rejects(
  () => analyzeSourceOperation({
    admin: {},
    user,
    helpers,
    args: {
      sourceRef: source.storageRef,
      expectedSha256: source.sha256,
      requestId: 'sfx-forge-analyze-transcription-rejected',
      approved: true,
      transcription: {enabled: true},
    },
  }),
  /separate Google Cloud stage/,
);

const transcribed = await transcribeSlateOperation({
  admin: {},
  user,
  speechClient,
  helpers,
  args: {
    sourceRef: source.storageRef,
    expectedSha256: source.sha256,
    requestId: 'sfx-forge-transcribe-contract',
    approved: true,
    owner: 'drew',
    ownerEmail: user.email,
    family: 'heavy-bag',
    transcription: {languageCode: 'en-US', model: 'latest_long'},
  },
});
assert.equal(transcribed.ok, true);
assert.equal(transcribed.providerExecution, 'google_cloud_project_identity');
assert.equal(transcribed.remoteOpenAiApiUsed, false);
assert.equal(transcribed.transcription.provider, 'google_cloud_speech_to_text');
assert.equal(transcribed.transcription.words.length, 7);
assert.equal(transcribed.transcription.segments[1].start, 0.7);
assert.equal(transcribed.recognitionInput.format, 'FLAC 16 kHz mono');
assert.equal(transcribed.recognitionInput.normalized, false);
assert.ok(transcribed.artifacts.every((artifact) => artifact.verified && artifact.sha256 === artifact.readbackSha256));

const replay = await analyzeSourceOperation({
  admin: {},
  user,
  helpers,
  args: {
    sourceRef: source.storageRef,
    expectedSha256: source.sha256,
    requestId: 'sfx-forge-analyze-contract',
    approved: true,
    owner: 'drew',
    ownerEmail: user.email,
    family: 'heavy-bag',
    transcription: {enabled: false},
  },
});
assert.equal(replay.idempotent, true);
await assert.rejects(
  () => analyzeSourceOperation({
    admin: {},
    user,
    helpers,
    args: {
      sourceRef: source.storageRef,
      expectedSha256: source.sha256,
      requestId: 'sfx-forge-analyze-contract',
      approved: true,
      family: 'different-family',
      transcription: {enabled: false},
    },
  }),
  /different SFX Forge inputs/,
);

const segmented = await segmentSourceOperation({
  admin: {},
  user,
  helpers,
  args: {
    sourceRef: source.storageRef,
    expectedSha256: source.sha256,
    requestId: 'sfx-forge-segment-contract',
    approved: true,
    owner: 'drew',
    ownerEmail: user.email,
    family: 'heavy-bag',
    sourceMechanism: {
      fixtureType: 'floor_standing',
      floorCoupled: true,
      semanticAuthority: 'human_source_description',
    },
    events: [
      {
        eventId: 'room-001',
        labelSlateText: 'room tone',
        spokenLabelTimeRange: [0, 0.08],
        impactTimeRange: [0.08, 0.16],
        eventType: 'room_tone',
        strikeActionClass: 'none',
        confidence: 0.9,
      },
      {
        eventId: 'impact-001',
        labelSlateText: 'clean body punch take one',
        spokenLabelTimeRange: [0.1, 0.18],
        impactTimeRange: [0.19, 0.42],
        eventType: 'impact',
        strikeActionClass: 'clean_body_punch',
        takeNumber: 1,
        force: 'medium',
        confidence: 0.98,
      },
      {
        eventId: 'impact-rejected-001',
        labelSlateText: 'miss',
        impactTimeRange: [0.62, 0.82],
        eventType: 'miss_air',
        disposition: 'rejected',
        rejectionReason: 'contract fixture rejection',
        confidence: 0.8,
      },
      {
        eventId: 'bag-rocking-001',
        labelSlateText: 'post-impact floor-bag rocking',
        impactTimeRange: [0.82, 0.98],
        eventType: 'bag_rocking',
        strikeActionClass: 'none',
        confidence: 0.95,
      },
    ],
  },
});
assert.equal(segmented.ok, true);
assert.equal(segmented.events.length, 4);
assert.deepEqual(segmented.rejectedEventIds, ['impact-rejected-001']);
assert.ok(segmented.events[1].raw);
assert.ok(segmented.events[1].cleaned);
assert.equal(segmented.events[1].cleanupRecipe.normalization, false);
assert.equal(segmented.events[1].cleanupRecipe.tailPreserved, true);
assert.equal(segmented.events[2].cleaned, null);
assert.ok(Number.isFinite(segmented.events[1].physicalProfile.signal.crestFactorDb));
assert.ok(Number.isFinite(segmented.events[1].physicalProfile.spectralEnvelope.lowMidMassRatio));
assert.equal(segmented.events[1].physicalProfile.metricsGrantArtisticAcceptance, false);
assert.equal(segmented.physicalProfiles.verified, true);
assert.equal(segmented.eventManifest.verified, true);
assert.equal(segmented.events[1].event.eventDomain, 'impact');
assert.equal(segmented.events[3].event.eventDomain, 'bag_movement');
assert.ok(segmented.artifacts.some((artifact) => artifact.name === 'impact-only-audition-reel.wav'));
assert.ok(segmented.artifacts.some((artifact) => artifact.name === 'bag-rocking-audition-reel.wav'));

await assert.rejects(
  () => segmentSourceOperation({
    admin: {},
    user,
    helpers,
    args: {
      sourceRef: source.storageRef,
      expectedSha256: source.sha256,
      requestId: 'sfx-forge-floor-suspension-event-rejection-contract',
      approved: true,
      owner: 'drew',
      ownerEmail: user.email,
      family: 'heavy-bag',
      sourceMechanism: {fixtureType: 'floor_standing'},
      events: [{
        eventId: 'impossible-suspension',
        impactTimeRange: [0.2, 0.4],
        eventType: 'suspension_movement',
      }],
    },
  }),
  /incompatible with floor-standing source mechanism/,
);

const recipe = {
  schemaVersion: SCHEMA_VERSION,
  engineVersion: ENGINE_VERSION,
  seed: 'heavy-bag-contract-seed',
  candidates: [
    {
      candidateId: 'clean-body-001',
      outputKind: 'impact_only',
      controls: {force: 0.55, mass: 0.7, distance: 0.05, intensity: 0.45},
      layers: [
        {role: 'contact', sourceTimeRange: [0.19, 0.27], gainDb: -1},
        {role: 'body_deformation', sourceTimeRange: [0.2, 0.42], lowpassHz: 1800, gainDb: 1},
      ],
    },
    {
      candidateId: 'heavy-cross-001',
      outputKind: 'impact_only',
      controls: {force: 0.9, mass: 0.8, distance: 0.08, intensity: 0.7},
      layers: [
        {role: 'contact', sourceTimeRange: [0.64, 0.72], gainDb: -2},
        {role: 'body_deformation', sourceTimeRange: [0.65, 0.84], lowpassHz: 1500, gainDb: 2},
      ],
    },
  ],
};
const rendered = await renderSourceConditionedOperation({
  admin: {},
  user,
  helpers,
  args: {
    sourceRef: source.storageRef,
    expectedSha256: source.sha256,
    requestId: 'sfx-forge-render-contract',
    approved: true,
    owner: 'drew',
    ownerEmail: user.email,
    family: 'heavy-bag',
    sourceMechanism: {fixtureType: 'floor_standing', floorCoupled: true},
    recipe,
  },
});
assert.equal(rendered.ok, true);
assert.equal(rendered.candidates.length, 2);
assert.ok(/^[a-f0-9]{64}$/.test(rendered.recipeSha256));
assert.ok(rendered.candidates.every((candidate) => candidate.state === 'candidate' && candidate.humanAcceptance === 'unreviewed'));
assert.ok(rendered.candidates.every((candidate) => candidate.outputKind === 'impact_only'));
assert.ok(rendered.candidates.every((candidate) => candidate.sourceRegions.every((region) => region.domain === 'impact')));
assert.ok(rendered.candidates.every((candidate) => !Object.hasOwn(candidate.metrics, 'integratedLufs')));
assert.ok(rendered.candidates.every((candidate) => candidate.metrics.standards.standard === 'EBU R128 / ITU-R BS.1770 via FFmpeg ebur128'));
assert.ok(rendered.candidates.every((candidate) => Number.isFinite(candidate.metrics.standards.integratedLufs)));
assert.ok(rendered.candidates.every((candidate) => Number.isFinite(candidate.metrics.standards.truePeakDbtp)));
assert.equal(rendered.renderManifest.verified, true);

await assert.rejects(
  () => renderSourceConditionedOperation({
    admin: {},
    user,
    helpers,
    args: {
      sourceRef: source.storageRef,
      expectedSha256: source.sha256,
      requestId: 'sfx-forge-floor-suspension-layer-rejection-contract',
      approved: true,
      owner: 'drew',
      ownerEmail: user.email,
      family: 'heavy-bag',
      sourceMechanism: {fixtureType: 'floor_standing'},
      recipe: {
        candidates: [{
          candidateId: 'invalid-floor-suspension',
          outputKind: 'impact_only',
          layers: [{role: 'suspension', sourceTimeRange: [0.2, 0.4]}],
        }],
      },
    },
  }),
  /suspended-bag layer and cannot be used with a floor-standing source/,
);

await assert.rejects(
  () => renderSourceConditionedOperation({
    admin: {},
    user,
    helpers,
    args: {
      sourceRef: source.storageRef,
      expectedSha256: source.sha256,
      requestId: 'sfx-forge-clone-rejection-contract',
      approved: true,
      family: 'heavy-bag',
      recipe: {
        candidates: [
          {candidateId: 'a', layers: [{role: 'contact', sourceTimeRange: [0.2, 0.3]}]},
          {candidateId: 'b', layers: [{role: 'contact', sourceTimeRange: [0.2, 0.3]}]},
        ],
      },
    },
  }),
  /same source-region set/,
);

const status = await sfxForgeStatusOperation({admin: {}, requestId: 'sfx-forge-render-contract', helpers});
assert.equal(status.ok, true);
assert.equal(status.status, 'completed');
assert.equal(status.humanAcceptance, 'unreviewed');

const deployScript = readFileSync(new URL('./deploy_functions_termux.sh', import.meta.url), 'utf8');
const homeCenterSecrets = deployScript.match(/home_center_mcp_secrets_arg\(\) \{([\s\S]*?)\n\}/);
assert.ok(homeCenterSecrets, 'homeCenterMcp secret binding helper must exist');
assert.doesNotMatch(homeCenterSecrets[1], /OPENAI_API_KEY/, 'homeCenterMcp must not bind the dead OpenAI transcription secret');

assert.equal(silence({duration: 0.01, sampleRate: 48000, channels: 2}).sampleRate, 48000);
console.log(JSON.stringify({
  ok: true,
  engineVersion: ENGINE_VERSION,
  schemaVersion: SCHEMA_VERSION,
  analyzedArtifacts: analyzed.artifacts.length,
  transcriptionArtifacts: transcribed.artifacts.length,
  detectedTransients: analyzed.transientAnalysis.candidates.length,
  segmentedEvents: segmented.events.length,
  renderedCandidates: rendered.candidates.length,
  humanAcceptance: rendered.humanAcceptance,
}, null, 2));
