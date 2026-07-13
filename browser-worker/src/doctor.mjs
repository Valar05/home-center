const supported = new Set(['linux', 'darwin', 'win32']);
const platform = process.platform;
const ok = supported.has(platform);
const onDeviceChromium = process.env.HOME_CENTER_CHROMIUM_EXECUTABLE || '';
const result = {
  ok,
  platform,
  arch: process.arch,
  runtime: 'playwright-desktop-chromium',
  executablePath: onDeviceChromium || 'playwright-managed',
  note: ok
    ? 'This host can run the Home Center Playwright browser worker. On Android phones, use Debian/proot with Debian-native Node and /usr/bin/chromium.'
    : 'Playwright does not support this Node platform. On Android/Termux, run the worker inside Debian/proot with Debian-native /usr/bin/node and /usr/bin/chromium; desktop/cloud workers are fallback capacity, not the phone acceptance target.',
};
console.log(JSON.stringify(result, null, 2));
process.exit(ok ? 0 : 2);
