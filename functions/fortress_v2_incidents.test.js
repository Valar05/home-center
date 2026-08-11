'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const incidents = require('./fortress_v2.incidents.json');
const {
  chooseNextAction,
  assessHandoff,
  correctionDiff,
} = require('./fortress_v2');

for (const incident of incidents) {
  test(`historical incident: ${incident.id}`, () => {
    if (incident.expectedAction) {
      assert.equal(chooseNextAction(incident.mission).type, incident.expectedAction);
    }

    if (typeof incident.expectedCompletionClaimAllowed === 'boolean') {
      assert.equal(
        assessHandoff(incident.mission).completionClaimAllowed,
        incident.expectedCompletionClaimAllowed,
      );
    }

    if (typeof incident.expectedCorrectionOk === 'boolean') {
      assert.equal(
        correctionDiff(incident.before, incident.after).ok,
        incident.expectedCorrectionOk,
      );
    }
  });
}
