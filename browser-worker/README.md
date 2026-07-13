# Home Center Browser Worker

This package is the first-class Home Center browser-hands runtime. It is not an optional smoke helper.

V1 uses Playwright desktop Chromium by default because Home Center needs the full desktop web surface for accessibility, manual automation, and reusable learning. Android Shizuku remains the phone/window fallback lane for Chrome launch, subframe control, screenshots, and device evidence.

## Host Requirement

Playwright is essential, but it does not run under Android/Termux Node. The phone-local host is Debian/proot with Debian-native `/usr/bin/node` and Debian `/usr/bin/chromium`. Desktop/cloud workers are fallback capacity, not the acceptance target for on-device operation.

Run `npm run doctor` on a candidate worker host before provisioning browsers.

## Contract

Every browser invocation must produce a redacted episode payload suitable for `command_center_operation`:

```text
operation: browser_sessions.record_episode
```

The worker must not store passwords, payment data, raw form values, tokens, cookies, or authorization headers in episode payloads. Sensitive gates such as CAPTCHA, login verification, payment, purchase, and account security are human-controlled blockers.

## Local Smoke

On this Android device, run through Debian/proot:

```sh
proot-distro login debian -- sh -lc 'cd /storage/emulated/0/Documents/GodotProjects/home-center/browser-worker && PATH=/usr/bin:/bin:/usr/sbin:/sbin PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install --ignore-scripts --no-bin-links'
sh tools/run_browser_worker_on_device.sh "scrambled eggs recipe"
```

The launcher sets `HOME_CENTER_CHROMIUM_EXECUTABLE=/usr/bin/chromium`, so Playwright uses the Debian Chromium already installed on the device instead of trying to provision an Android browser binary.
Use `--no-bin-links` for installs under Android shared storage because `/storage/emulated` rejects npm symlink creation.

On a conventional Linux/macOS/Windows worker host, install dependencies in this folder, including Playwright browsers, then run:

```sh
npm install
npx playwright install chromium
npm run smoke:google -- --query "scrambled eggs recipe"
```

The smoke writes a JSON episode under `generated/browser-worker/`. That file is local evidence; Home Center cloud owns durable learning through `browserEpisodes`, `browserDiscoveries`, and `browserPlaybooks`.
