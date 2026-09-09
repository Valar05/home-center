#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {fileURLToPath} from 'node:url';

const STATES = new Set([
  'waiting',
  'action_required',
  'failed',
  'disconnected',
  'due',
  'resolved',
]);

const SEVERITIES = Object.freeze({
  attention: '⚠️',
  critical: '🚨',
});

const STINGS = Object.freeze([
  'SILENCE IS NOT EVIDENCE.',
  'THE QUIET PART IS THE TRAP.',
  'THE MACHINE MOVED. YOUR TURN.',
  'QUIET IS NOT AN ALL-CLEAR.',
  'THE DOOR WILL NOT OPEN ITSELF.',
]);

const LIMITS = Object.freeze({
  actor: 20,
  action: 44,
  fact: 62,
  id: 100,
  notification: 160,
});

function cleanClause(value, field, maxLength) {
  if (typeof value !== 'string') {
    throw new TypeError(`${field} must be a string`);
  }
  const cleaned = value.trim().replace(/\s+/g, ' ').replace(/[.!?]+$/g, '').toUpperCase();
  if (!cleaned) {
    throw new RangeError(`${field} must not be empty`);
  }
  if (cleaned.length > maxLength) {
    throw new RangeError(`${field} exceeds ${maxLength} characters`);
  }
  return cleaned;
}

function stableHash(value) {
  let hash = 0x811c9dc5;
  for (const character of value) {
    hash ^= character.codePointAt(0);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

/**
 * Compile one notification-first attention line.
 *
 * The caller owns truth. This function never infers whether an event happened;
 * it formats a caller-supplied verified state. Critical information belongs in
 * the returned notification line, never only in a message body.
 *
 * @param {object} event
 * @param {string} event.id stable event identity
 * @param {string} event.state waiting|action_required|failed|disconnected|due|resolved
 * @param {string} event.action imperative action; appears first after the actor
 * @param {string} event.fact verified fact explaining why attention is needed
 * @param {string} [event.actor='Drew'] notification addressee
 * @param {'attention'|'critical'} [event.severity='critical'] visual alarm tier
 * @param {number} [event.pulse=0] explicit repeat counter; rotates the sting deterministically
 * @returns {string|null} complete notification text, or null when resolved
 */
export function compileAttentionNotice(event) {
  if (!event || typeof event !== 'object' || Array.isArray(event)) {
    throw new TypeError('event must be an object');
  }

  const id = cleanClause(event.id, 'id', LIMITS.id);
  const state = String(event.state ?? '').trim().toLowerCase();
  if (!STATES.has(state)) {
    throw new RangeError(`state must be one of: ${[...STATES].join(', ')}`);
  }
  if (state === 'resolved') {
    return null;
  }

  const severity = String(event.severity ?? 'critical').trim().toLowerCase();
  if (!(severity in SEVERITIES)) {
    throw new RangeError(`severity must be one of: ${Object.keys(SEVERITIES).join(', ')}`);
  }

  const pulse = event.pulse ?? 0;
  if (!Number.isSafeInteger(pulse) || pulse < 0) {
    throw new RangeError('pulse must be a non-negative safe integer');
  }

  const actor = cleanClause(event.actor ?? 'Drew', 'actor', LIMITS.actor);
  const action = cleanClause(event.action, 'action', LIMITS.action);
  const fact = cleanClause(event.fact, 'fact', LIMITS.fact);
  const stingIndex = (stableHash(`${id}|${state}`) + pulse) % STINGS.length;
  const notice = `${SEVERITIES[severity]} ${actor}. ${action}. ${fact}. ${STINGS[stingIndex]}`;

  if (notice.length > LIMITS.notification) {
    throw new RangeError(
      `compiled notification exceeds ${LIMITS.notification} characters; shorten action or fact`,
    );
  }

  return notice;
}

function isMainModule() {
  if (!process.argv[1]) return false;
  return path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
}

if (isMainModule()) {
  const raw = process.argv[2] ?? fs.readFileSync(0, 'utf8');
  const event = JSON.parse(raw);
  const notice = compileAttentionNotice(event);
  if (notice !== null) {
    process.stdout.write(`${notice}\n`);
  }
}
