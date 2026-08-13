#!/data/data/com.termux/files/usr/bin/python
"""Adam background Spotify radio account plane.

The Android playback body is the exact com.spotify.music MediaController hosted
in a Shizuku UserService. This module owns OAuth PKCE, one private rolling
playlist, deterministic prompt-to-policy compilation, and bounded tail refill.
It never launches Spotify, dispatches generic media keys, or drives the screen.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

CONFIG = Path(os.environ.get("HC_SPOTIFY_RADIO_CONFIG", "~/.config/home-center/spotify-radio.json")).expanduser()
STATE_DIR = Path(os.environ.get("HC_SPOTIFY_RADIO_STATE", "~/.local/state/home-center/spotify-radio")).expanduser()
STATE = STATE_DIR / "state.json"
OAUTH_PENDING = STATE_DIR / "oauth-pending.json"
RECEIPTS = STATE_DIR / "receipts.jsonl"
LATEST = STATE_DIR / "latest.json"
PLAYLIST_NAME = "Adam Radio — Rolling"
SPOTIFY_API = "https://api.spotify.com/v1"
TOKEN_URL = "https://accounts.spotify.com/api/token"
AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SCOPES = [
    "playlist-modify-private",
    "playlist-read-private",
    "user-top-read",
    "user-read-currently-playing",
    "user-read-playback-state",
]
TARGET_PACKAGE = "com.spotify.music"
STATE_URI = "content://com.homecenter.operatoroverlay.state/state"
FORBIDDEN_RECEIPT_KEYS = ("token", "secret", "verifier", "authorization", "clientsecret")
TERM_VOCABULARY = (
    "instrumental", "synth", "electronic", "ambient", "cinematic", "orchestral",
    "metal", "rock", "jazz", "blues", "folk", "acoustic", "techno", "house",
    "trance", "industrial", "dark", "tense", "propulsive", "driving", "calm",
    "dreamy", "energetic", "heavy", "soft", "vocals", "choir", "piano",
    "guitar", "soundtrack", "game", "retro", "space", "melodic", "rhythmic",
)


class RadioError(RuntimeError):
    def __init__(self, code: str, detail: str = "", status: int = 0, retry_after: int = 0):
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code
        self.status = status
        self.retry_after = retry_after


def now_ms() -> int:
    return int(time.time() * 1000)


def mkdirs() -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG.parent, 0o700)
        os.chmod(STATE_DIR, 0o700)
    except OSError:
        pass


def read_json(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, value: Any, mode: int = 0o600) -> None:
    mkdirs()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(tmp, mode)
    tmp.replace(path)
    os.chmod(path, mode)


def redacted(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            lower = str(key).lower().replace("_", "")
            out[key] = "[REDACTED]" if any(part in lower for part in FORBIDDEN_RECEIPT_KEYS) else redacted(item)
        return out
    if isinstance(value, list):
        return [redacted(item) for item in value]
    if isinstance(value, str) and value.lower().startswith("bearer "):
        return "[REDACTED]"
    return value


def emit(stage: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    mkdirs()
    body = redacted({
        "schema": "home-center.spotify-radio-receipt.v1",
        "stage": stage,
        "status": status,
        "detail": detail,
        "atMs": now_ms(),
        "targetPackage": TARGET_PACKAGE,
        "activityLaunchUsed": False,
        "genericMediaKeyUsed": False,
        "screenAutomationUsed": False,
        **extra,
    })
    with RECEIPTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n")
    write_json(LATEST, body)
    print(json.dumps(body, ensure_ascii=False, sort_keys=True), flush=True)
    return body


def default_state() -> dict[str, Any]:
    return {
        "schema": "home-center.spotify-radio-state.v1",
        "playlistName": PLAYLIST_NAME,
        "playlistId": "",
        "snapshotId": "",
        "rolling": False,
        "stopAfterCurrent": False,
        "stopAfterUri": "",
        "minimumTailTracks": 3,
        "refillTracks": 7,
        "recentTrackUris": [],
        "recentArtistIds": [],
        "policy": {},
        "policyHash": "",
        "lastCurrentUri": "",
        "lastRefillAtMs": 0,
        "updatedAtMs": 0,
    }


def load_state() -> dict[str, Any]:
    return {**default_state(), **read_json(STATE, {})}


def save_state(state: dict[str, Any]) -> None:
    state["updatedAtMs"] = now_ms()
    write_json(STATE, state)


def form_request(url: str, fields: dict[str, Any]) -> dict[str, Any]:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    return request_json(request)


def request_json(request: urllib.request.Request) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")[:4000]
        retry = int(error.headers.get("Retry-After", "0") or 0)
        try:
            parsed = json.loads(raw)
            detail = str(parsed.get("error_description") or parsed.get("error", {}).get("message") or parsed.get("error") or raw)
        except (ValueError, AttributeError):
            detail = raw or str(error)
        code = "SPOTIFY_RATE_LIMITED" if error.code == 429 else "SPOTIFY_HTTP_ERROR"
        raise RadioError(code, detail, error.code, retry) from error
    except urllib.error.URLError as error:
        raise RadioError("SPOTIFY_NETWORK_UNAVAILABLE", str(error.reason)) from error


def configure(client_id: str, redirect_uri: str) -> dict[str, Any]:
    config = read_json(CONFIG, {})
    if client_id:
        if not re.fullmatch(r"[A-Za-z0-9]{16,128}", client_id):
            raise RadioError("SPOTIFY_CLIENT_ID_INVALID")
        config["clientId"] = client_id
    if redirect_uri:
        parsed = urllib.parse.urlparse(redirect_uri)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RadioError("SPOTIFY_REDIRECT_URI_INVALID")
        config["redirectUri"] = redirect_uri
    write_json(CONFIG, config)
    return config


def auth_url(client_id: str = "", redirect_uri: str = "") -> dict[str, Any]:
    config = configure(client_id, redirect_uri)
    cid = str(config.get("clientId") or "")
    redirect = str(config.get("redirectUri") or "")
    if not cid or not redirect:
        raise RadioError("SPOTIFY_CONFIGURATION_REQUIRED", "clientId and redirectUri are required")
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(32)
    pending = {
        "state": state,
        "verifier": verifier,
        "clientId": cid,
        "redirectUri": redirect,
        "expiresAtMs": now_ms() + 10 * 60 * 1000,
    }
    write_json(OAUTH_PENDING, pending)
    query = urllib.parse.urlencode({
        "client_id": cid,
        "response_type": "code",
        "redirect_uri": redirect,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    })
    return emit("auth-url", "operator_authorization_required", "Open this URL in an ordinary browser and return the code", authorizationUrl=f"{AUTHORIZE_URL}?{query}", expiresAtMs=pending["expiresAtMs"])


def auth_complete(code: str, state_value: str) -> dict[str, Any]:
    pending = read_json(OAUTH_PENDING, {})
    if not pending or now_ms() > int(pending.get("expiresAtMs") or 0):
        raise RadioError("SPOTIFY_AUTH_STATE_EXPIRED")
    if not secrets.compare_digest(str(pending.get("state") or ""), state_value):
        raise RadioError("SPOTIFY_AUTH_STATE_MISMATCH")
    if not code or len(code) > 4096:
        raise RadioError("SPOTIFY_AUTH_CODE_INVALID")
    token = form_request(TOKEN_URL, {
        "client_id": pending["clientId"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": pending["redirectUri"],
        "code_verifier": pending["verifier"],
    })
    if not token.get("access_token") or not token.get("refresh_token"):
        raise RadioError("SPOTIFY_TOKEN_RESPONSE_INVALID")
    config = read_json(CONFIG, {})
    config.update({
        "accessToken": token["access_token"],
        "refreshToken": token["refresh_token"],
        "expiresAtMs": now_ms() + int(token.get("expires_in") or 3600) * 1000,
        "scopes": str(token.get("scope") or "").split(),
        "tokenType": str(token.get("token_type") or "Bearer"),
    })
    write_json(CONFIG, config)
    try:
        OAUTH_PENDING.unlink()
    except OSError:
        pass
    return emit("auth-complete", "authorized", "Spotify PKCE authorization stored in owner-private local state", scopes=config["scopes"], tokensExposed=False)


class SpotifyClient:
    def __init__(self) -> None:
        self.config = read_json(CONFIG, {})

    def access_token(self, force_refresh: bool = False) -> str:
        token = str(self.config.get("accessToken") or "")
        expiry = int(self.config.get("expiresAtMs") or 0)
        if token and not force_refresh and expiry > now_ms() + 60_000:
            return token
        refresh = str(self.config.get("refreshToken") or "")
        client_id = str(self.config.get("clientId") or "")
        if not refresh or not client_id:
            raise RadioError("SPOTIFY_AUTHORIZATION_REQUIRED")
        result = form_request(TOKEN_URL, {"client_id": client_id, "grant_type": "refresh_token", "refresh_token": refresh})
        if not result.get("access_token"):
            raise RadioError("SPOTIFY_REFRESH_FAILED")
        self.config["accessToken"] = result["access_token"]
        self.config["refreshToken"] = result.get("refresh_token", refresh)
        self.config["expiresAtMs"] = now_ms() + int(result.get("expires_in") or 3600) * 1000
        if result.get("scope"):
            self.config["scopes"] = str(result["scope"]).split()
        write_json(CONFIG, self.config)
        return str(self.config["accessToken"])

    def api(self, method: str, path: str, params: dict[str, Any] | None = None, body: Any = None, retry_auth: bool = True) -> dict[str, Any]:
        url = path if path.startswith("https://") else SPOTIFY_API + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        headers = {"Authorization": "Bearer " + self.access_token(), "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            return request_json(request)
        except RadioError as error:
            if retry_auth and error.status == 401:
                self.access_token(force_refresh=True)
                return self.api(method, path, params, body, retry_auth=False)
            raise

    def me(self) -> dict[str, Any]:
        return self.api("GET", "/me")

    def ensure_playlist(self, state: dict[str, Any]) -> dict[str, Any]:
        me = self.me()
        owner_id = str(me.get("id") or "")
        if not owner_id:
            raise RadioError("SPOTIFY_PROFILE_INVALID")
        existing_id = str(state.get("playlistId") or "")
        if existing_id:
            try:
                playlist = self.api("GET", f"/playlists/{existing_id}", {"fields": "id,name,snapshot_id,owner(id),items(total)"})
                if playlist.get("name") == PLAYLIST_NAME and str(playlist.get("owner", {}).get("id") or "") == owner_id:
                    state["snapshotId"] = str(playlist.get("snapshot_id") or state.get("snapshotId") or "")
                    return playlist
            except RadioError as error:
                if error.status not in {403, 404}:
                    raise
        offset = 0
        while offset <= 10_000:
            page = self.api("GET", "/me/playlists", {"limit": 50, "offset": offset})
            items = page.get("items") or []
            for playlist in items:
                if playlist.get("name") == PLAYLIST_NAME and str(playlist.get("owner", {}).get("id") or "") == owner_id:
                    state["playlistId"] = str(playlist.get("id") or "")
                    state["snapshotId"] = str(playlist.get("snapshot_id") or "")
                    save_state(state)
                    return playlist
            if not page.get("next") or not items:
                break
            offset += len(items)
        playlist = self.api("POST", "/me/playlists", body={
            "name": PLAYLIST_NAME,
            "public": False,
            "collaborative": False,
            "description": "Private rolling playlist controlled by Drew through Adam and Home Center.",
        })
        state["playlistId"] = str(playlist.get("id") or "")
        state["snapshotId"] = str(playlist.get("snapshot_id") or "")
        if not state["playlistId"]:
            raise RadioError("SPOTIFY_PLAYLIST_CREATE_UNVERIFIED")
        save_state(state)
        return playlist

    def playlist_items(self, playlist_id: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = self.api("GET", f"/playlists/{playlist_id}/items", {"limit": 50, "offset": offset, "additional_types": "track"})
            rows = page.get("items") or []
            for row in rows:
                track = row.get("item") or {}
                uri = str(track.get("uri") or "")
                if uri.startswith("spotify:track:"):
                    result.append(normalize_track(track))
            if not page.get("next") or not rows:
                break
            offset += len(rows)
        return result

    def replace_items(self, playlist_id: str, uris: list[str]) -> str:
        first, rest = uris[:100], uris[100:]
        result = self.api("PUT", f"/playlists/{playlist_id}/items", body={"uris": first})
        snapshot = str(result.get("snapshot_id") or "")
        for start in range(0, len(rest), 100):
            result = self.api("POST", f"/playlists/{playlist_id}/items", body={"uris": rest[start:start + 100]})
            snapshot = str(result.get("snapshot_id") or snapshot)
        if not snapshot:
            raise RadioError("SPOTIFY_PLAYLIST_MUTATION_UNVERIFIED")
        return snapshot

    def add_items(self, playlist_id: str, uris: list[str]) -> str:
        snapshot = ""
        for start in range(0, len(uris), 100):
            result = self.api("POST", f"/playlists/{playlist_id}/items", body={"uris": uris[start:start + 100]})
            snapshot = str(result.get("snapshot_id") or snapshot)
        if uris and not snapshot:
            raise RadioError("SPOTIFY_PLAYLIST_MUTATION_UNVERIFIED")
        return snapshot

    def search_tracks(self, query: str) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        page = self.api("GET", "/search", {"q": query[:240], "type": "track", "limit": 10})
        return [normalize_track(track) for track in (page.get("tracks", {}).get("items") or []) if str(track.get("uri") or "").startswith("spotify:track:")]

    def top_tracks(self) -> list[dict[str, Any]]:
        page = self.api("GET", "/me/top/tracks", {"time_range": "medium_term", "limit": 50, "offset": 0})
        return [normalize_track(track) for track in (page.get("items") or []) if str(track.get("uri") or "").startswith("spotify:track:")]

    def currently_playing(self) -> dict[str, Any]:
        return self.api("GET", "/me/player/currently-playing", {"additional_types": "track"})


def normalize_track(track: dict[str, Any]) -> dict[str, Any]:
    artists = track.get("artists") or []
    return {
        "uri": str(track.get("uri") or ""),
        "id": str(track.get("id") or ""),
        "name": str(track.get("name") or ""),
        "durationMs": int(track.get("duration_ms") or 0),
        "artistIds": [str(a.get("id") or a.get("name") or "") for a in artists if a],
        "artistNames": [str(a.get("name") or "") for a in artists if a],
    }


def policy_hash(policy: dict[str, Any]) -> str:
    body = json.dumps(policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def compile_prompt(text: str, prior: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = " ".join(str(text or "").strip().split())
    if not raw:
        raise RadioError("SPOTIFY_PROMPT_REQUIRED")
    lower = raw.lower()
    exact = re.sub(r"[^a-z0-9 ]+", " ", lower).strip()
    transport = {
        "play": "play", "resume": "play", "pause": "pause", "next": "next",
        "skip": "next", "previous": "previous", "back": "previous",
        "stop": "stop", "status": "status", "what is playing": "status",
    }
    if exact in transport:
        return {"schema": "spotify.plan.v1", "kind": "transport", "action": transport[exact], "argument": "", "prompt": raw}
    if "stop after" in lower and ("track" in lower or "song" in lower or "this" in lower):
        return {"schema": "spotify.plan.v1", "kind": "stop_after_current", "prompt": raw}
    if any(phrase in lower for phrase in ("stop rolling", "rolling off", "do not refill")):
        return {"schema": "spotify.plan.v1", "kind": "rolling", "enabled": False, "prompt": raw}
    if any(phrase in lower for phrase in ("keep it rolling", "keep rolling", "rolling on", "continue rolling")):
        return {"schema": "spotify.plan.v1", "kind": "rolling", "enabled": True, "prompt": raw}

    prior_policy = dict(prior or {})
    avoid = list(prior_policy.get("avoid") or [])
    for match in re.finditer(r"(?:less|fewer|no|avoid|without)\s+([a-z0-9_-]+(?:\s+[a-z0-9_-]+){0,2})", lower):
        phrase = match.group(1).strip()
        if phrase and phrase not in avoid:
            avoid.append(phrase)
    positive = [term for term in TERM_VOCABULARY if re.search(rf"\b{re.escape(term)}\b", lower) and not any(term in item for item in avoid)]
    quoted = [match.strip() for match in re.findall(r"[\"']([^\"']{2,80})[\"']", raw)]
    stripped = re.sub(r"(?:less|fewer|no|avoid|without)\s+[a-z0-9_-]+(?:\s+[a-z0-9_-]+){0,2}", " ", lower)
    stripped = re.sub(r"\b(?:make|create|build|start|playlist|radio|keep|rolling|more|please|me|a|an|the|with|and)\b", " ", stripped)
    stripped = " ".join(stripped.split())[:160]
    queries: list[str] = []
    for value in quoted + ([stripped] if stripped else []) + positive:
        clean = " ".join(value.split())
        if clean and clean not in queries:
            queries.append(clean)
    if not queries:
        queries = list(prior_policy.get("queries") or ["instrumental electronic", "cinematic driving"])

    minutes = int(prior_policy.get("targetMinutes") or 90)
    hour = re.search(r"(\d+(?:\.\d+)?)\s*hours?", lower)
    minute = re.search(r"(\d+)\s*(?:minutes?|mins?)", lower)
    if hour:
        minutes = max(15, min(360, round(float(hour.group(1)) * 60)))
    elif minute:
        minutes = max(15, min(360, int(minute.group(1))))

    policy = {
        "queries": queries[:8],
        "avoid": avoid[:20],
        "targetMinutes": minutes,
        "artistRepeatWindow": int(prior_policy.get("artistRepeatWindow") or 8),
        "preserveCurrentTrack": not any(phrase in lower for phrase in ("skip current", "replace current", "change this song")),
    }
    policy["policyHash"] = policy_hash(policy)
    mode = "create" if any(word in lower for word in ("make ", "create ", "build ", "new playlist")) else "revise"
    return {
        "schema": "spotify.plan.v1",
        "kind": "playlist",
        "mode": mode,
        "startPlayback": any(phrase in lower for phrase in ("start", "play it", "play this", "make me", "create me")),
        "rolling": any(phrase in lower for phrase in ("keep it rolling", "keep rolling", "rolling")) or bool(prior_policy.get("rolling")),
        "policy": policy,
        "prompt": raw,
    }


def candidate_text(track: dict[str, Any]) -> str:
    return (track.get("name", "") + " " + " ".join(track.get("artistNames") or [])).lower()


def choose_tracks(client: SpotifyClient, policy: dict[str, Any], state: dict[str, Any], excluded: Iterable[str], count: int) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for query in list(policy.get("queries") or [])[:8]:
        for track in client.search_tracks(str(query)):
            if track["uri"]:
                candidates.setdefault(track["uri"], track)
    for track in client.top_tracks():
        if track["uri"]:
            candidates.setdefault(track["uri"], track)
    excluded_set = set(excluded) | set(state.get("recentTrackUris") or [])
    avoid = [str(value).lower() for value in (policy.get("avoid") or [])]
    recent_artists = list(state.get("recentArtistIds") or [])
    window = max(1, int(policy.get("artistRepeatWindow") or 8))
    seed = str(policy.get("policyHash") or policy_hash(policy))
    ordered = sorted(candidates.values(), key=lambda item: hashlib.sha256((seed + "\n" + item["uri"]).encode()).hexdigest())
    chosen: list[dict[str, Any]] = []
    artist_window = recent_artists[-window:]
    for track in ordered:
        if track["uri"] in excluded_set:
            continue
        text = candidate_text(track)
        if any(term and term in text for term in avoid):
            continue
        primary = (track.get("artistIds") or [""])[0]
        if primary and primary in artist_window:
            continue
        chosen.append(track)
        excluded_set.add(track["uri"])
        if primary:
            artist_window.append(primary)
            artist_window = artist_window[-window:]
        if len(chosen) >= count:
            break
    return chosen


def target_track_count(policy: dict[str, Any], tracks: list[dict[str, Any]]) -> int:
    minutes = max(15, min(360, int(policy.get("targetMinutes") or 90)))
    durations = [int(track.get("durationMs") or 0) for track in tracks if int(track.get("durationMs") or 0) > 0]
    average = sum(durations) / len(durations) if durations else 240_000
    return max(8, min(80, round(minutes * 60_000 / average)))


def find_rish() -> str:
    explicit = os.environ.get("HC_RISH", "").strip()
    candidates = [explicit, shutil.which("rish") or "", str(Path("~/.local/bin/rish").expanduser()), str(Path("~/rish").expanduser())]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise RadioError("SHIZUKU_RISH_UNAVAILABLE")


def rish(command: str, timeout: int = 20) -> str:
    env = dict(os.environ)
    env["RISH_PRESERVE_ENV"] = "0"
    result = subprocess.run([find_rish(), "-c", command], text=True, capture_output=True, timeout=timeout, env=env)
    if result.returncode != 0:
        raise RadioError("SHIZUKU_RISH_FAILED", (result.stderr or result.stdout)[-2000:])
    return result.stdout.strip()


def parse_provider_row(raw: str) -> dict[str, str]:
    body = raw.split("Row:", 1)[-1]
    values: dict[str, str] = {}
    for part in re.split(r",\s+(?=[a-z_]+=)", body):
        if "=" in part:
            key, value = part.split("=", 1)
            values[key.strip().split()[-1]] = value.strip()
    return values


def transport(action: str, argument: str = "", timeout: int = 15) -> dict[str, Any]:
    allowed = {"probe", "status", "play", "pause", "play_pause", "next", "previous", "stop", "play_context"}
    if action not in allowed:
        raise RadioError("SPOTIFY_ACTION_UNSUPPORTED", action)
    request_id = now_ms()
    argument_b64 = base64.urlsafe_b64encode(argument.encode("utf-8")).decode().rstrip("=")
    command = (
        "content call --uri " + shlex.quote(STATE_URI)
        + " --method spotify_control --arg " + shlex.quote(action)
        + " --extra string:argument_b64:" + shlex.quote(argument_b64)
        + " --extra long:request_id:" + str(request_id)
    )
    accepted = rish(command, timeout=20)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        row = parse_provider_row(rish("content query --uri " + shlex.quote(STATE_URI), timeout=15))
        if int(row.get("spotify_request_id") or 0) == request_id:
            encoded = row.get("spotify_receipt_b64") or ""
            try:
                receipt = json.loads(base64.b64decode(encoded).decode("utf-8"))
            except (ValueError, UnicodeError) as error:
                raise RadioError("SPOTIFY_RECEIPT_INVALID", str(error)) from error
            receipt["providerAccepted"] = bool(accepted)
            receipt["requestId"] = request_id
            return receipt
        time.sleep(0.2)
    raise RadioError("SPOTIFY_RECEIPT_TIMEOUT", f"requestId={request_id}")


def current_track(current: dict[str, Any]) -> dict[str, Any]:
    item = current.get("item") or {}
    return normalize_track(item) if str(item.get("uri") or "").startswith("spotify:track:") else normalize_track({})


def create_or_revise(client: SpotifyClient, state: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    playlist = client.ensure_playlist(state)
    playlist_id = str(state["playlistId"])
    existing = client.playlist_items(playlist_id)
    current = client.currently_playing()
    current_item = current_track(current)
    active_context = str(current.get("context", {}).get("uri") or "") == f"spotify:playlist:{playlist_id}"
    current_index = next((index for index, item in enumerate(existing) if item["uri"] == current_item["uri"]), -1)

    policy = dict(plan["policy"])
    preview = choose_tracks(client, policy, state, [item["uri"] for item in existing], 80)
    desired = target_track_count(policy, preview)
    candidates = preview[:desired]
    if len(candidates) < min(5, desired):
        raise RadioError("SPOTIFY_CATALOG_CANDIDATES_INSUFFICIENT", f"found={len(candidates)}")

    preserve = bool(policy.get("preserveCurrentTrack")) and active_context and current_index >= 0
    prefix = existing[:current_index + 1] if preserve else []
    final = prefix + candidates
    snapshot = client.replace_items(playlist_id, [item["uri"] for item in final])
    state.update({
        "snapshotId": snapshot,
        "policy": policy,
        "policyHash": policy["policyHash"],
        "rolling": bool(plan.get("rolling")),
        "stopAfterCurrent": False,
        "stopAfterUri": "",
        "recentTrackUris": ([item["uri"] for item in final][-40:]),
        "recentArtistIds": (sum([item.get("artistIds") or [] for item in final], [])[-40:]),
    })
    save_state(state)
    playback = None
    if plan.get("startPlayback"):
        playback = transport("play_context", f"spotify:playlist:{playlist_id}")
    return {
        "playlistId": playlist_id,
        "playlistName": playlist.get("name") or PLAYLIST_NAME,
        "snapshotId": snapshot,
        "itemCount": len(final),
        "preservedPrefixCount": len(prefix),
        "rolling": state["rolling"],
        "policyHash": state["policyHash"],
        "playbackReceipt": playback,
    }


def ensure_once(client: SpotifyClient, state: dict[str, Any]) -> dict[str, Any]:
    if not state.get("playlistId"):
        client.ensure_playlist(state)
    playlist_id = str(state["playlistId"])
    current = client.currently_playing()
    item = current_track(current)
    context_uri = str(current.get("context", {}).get("uri") or "")

    if state.get("stopAfterCurrent"):
        anchor = str(state.get("stopAfterUri") or "")
        if anchor and item["uri"] and item["uri"] != anchor:
            pause = transport("pause")
            state["stopAfterCurrent"] = False
            state["stopAfterUri"] = ""
            state["rolling"] = False
            save_state(state)
            return {"state": "stopped_after_current", "pauseReceipt": pause}

    if not state.get("rolling"):
        return {"state": "rolling_disabled", "playlistId": playlist_id}
    if context_uri != f"spotify:playlist:{playlist_id}":
        return {"state": "playlist_not_active", "playlistId": playlist_id, "contextUri": context_uri}

    items = client.playlist_items(playlist_id)
    current_index = next((index for index, value in enumerate(items) if value["uri"] == item["uri"]), -1)
    if current_index < 0:
        return {"state": "current_item_not_in_playlist", "playlistId": playlist_id}
    remaining = len(items) - current_index - 1
    threshold = max(1, int(state.get("minimumTailTracks") or 3))
    if remaining > threshold:
        state["lastCurrentUri"] = item["uri"]
        save_state(state)
        return {"state": "tail_healthy", "remaining": remaining, "playlistId": playlist_id}

    count = max(1, min(20, int(state.get("refillTracks") or 7)))
    policy = dict(state.get("policy") or {})
    if not policy:
        raise RadioError("SPOTIFY_RADIO_POLICY_REQUIRED")
    chosen = choose_tracks(client, policy, state, [value["uri"] for value in items], count)
    if not chosen:
        raise RadioError("SPOTIFY_REFILL_CANDIDATES_EXHAUSTED")
    snapshot = client.add_items(playlist_id, [value["uri"] for value in chosen])
    state["snapshotId"] = snapshot
    state["lastRefillAtMs"] = now_ms()
    state["lastCurrentUri"] = item["uri"]
    state["recentTrackUris"] = (list(state.get("recentTrackUris") or []) + [value["uri"] for value in chosen])[-40:]
    state["recentArtistIds"] = (list(state.get("recentArtistIds") or []) + sum([value.get("artistIds") or [] for value in chosen], []))[-40:]
    save_state(state)
    return {"state": "refilled", "added": len(chosen), "remainingBefore": remaining, "snapshotId": snapshot, "playlistId": playlist_id}


def handle_prompt(text: str) -> dict[str, Any]:
    state = load_state()
    plan = compile_prompt(text, state.get("policy") or {})
    if plan["kind"] == "transport":
        return emit("prompt", "completed", "Typed Spotify transport command completed", plan=plan, transportReceipt=transport(plan["action"], plan.get("argument", "")))
    client = SpotifyClient()
    if plan["kind"] == "rolling":
        state["rolling"] = bool(plan["enabled"])
        if not state["rolling"]:
            state["stopAfterCurrent"] = False
            state["stopAfterUri"] = ""
        save_state(state)
        return emit("prompt", "completed", "Rolling state changed", plan=plan, rolling=state["rolling"])
    if plan["kind"] == "stop_after_current":
        current = current_track(client.currently_playing())
        if not current["uri"]:
            raise RadioError("SPOTIFY_CURRENT_TRACK_UNAVAILABLE")
        state["stopAfterCurrent"] = True
        state["stopAfterUri"] = current["uri"]
        state["rolling"] = False
        save_state(state)
        return emit("prompt", "completed", "Will pause after the current Spotify track changes", plan=plan, anchorUri=current["uri"])
    result = create_or_revise(client, state, plan)
    return emit("prompt", "completed", "Spotify rolling playlist updated", plan=plan, result=result)


def doctor() -> dict[str, Any]:
    config = read_json(CONFIG, {})
    state = load_state()
    auth_ready = bool(config.get("clientId") and config.get("redirectUri") and config.get("refreshToken"))
    rish_ready = False
    try:
        find_rish()
        rish_ready = True
    except RadioError:
        pass
    return emit(
        "doctor",
        "ready" if auth_ready and rish_ready else "configuration_required",
        "Spotify radio readiness inspected without provider calls",
        authConfigured=auth_ready,
        shizukuTransportConfigured=rish_ready,
        playlistId=state.get("playlistId") or "",
        rolling=bool(state.get("rolling")),
        policyConfigured=bool(state.get("policyHash")),
        tokensExposed=False,
    )


def daemon(interval: int) -> int:
    interval = max(10, min(300, interval))
    last_signature = ""
    while True:
        try:
            result = ensure_once(SpotifyClient(), load_state())
            signature = json.dumps(result, sort_keys=True)
            if signature != last_signature or result.get("state") in {"refilled", "stopped_after_current"}:
                emit("daemon", "healthy", "Rolling check complete", result=result)
                last_signature = signature
        except KeyboardInterrupt:
            return 0
        except RadioError as error:
            signature = f"{error.code}:{error.detail}"
            if signature != last_signature:
                emit("daemon", "degraded", error.detail, error=error.code, providerStatus=error.status, retryAfterSeconds=error.retry_after)
                last_signature = signature
            if error.retry_after:
                time.sleep(min(300, max(interval, error.retry_after)))
                continue
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(prog="spotify-radio")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    auth = sub.add_parser("auth-url")
    auth.add_argument("--client-id", default="")
    auth.add_argument("--redirect-uri", default="")
    complete = sub.add_parser("auth-complete")
    complete.add_argument("--code", required=True)
    complete.add_argument("--state", required=True)
    prompt = sub.add_parser("prompt")
    prompt.add_argument("text", nargs="+")
    transport_parser = sub.add_parser("transport")
    transport_parser.add_argument("action", choices=["probe", "status", "play", "pause", "play_pause", "next", "previous", "stop", "play_context"])
    transport_parser.add_argument("argument", nargs="?", default="")
    sub.add_parser("ensure")
    run = sub.add_parser("daemon")
    run.add_argument("--interval", type=int, default=20)
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            doctor()
        elif args.command == "auth-url":
            auth_url(args.client_id, args.redirect_uri)
        elif args.command == "auth-complete":
            auth_complete(args.code, args.state)
        elif args.command == "prompt":
            handle_prompt(" ".join(args.text))
        elif args.command == "transport":
            emit("transport", "completed", "Typed Spotify background command completed", transportReceipt=transport(args.action, args.argument))
        elif args.command == "ensure":
            emit("ensure", "completed", "Rolling check complete", result=ensure_once(SpotifyClient(), load_state()))
        else:
            return daemon(args.interval)
        return 0
    except RadioError as error:
        emit("error", "blocked", error.detail, error=error.code, providerStatus=error.status, retryAfterSeconds=error.retry_after)
        return 2
    except Exception as error:
        emit("error", "failed", f"{type(error).__name__}: {error}", error="SPOTIFY_RADIO_INTERNAL_ERROR")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
