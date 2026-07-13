const CHROME_PROFILE = require('./app_control_seed/com.android.chrome.150.0.7871.114+787111433.json');

const APP_CONTROL_COLLECTIONS = Object.freeze({
  profiles: 'appControlProfiles',
  runs: 'appControlRuns',
});
const APP_CONTROL_DEFAULT_SEEDS = Object.freeze([CHROME_PROFILE]);

function appControlProfileObjectId(profile) {
  return `app_control_profile_${String(profile.profileId || '').replace(/[^A-Za-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 140)}`;
}

function appControlProfilePath(profile) {
  const packageName = String(profile.packageName || 'unknown-package').replace(/[^a-zA-Z0-9_.-]+/g, '-');
  const profileId = String(profile.profileId || packageName).replace(/[^a-zA-Z0-9@+_.-]+/g, '-');
  return `app-control/profiles/${packageName}/${profileId}.json`;
}

module.exports = {
  APP_CONTROL_COLLECTIONS,
  APP_CONTROL_DEFAULT_SEEDS,
  appControlProfileObjectId,
  appControlProfilePath,
};
