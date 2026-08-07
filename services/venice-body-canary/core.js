'use strict';

const LOCKED_PORTRAIT_SHA256 = 'e068976188595971194b1d7945750086c65b701eafa04c40db53d95d84884cd8';
const STATES = Object.freeze({DORMANT: 'DORMANT', PRESENT: 'PRESENT', CUT: 'CUT'});
const EXPRESSIONS = new Set(['neutral', 'soft', 'amused', 'concerned', 'focused']);
const GESTURES = new Set(['still', 'breathe', 'nod', 'tilt', 'lean']);

function boundedText(value, limit, field) {
  const text = String(value ?? '').trim();
  if (!text || text.length > limit) throw new Error(`${field} must contain 1-${limit} characters`);
  return text;
}

class VeniceBodyState {
  constructor({portraitReady = false, voiceReady = false} = {}) {
    this.assets = {portraitReady: Boolean(portraitReady), voiceReady: Boolean(voiceReady)};
    this.state = STATES.DORMANT;
    this.epoch = 0;
    this.cutEpoch = 0;
    this.sequence = 0;
    this.expression = 'neutral';
    this.gesture = 'still';
    this.caption = '';
    this.speaking = false;
    this.updatedAt = new Date().toISOString();
  }

  snapshot() {
    return {
      schemaVersion: 'venice.body-event.v1',
      state: this.state,
      epoch: this.epoch,
      cutEpoch: this.cutEpoch,
      sequence: this.sequence,
      expression: this.expression,
      gesture: this.gesture,
      caption: this.caption,
      speaking: this.speaking,
      assets: {...this.assets},
      portraitStatus: 'candidate-reference-not-canon',
      updatedAt: this.updatedAt,
    };
  }

  touch() {
    this.sequence += 1;
    this.updatedAt = new Date().toISOString();
    return this.snapshot();
  }

  requirePresent(command) {
    if (this.state !== STATES.PRESENT) throw new Error('Venice is not PRESENT');
    if (!Number.isInteger(command.epoch) || command.epoch !== this.epoch) {
      throw new Error('stale or missing Venice epoch');
    }
  }

  apply(command = {}) {
    const type = String(command.type || '').toLowerCase();
    if (type === 'cut') {
      this.state = STATES.CUT;
      this.epoch += 1;
      this.cutEpoch += 1;
      this.expression = 'neutral';
      this.gesture = 'still';
      this.caption = '';
      this.speaking = false;
      return this.touch();
    }

    if (type === 'begin') {
      if (!this.assets.portraitReady) throw new Error('verified Venice portrait is unavailable');
      this.state = STATES.PRESENT;
      this.epoch += 1;
      this.expression = 'neutral';
      this.gesture = 'breathe';
      this.caption = '';
      this.speaking = false;
      return this.touch();
    }

    if (type === 'withdraw') {
      this.state = STATES.DORMANT;
      this.epoch += 1;
      this.expression = 'neutral';
      this.gesture = 'still';
      this.caption = '';
      this.speaking = false;
      return this.touch();
    }

    this.requirePresent(command);
    if (type === 'expression') {
      const expression = String(command.expression || '').toLowerCase();
      if (!EXPRESSIONS.has(expression)) throw new Error('unsupported Venice expression');
      this.expression = expression;
      return this.touch();
    }
    if (type === 'gesture') {
      const gesture = String(command.gesture || '').toLowerCase();
      if (!GESTURES.has(gesture)) throw new Error('unsupported Venice gesture');
      this.gesture = gesture;
      return this.touch();
    }
    if (type === 'speak') {
      if (!this.assets.voiceReady) throw new Error('verified Venice voice media is unavailable');
      this.caption = boundedText(command.caption, 1800, 'caption');
      this.speaking = true;
      return this.touch();
    }
    if (type === 'ended') {
      this.caption = '';
      this.speaking = false;
      this.gesture = 'breathe';
      return this.touch();
    }
    throw new Error('unsupported Venice body command');
  }
}

module.exports = {EXPRESSIONS, GESTURES, LOCKED_PORTRAIT_SHA256, STATES, VeniceBodyState};
