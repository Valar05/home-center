# Android shared-file MediaStore refresh

The authoritative live Campaign Etiquette now requires a bounded refresh **after** final file creation/copy. The canonical one-word Termux command is `refreshmedia`, installed in `$PREFIX/bin/refreshmedia` through the repo-owned `tools/campaigns/ritsu_refreshmedia_install.sh`. Existing isolated campaign launcher `tools/campaigns/ritsu_sticky_onepaste.sh install-media` can install it at a pinned Git source revision from any working directory without modifying an existing dirty home-center checkout.

## Use on phone

After one-time installation:

```bash
refreshmedia
refreshmedia "$HOME/storage/downloads/Ritsu-Sticky-v0.18.0.apk"
refreshmedia "$HOME/storage/pictures"
```

No argument scans only Downloads recursively. An explicit path scans just that file or directory (recursively for a directory). Private Termux data and signing keys are refused. The supported Termux API equivalent for immediate use, without this alias, is `termux-media-scan -r "$HOME/storage/downloads"`.

Requires `termux-api` CLI package and the compatible Termux:API Android companion with permissions. If either is unavailable, the script emits an explicit failure reason without touching user files. Use `pkg install termux-api` if the CLI is absent, then ensure the matching companion app is installed and allowed. Termux storage access may require `termux-setup-storage` if the Downloads link is not present.

The command's success means a **MediaStore indexing request** was issued, not that a file-picker refresh happened or an APK was installed. APKs aren't gallery media. If an APK remains missing from a particular Files view, reopen the Downloads view or inspect the filesystem path directly. The standalone `refreshmedia` command never builds, signs, installs or launches anything.

## Creation-time hook

`tools/campaigns/ritsu_sticky_copy_to_downloads.sh` requests `refreshmedia <exact verified final APK>` after atomic copy and hash readback, using the checked-in helper even if the PATH command is not yet installed. Scan failure is nonblocking and separately reported as `DOWNLOADS_MEDIA_REFRESH=UNAVAILABLE_OR_FAILED_COPY_REMAINS_VALID`. `COPY_VERIFIED=PASS` remains its own receipt.

## Checks

GitHub Actions `.github/workflows/build.yml` runs `refreshmedia.test.sh`, which verifies file scan, recursive folder scan, private-path rejection, missing API, one-word installation, repeated installation and refusal to overwrite an unrelated command. The isolated one-paste test validates `install-media` using a temporary mocked Termux PREFIX. Host mocks do not establish on-phone API functionality.
