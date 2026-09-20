'use strict';

const {createHash} = require('node:crypto');
const {
  normalizeHomeCenterEmail,
  isHomeCenterIdentityBlocked,
  requireHomeCenterSecurityOwner,
} = require('./home_center_access_policy');

function safeNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function ownerKeyFromEmail(email) {
  return `owner_${createHash('sha256').update(normalizeHomeCenterEmail(email) || 'anonymous').digest('hex').slice(0, 32)}`;
}

function assertBlockedTarget(email) {
  const clean = normalizeHomeCenterEmail(email);
  if (!clean || !isHomeCenterIdentityBlocked(clean)) {
    const err = new Error('security.identity_* only operates on identities explicitly blocked by Home Center policy.');
    err.status = 400;
    err.code = 'home_center_security_target_not_blocked';
    throw err;
  }
  return clean;
}

async function firebaseIdentity(admin, email) {
  try {
    return await admin.auth().getUserByEmail(email);
  } catch (err) {
    if (err && err.code === 'auth/user-not-found') return null;
    throw err;
  }
}

async function queryByEmail(db, collectionName, email) {
  const snap = await db.collection(collectionName).where('email', '==', email).get();
  return snap.docs;
}

function isActiveCredential(data, now = Date.now()) {
  if (!data || data.revokedAtMs) return false;
  const expiresAtMs = safeNumber(data.expiresAtMs, 0);
  return expiresAtMs <= 0 || expiresAtMs > now;
}

async function tokenStatus(db, collectionName, email) {
  const docs = await queryByEmail(db, collectionName, email);
  const now = Date.now();
  return {
    total: docs.length,
    active: docs.filter((doc) => isActiveCredential(doc.data() || {}, now)).length,
  };
}

async function householdMembershipStatus(db, email, uid = '') {
  const paths = new Set();
  const groupPaths = new Set();
  const households = await db.collection('households').get();
  for (const householdDoc of households.docs) {
    const members = householdDoc.ref.collection('members');
    if (uid) {
      const direct = await members.doc(uid).get();
      if (direct.exists) paths.add(direct.ref.path);
    }
    const byEmail = await members.where('email', '==', email).get();
    byEmail.docs.forEach((doc) => paths.add(doc.ref.path));

    const groups = await householdDoc.ref.collection('groups').get();
    for (const groupDoc of groups.docs) {
      const groupMembers = groupDoc.ref.collection('members');
      if (uid) {
        const direct = await groupMembers.doc(uid).get();
        if (direct.exists) groupPaths.add(direct.ref.path);
      }
      const byEmailGroup = await groupMembers.where('email', '==', email).get();
      byEmailGroup.docs.forEach((doc) => groupPaths.add(doc.ref.path));
    }
  }
  return {
    householdMembershipPaths: [...paths],
    groupMembershipPaths: [...groupPaths],
  };
}

async function phoneDeviceStatus(db, email) {
  const ownerKey = ownerKeyFromEmail(email);
  const snap = await db.collection('phoneHandsDevices').where('ownerKey', '==', ownerKey).get();
  const active = snap.docs.filter((doc) => {
    const data = doc.data() || {};
    return data.status !== 'revoked' && data.tokenHash && data.tokenHash !== '[revoked]';
  });
  return {ownerKey, total: snap.size, active: active.length};
}

async function providerTokenStatus(db, email, uid = '') {
  const emailSnap = await db.collection('googleToolTokens').doc(email).get();
  let userSnap = null;
  if (uid) userSnap = await db.collection('users').doc(uid).collection('private').doc('googleTokens').get();
  return {
    emailTokenPresent: emailSnap.exists,
    userTokenPresent: !!(userSnap && userSnap.exists),
  };
}

async function oauthTransientStatus(db, email) {
  const codeDocs = await queryByEmail(db, 'mcpOAuthCodes', email);
  const stateDocs = await queryByEmail(db, 'mcpOAuthStates', email);
  return {authorizationCodes: codeDocs.length, oauthStates: stateDocs.length};
}

async function pairingStatus(db, email) {
  const docs = await queryByEmail(db, 'termuxPairingRequests', email);
  const activeStatuses = new Set(['pending', 'approved', 'claimed']);
  return {
    total: docs.length,
    active: docs.filter((doc) => activeStatuses.has(String((doc.data() || {}).status || ''))).length,
  };
}

async function homeCenterIdentityStatusOperation({admin, user, args = {}}) {
  requireHomeCenterSecurityOwner(user, 'security.identity_status');
  const email = assertBlockedTarget(args.email);
  const db = admin.firestore();
  const authUser = await firebaseIdentity(admin, email);
  const uid = authUser ? authUser.uid : '';

  const [
    mcpAccess,
    mcpRefresh,
    termuxAccess,
    termuxRefresh,
    pairings,
    providerTokens,
    transients,
    memberships,
    devices,
  ] = await Promise.all([
    tokenStatus(db, 'mcpOAuthAccessTokens', email),
    tokenStatus(db, 'mcpOAuthRefreshTokens', email),
    tokenStatus(db, 'termuxHubAccessTokens', email),
    tokenStatus(db, 'termuxHubRefreshTokens', email),
    pairingStatus(db, email),
    providerTokenStatus(db, email, uid),
    oauthTransientStatus(db, email),
    householdMembershipStatus(db, email, uid),
    phoneDeviceStatus(db, email),
  ]);

  const result = {
    email,
    blockedByPolicy: isHomeCenterIdentityBlocked(email),
    firebase: {
      exists: !!authUser,
      uidPresent: !!uid,
      disabled: authUser ? authUser.disabled === true : true,
      tokensValidAfterTime: authUser && authUser.tokensValidAfterTime ? authUser.tokensValidAfterTime : '',
    },
    mcpAccess,
    mcpRefresh,
    termuxAccess,
    termuxRefresh,
    termuxPairings: pairings,
    oauthTransients: transients,
    providerTokens,
    memberships: {
      household: memberships.householdMembershipPaths.length,
      groups: memberships.groupMembershipPaths.length,
    },
    phoneDevices: {
      total: devices.total,
      active: devices.active,
    },
  };

  result.fullyRevoked = result.blockedByPolicy
    && result.firebase.disabled
    && result.mcpAccess.active === 0
    && result.mcpRefresh.active === 0
    && result.termuxAccess.active === 0
    && result.termuxRefresh.active === 0
    && result.termuxPairings.active === 0
    && result.oauthTransients.authorizationCodes === 0
    && result.oauthTransients.oauthStates === 0
    && result.providerTokens.emailTokenPresent === false
    && result.providerTokens.userTokenPresent === false
    && result.memberships.household === 0
    && result.memberships.groups === 0
    && result.phoneDevices.active === 0;

  return result;
}

