"""Outbound-only THECAULDRON inference worker for VenusOS.

This process polls Helm Center over HTTPS and calls an Ollama OpenAI-compatible API
on loopback. It opens no listener and has no arbitrary command execution surface.
"""

from __future__ import annotations

import ipaddress
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CONTRACT_VERSION = "home-center.venus-cauldron-relay.v1"
WORKER_ID = os.environ.get("HOME_CENTER_VENUS_WORKER_ID", "cauldron-llm-01")
MAX_RESPONSE_BYTES = 256 * 1024


def checked_https_origin(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("HOME_CENTER_VENUS_RELAY_ORIGIN must be one HTTPS origin.")
    return f"https://{parsed.netloc}" + parsed.path.rstrip("/")


def checked_ollama_origin(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("OLLAMA_BASE_URL must be one loopback HTTP origin.")
    try:
        loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        loopback = parsed.hostname.lower() == "localhost"
    if not loopback:
        raise ValueError("OLLAMA_BASE_URL must remain loopback-only.")
    return f"http://{parsed.netloc}" + parsed.path.rstrip("/")


def safe_models(value: str) -> list[str]:
    models = []
    for item in value.split(","):
        item = item.strip()
        if item and 2 <= len(item) <= 120 and all(character.isalnum() or character in "_.:-" for character in item):
            if item not in models:
                models.append(item)
    if not models:
        raise ValueError("HOME_CENTER_VENUS_MODELS requires an explicit model allowlist.")
    return models


def load_text(root: pathlib.Path, environment: str, filename: str) -> str:
    value = os.environ.get(environment, "").strip()
    if value:
        return value
    target = root / filename
    if target.is_file():
        return target.read_text(encoding="utf-8").strip()
    raise ValueError(f"{environment} or {filename} is required.")


def request_json(method: str, url: str, payload: dict | None = None, headers: dict | None = None, timeout: int = 60) -> dict:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, method=method, data=body, headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise RuntimeError("Remote response exceeded the worker byte limit.")
        return json.loads(data.decode("utf-8")) if data else {}


class RelayClient:
    def __init__(self, origin: str, token: str, models: list[str]):
        self.origin = checked_https_origin(origin)
        if not token:
            raise ValueError("Helm Center worker token is required.")
        self.headers = {"Authorization": f"Bearer {token}", "X-Home-Center-Worker": WORKER_ID}
        self.models = models

    def lease(self) -> dict:
        return request_json("POST", self.origin + "/worker/v1/lease", {"contractVersion": CONTRACT_VERSION, "workerId": WORKER_ID, "models": self.models}, self.headers, 30)

    def finish(self, ticket_id: str, action: str, payload: dict) -> dict:
        if action not in ("complete", "fail") or not ticket_id.startswith("vcr-"):
            raise ValueError("Relay completion path escaped its allowlist.")
        safe_ticket = urllib.parse.quote(ticket_id, safe="._-:")
        return request_json("POST", f"{self.origin}/worker/v1/tickets/{safe_ticket}/{action}", payload, self.headers, 30)


def call_ollama(origin: str, request: dict, models: list[str]) -> dict:
    if request.get("contractVersion") != CONTRACT_VERSION or request.get("provider") != "local_cauldron" or request.get("engine") != "ollama":
        raise RuntimeError("Ticket identity does not match the Venus relay worker.")
    model = request.get("model", "")
    if model not in models:
        raise RuntimeError("Ticket requested a model outside the local allowlist.")
    payload = {key: request[key] for key in ("model", "messages", "temperature", "max_tokens")}
    payload["stream"] = False
    response = request_json("POST", origin + "/v1/chat/completions", payload, timeout=50)
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise RuntimeError("Ollama returned an invalid choices envelope.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("Ollama returned no assistant string content.")
    return {"model": model, "content": content, "finishReason": choices[0].get("finish_reason") or "stop", "usage": response.get("usage") or {}}


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent
    origin = checked_https_origin(load_text(root, "HOME_CENTER_VENUS_RELAY_ORIGIN", ".worker-origin"))
    ollama = checked_ollama_origin(os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    models = safe_models(load_text(root, "HOME_CENTER_VENUS_MODELS", ".worker-models"))
    token = load_text(root, "HOME_CENTER_VENUS_WORKER_TOKEN", ".worker-token")
    if "--verify" in sys.argv:
        print(json.dumps({"ok": True, "workerId": WORKER_ID, "models": models, "ollama": ollama, "network": "outbound_https_only"}))
        return 0
    client = RelayClient(origin, token, models)
    once = "--once" in sys.argv
    deadline = time.monotonic() + 120 if once else None
    while True:
        try:
            leased = client.lease()
            ticket = leased.get("ticket")
            if ticket:
                try:
                    result = call_ollama(ollama, ticket["request"], models)
                    print(json.dumps(client.finish(ticket["ticketId"], "complete", result)))
                    if once:
                        return 0
                except Exception as error:  # fail receipt is bounded and contains no request content
                    client.finish(ticket["ticketId"], "fail", {"code": "ollama_failed", "detail": str(error)[:500]})
                    if once:
                        raise
            elif once and deadline and time.monotonic() >= deadline:
                raise RuntimeError("No Venus relay ticket arrived within two minutes.")
            else:
                time.sleep(max(1, min(15, int(leased.get("pollAfterSeconds", 2)))))
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise
            if once and deadline and time.monotonic() >= deadline:
                raise
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())

