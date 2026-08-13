#!/usr/bin/env python3
"""Small authenticated Home Center MCP client for Termux/local daemons.

The pairing file remains the source of credentials. This module never prints tokens.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MCP_URL = os.environ.get(
    "HOME_CENTER_MCP_URL",
    "https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp",
)
DEFAULT_GATEWAY = os.environ.get(
    "HOME_CENTER_GATEWAY_BASE",
    "https://us-central1-home-center-dclar.cloudfunctions.net",
)
DEFAULT_TOKEN_CONFIG = Path(
    os.environ.get(
        "HOME_CENTER_CODEX_CONFIG",
        "~/.config/home-center/codex-hub.json",
    )
).expanduser()


class HomeCenterError(RuntimeError):
    pass


def _json(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HomeCenterError(f"{label} did not return JSON: {text[:500]}") from exc
    if not isinstance(value, dict):
        raise HomeCenterError(f"{label} returned a non-object JSON value")
    return value


def _mcp_json(text: str, label: str) -> dict[str, Any]:
    data = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
    return _json("\n".join(data) if data else text, label)


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise HomeCenterError(f"Home Center HTTP {exc.code}: {body[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HomeCenterError(f"Home Center transport failed: {exc}") from exc


def _save_token_config(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def bearer_token(config_path: Path = DEFAULT_TOKEN_CONFIG) -> str:
    direct = os.environ.get("HOME_CENTER_MCP_BEARER_TOKEN", "").strip()
    if direct:
        return direct

    refresh_from_env = os.environ.get("HOME_CENTER_MCP_REFRESH_TOKEN", "").strip()
    config: dict[str, Any] = {}
    if config_path.is_file():
        config = _json(config_path.read_text(encoding="utf-8"), str(config_path))

    access = str(config.get("accessToken") or "").strip()
    if access and int(config.get("expiresAtMs") or 0) > int(time.time() * 1000) + 60_000:
        return access

    refresh = refresh_from_env or str(config.get("refreshToken") or "").strip()
    if not refresh:
        raise HomeCenterError(
            "Home Center pairing unavailable: no bearer token, refresh token, or usable "
            f"{config_path}"
        )

    gateway = str(config.get("gatewayBase") or DEFAULT_GATEWAY).rstrip("/")
    status, text = _post_json(
        gateway + "/termuxTokenRefresh",
        {"refreshToken": refresh},
        {},
        timeout=30,
    )
    result = _json(text, "termuxTokenRefresh")
    token = str(result.get("access_token") or "").strip()
    if status != 200 or not token:
        raise HomeCenterError("Home Center token refresh returned no access token")

    if config_path.is_file() or not refresh_from_env:
        next_value = {
            **config,
            "accessToken": token,
            "refreshToken": result.get("refresh_token") or refresh,
            "tokenType": result.get("token_type") or "Bearer",
            "expiresAtMs": int(time.time() * 1000)
            + int(result.get("expires_in") or 3300) * 1000,
            "refreshedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _save_token_config(config_path, next_value)
    return token


class HomeCenterMcp:
    def __init__(
        self,
        url: str = DEFAULT_MCP_URL,
        token_config: Path = DEFAULT_TOKEN_CONFIG,
        timeout: int = 45,
    ) -> None:
        self.url = url
        self.token_config = token_config
        self.timeout = timeout
        self._token: str | None = None
        self._initialized = False
        self._counter = 0

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._token:
            self._token = bearer_token(self.token_config)
        self._counter += 1
        payload = {
            "jsonrpc": "2.0",
            "id": f"vlad-jars-{self._counter}",
            "method": method,
            "params": params,
        }
        _, text = _post_json(
            self.url,
            payload,
            {
                "Authorization": "Bearer " + self._token,
                "Accept": "application/json, text/event-stream",
            },
            timeout=self.timeout,
        )
        result = _mcp_json(text, method)
        if result.get("error"):
            raise HomeCenterError(f"Home Center MCP error: {result['error']}")
        return result

    def initialize(self) -> None:
        if self._initialized:
            return
        self._request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "vlad-judgment-jars", "version": "2"},
            },
        )
        self._initialized = True

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        response = self._request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        content = response.get("result", {}).get("content", [])
        text = next(
            (
                str(item.get("text") or "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ),
            "",
        )
        if not text:
            raise HomeCenterError(f"{name} returned no text payload")
        value = _json(text, name)
        if value.get("ok") is False:
            raise HomeCenterError(
                f"{name} failed: {value.get('error') or value.get('detail') or 'unknown'}"
            )
        return value

    def drive_operation(self, operation: str, args: dict[str, Any]) -> dict[str, Any]:
        envelope = self.call_tool(
            "drive_operation",
            {"operation": operation, "args": args},
        )
        # Current Home Center may return either the operation result directly or
        # a stable dispatcher envelope containing result.
        result = envelope.get("result")
        return result if isinstance(result, dict) else envelope

    def read_document(self, file_id: str, name: str = "") -> str:
        value = self.drive_operation(
            "docs.read",
            {"fileId": file_id, "name": name},
        )
        content = value.get("content")
        if not isinstance(content, str) or not content.strip():
            raise HomeCenterError(f"docs.read returned no content for {file_id}")
        return content

    def search_drive(self, query: str, page_size: int = 10) -> list[dict[str, Any]]:
        value = self.drive_operation(
            "drive.search",
            {"query": query, "pageSize": max(1, min(int(page_size), 10))},
        )
        files = value.get("files") or []
        return [item for item in files if isinstance(item, dict)]

    def read_sheet(
        self,
        spreadsheet_id: str,
        cell_range: str = "A1:ZZ1000",
    ) -> dict[str, Any]:
        return self.drive_operation(
            "sheets.read",
            {"spreadsheetId": spreadsheet_id, "range": cell_range},
        )
