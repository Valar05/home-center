'use strict';

const BLOCKED_HOME_CENTER_EMAILS = Object.freeze([
  'junewren28@gmail.com',
]);
const BLOCKED_HOME_CENTER_EMAIL_SET = new Set(BLOCKED_HOME_CENTER_EMAILS);
const HOME_CENTER_SECURITY_OWNER_EMAILS = Object.freeze([
  'dclarke1005@gmail.com',
]);
const HOME_CENTER_SECURITY_OWNER_EMAIL_SET = new Set(HOME_CENTER_SECURITY_OWNER_EMAILS);

function normalizeHomeCenterEmail(value) {
  return typeof value === 'string' ? value.trim().toLowerCase().slice(0, 320) : '';
}

function isHomeCenterIdentityBlocked(email) {
  return BLOCKED_HOME_CENTER_EMAIL_SET.has(normalizeHomeCenterEmail(email));
}

function assertHomeCenterIdentityAllowed(email, surface = 'Home Center') {
  const clean = normalizeHomeCenterEmail(email);
  if (!isHomeCenterIdentityBlocked(clean)) return clean;
  const err = new Error(`${surface} access is revoked for this Home Center identity.`);
  err.status = 403;
  err.code = 'home_center_identity_blocked';
  err.failureKind = 'home_center_identity_blocked';
  throw err;
}

function requireHomeCenterSecurityOwner(user, surface = 'Home Center security') {
  const email = assertHomeCenterIdentityAllowed(user && user.email, surface);
  if (HOME_CENTER_SECURITY_OWNER_EMAIL_SET.has(email)) return email;
  const err = new Error(`${surface} is restricted to the Home Center owner.`);
  err.status = 403;
  err.code = 'home_center_security_owner_required';
  err.failureKind = 'home_center_security_owner_required';
  throw err;
}

module.exports = {
  BLOCKED_HOME_CENTER_EMAILS,
  HOME_CENTER_SECURITY_OWNER_EMAILS,
  normalizeHomeCenterEmail,
  isHomeCenterIdentityBlocked,
  assertHomeCenterIdentityAllowed,
  requireHomeCenterSecurityOwner,
};