async function markCollectionRevoked(db, collectionName, email, now, extra = {}) {
  const docs = await queryByEmail(db, collectionName, email);
  for (const doc of docs) {
    await doc.ref.set({
      revokedAtMs: now,
      expiresAtMs: now - 1,
      revokedReason: 'home_center_identity_revoked',
      ...extra,
    }, {merge: true});
  }
  return docs.length;
}

async function deleteCollectionByEmail(db, collectionName, email) {
  const docs = await queryByEmail(db, collectionName, email);
  for (const doc of docs) await doc.ref.delete();
  return docs.length;
}

async function deleteMemberships(db, email, uid = '') {
  const status = await householdMembershipStatus(db, email, uid);
  for (const path of [...status.householdMembershipPaths, ...status.groupMembershipPaths]) {
    await db.doc(path).delete();
  }
  return {
    household: status.householdMembershipPaths.length,
    groups: status.groupMembershipPaths.length,
  };
}

async function revokePhoneDevices(db, email, now) {
  const ownerKey = ownerKeyFromEmail(email);
  const snap = await db.collection('phoneHandsDevices').where('ownerKey', '==', ownerKey).get();
  for (const doc of snap.docs) {
    await doc.ref.set({
      status: 'revoked',
      tokenHash: '[revoked]',
      revokedAtMs: now,
      updatedAtMs: now,
    }, {merge: true});
  }
  return snap.size;
}

async function homeCenterIdentityRevokeOperation({admin, user, args = {}}) {
  requireHomeCenterSecurityOwner(user, 'security.revoke_identity');
  const email = assertBlockedTarget(args.email);
  if (args.approved !== true) {
    const err = new Error('security.revoke_identity requires approved=true.');
    err.status = 400;
    err.code = 'home_center_security_approval_required';
    throw err;
  }

  const db = admin.firestore();
  const now = Date.now();
  const before = await homeCenterIdentityStatusOperation({admin, user, args: {email}});
  const authUser = await firebaseIdentity(admin, email);
  const uid = authUser ? authUser.uid : '';

  const revoked = {
    mcpAccess: await markCollectionRevoked(db, 'mcpOAuthAccessTokens', email, now),
    mcpRefresh: await markCollectionRevoked(db, 'mcpOAuthRefreshTokens', email, now),
    termuxAccess: await markCollectionRevoked(db, 'termuxHubAccessTokens', email, now),
    termuxRefresh: await markCollectionRevoked(db, 'termuxHubRefreshTokens', email, now),
    termuxPairings: await markCollectionRevoked(db, 'termuxPairingRequests', email, now, {status: 'revoked'}),
    oauthCodesDeleted: await deleteCollectionByEmail(db, 'mcpOAuthCodes', email),
    oauthStatesDeleted: await deleteCollectionByEmail(db, 'mcpOAuthStates', email),
  };

  const emailTokenRef = db.collection('googleToolTokens').doc(email);
  const emailTokenSnap = await emailTokenRef.get();
  if (emailTokenSnap.exists) await emailTokenRef.delete();
  revoked.googleEmailTokenDeleted = emailTokenSnap.exists;

  if (uid) {
    const userTokenRef = db.collection('users').doc(uid).collection('private').doc('googleTokens');
    const userTokenSnap = await userTokenRef.get();
    if (userTokenSnap.exists) await userTokenRef.delete();
    revoked.googleUserTokenDeleted = userTokenSnap.exists;
    await admin.auth().revokeRefreshTokens(uid);
    await admin.auth().updateUser(uid, {disabled: true});
    revoked.firebaseRefreshTokensRevoked = true;
    revoked.firebaseUserDisabled = true;
  } else {
    revoked.googleUserTokenDeleted = false;
    revoked.firebaseRefreshTokensRevoked = false;
    revoked.firebaseUserDisabled = true;
  }

  revoked.membershipsDeleted = await deleteMemberships(db, email, uid);
  revoked.phoneDevicesRevoked = await revokePhoneDevices(db, email, now);

  const after = await homeCenterIdentityStatusOperation({admin, user, args: {email}});
  return {
    email,
    approved: true,
    revokedAtMs: now,
    before,
    revoked,
    after,
    fullyRevoked: after.fullyRevoked === true,
  };
}

module.exports = {
  ownerKeyFromEmail,
  homeCenterIdentityStatusOperation,
  homeCenterIdentityRevokeOperation,
};
