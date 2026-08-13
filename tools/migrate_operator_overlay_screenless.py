#!/usr/bin/env python3
"""Screenless, recovery-first signer migration for the Home Center overlay.

This tool is intentionally package-specific. It never launches an Activity,
injects input, dispatches generic media commands, authorizes Spotify, changes a
playlist, or starts playback. The irreversible phase requires both a verified
Drive-synced recovery set and an explicit mutation flag.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PACKAGE = "com.homecenter.operatoroverlay"
SERVICE = f"{PACKAGE}/.OperatorOverlayService"
STATE_URI = f"content://{PACKAGE}.state/state"
RESTORE_METHOD = "restore_migration_state"
EXPECTED_SERIAL = "61070DLCQ00045"
EXPECTED_OLD_VERSION = "1.0.0"
EXPECTED_OLD_VERSION_CODE = 1
EXPECTED_OLD_APK_SHA256 = "c5bf50d5132d4644db01e9d65da2989e44244447594544b84e3265ce41fc26e5"
EXPECTED_OLD_SIGNER_SHA256 = "be0cb034e5da28aa8aa776cf2d7e1bfb1f88f4cb1ce8f7ac220751218aa64b24"
EXPECTED_NEW_VERSION = "1.3.0"
EXPECTED_NEW_VERSION_CODE = 4
EXPECTED_NEW_APK_SHA256 = "5d01f34d41b875eea3de3f93135a63a0be52c4ab3ab24b4bf8c85d90f523ea5b"
EXPECTED_NEW_SIGNER_SHA256 = "c0652840ce34ab4e957ac6c99698c21b694c4ca09c412c473b72c02005909400"
EXPECTED_SOURCE_COMMIT = "43701d1cb8c97c9a4f56e5b3c913f689c6215269"
ALLOWED_RESTORE_KEYS = {
    "muted",
    "last_heartbeat_ms",
    "last_update_ms",
    "latest_source",
    "panel_collapsed",
    "overlay_hidden",
    "control_enabled",
    "screen_active_until_ms",
    "screen_yield_until_ms",
}


class MigrationError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def parse_provider_row(raw: str) -> dict[str, str]:
    body = raw.strip()
    if "Row:" in body:
        body = body.split("Row:", 1)[1]
        body = re.sub(r"^\s*\d+\s+", "", body)
    values: dict[str, str] = {}
    for match in re.finditer(r"(?:^|,\s+)([a-z_]+)=([^,]*)", body):
        values[match.group(1)] = match.group(2).strip()
    return values


def parse_manifest(raw: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\./(.+)", line)
        if not match:
            raise MigrationError("PRIVATE_MANIFEST_INVALID", line[:500])
        name = match.group(2).replace("\\", "/")
        if name.startswith("/") or ".." in Path(name).parts:
            raise MigrationError("PRIVATE_MANIFEST_UNSAFE_PATH", name)
        entries[name] = match.group(1).lower()
    if not entries:
        raise MigrationError("PRIVATE_MANIFEST_EMPTY")
    return entries


def safe_extract_tar(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, "r:") as handle:
        for member in handle.getmembers():
            resolved = (destination / member.name).resolve()
            if resolved != root and root not in resolved.parents:
                raise MigrationError("PRIVATE_ARCHIVE_UNSAFE_PATH", member.name)
        handle.extractall(destination)


def signer_digest(apksigner: Path, apk: Path) -> str:
    result = subprocess.run(
        [str(apksigner), "verify", "--print-certs", str(apk)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise MigrationError("APK_SIGNATURE_INVALID", (result.stdout + result.stderr)[-2000:])
    match = re.search(r"certificate SHA-256 digest:\s*([0-9a-f]{64})", result.stdout + result.stderr, re.IGNORECASE)
    if not match:
        raise MigrationError("APK_SIGNER_UNREADABLE")
    return match.group(1).lower()


@dataclass(frozen=True)
class PackageIdentity:
    version_name: str
    version_code: int
    apk_path: str
    apk_sha256: str


class AdbBody:
    def __init__(self, adb: Path, target: str) -> None:
        self.adb = adb
        self.target = target

    def connect(self) -> str:
        result = subprocess.run([str(self.adb), "connect", self.target], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            raise MigrationError("ADB_CONNECT_FAILED", (result.stdout + result.stderr)[-2000:])
        return result.stdout.strip()

    def run(self, *arguments: str, check: bool = True, timeout: int = 45) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(self.adb), "-s", self.target, *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if check and result.returncode:
            raise MigrationError("ADB_COMMAND_FAILED", f"args={arguments!r} rc={result.returncode} output={(result.stdout + result.stderr)[-3000:]}")
        return result

    def text(self, *arguments: str, check: bool = True, timeout: int = 45) -> str:
        return self.run(*arguments, check=check, timeout=timeout).stdout.strip()

    def shell(self, *arguments: str, check: bool = True, timeout: int = 45) -> str:
        return self.text("shell", *arguments, check=check, timeout=timeout)

    def exec_out_to_file(self, destination: Path, *arguments: str, timeout: int = 60) -> str:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as stream:
            result = subprocess.run(
                [str(self.adb), "-s", self.target, "exec-out", *arguments],
                stdout=stream,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        stderr = result.stderr.decode("utf-8", "replace") if result.stderr else ""
        if result.returncode or not destination.exists() or destination.stat().st_size < 1:
            raise MigrationError("ADB_BINARY_EXPORT_FAILED", stderr[-2000:])
        return stderr

    def exec_in_from_file(self, source: Path, *arguments: str, timeout: int = 60) -> str:
        with source.open("rb") as stream:
            result = subprocess.run(
                [str(self.adb), "-s", self.target, "exec-in", *arguments],
                stdin=stream,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        output = (result.stdout + result.stderr).decode("utf-8", "replace")
        if result.returncode:
            raise MigrationError("ADB_BINARY_IMPORT_FAILED", output[-2000:])
        return output

    def pull(self, remote: str, local: Path) -> str:
        local.parent.mkdir(parents=True, exist_ok=True)
        result = self.run("pull", remote, str(local), timeout=90)
        if not local.exists():
            raise MigrationError("ADB_PULL_MISSING_OUTPUT", remote)
        return result.stdout.strip()

    def push(self, local: Path, remote: str) -> str:
        return self.run("push", str(local), remote, timeout=90).stdout.strip()


def resolve_android_tool(sdk: Path, name: str) -> Path:
    candidates = sorted((sdk / "build-tools").glob(f"*/{name}"), reverse=True)
    if not candidates:
        raise MigrationError("ANDROID_TOOL_MISSING", name)
    return candidates[0]


def foreground(body: AdbBody) -> dict[str, str]:
    raw = body.shell("dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp' | head -2")
    match = re.search(r"([A-Za-z0-9._]+/[A-Za-z0-9._$]+)", raw)
    if not match:
        raise MigrationError("FOREGROUND_UNREADABLE", raw[-1000:])
    return {"component": match.group(1), "raw": raw}


def package_identity(body: AdbBody) -> PackageIdentity:
    path_output = body.shell("pm", "path", PACKAGE)
    path_match = re.search(r"^package:(.+)$", path_output, re.MULTILINE)
    if not path_match:
        raise MigrationError("PACKAGE_PATH_UNREADABLE", path_output)
    apk_path = path_match.group(1).strip()
    package_dump = body.shell("dumpsys", "package", PACKAGE)
    version_name = re.search(r"versionName=([^\s]+)", package_dump)
    version_code = re.search(r"versionCode=(\d+)", package_dump)
    if not version_name or not version_code:
        raise MigrationError("PACKAGE_VERSION_UNREADABLE")
    hash_output = body.shell("sha256sum", apk_path)
    hash_match = re.match(r"([0-9a-fA-F]{64})", hash_output)
    if not hash_match:
        raise MigrationError("PACKAGE_HASH_UNREADABLE")
    return PackageIdentity(version_name.group(1), int(version_code.group(1)), apk_path, hash_match.group(1).lower())


def provider_state(body: AdbBody) -> tuple[str, dict[str, str]]:
    raw = body.shell("content", "query", "--uri", STATE_URI)
    values = parse_provider_row(raw)
    if not values:
        raise MigrationError("PROVIDER_STATE_UNREADABLE", raw)
    return raw, values


def require_safe_state(values: dict[str, str]) -> None:
    if values.get("control_enabled") != "0":
        raise MigrationError("REMOTE_CONTROL_NOT_DISABLED")
    if values.get("screen_active_until_ms") not in {"", "0", None}:
        raise MigrationError("SCREEN_LEASE_ACTIVE")
    if values.get("screen_yield_until_ms") not in {"", "0", None}:
        raise MigrationError("SCREEN_YIELD_ACTIVE")


def fresh_baseline(body: AdbBody) -> dict[str, Any]:
    body.connect()
    state = body.text("get-state")
    serial = body.shell("getprop", "ro.serialno")
    if state != "device" or serial != EXPECTED_SERIAL:
        raise MigrationError("DEVICE_IDENTITY_MISMATCH", f"state={state} serial={serial}")
    focus = foreground(body)
    if focus["component"].startswith(PACKAGE + "/"):
        raise MigrationError("OVERLAY_ACTIVITY_IS_FOREGROUND", focus["component"])
    identity = package_identity(body)
    raw_state, state_values = provider_state(body)
    require_safe_state(state_values)
    return {
        "adbState": state,
        "serial": serial,
        "foreground": focus,
        "package": identity.__dict__,
        "providerRaw": raw_state,
        "provider": state_values,
        "appOps": body.shell("appops", "get", PACKAGE, check=False),
        "notificationPermission": body.shell("cmd", "package", "check-permission", "android.permission.POST_NOTIFICATIONS", PACKAGE, "0", check=False),
        "serviceState": body.shell("dumpsys activity services " + PACKAGE, check=False),
        "shizukuState": body.shell("ps -A | grep -i shizuku || true", check=False),
        "termuxState": body.shell("ps -A | grep -E 'com.termux|termux' || true", check=False),
        "spotifySession": body.shell("dumpsys media_session | grep -F com.spotify.music | head -20 || true", check=False),
    }


def private_manifest(body: AdbBody) -> str:
    result = body.run(
        "exec-out",
        "run-as",
        PACKAGE,
        "sh",
        "-c",
        "find . -type f -exec sha256sum '{}' ';'",
        timeout=60,
    )
    if not result.stdout.strip():
        raise MigrationError("PRIVATE_MANIFEST_EMPTY")
    parse_manifest(result.stdout)
    return result.stdout.strip() + "\n"


def verify_private_archive(archive: Path, manifest_text: str, extracted: Path) -> dict[str, Any]:
    expected = parse_manifest(manifest_text)
    safe_extract_tar(archive, extracted)
    actual: dict[str, str] = {}
    for file in extracted.rglob("*"):
        if file.is_file():
            relative = file.relative_to(extracted).as_posix().removeprefix("./")
            actual[relative] = sha256_file(file)
    if actual != expected:
        raise MigrationError(
            "PRIVATE_ARCHIVE_READBACK_MISMATCH",
            json.dumps({"expected": expected, "actual": actual}, sort_keys=True)[:4000],
        )
    return {"fileCount": len(actual), "files": actual}


def validate_old_identity(identity: PackageIdentity) -> None:
    if (
        identity.version_name != EXPECTED_OLD_VERSION
        or identity.version_code != EXPECTED_OLD_VERSION_CODE
        or identity.apk_sha256 != EXPECTED_OLD_APK_SHA256
    ):
        raise MigrationError("OLD_PACKAGE_BASELINE_CHANGED", json.dumps(identity.__dict__, sort_keys=True))


def validate_new_identity(identity: PackageIdentity) -> None:
    if (
        identity.version_name != EXPECTED_NEW_VERSION
        or identity.version_code != EXPECTED_NEW_VERSION_CODE
        or identity.apk_sha256 != EXPECTED_NEW_APK_SHA256
    ):
        raise MigrationError("NEW_PACKAGE_IDENTITY_MISMATCH", json.dumps(identity.__dict__, sort_keys=True))


def verify_final_artifact(apk: Path, build_receipt: Path, apksigner: Path) -> dict[str, Any]:
    if not apk.is_file() or not build_receipt.is_file():
        raise MigrationError("FINAL_ARTIFACT_MISSING")
    receipt = json.loads(build_receipt.read_text(encoding="utf-8"))
    actual_hash = sha256_file(apk)
    actual_signer = signer_digest(apksigner, apk)
    if (
        actual_hash != EXPECTED_NEW_APK_SHA256
        or actual_signer != EXPECTED_NEW_SIGNER_SHA256
        or receipt.get("sourceCommit") != EXPECTED_SOURCE_COMMIT
        or receipt.get("sha256") != EXPECTED_NEW_APK_SHA256
        or receipt.get("signingCertificateSha256") != EXPECTED_NEW_SIGNER_SHA256
    ):
        raise MigrationError("FINAL_ARTIFACT_IDENTITY_MISMATCH")
    return {
        "path": str(apk),
        "sha256": actual_hash,
        "byteCount": apk.stat().st_size,
        "signerSha256": actual_signer,
        "sourceCommit": receipt["sourceCommit"],
        "receipt": receipt,
    }


def backup(args: argparse.Namespace, body: AdbBody, apksigner: Path) -> dict[str, Any]:
    recovery = args.recovery_root / args.migration_id
    receipt_path = recovery / "backup-receipt.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        verify_recovery_set(recovery, receipt, apksigner)
        return receipt
    if recovery.exists() and any(recovery.iterdir()):
        raise MigrationError("RECOVERY_DIRECTORY_PARTIAL", str(recovery))
    recovery.mkdir(parents=True, exist_ok=True)

    baseline = fresh_baseline(body)
    old_identity = PackageIdentity(**baseline["package"])
    validate_old_identity(old_identity)
    final = verify_final_artifact(args.final_apk, args.final_receipt, apksigner)
    old_apk = recovery / "operator-overlay-old-1.0.0.apk"
    private_tar = recovery / "operator-overlay-old-private-state.tar"
    private_manifest_path = recovery / "operator-overlay-old-private-state.sha256"
    extracted = recovery / "private-state-extracted"

    body.run("pull", old_identity.apk_path, str(old_apk), timeout=90)
    if sha256_file(old_apk) != old_identity.apk_sha256:
        raise MigrationError("OLD_APK_READBACK_MISMATCH")
    old_signer = signer_digest(apksigner, old_apk)
    if old_signer != EXPECTED_OLD_SIGNER_SHA256:
        raise MigrationError("OLD_APK_SIGNER_MISMATCH", old_signer)

    body.shell("am", "force-stop", PACKAGE)
    try:
        after_stop = foreground(body)
        if after_stop["component"] != baseline["foreground"]["component"]:
            raise MigrationError("FOREGROUND_CHANGED_DURING_BACKUP")
        manifest_before = private_manifest(body)
        body.exec_out_to_file(private_tar, "run-as", PACKAGE, "tar", "-cf", "-", ".")
        manifest_after = private_manifest(body)
        if manifest_before != manifest_after:
            raise MigrationError("PRIVATE_STATE_CHANGED_DURING_BACKUP")
        private_manifest_path.write_text(manifest_before, encoding="utf-8")
        archive_verification = verify_private_archive(private_tar, manifest_before, extracted)
    finally:
        body.shell("am", "start-foreground-service", "-n", SERVICE, check=False)

    time.sleep(0.8)
    after_restore = fresh_baseline(body)
    if after_restore["foreground"]["component"] != baseline["foreground"]["component"]:
        raise MigrationError("FOREGROUND_CHANGED_AFTER_BACKUP")

    final_copy = recovery / "operator-overlay-final-1.3.0.apk"
    final_receipt_copy = recovery / "operator-overlay-final-receipt.json"
    shutil.copy2(args.final_apk, final_copy)
    shutil.copy2(args.final_receipt, final_receipt_copy)
    if sha256_file(final_copy) != EXPECTED_NEW_APK_SHA256:
        raise MigrationError("FINAL_APK_RECOVERY_COPY_MISMATCH")

    for name, value in {
        "package-dump.txt": body.shell("dumpsys", "package", PACKAGE),
        "provider-state-before.txt": baseline["providerRaw"],
        "appops-before.txt": baseline["appOps"],
        "services-before.txt": baseline["serviceState"],
        "shizuku-before.txt": baseline["shizukuState"],
        "termux-before.txt": baseline["termuxState"],
        "spotify-session-before.txt": baseline["spotifySession"],
    }.items():
        (recovery / name).write_text(str(value) + "\n", encoding="utf-8")

    receipt = {
        "schema": "home-center.operator-overlay-screenless-backup.v1",
        "migrationId": args.migration_id,
        "createdAtMs": int(time.time() * 1000),
        "recoveryRoot": str(recovery),
        "device": {
            "target": args.adb_target,
            "serial": baseline["serial"],
            "foreground": baseline["foreground"]["component"],
        },
        "oldPackage": {
            **old_identity.__dict__,
            "localApk": old_apk.name,
            "localApkSha256": sha256_file(old_apk),
            "signerSha256": old_signer,
            "byteCount": old_apk.stat().st_size,
        },
        "privateState": {
            "archive": private_tar.name,
            "archiveSha256": sha256_file(private_tar),
            "archiveByteCount": private_tar.stat().st_size,
            "manifest": private_manifest_path.name,
            "manifestSha256": sha256_file(private_manifest_path),
            "fileCount": archive_verification["fileCount"],
            "files": archive_verification["files"],
            "stableAcrossArchive": True,
            "localExtractionVerified": True,
        },
        "boundedState": baseline["provider"],
        "appOps": baseline["appOps"],
        "notificationPermission": baseline["notificationPermission"],
        "finalArtifact": {
            **final,
            "recoveryApk": final_copy.name,
            "recoveryReceipt": final_receipt_copy.name,
        },
        "recoveryInputsVerified": True,
        "packageMutationStarted": False,
        "activityLaunchUsed": False,
        "screenInputUsed": False,
        "genericMediaControlUsed": False,
        "spotifyProviderCalled": False,
    }
    write_json(receipt_path, receipt)
    return receipt


def verify_recovery_set(recovery: Path, receipt: dict[str, Any], apksigner: Path) -> None:
    old_apk = recovery / receipt["oldPackage"]["localApk"]
    private_tar = recovery / receipt["privateState"]["archive"]
    manifest_path = recovery / receipt["privateState"]["manifest"]
    final_apk = recovery / receipt["finalArtifact"]["recoveryApk"]
    final_receipt = recovery / receipt["finalArtifact"]["recoveryReceipt"]
    required = [old_apk, private_tar, manifest_path, final_apk, final_receipt]
    if any(not path.is_file() for path in required):
        raise MigrationError("RECOVERY_FILE_MISSING")
    if sha256_file(old_apk) != receipt["oldPackage"]["localApkSha256"]:
        raise MigrationError("RECOVERY_OLD_APK_HASH_MISMATCH")
    if signer_digest(apksigner, old_apk) != EXPECTED_OLD_SIGNER_SHA256:
        raise MigrationError("RECOVERY_OLD_APK_SIGNER_MISMATCH")
    if sha256_file(private_tar) != receipt["privateState"]["archiveSha256"]:
        raise MigrationError("RECOVERY_PRIVATE_ARCHIVE_HASH_MISMATCH")
    if sha256_file(manifest_path) != receipt["privateState"]["manifestSha256"]:
        raise MigrationError("RECOVERY_PRIVATE_MANIFEST_HASH_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="hc-overlay-recovery-") as temp:
        verify_private_archive(private_tar, manifest_path.read_text(encoding="utf-8"), Path(temp))
    verify_final_artifact(final_apk, final_receipt, apksigner)


def restore_extras(state: dict[str, str]) -> list[str]:
    latest_source = state.get("latest_source", "")
    if not re.fullmatch(r"[A-Za-z0-9 ._/-]{0,80}", latest_source):
        latest_source = ""
    values: dict[str, tuple[str, str]] = {
        "muted": ("boolean", "true" if state.get("muted") == "1" else "false"),
        "last_heartbeat_ms": ("long", str(max(0, int(state.get("last_heartbeat_ms", "0") or 0)))),
        "last_update_ms": ("long", str(max(0, int(state.get("last_update_ms", "0") or 0)))),
        "latest_source": ("string", latest_source),
        "panel_collapsed": ("boolean", "true" if state.get("panel_collapsed") == "1" else "false"),
        "overlay_hidden": ("boolean", "true" if state.get("overlay_hidden") == "1" else "false"),
        "control_enabled": ("boolean", "false"),
        "screen_active_until_ms": ("long", "0"),
        "screen_yield_until_ms": ("long", "0"),
    }
    if set(values) != ALLOWED_RESTORE_KEYS:
        raise MigrationError("RESTORE_FIELD_SET_INVALID")
    extras: list[str] = []
    for key, (kind, value) in values.items():
        extras.extend(["--extra", f"{kind}:{key}:{value}"])
    return extras


def restore_permissions(body: AdbBody, receipt: dict[str, Any]) -> dict[str, Any]:
    appops = str(receipt.get("appOps") or "")
    restored: dict[str, Any] = {}
    if re.search(r"SYSTEM_ALERT_WINDOW:\s*allow", appops, re.IGNORECASE):
        result = body.run("shell", "appops", "set", PACKAGE, "SYSTEM_ALERT_WINDOW", "allow", check=False)
        restored["systemAlertWindow"] = {"exitCode": result.returncode, "output": (result.stdout + result.stderr).strip()}
        if result.returncode:
            raise MigrationError("OVERLAY_APP_OP_RESTORE_FAILED")
    notification = str(receipt.get("notificationPermission") or "").strip().lower()
    if "granted" in notification:
        result = body.run("shell", "pm", "grant", PACKAGE, "android.permission.POST_NOTIFICATIONS", check=False)
        restored["postNotifications"] = {"exitCode": result.returncode, "output": (result.stdout + result.stderr).strip()}
        if result.returncode:
            raise MigrationError("NOTIFICATION_PERMISSION_RESTORE_FAILED")
    return restored


def rollback(args: argparse.Namespace, body: AdbBody, apksigner: Path, reason: str = "explicit") -> dict[str, Any]:
    if not args.allow_package_mutation:
        raise MigrationError("PACKAGE_MUTATION_FLAG_REQUIRED")
    recovery = args.recovery_root / args.migration_id
    receipt = json.loads((recovery / "backup-receipt.json").read_text(encoding="utf-8"))
    verify_recovery_set(recovery, receipt, apksigner)
    old_apk = recovery / receipt["oldPackage"]["localApk"]
    private_tar = recovery / receipt["privateState"]["archive"]
    baseline_foreground = receipt["device"]["foreground"]

    body.run("shell", "pm", "uninstall", PACKAGE, check=False, timeout=90)
    install = body.run("install", str(old_apk), timeout=120)
    if "Success" not in install.stdout:
        raise MigrationError("ROLLBACK_OLD_APK_INSTALL_FAILED", install.stdout + install.stderr)
    identity = package_identity(body)
    validate_old_identity(identity)
    body.shell("am", "force-stop", PACKAGE)
    body.exec_in_from_file(private_tar, "run-as", PACKAGE, "tar", "-xf", "-", ".")
    restored_manifest = private_manifest(body)
    if parse_manifest(restored_manifest) != receipt["privateState"]["files"]:
        raise MigrationError("ROLLBACK_PRIVATE_STATE_MISMATCH")
    permission_receipt = restore_permissions(body, receipt)
    body.shell("am", "start-foreground-service", "-n", SERVICE)
    time.sleep(0.8)
    focus = foreground(body)
    if focus["component"] != baseline_foreground:
        raise MigrationError("ROLLBACK_FOREGROUND_CHANGED")
    raw_state, state = provider_state(body)
    require_safe_state(state)
    result = {
        "schema": "home-center.operator-overlay-screenless-rollback.v1",
        "migrationId": args.migration_id,
        "reason": reason,
        "identity": identity.__dict__,
        "foreground": focus,
        "providerRaw": raw_state,
        "permissions": permission_receipt,
        "oldApkRestored": True,
        "privateStateRestored": True,
        "activityLaunchUsed": False,
        "screenInputUsed": False,
    }
    write_json(recovery / "rollback-receipt.json", result)
    return result


def migrate(args: argparse.Namespace, body: AdbBody, apksigner: Path) -> dict[str, Any]:
    if not args.allow_package_mutation:
        raise MigrationError("PACKAGE_MUTATION_FLAG_REQUIRED")
    recovery = args.recovery_root / args.migration_id
    receipt = json.loads((recovery / "backup-receipt.json").read_text(encoding="utf-8"))
    verify_recovery_set(recovery, receipt, apksigner)
    baseline = fresh_baseline(body)
    old_identity = PackageIdentity(**baseline["package"])
    validate_old_identity(old_identity)
    if baseline["foreground"]["component"] != receipt["device"]["foreground"]:
        raise MigrationError("FOREGROUND_BASELINE_CHANGED")
    if baseline["provider"] != receipt["boundedState"]:
        raise MigrationError("BOUNDED_STATE_BASELINE_CHANGED")

    final_apk = recovery / receipt["finalArtifact"]["recoveryApk"]
    final_receipt = recovery / receipt["finalArtifact"]["recoveryReceipt"]
    verify_final_artifact(final_apk, final_receipt, apksigner)
    remote_final = "/data/local/tmp/home-center-operator-overlay-1.3.0.apk"
    body.push(final_apk, remote_final)
    staged_hash = re.match(r"([0-9a-fA-F]{64})", body.shell("sha256sum", remote_final))
    if not staged_hash or staged_hash.group(1).lower() != EXPECTED_NEW_APK_SHA256:
        raise MigrationError("STAGED_FINAL_APK_HASH_MISMATCH")

    uninstalled = False
    try:
        body.shell("am", "force-stop", PACKAGE)
        uninstall = body.run("shell", "pm", "uninstall", PACKAGE, timeout=90)
        if "Success" not in uninstall.stdout:
            raise MigrationError("OLD_PACKAGE_UNINSTALL_FAILED", uninstall.stdout + uninstall.stderr)
        uninstalled = True
        install = body.run("shell", "pm", "install", remote_final, timeout=120)
        if "Success" not in install.stdout:
            raise MigrationError("NEW_PACKAGE_INSTALL_FAILED", install.stdout + install.stderr)
        new_identity = package_identity(body)
        validate_new_identity(new_identity)

        installed_copy = recovery / "operator-overlay-new-installed.apk"
        body.pull(new_identity.apk_path, installed_copy)
        if sha256_file(installed_copy) != EXPECTED_NEW_APK_SHA256:
            raise MigrationError("INSTALLED_NEW_APK_READBACK_MISMATCH")
        if signer_digest(apksigner, installed_copy) != EXPECTED_NEW_SIGNER_SHA256:
            raise MigrationError("INSTALLED_NEW_APK_SIGNER_MISMATCH")

        extras = restore_extras(receipt["boundedState"])
        restore = body.run("shell", "content", "call", "--uri", STATE_URI, "--method", RESTORE_METHOD, *extras)
        if not re.search(r"accepted=(?:true|1)", restore.stdout, re.IGNORECASE):
            raise MigrationError("BOUNDED_STATE_RESTORE_REJECTED", restore.stdout + restore.stderr)
        permission_receipt = restore_permissions(body, receipt)
        body.shell("am", "start-foreground-service", "-n", SERVICE)
        time.sleep(1.0)

        focus = foreground(body)
        if focus["component"] != receipt["device"]["foreground"]:
            raise MigrationError("FOREGROUND_CHANGED_AFTER_MIGRATION")
        raw_state, state = provider_state(body)
        require_safe_state(state)
        for key in ("muted", "last_heartbeat_ms", "last_update_ms", "latest_source", "panel_collapsed", "overlay_hidden"):
            if state.get(key, "") != receipt["boundedState"].get(key, ""):
                raise MigrationError("BOUNDED_STATE_READBACK_MISMATCH", key)
        service_state = body.shell("dumpsys activity services " + PACKAGE, check=False)
        if "OperatorOverlayService" not in service_state:
            raise MigrationError("OVERLAY_SERVICE_NOT_RUNNING")

        result = {
            "schema": "home-center.operator-overlay-screenless-migration.v1",
            "migrationId": args.migration_id,
            "completedAtMs": int(time.time() * 1000),
            "identity": new_identity.__dict__,
            "signerSha256": EXPECTED_NEW_SIGNER_SHA256,
            "foreground": focus,
            "providerRaw": raw_state,
            "provider": state,
            "permissions": permission_receipt,
            "serviceVerified": True,
            "rollbackInputsRemainVerified": True,
            "activityLaunchUsed": False,
            "screenInputUsed": False,
            "genericMediaControlUsed": False,
            "spotifyProviderCalled": False,
            "playlistMutationUsed": False,
            "playbackUsed": False,
        }
        write_json(recovery / "migration-receipt.json", result)
        body.shell("rm", "-f", remote_final, check=False)
        return result
    except Exception as error:
        if uninstalled:
            try:
                rollback(args, body, apksigner, reason=f"automatic:{type(error).__name__}:{error}")
            except Exception as rollback_error:
                write_json(
                    recovery / "migration-failure.json",
                    {
                        "migrationError": f"{type(error).__name__}: {error}",
                        "rollbackError": f"{type(rollback_error).__name__}: {rollback_error}",
                        "rollbackVerified": False,
                    },
                )
                raise MigrationError("MIGRATION_AND_ROLLBACK_FAILED", f"migration={error}; rollback={rollback_error}") from rollback_error
        raise


def verify(args: argparse.Namespace, body: AdbBody, apksigner: Path) -> dict[str, Any]:
    recovery = args.recovery_root / args.migration_id
    migration_receipt = json.loads((recovery / "migration-receipt.json").read_text(encoding="utf-8"))
    verify_recovery_set(recovery, json.loads((recovery / "backup-receipt.json").read_text(encoding="utf-8")), apksigner)
    identity = package_identity(body)
    validate_new_identity(identity)
    focus = foreground(body)
    if focus["component"] != migration_receipt["foreground"]["component"]:
        raise MigrationError("VERIFY_FOREGROUND_MISMATCH")
    raw_state, state = provider_state(body)
    require_safe_state(state)
    return {
        "schema": "home-center.operator-overlay-screenless-verify.v1",
        "identity": identity.__dict__,
        "foreground": focus,
        "providerRaw": raw_state,
        "provider": state,
        "recoverySetVerified": True,
        "activityLaunchUsed": False,
        "screenInputUsed": False,
    }


def read_only_probe(args: argparse.Namespace, body: AdbBody) -> dict[str, Any]:
    request_id = int(time.time_ns() & ((1 << 63) - 1)) or 1
    result = body.run(
        "shell",
        "content",
        "call",
        "--uri",
        STATE_URI,
        "--method",
        "spotify_control",
        "--arg",
        "status",
        "--extra",
        "long:request_id:" + str(request_id),
    )
    deadline = time.monotonic() + 12
    latest: dict[str, str] = {}
    while time.monotonic() < deadline:
        _, latest = provider_state(body)
        if latest.get("spotify_request_id") == str(request_id):
            break
        time.sleep(0.2)
    encoded = latest.get("spotify_receipt_b64", "")
    receipt: dict[str, Any] = {}
    if encoded:
        try:
            receipt = json.loads(base64.b64decode(encoded).decode("utf-8"))
        except Exception as error:
            raise MigrationError("SPOTIFY_STATUS_RECEIPT_INVALID", str(error)) from error
    return {
        "schema": "home-center.operator-overlay-read-only-probe.v1",
        "requestId": request_id,
        "providerCall": result.stdout.strip(),
        "spotifyReceipt": receipt,
        "provider": latest,
        "activityLaunchUsed": False,
        "screenInputUsed": False,
        "genericMediaControlUsed": False,
        "spotifyAuthorizationUsed": False,
        "playlistMutationUsed": False,
        "playbackUsed": False,
    }


def parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    default_recovery = Path(r"G:\My Drive\Adam - Fortress Online\Runtime Recovery\Spotify Radio")
    default_sdk = Path(os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME") or r"C:\Users\dclar\AppData\Local\Android\Sdk")
    result = argparse.ArgumentParser(prog="migrate-operator-overlay-screenless")
    result.add_argument("phase", choices=["backup", "migrate", "verify", "rollback", "probe"])
    result.add_argument("--adb-target", default="192.168.1.3:36667")
    result.add_argument("--migration-id", default="spotify-radio-migration-43701d1-20260813T2130Z")
    result.add_argument("--recovery-root", type=Path, default=default_recovery)
    result.add_argument("--final-apk", type=Path, default=root / "build" / "operator-overlay-final-main-signed" / "operator-overlay-debug.apk")
    result.add_argument("--final-receipt", type=Path, default=root / "build" / "operator-overlay-final-main-signed" / "operator-overlay-receipt.json")
    result.add_argument("--android-sdk", type=Path, default=default_sdk)
    result.add_argument("--adb", type=Path, default=Path(shutil.which("adb") or "adb"))
    result.add_argument("--allow-package-mutation", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        apksigner_name = "apksigner.bat" if os.name == "nt" else "apksigner"
        apksigner = resolve_android_tool(args.android_sdk, apksigner_name)
        body = AdbBody(args.adb, args.adb_target)
        if args.phase == "backup":
            output = backup(args, body, apksigner)
        elif args.phase == "migrate":
            output = migrate(args, body, apksigner)
        elif args.phase == "verify":
            output = verify(args, body, apksigner)
        elif args.phase == "rollback":
            output = rollback(args, body, apksigner)
        else:
            output = read_only_probe(args, body)
        print(json.dumps({"ok": True, "phase": args.phase, "result": output}, ensure_ascii=False, sort_keys=True))
        return 0
    except MigrationError as error:
        print(json.dumps({"ok": False, "phase": args.phase, "error": error.code, "detail": error.detail}, ensure_ascii=False, sort_keys=True))
        return 2
    except Exception as error:
        print(json.dumps({"ok": False, "phase": args.phase, "error": "MIGRATION_INTERNAL_ERROR", "detail": f"{type(error).__name__}: {error}"}, ensure_ascii=False, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
