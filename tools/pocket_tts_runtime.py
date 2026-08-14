#!/usr/bin/env python3
"""Pocket TTS: local, offline, restart-legible speech orchestration.

The runtime deliberately keeps synthesis, playback, cache, and control as distinct
organs. It contains no cloud provider and never executes a caller-supplied command.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
import wave
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol


SCHEMA = "home-center.pocket-tts-runtime.v1"
REGISTRY_SCHEMA = "home-center.pocket-tts-voice-registry.v1"
ALLOWED_ENGINES = {"piper", "kokoro-onnx"}
ALLOWED_ROLES = {"utility", "fallback", "companion", "narration"}
MAX_TEXT_CHARS = 32_000
DEFAULT_CHUNK_CHARS = 260
QUEUE_END = object()


class PocketTtsError(RuntimeError):
    pass


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        raise PocketTtsError("text must be a string")
    value = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[\t\f\v ]+", " ", value)
    value = re.sub(r" *\n+ *", " ", value).strip()
    if not value:
        raise PocketTtsError("text is empty after normalization")
    if len(value) > MAX_TEXT_CHARS:
        raise PocketTtsError(f"text exceeds {MAX_TEXT_CHARS} characters")
    return value


def chunk_text(normalized: str, max_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    if normalized != normalize_text(normalized):
        raise PocketTtsError("chunk_text requires normalized text")
    limit = max(80, min(800, int(max_chars)))
    chunks: list[str] = []
    offset = 0
    while offset < len(normalized):
        end = min(len(normalized), offset + limit)
        if end < len(normalized):
            window = normalized[offset:end]
            candidates = [match.end() for match in re.finditer(r"[.!?;:,]\s+|\s+", window)]
            eligible = [candidate for candidate in candidates if candidate >= int(limit * 0.45)]
            if eligible:
                end = offset + eligible[-1]
        chunks.append(normalized[offset:end])
        offset = end
    if "".join(chunks) != normalized:
        raise PocketTtsError("chunking changed normalized text")
    return chunks


def wav_metrics(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as source:
        if source.getcomptype() != "NONE" or source.getsampwidth() != 2:
            raise PocketTtsError("only PCM16 WAV is accepted")
        frames = source.getnframes()
        rate = source.getframerate()
        channels = source.getnchannels()
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "audioSeconds": frames / float(rate),
        "sampleRate": rate,
        "channels": channels,
    }


def stitch_pcm16(paths: list[Path], output: Path) -> None:
    if not paths:
        raise PocketTtsError("no WAV chunks to stitch")
    output.parent.mkdir(parents=True, exist_ok=True)
    params: tuple[int, int, int] | None = None
    with wave.open(str(output), "wb") as destination:
        for path in paths:
            with wave.open(str(path), "rb") as source:
                current = (source.getnchannels(), source.getsampwidth(), source.getframerate())
                if source.getcomptype() != "NONE" or source.getsampwidth() != 2:
                    raise PocketTtsError("only PCM16 WAV chunks may be stitched")
                if params is None:
                    params = current
                    destination.setnchannels(current[0])
                    destination.setsampwidth(current[1])
                    destination.setframerate(current[2])
                elif params != current:
                    raise PocketTtsError("WAV chunk parameters differ")
                destination.writeframes(source.readframes(source.getnframes()))


def _expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


@dataclass(frozen=True)
class VoiceProfile:
    id: str
    role: str
    engine: str
    voice: str
    model_path: Path
    model_sha256: str
    voices_path: Path | None
    voices_sha256: str
    license: str
    source: str
    language: str = "en-us"
    speed: float = 1.0

    @property
    def fingerprint(self) -> str:
        return sha256_text(stable_json({
            "id": self.id,
            "role": self.role,
            "engine": self.engine,
            "voice": self.voice,
            "modelSha256": self.model_sha256,
            "voicesSha256": self.voices_sha256,
            "language": self.language,
            "speed": self.speed,
            "license": self.license,
            "source": self.source,
        }))


class VoiceRegistry:
    def __init__(self, path: Path):
        self.path = path.resolve()
        raw = json.loads(self.path.read_text("utf-8"))
        if raw.get("schema") != REGISTRY_SCHEMA:
            raise PocketTtsError("unsupported voice registry schema")
        profiles = raw.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            raise PocketTtsError("voice registry must contain profiles")
        self._profiles: dict[str, VoiceProfile] = {}
        for item in profiles:
            profile = self._parse(item)
            if profile.id in self._profiles:
                raise PocketTtsError(f"duplicate voice profile: {profile.id}")
            self._profiles[profile.id] = profile

    @staticmethod
    def _parse(item: dict[str, Any]) -> VoiceProfile:
        profile_id = str(item.get("id", ""))
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{2,79}", profile_id):
            raise PocketTtsError("invalid voice profile id")
        role = str(item.get("role", ""))
        engine = str(item.get("engine", ""))
        if role not in ALLOWED_ROLES:
            raise PocketTtsError(f"unsupported voice role: {role}")
        if engine not in ALLOWED_ENGINES:
            raise PocketTtsError(f"unsupported or nonlocal voice engine: {engine}")
        license_name = str(item.get("license", "")).strip()
        source = str(item.get("source", "")).strip()
        if not license_name or not source.startswith("https://"):
            raise PocketTtsError(f"voice profile {profile_id} requires license and HTTPS source provenance")
        model_sha = str(item.get("modelSha256", ""))
        voices_sha = str(item.get("voicesSha256", ""))
        if not re.fullmatch(r"[a-f0-9]{64}", model_sha):
            raise PocketTtsError(f"voice profile {profile_id} requires a pinned model SHA-256")
        if engine == "kokoro-onnx" and not re.fullmatch(r"[a-f0-9]{64}", voices_sha):
            raise PocketTtsError(f"voice profile {profile_id} requires a pinned voice-bank SHA-256")
        model_path = _expand_path(str(item.get("modelPath", "")))
        voices_path = _expand_path(str(item.get("voicesPath", ""))) if engine == "kokoro-onnx" else None
        return VoiceProfile(
            id=profile_id,
            role=role,
            engine=engine,
            voice=str(item.get("voice", "")).strip(),
            model_path=model_path,
            model_sha256=model_sha,
            voices_path=voices_path,
            voices_sha256=voices_sha,
            license=license_name,
            source=source,
            language=str(item.get("language", "en-us")),
            speed=max(0.5, min(2.0, float(item.get("speed", 1.0)))),
        )

    def get(self, profile_id: str) -> VoiceProfile:
        try:
            return self._profiles[profile_id]
        except KeyError as error:
            raise PocketTtsError(f"unknown voice profile: {profile_id}") from error

    def voices(self) -> list[dict[str, Any]]:
        output = []
        for profile in self._profiles.values():
            assets = [profile.model_path] + ([profile.voices_path] if profile.voices_path else [])
            output.append({
                "id": profile.id,
                "role": profile.role,
                "engine": profile.engine,
                "voice": profile.voice,
                "language": profile.language,
                "license": profile.license,
                "source": profile.source,
                "ready": all(path is not None and path.is_file() for path in assets),
                "fingerprint": profile.fingerprint,
            })
        return output


class Engine(Protocol):
    def render(self, text: str, profile: VoiceProfile, output: Path) -> dict[str, Any]: ...


class PiperEngine:
    def __init__(self, executable: str = "piper"):
        resolved = shutil.which(executable) if not Path(executable).is_file() else executable
        if not resolved:
            raise PocketTtsError("Piper executable is unavailable")
        self.executable = str(resolved)

    def render(self, text: str, profile: VoiceProfile, output: Path) -> dict[str, Any]:
        _verify_asset(profile.model_path, profile.model_sha256)
        command = [self.executable, "--model", str(profile.model_path), "--output_file", str(output)]
        started = time.perf_counter()
        result = subprocess.run(command, input=text, text=True, capture_output=True, timeout=180, check=False)
        if result.returncode or not output.is_file():
            raise PocketTtsError((result.stderr or result.stdout or "Piper render failed")[-3000:])
        return {"renderMs": round((time.perf_counter() - started) * 1000, 3), **wav_metrics(output)}


class KokoroEngine:
    def __init__(self):
        self._instances: dict[tuple[str, str], Any] = {}

    def render(self, text: str, profile: VoiceProfile, output: Path) -> dict[str, Any]:
        if profile.voices_path is None:
            raise PocketTtsError("Kokoro voice bank is missing")
        _verify_asset(profile.model_path, profile.model_sha256)
        _verify_asset(profile.voices_path, profile.voices_sha256)
        key = (str(profile.model_path), str(profile.voices_path))
        try:
            from kokoro_onnx import Kokoro
            import soundfile as sf
        except ImportError as error:
            raise PocketTtsError("kokoro-onnx and soundfile are required") from error
        engine = self._instances.get(key)
        if engine is None:
            engine = Kokoro(*key)
            self._instances[key] = engine
        started = time.perf_counter()
        samples, sample_rate = engine.create(text, voice=profile.voice, speed=profile.speed, lang=profile.language)
        sf.write(output, samples, sample_rate, subtype="PCM_16")
        return {"renderMs": round((time.perf_counter() - started) * 1000, 3), **wav_metrics(output)}


def _verify_asset(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise PocketTtsError(f"model asset is unavailable: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise PocketTtsError(f"model asset SHA-256 mismatch: {path}")


class EnginePool:
    def __init__(self, factories: dict[str, Any] | None = None):
        self.factories = factories or {"piper": PiperEngine, "kokoro-onnx": KokoroEngine}
        self.instances: dict[str, Engine] = {}

    def get(self, engine_id: str) -> Engine:
        if engine_id not in self.instances:
            factory = self.factories.get(engine_id)
            if factory is None:
                raise PocketTtsError(f"engine is unavailable: {engine_id}")
            self.instances[engine_id] = factory()
        return self.instances[engine_id]


class Control:
    def __init__(self):
        self._state = "running"
        self._condition = threading.Condition()

    @property
    def state(self) -> str:
        with self._condition:
            return self._state

    def set(self, state: str) -> None:
        if state not in {"running", "paused", "stopping"}:
            raise PocketTtsError(f"invalid control state: {state}")
        with self._condition:
            self._state = state
            self._condition.notify_all()

    def checkpoint(self) -> None:
        with self._condition:
            while self._state == "paused":
                self._condition.wait(timeout=0.2)
            if self._state == "stopping":
                raise InterruptedError("job stopped")


class Player(Protocol):
    def play(self, path: Path, control: Control) -> dict[str, Any]: ...


class FfplayPlayer:
    """Local playback only. Command shape is fixed; no caller command crosses."""

    def __init__(self, executable: str = "ffplay"):
        resolved = shutil.which(executable) if not Path(executable).is_file() else executable
        if not resolved:
            raise PocketTtsError("ffplay is unavailable")
        self.executable = str(resolved)

    def play(self, path: Path, control: Control) -> dict[str, Any]:
        started = time.perf_counter()
        process = subprocess.Popen([self.executable, "-nodisp", "-autoexit", "-loglevel", "error", str(path)])
        paused = False
        glitches = 0
        try:
            while process.poll() is None:
                state = control.state
                if state == "stopping":
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise InterruptedError("job stopped")
                if os.name == "posix" and state == "paused" and not paused:
                    os.kill(process.pid, signal.SIGSTOP)
                    paused = True
                elif os.name == "posix" and state == "running" and paused:
                    os.kill(process.pid, signal.SIGCONT)
                    paused = False
                time.sleep(0.03)
            if process.returncode:
                glitches += 1
                raise PocketTtsError(f"ffplay failed ({process.returncode})")
        finally:
            if process.poll() is None:
                process.kill()
        return {"playMs": round((time.perf_counter() - started) * 1000, 3), "glitches": glitches}


class NullPlayer:
    def play(self, path: Path, control: Control) -> dict[str, Any]:
        control.checkpoint()
        return {"playMs": 0.0, "glitches": 0}


class AudioCache:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def key(self, profile: VoiceProfile, text: str) -> str:
        return sha256_text(stable_json({"schema": SCHEMA, "profile": profile.fingerprint, "text": text}))

    def get(self, key: str) -> tuple[Path, dict[str, Any]] | None:
        wav_path = self.root / key[:2] / f"{key}.wav"
        manifest_path = wav_path.with_suffix(".json")
        if not wav_path.is_file() or not manifest_path.is_file():
            return None
        try:
            manifest = json.loads(manifest_path.read_text("utf-8"))
            metrics = wav_metrics(wav_path)
        except Exception:
            return None
        if manifest.get("cacheKey") != key or manifest.get("sha256") != metrics["sha256"] or manifest.get("bytes") != metrics["bytes"]:
            return None
        return wav_path, {**manifest, **metrics, "cacheHit": True}

    def put(self, key: str, rendered: Path, metadata: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
        target = self.root / key[:2] / f"{key}.wav"
        target.parent.mkdir(parents=True, exist_ok=True)
        metrics = wav_metrics(rendered)
        temp = target.with_name(target.name + f".{os.getpid()}.tmp")
        shutil.copyfile(rendered, temp)
        os.replace(temp, target)
        manifest = {
            "schema": SCHEMA,
            "kind": "audio-cache-entry",
            "cacheKey": key,
            "createdAtMs": int(time.time() * 1000),
            **metadata,
            **metrics,
            "cacheHit": False,
        }
        atomic_json(target.with_suffix(".json"), manifest)
        return target, manifest


@dataclass
class Job:
    id: str
    mode: str
    voice_id: str
    text: str
    normalized: str
    chunks: list[str]
    output: Path | None
    use_cache: bool
    control: Control = field(default_factory=Control)
    created_at: float = field(default_factory=time.perf_counter)
    status: str = "queued"
    error: str = ""
    receipts: list[dict[str, Any]] = field(default_factory=list)
    playback: list[dict[str, Any]] = field(default_factory=list)
    render_finished_at: float = 0.0
    first_play_at: float = 0.0
    completed_at: float = 0.0
    done: threading.Event = field(default_factory=threading.Event)


class PocketTtsRuntime:
    """One bounded job at a time, with persistent synthesis/playback workers."""

    def __init__(self, registry: VoiceRegistry, state_root: Path, engine_pool: EnginePool | None = None, player: Player | None = None):
        self.registry = registry
        self.state_root = state_root.resolve()
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.cache = AudioCache(self.state_root / "cache")
        self.engine_pool = engine_pool or EnginePool()
        self.player = player or FfplayPlayer()
        self._lock = threading.Lock()
        self._active: Job | None = None
        self._synthesis_queue: queue.Queue[Job] = queue.Queue(maxsize=1)
        self._playback_queue: queue.Queue[Any] = queue.Queue(maxsize=4)
        self._synthesis_thread = threading.Thread(target=self._synthesis_loop, name="pocket-tts-synthesis", daemon=True)
        self._playback_thread = threading.Thread(target=self._playback_loop, name="pocket-tts-playback", daemon=True)
        self._synthesis_thread.start()
        self._playback_thread.start()

    def start(self, mode: str, text: str, voice_id: str, output: Path | None = None, use_cache: bool = True, max_chars: int = DEFAULT_CHUNK_CHARS) -> dict[str, Any]:
        if mode not in {"speak", "render"}:
            raise PocketTtsError("mode must be speak or render")
        normalized = normalize_text(text)
        voice = self.registry.get(voice_id)
        if not any(item["id"] == voice_id and item["ready"] for item in self.registry.voices()):
            raise PocketTtsError(f"voice assets are not ready: {voice_id}")
        with self._lock:
            if self._active and not self._active.done.is_set():
                raise PocketTtsError(f"runtime is busy with {self._active.id}")
            job = Job(
                id="ptts-" + uuid.uuid4().hex[:16],
                mode=mode,
                voice_id=voice.id,
                text=text,
                normalized=normalized,
                chunks=chunk_text(normalized, max_chars),
                output=output.resolve() if output else None,
                use_cache=use_cache,
            )
            self._active = job
            self._write_status(job)
            self._synthesis_queue.put(job)
        return self.status()

    def wait(self, timeout: float | None = None) -> dict[str, Any]:
        with self._lock:
            job = self._active
        if not job:
            return self.status()
        if not job.done.wait(timeout):
            raise TimeoutError(f"job did not complete within {timeout} seconds")
        return self.status()

    def pause(self) -> dict[str, Any]:
        return self._control("paused")

    def resume(self) -> dict[str, Any]:
        return self._control("running")

    def stop(self) -> dict[str, Any]:
        return self._control("stopping")

    def _control(self, state: str) -> dict[str, Any]:
        with self._lock:
            job = self._active
            if not job or job.done.is_set():
                raise PocketTtsError("no active job")
            if state == "paused":
                job.status = "paused"
            elif state == "running":
                job.status = "running"
            else:
                job.status = "stopping"
            self._write_status(job)
            # Publish the requested state before waking the worker. The worker's
            # terminal receipt must always win the race with this control write.
            job.control.set(state)
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            job = self._active
            if not job:
                return {
                    "schema": SCHEMA,
                    "status": "idle",
                    "workers": self._workers(),
                    "cloudSpeechAllowed": False,
                }
            return self._receipt(job)

    def voices(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "voices": self.registry.voices(), "cloudSpeechAllowed": False}

    def _synthesis_loop(self) -> None:
        while True:
            job = self._synthesis_queue.get()
            try:
                self._run_synthesis(job)
            except InterruptedError:
                self._finish(job, "stopped")
            except Exception as error:
                job.error = str(error)[-3000:]
                self._finish(job, "failed")

    def _run_synthesis(self, job: Job) -> None:
        profile = self.registry.get(job.voice_id)
        engine = self.engine_pool.get(profile.engine)
        job.status = "running"
        self._write_status(job)
        for index, text_chunk in enumerate(job.chunks):
            job.control.checkpoint()
            key = self.cache.key(profile, text_chunk)
            cached = self.cache.get(key) if job.use_cache else None
            if cached:
                wav_path, receipt = cached
            else:
                with tempfile.TemporaryDirectory(prefix="pocket-tts-render-") as temp_root:
                    rendered = Path(temp_root) / "chunk.wav"
                    render_metrics = engine.render(text_chunk, profile, rendered)
                    wav_path, receipt = self.cache.put(key, rendered, {
                        "engine": profile.engine,
                        "voiceId": profile.id,
                        "voiceFingerprint": profile.fingerprint,
                        "textSha256": sha256_text(text_chunk),
                        "renderMs": render_metrics.get("renderMs", 0.0),
                    })
            item = {"job": job, "index": index, "path": wav_path, "receipt": receipt}
            job.receipts.append({"index": index, **receipt})
            self._write_status(job)
            self._playback_queue.put(item)
        job.render_finished_at = time.perf_counter()
        self._playback_queue.put({"job": job, "kind": QUEUE_END})

    def _playback_loop(self) -> None:
        while True:
            item = self._playback_queue.get()
            job: Job = item["job"]
            try:
                if item.get("kind") is QUEUE_END:
                    if job.mode == "render":
                        output = job.output or (self.state_root / "renders" / f"{job.id}.wav")
                        stitch_pcm16([Path(receipt["path"]) if "path" in receipt else self.cache.root / receipt["cacheKey"][:2] / f"{receipt['cacheKey']}.wav" for receipt in job.receipts], output)
                        metrics = wav_metrics(output)
                        job.output = output
                        job.playback.append({"renderOutput": str(output), **metrics, "glitches": 0})
                    self._finish(job, "completed")
                    continue
                job.control.checkpoint()
                if job.mode == "speak":
                    if not job.first_play_at:
                        job.first_play_at = time.perf_counter()
                    playback = self.player.play(item["path"], job.control)
                    job.playback.append({"index": item["index"], **playback})
                    self._write_status(job)
            except InterruptedError:
                self._finish(job, "stopped")
            except Exception as error:
                job.error = str(error)[-3000:]
                self._finish(job, "failed")

    def _finish(self, job: Job, status: str) -> None:
        if job.done.is_set():
            return
        job.status = status
        job.completed_at = time.perf_counter()
        self._write_status(job)
        job.done.set()

    def _workers(self) -> dict[str, Any]:
        return {
            "synthesis": {"name": self._synthesis_thread.name, "alive": self._synthesis_thread.is_alive(), "warmEngines": sorted(self.engine_pool.instances)},
            "playback": {"name": self._playback_thread.name, "alive": self._playback_thread.is_alive()},
        }

    def _receipt(self, job: Job) -> dict[str, Any]:
        now = job.completed_at or time.perf_counter()
        audio_seconds = sum(float(item.get("audioSeconds", 0.0)) for item in job.receipts)
        render_ms = sum(float(item.get("renderMs", 0.0)) for item in job.receipts if not item.get("cacheHit"))
        cache_hits = sum(1 for item in job.receipts if item.get("cacheHit"))
        glitches = sum(int(item.get("glitches", 0)) for item in job.playback)
        return {
            "schema": SCHEMA,
            "jobId": job.id,
            "mode": job.mode,
            "status": job.status,
            "voiceId": job.voice_id,
            "inputSha256": sha256_text(job.text),
            "normalizedSha256": sha256_text(job.normalized),
            "textChunks": len(job.chunks),
            "renderedChunks": len(job.receipts),
            "playedChunks": len([item for item in job.playback if "index" in item]),
            "cacheHits": cache_hits,
            "cacheHitRatio": round(cache_hits / len(job.receipts), 4) if job.receipts else 0.0,
            "ttfaMs": round((job.first_play_at - job.created_at) * 1000, 3) if job.first_play_at else None,
            "totalMs": round((now - job.created_at) * 1000, 3),
            "renderMs": round(render_ms, 3),
            "audioSeconds": round(audio_seconds, 3),
            "rtf": round(render_ms / 1000 / audio_seconds, 6) if audio_seconds else None,
            "firstPlaybackBeforeRenderComplete": bool(job.first_play_at and job.render_finished_at and job.first_play_at < job.render_finished_at),
            "glitches": glitches,
            "output": str(job.output) if job.output else "",
            "error": job.error,
            "workers": self._workers(),
            "cloudSpeechAllowed": False,
            "hostedDefaultMouth": False,
        }

    def _write_status(self, job: Job) -> None:
        atomic_json(self.state_root / "status.json", self._receipt(job))


class RuntimeHttp:
    def __init__(self, runtime: PocketTtsRuntime, host: str, port: int, token_path: Path):
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise PocketTtsError("Pocket TTS server must bind loopback")
        self.runtime = runtime
        self.token_path = token_path.resolve()
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        if self.token_path.exists():
            self.token = self.token_path.read_text("utf-8").strip()
        else:
            self.token = uuid.uuid4().hex + uuid.uuid4().hex
            self.token_path.write_text(self.token + "\n", "utf-8")
            os.chmod(self.token_path, 0o600)
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:
                return

            def _reply(self, status: int, payload: Any) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                if self.path == "/health":
                    self._reply(200, {"schema": SCHEMA, "status": "ready", "loopback": True, "workers": parent.runtime._workers()})
                else:
                    self._reply(404, {"error": "not_found"})

            def do_POST(self) -> None:
                if self.path != "/v1/command":
                    self._reply(404, {"error": "not_found"})
                    return
                if self.headers.get("Authorization", "") != "Bearer " + parent.token:
                    self._reply(401, {"error": "unauthorized"})
                    return
                try:
                    length = min(100_000, int(self.headers.get("Content-Length", "0")))
                    request = json.loads(self.rfile.read(length).decode("utf-8"))
                    self._reply(200, parent.dispatch(request))
                except Exception as error:
                    self._reply(400, {"error": str(error)[-3000:]})

        self.server = ThreadingHTTPServer((host, port), Handler)

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        command = str(request.get("command", ""))
        if command in {"speak", "render"}:
            output = Path(request["output"]) if request.get("output") else None
            return self.runtime.start(command, str(request.get("text", "")), str(request.get("voice", "")), output, bool(request.get("cache", True)), int(request.get("chunkChars", DEFAULT_CHUNK_CHARS)))
        if command == "pause":
            return self.runtime.pause()
        if command == "resume":
            return self.runtime.resume()
        if command == "stop":
            return self.runtime.stop()
        if command == "status":
            return self.runtime.status()
        if command == "voices":
            return self.runtime.voices()
        if command == "benchmark":
            started = self.runtime.start("speak" if request.get("play") else "render", str(request.get("text", "Fortress interface ready.")), str(request.get("voice", "")), None, bool(request.get("cache", True)), int(request.get("chunkChars", DEFAULT_CHUNK_CHARS)))
            return self.runtime.wait(float(request.get("timeout", 300))) if started else started
        raise PocketTtsError("unsupported command")

    def serve_forever(self) -> None:
        self.server.serve_forever(poll_interval=0.2)


def client_request(origin: str, token_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if not re.fullmatch(r"http://(?:127\.0\.0\.1|localhost|\[::1\]):[0-9]{1,5}", origin):
        raise PocketTtsError("Pocket TTS client only accepts a loopback origin")
    token = token_path.read_text("utf-8").strip()
    request = urllib.request.Request(
        origin + "/v1/command",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=310) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise PocketTtsError(error.read().decode("utf-8")[-3000:]) from error


def main() -> int:
    parser = argparse.ArgumentParser(prog="pocket-tts", description="Local offline Pocket TTS runtime")
    parser.add_argument("--registry", type=Path, default=Path(os.environ.get("POCKET_TTS_REGISTRY", "config/pocket-tts-voices.v1.json")))
    parser.add_argument("--state-root", type=Path, default=Path(os.environ.get("POCKET_TTS_STATE", str(Path.home() / ".local/state/home-center/pocket-tts"))))
    parser.add_argument("--origin", default="http://127.0.0.1:10206")
    parser.add_argument("--token", type=Path, default=Path(os.environ.get("POCKET_TTS_TOKEN", str(Path.home() / ".config/home-center/pocket-tts.token"))))
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=10206)
    for name in ("speak", "render"):
        command = sub.add_parser(name)
        command.add_argument("text")
        command.add_argument("--voice", required=True)
        command.add_argument("--output")
        command.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS)
        command.add_argument("--no-cache", action="store_true")
    for name in ("stop", "pause", "resume", "status", "voices"):
        sub.add_parser(name)
    benchmark = sub.add_parser("benchmark")
    benchmark.add_argument("--text", default="Fortress interface ready.")
    benchmark.add_argument("--voice", required=True)
    benchmark.add_argument("--play", action="store_true")
    benchmark.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()
    if args.command == "serve":
        registry = VoiceRegistry(args.registry)
        runtime = PocketTtsRuntime(registry, args.state_root)
        RuntimeHttp(runtime, args.host, args.port, args.token).serve_forever()
        return 0
    payload: dict[str, Any] = {"command": args.command}
    if args.command in {"speak", "render"}:
        payload.update({"text": args.text, "voice": args.voice, "output": args.output, "chunkChars": args.chunk_chars, "cache": not args.no_cache})
    elif args.command == "benchmark":
        payload.update({"text": args.text, "voice": args.voice, "play": args.play, "cache": not args.no_cache})
    print(json.dumps(client_request(args.origin, args.token, payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
