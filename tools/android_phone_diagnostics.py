#!/data/data/com.termux/files/usr/bin/python
"""Bounded, read-only diagnostics for the registered Home Center phone.

This module deliberately has no subprocess, socket, urllib, write, build,
install, or UI capability.  Callers choose a fixed diagnostic kind and an
allowlisted root id; they never supply a path, command, or argv.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import time
from pathlib import Path
from typing import Any

SCHEMA = "phone.diagnostics.request.v1"
RECEIPT_SCHEMA = "phone.diagnostics.receipt.v1"
ROOTS = {
    "GODOT_PROJECTS": Path("/storage/emulated/0/Documents/GodotProjects"),
}
KINDS = {
    "capability_snapshot",
    "tree_inventory",
    "repo_status",
    "toolchain_probe",
    "cache_probe",
    "file_manifest",
}
REQUEST_KEYS = {
    "action", "schema", "diagnosticKind", "deviceId", "packageId", "workerId",
    "queueDocId", "queueRevision", "commissionHash", "laneId", "sessionId",
    "streamId", "chunkIndex", "rootId", "watermark", "previousChunkHash",
    "maxEntries", "maxBytes", "extensions",
}
TEXT_EXTENSIONS = {
    ".gd", ".tscn", ".tres", ".godot", ".md", ".txt", ".json", ".toml",
    ".yaml", ".yml", ".xml", ".cfg", ".ini", ".py", ".js", ".mjs", ".ts",
    ".tsx", ".java", ".kt", ".kts", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".glsl", ".vert", ".frag", ".shader", ".sh", ".ps1",
}
SECRET_NAMES = {
    ".env", ".npmrc", ".pypirc", ".netrc", "credentials", "credentials.json",
    "cookies", "cookies.sqlite", "known_hosts", "authorized_keys",
    "id_rsa", "id_ed25519", "codex-hub.json", "phone-relay.json",
}
SECRET_SUFFIXES = {
    ".pem", ".key", ".keystore", ".jks", ".p12", ".pfx", ".mobileprovision",
}
SECRET_PARTS = ("token", "secret", "password", "credential", "cookie", "oauth", "auth")
TOOL_NAMES = (
    "git", "bash", "python", "python3", "node", "npm", "java", "javac",
    "gradle", "aapt2", "apksigner", "adb", "godot", "godot4", "clang",
    "clang++", "cmake", "ninja", "ollama", "continue", "vlad", "dungeon",
)
ALLOWED_TOOL_PREFIXES = (
    "/data/data/com.termux/files/usr/",
    "/data/data/com.termux/files/home/",
)
DEFAULT_MAX_ENTRIES = 200
HARD_MAX_ENTRIES = 500
DEFAULT_MAX_BYTES = 512 * 1024
HARD_MAX_BYTES = 2 * 1024 * 1024
MAX_HASH_FILE_BYTES = 1024 * 1024
MAX_TOOL_HASH_BYTES = 16 * 1024 * 1024
TIME_BUDGET_SECONDS = 8.0


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha256_file(path: Path, limit: int) -> tuple[str, str]:
    size = path.stat().st_size
    if size > limit:
        return "", "TOO_LARGE"
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            h.update(block)
    return h.hexdigest(), "HASHED"


def _secret_name(name: str) -> bool:
    lower = name.lower()
    if lower in SECRET_NAMES or any(lower.endswith(suffix) for suffix in SECRET_SUFFIXES):
        return True
    return any(part in lower for part in SECRET_PARTS)


def _hidden_relative(relative: Path) -> bool:
    return any(part.startswith(".") for part in relative.parts)


def _contained(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve(strict=True)
    resolved = candidate.resolve(strict=True)
    if os.path.commonpath((str(resolved_root), str(resolved))) != str(resolved_root):
        raise PermissionError("diagnostic path escapes registered root")
    return resolved


def _bounds(action: dict[str, Any]) -> tuple[int, int]:
    entries = int(action.get("maxEntries") if action.get("maxEntries") is not None else DEFAULT_MAX_ENTRIES)
    byte_budget = int(action.get("maxBytes") if action.get("maxBytes") is not None else DEFAULT_MAX_BYTES)
    if not 1 <= entries <= HARD_MAX_ENTRIES or not 1024 <= byte_budget <= HARD_MAX_BYTES:
        raise ValueError("diagnostics budgets exceed fixed bounds")
    return entries, byte_budget


def _validate_action(action: dict[str, Any]) -> str:
    unknown = set(action) - REQUEST_KEYS
    if unknown:
        raise ValueError("diagnostics rejects unknown field")
    if str(action.get("action") or "") != "phone_diagnostics":
        raise ValueError("unsupported diagnostics action")
    if str(action.get("schema") or "") != SCHEMA:
        raise ValueError("unsupported diagnostics schema")
    kind = str(action.get("diagnosticKind") or "")
    if kind not in KINDS:
        raise ValueError("unsupported diagnosticKind")
    required = ("deviceId", "packageId", "workerId", "queueDocId", "queueRevision",
                "commissionHash", "laneId", "sessionId", "streamId")
    if any(not isinstance(action.get(key), str) or not action[key].strip() for key in required):
        raise ValueError("diagnostics identity binding is incomplete")
    if action["deviceId"] != "primary-phone":
        raise PermissionError("diagnostics device identity mismatch")
    if action["packageId"] != "com.termux":
        raise PermissionError("diagnostics package identity mismatch")
    if action["workerId"] != "phone-relay:primary-phone":
        raise PermissionError("diagnostics worker identity mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", action["commissionHash"].lower()):
        raise ValueError("diagnostics commissionHash must be SHA-256")
    previous = str(action.get("previousChunkHash") or "")
    if previous and not re.fullmatch(r"[0-9a-f]{64}", previous.lower()):
        raise ValueError("diagnostics previousChunkHash must be SHA-256")
    watermark = str(action.get("watermark") or "")
    if watermark.startswith("/") or ".." in watermark or "\\" in watermark:
        raise PermissionError("diagnostics watermark must be a safe relative path")
    chunk_index = action.get("chunkIndex")
    if not isinstance(chunk_index, int) or isinstance(chunk_index, bool) or chunk_index < 0:
        raise ValueError("diagnostics chunkIndex must be a nonnegative integer")
    if chunk_index == 0 and (watermark or previous):
        raise ValueError("diagnostics first chunk cannot claim prior state")
    if chunk_index > 0 and not previous:
        raise ValueError("diagnostics resume requires previousChunkHash")
    root_kinds = {"tree_inventory", "repo_status", "file_manifest"}
    root_id = str(action.get("rootId") or "")
    if kind in root_kinds and root_id != "GODOT_PROJECTS":
        raise PermissionError("diagnostics rootId must be GODOT_PROJECTS")
    if kind not in root_kinds and root_id:
        raise PermissionError("diagnostics rootId is not valid for this diagnosticKind")
    for key in ("maxEntries", "maxBytes"):
        value = action.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise ValueError("diagnostics budgets must be integers")
    extensions = action.get("extensions")
    if extensions is not None and (
        not isinstance(extensions, list) or len(extensions) > 64 or
        any(not isinstance(value, str) or len(value) > 16 or value.lower() not in TEXT_EXTENSIONS
            for value in extensions)
    ):
        raise PermissionError("file_manifest extensions exceed allowlist")
    return kind


def _registered_root(action: dict[str, Any], roots: dict[str, Path]) -> tuple[str, Path]:
    root_id = str(action.get("rootId") or "")
    if root_id not in roots:
        raise PermissionError("unknown diagnostic rootId")
    root = roots[root_id]
    if root.is_symlink():
        raise PermissionError("registered diagnostics root cannot be a symlink")
    resolved = _contained(root, root)
    if not resolved.is_dir():
        raise PermissionError("registered diagnostics root is not a real directory")
    return root_id, resolved


def _entry_metadata(root: Path, path: Path) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        kind = "symlink"
    elif stat.S_ISDIR(info.st_mode):
        kind = "directory"
    elif stat.S_ISREG(info.st_mode):
        kind = "file"
    else:
        kind = "other"
    return {
        "relativePath": relative,
        "type": kind,
        "size": int(info.st_size),
        "mtimeNs": int(info.st_mtime_ns),
    }


def _walk_metadata(root: Path, deadline: float) -> tuple[list[dict[str, Any]], dict[str, int], bool]:
    entries: list[dict[str, Any]] = []
    skipped = {"hidden": 0, "secret": 0, "symlink": 0, "other": 0}
    pending = [root]
    complete = True
    while pending:
        if time.monotonic() > deadline:
            complete = False
            break
        directory = pending.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
        except (OSError, PermissionError):
            skipped["other"] += 1
            continue
        for child in children:
            if time.monotonic() > deadline:
                complete = False
                break
            relative = child.relative_to(root)
            if _hidden_relative(relative):
                skipped["hidden"] += 1
                continue
            if _secret_name(child.name):
                skipped["secret"] += 1
                continue
            try:
                meta = _entry_metadata(root, child)
            except (OSError, PermissionError):
                skipped["other"] += 1
                continue
            if meta["type"] == "symlink":
                skipped["symlink"] += 1
                continue
            entries.append(meta)
            if meta["type"] == "directory":
                pending.append(child)
    entries.sort(key=lambda item: item["relativePath"])
    return entries, skipped, complete


def _chunk(
    entries: list[dict[str, Any]],
    skipped: dict[str, int],
    action: dict[str, Any],
    root_id: str,
    scan_complete: bool = True,
) -> dict[str, Any]:
    max_entries, max_bytes = _bounds(action)
    watermark = str(action.get("watermark") or "")
    selected: list[dict[str, Any]] = []
    used = 0
    remaining = [entry for entry in entries if entry["relativePath"] > watermark]
    for entry in remaining:
        encoded = len(canonical_bytes(entry))
        if selected and (len(selected) >= max_entries or used + encoded > max_bytes):
            break
        if encoded > max_bytes:
            continue
        selected.append(entry)
        used += encoded
    next_watermark = selected[-1]["relativePath"] if selected else watermark
    more = len(remaining) > len(selected) or not scan_complete
    payload = {
        "rootId": root_id,
        "watermarkBefore": watermark,
        "watermarkAfter": next_watermark,
        "previousChunkHash": str(action.get("previousChunkHash") or ""),
        "entries": selected,
        "entryCount": len(selected),
        "observedEntryCount": len(entries),
        "skipped": skipped,
        "scanComplete": scan_complete,
        "more": more,
    }
    return {
        **payload,
        "chunkHash": digest(payload),
        "status": "MORE" if more else "COMPLETE",
        "byteCount": used,
    }


def _capability_snapshot() -> dict[str, Any]:
    home = Path.home()
    usage = shutil.disk_usage(home)
    memory: dict[str, int] = {}
    try:
        page = int(os.sysconf("SC_PAGE_SIZE"))
        memory["physicalBytes"] = page * int(os.sysconf("SC_PHYS_PAGES"))
        memory["availableBytes"] = page * int(os.sysconf("SC_AVPHYS_PAGES"))
    except (ValueError, OSError, AttributeError):
        pass
    try:
        load = [float(value) for value in os.getloadavg()]
    except (OSError, AttributeError):
        load = []
    return {
        "architecture": platform.machine(),
        "platform": platform.system(),
        "platformRelease": platform.release(),
        "pythonRuntime": platform.python_version(),
        "homeStorage": {"totalBytes": usage.total, "usedBytes": usage.used, "freeBytes": usage.free},
        "memory": memory,
        "loadAverage": load,
        "networkUsed": False,
        "subprocessUsed": False,
    }


def _toolchain_probe() -> dict[str, Any]:
    tools = []
    for name in TOOL_NAMES:
        located = shutil.which(name)
        if not located:
            tools.append({"tool": name, "state": "ABSENT"})
            continue
        path = Path(located).resolve(strict=True)
        if not any(str(path).startswith(prefix) for prefix in ALLOWED_TOOL_PREFIXES):
            tools.append({"tool": name, "state": "REJECTED_PATH"})
            continue
        info = path.stat()
        sha, hash_state = _sha256_file(path, MAX_TOOL_HASH_BYTES)
        tools.append({
            "tool": name,
            "state": "PRESENT",
            "path": str(path),
            "size": int(info.st_size),
            "mtimeNs": int(info.st_mtime_ns),
            "sha256": sha,
            "hashState": hash_state,
            "version": "UNKNOWN_NO_EXEC",
        })
    return {"tools": tools, "subprocessUsed": False, "networkUsed": False}


def _cache_probe(deadline: float) -> dict[str, Any]:
    home = Path.home().resolve(strict=True)
    candidates = {
        "GRADLE": home / ".gradle" / "caches",
        "NPM": home / ".npm",
        "PIP": home / ".cache" / "pip",
        "OLLAMA": home / ".ollama" / "models",
    }
    caches = []
    for cache_id, candidate in candidates.items():
        if time.monotonic() > deadline:
            break
        if not candidate.exists():
            caches.append({"cacheId": cache_id, "state": "ABSENT"})
            continue
        try:
            resolved = _contained(home, candidate)
        except (OSError, PermissionError):
            caches.append({"cacheId": cache_id, "state": "REJECTED_PATH"})
            continue
        total = 0
        files = 0
        newest = 0
        bounded = False
        for directory, names, filenames in os.walk(resolved, followlinks=False):
            if time.monotonic() > deadline or files >= HARD_MAX_ENTRIES:
                bounded = True
                break
            names[:] = [name for name in names if not _secret_name(name)]
            for filename in filenames:
                if time.monotonic() > deadline or files >= HARD_MAX_ENTRIES:
                    bounded = True
                    break
                if _secret_name(filename):
                    continue
                path = Path(directory) / filename
                try:
                    if path.is_symlink():
                        continue
                    info = path.stat()
                except OSError:
                    continue
                total += int(info.st_size)
                newest = max(newest, int(info.st_mtime_ns))
                files += 1
        caches.append({
            "cacheId": cache_id,
            "state": "PRESENT",
            "observedBytes": total,
            "observedFiles": files,
            "newestMtimeNs": newest,
            "bounded": bounded,
            "contentsDisclosed": False,
        })
    return {"caches": caches, "networkUsed": False, "subprocessUsed": False}


def _repo_status(root: Path, action: dict[str, Any], deadline: float) -> dict[str, Any]:
    repositories = []
    entries, skipped, scan_complete = _walk_metadata(root, deadline)
    directories = [root] + [root / item["relativePath"] for item in entries if item["type"] == "directory"]
    for candidate in directories:
        marker = candidate / ".git"
        if not marker.is_dir() or marker.is_symlink():
            continue
        try:
            _contained(root, marker)
            head_text = (marker / "HEAD").read_text(encoding="utf-8", errors="strict").strip()[:512]
        except (OSError, PermissionError, UnicodeError):
            continue
        branch = ""
        head = ""
        if head_text.startswith("ref: refs/heads/"):
            branch = head_text[len("ref: refs/heads/"):]
            ref_file = marker / "refs" / "heads" / branch
            try:
                head = ref_file.read_text(encoding="ascii", errors="strict").strip()
            except (OSError, UnicodeError):
                head = ""
        elif len(head_text) == 40 and all(char in "0123456789abcdef" for char in head_text.lower()):
            head = head_text
        repositories.append({
            "relativePath": "." if candidate == root else candidate.relative_to(root).as_posix(),
            "entryKind": "repository",
            "branch": branch,
            "head": head,
            "dirtyState": "UNKNOWN_NO_GIT_EXEC",
            "remoteDisclosure": "REDACTED_NOT_READ",
        })
    return _chunk(repositories, skipped, action, str(action["rootId"]), scan_complete)


def _file_manifest(root: Path, action: dict[str, Any], deadline: float) -> dict[str, Any]:
    requested = action.get("extensions") or sorted(TEXT_EXTENSIONS)
    extensions = {str(value).lower() for value in requested}
    if not extensions or not extensions.issubset(TEXT_EXTENSIONS):
        raise PermissionError("file_manifest extensions exceed allowlist")
    entries, skipped, scan_complete = _walk_metadata(root, deadline)
    manifest = []
    for item in entries:
        if item["type"] != "file":
            continue
        path = root / item["relativePath"]
        if path.suffix.lower() not in extensions:
            continue
        try:
            resolved = _contained(root, path)
            sha, hash_state = _sha256_file(resolved, MAX_HASH_FILE_BYTES)
        except (OSError, PermissionError):
            continue
        manifest.append({**item, "sha256": sha, "hashState": hash_state})
    return _chunk(manifest, skipped, action, str(action["rootId"]), scan_complete)


class DiagnosticsEngine:
    def __init__(self, roots: dict[str, Path] | None = None):
        self.roots = dict(roots or ROOTS)

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        kind = _validate_action(action)
        started = str(time.time_ns())
        deadline = time.monotonic() + TIME_BUDGET_SECONDS
        root_id = ""
        root = None
        if kind in {"tree_inventory", "repo_status", "file_manifest"}:
            root_id, root = _registered_root(action, self.roots)
        if kind == "capability_snapshot":
            result = _capability_snapshot()
        elif kind == "toolchain_probe":
            result = _toolchain_probe()
        elif kind == "cache_probe":
            result = _cache_probe(deadline)
        elif kind == "tree_inventory":
            entries, skipped, scan_complete = _walk_metadata(root, deadline)
            result = _chunk(entries, skipped, action, root_id, scan_complete)
        elif kind == "repo_status":
            result = _repo_status(root, action, deadline)
        else:
            result = _file_manifest(root, action, deadline)
        body = {
            "schema": RECEIPT_SCHEMA,
            "requestHash": digest(action),
            "diagnosticKind": kind,
            "deviceId": action["deviceId"],
            "packageId": action["packageId"],
            "workerId": action["workerId"],
            "queueDocId": action["queueDocId"],
            "queueRevision": action["queueRevision"],
            "commissionHash": action["commissionHash"],
            "laneId": action["laneId"],
            "sessionId": action["sessionId"],
            "streamId": action["streamId"],
            "chunkIndex": action["chunkIndex"],
            "rootId": root_id,
            "startedAtNs": started,
            "finishedAtNs": str(time.time_ns()),
            "networkUsed": False,
            "writeUsed": False,
            "subprocessUsed": False,
            "buildUsed": False,
            "installUsed": False,
            "uiUsed": False,
            "artifactPostback": {
                "required": True,
                "artifactKind": "phone-diagnostics-chunk.v1",
                "durable": False,
                "state": "PENDING_HOME_CENTER_POSTBACK",
            },
            "result": result,
        }
        return {**body, "receiptHash": digest(body)}


def execute(action: dict[str, Any]) -> dict[str, Any]:
    return DiagnosticsEngine().execute(action)


if __name__ == "__main__":
    raise SystemExit("android_phone_diagnostics is a library; direct execution is disabled")
