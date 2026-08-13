#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Iterable, Iterator

REPO = Path(os.environ.get(
    "FORTRESS_HOME_CENTER",
    "/storage/emulated/0/Documents/GodotProjects/home-center",
))
VOICE_CONFIG = Path(os.environ.get(
    "FORTRESS_ADAM_VOICE_CONFIG",
    str(REPO / "config/fortress-adam-voice.json"),
))
AUDIO_ROOT = Path("/storage/emulated/0/Documents/FortressAudio")
POCKET_PHONE = Path.home() / "bin/pocket-tts-phone"
PLAYBACK_COMPONENT = "com.dclar.homecenter/.PocketTtsPlaybackActivity"
PLAYBACK_LOG_TAG = "PocketTtsDuck"
DEFAULT_CHUNK = 700


def find_rish() -> Path | None:
    candidates = [
        os.environ.get("RISH", ""),
        str(Path.home() / "bin/rish"),
        str(Path.home() / "rish"),
        "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish",
        "/storage/emulated/0/Documents/rish",
        "/storage/emulated/0/Download/rish",
    ]
    for raw in candidates:
        if raw:
            path = Path(raw).expanduser()
            if path.is_file():
                return path
    return None


def profile() -> dict:
    raw = json.loads(VOICE_CONFIG.read_text(encoding="utf-8")) if VOICE_CONFIG.exists() else {}
    delivery = raw.get("delivery", {})
    voice = raw.get("voice", {})
    return {
        "id": raw.get("id", "adam-phone"),
        "displayName": raw.get("displayName", "Adam"),
        "language": raw.get("language", "english"),
        "engine": "pocket-tts-phone+home-center-playback+rish",
        "voiceKind": voice.get("kind", "builtin"),
        "voiceValue": voice.get("value", "michael"),
        "chunkChars": int(os.environ.get(
            "FORTRESS_READ_ALOUD_CHUNK",
            delivery.get("chunkChars", DEFAULT_CHUNK),
        )),
        "tempo": float(delivery.get("tempo", 1.0)),
        "volume": float(delivery.get("volume", 1.0)),
        "pitchSemitones": float(delivery.get("pitchSemitones", 0.0)),
        "prefetchChunks": 0,
        "style": delivery.get("style", ""),
        "canonicalProvider": "pocket-home-center",
        "allowSystemFallback": False,
    }


def run_rish(command: str, timeout: float = 20.0) -> str:
    rish = find_rish()
    if not rish:
        raise RuntimeError("ADAM VOICE BLOCKED: Shizuku rish unavailable")
    proc = subprocess.run(
        [str(rish), "-c", command],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    combined = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())
    if proc.returncode:
        raise RuntimeError((combined or f"rish failed ({proc.returncode})")[-4000:])
    return combined


def playback_component_status() -> dict:
    try:
        output = run_rish(
            "cmd package resolve-activity --brief -n " + shlex.quote(PLAYBACK_COMPONENT),
            15,
        )
        available = PLAYBACK_COMPONENT in output and "No activity found" not in output
        return {
            "available": available,
            "component": PLAYBACK_COMPONENT,
            "output": output[-1200:],
        }
    except Exception as error:
        return {
            "available": False,
            "component": PLAYBACK_COMPONENT,
            "error": str(error)[-1200:],
        }


def doctor() -> dict:
    selected = profile()
    pocket = POCKET_PHONE.is_file() and os.access(POCKET_PHONE, os.X_OK)
    rish = find_rish()
    component = playback_component_status() if rish else {
        "available": False,
        "component": PLAYBACK_COMPONENT,
        "error": "rish unavailable",
    }
    ready = bool(pocket and rish and component.get("available"))
    if ready:
        blocked = ""
    elif not pocket:
        blocked = "pocket-tts-phone missing"
    elif not rish:
        blocked = "Shizuku rish unavailable"
    else:
        blocked = "Home Center PocketTtsPlaybackActivity unavailable"
    return {
        "ok": ready,
        "preferred": "pocket-home-center" if ready else "",
        "canonicalProvider": "pocket-home-center",
        "voiceProfile": selected,
        "pocketPhone": str(POCKET_PHONE) if pocket else "",
        "androidLaunchTransport": "shizuku-rish",
        "rish": str(rish) if rish else "",
        "playbackComponent": component,
        "systemFallbackAllowed": False,
        "blockedReason": blocked,
        "textChunkChars": selected["chunkChars"],
        "prefetchChunks": 0,
        "batching": False,
        "cloudFallback": False,
    }


def chunk_text_piece(text: str) -> Iterator[str]:
    limit = profile()["chunkChars"]
    text = " ".join(str(text or "").split()).strip()
    while text:
        if len(text) <= limit:
            yield text
            return
        window = text[:limit + 1]
        cuts = [window.rfind(marker) for marker in (". ", "? ", "! ", "; ", ": ", ", ")]
        cut = max(cuts)
        if cut < limit // 3:
            cut = window.rfind(" ")
        if cut < limit // 3:
            cut = limit
        else:
            cut += 1
        yield text[:cut].strip()
        text = text[cut:].strip()


def chunks_from_text(text: str) -> Iterator[str]:
    yield from chunk_text_piece(text)


def chunks_from_file(path: str) -> Iterator[str]:
    source = Path(path).expanduser()
    source = source if source.is_absolute() else (Path.cwd() / source).resolve()
    if not source.is_file():
        raise FileNotFoundError(path)
    buffer = ""
    limit = profile()["chunkChars"]
    with source.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                if buffer:
                    yield from chunk_text_piece(buffer)
                    buffer = ""
                continue
            candidate = (buffer + " " + line).strip()
            if len(candidate) >= limit:
                yield from chunk_text_piece(candidate)
                buffer = ""
            else:
                buffer = candidate
    if buffer:
        yield from chunk_text_piece(buffer)


def chunks_from_stdin() -> Iterator[str]:
    buffer = ""
    limit = profile()["chunkChars"]
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            if buffer:
                yield from chunk_text_piece(buffer)
                buffer = ""
            continue
        candidate = (buffer + " " + line).strip()
        if len(candidate) >= limit:
            yield from chunk_text_piece(candidate)
            buffer = ""
        else:
            buffer = candidate
    if buffer:
        yield from chunk_text_piece(buffer)


def fix_wav_header(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise RuntimeError("Pocket output is not a WAV")
    body = bytearray(data)
    struct.pack_into("<I", body, 4, len(body) - 8)
    position = 12
    while position + 8 <= len(body):
        name = bytes(body[position:position + 4])
        size = struct.unpack_from("<I", body, position + 4)[0]
        if name == b"data":
            struct.pack_into("<I", body, position + 4, len(body) - (position + 8))
            break
        position += 8 + size + (size & 1)
        if position > len(body):
            break
    path.write_bytes(body)


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def synthesize_chunk(text: str, index: int, selected: dict) -> Path:
    AUDIO_ROOT.mkdir(parents=True, exist_ok=True)
    work = AUDIO_ROOT / f".adam-{os.getpid()}-{index}"
    work.mkdir(parents=True, exist_ok=True)
    command = [
        str(POCKET_PHONE),
        "generate",
        "--text",
        text,
        "--voice",
        selected["voiceValue"],
        "--language",
        selected["language"],
    ]
    proc = subprocess.run(
        command,
        cwd=work,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout or f"PocketTTS failed ({proc.returncode})")[-3000:])
    generated = work / "tts_output.wav"
    if not generated.is_file():
        raise RuntimeError("PocketTTS completed without tts_output.wav")
    fix_wav_header(generated)
    final = AUDIO_ROOT / f"adam-{os.getpid()}-{index}.wav"
    generated.replace(final)
    try:
        work.rmdir()
    except OSError:
        pass
    return final


def pocket_playback_logs() -> str:
    return run_rish(
        "logcat -d -v epoch -s " + shlex.quote(PLAYBACK_LOG_TAG + ":I") + " '*:S'",
        20,
    )


def verify_playback_log(path: Path) -> dict:
    logs = pocket_playback_logs()
    start_token = "play_start file=" + str(path)
    start_index = logs.rfind(start_token)
    if start_index < 0:
        rejected = "play_rejected" in logs or "play_error" in logs
        raise RuntimeError(
            "Pocket Space Android playback did not emit play_start"
            + ("; playback component reported rejection/error" if rejected else "")
        )
    tail = logs[start_index:]
    if "play_error" in tail or "play_rejected" in tail:
        raise RuntimeError("Pocket Space Android playback reported an error after play_start")
    if "play_finish reason=completed" not in tail:
        raise RuntimeError("Pocket Space Android playback did not emit completed playback receipt")
    return {
        "playStartObserved": True,
        "playCompletedObserved": True,
        "component": PLAYBACK_COMPONENT,
        "logTag": PLAYBACK_LOG_TAG,
    }


def play_home_center(path: Path) -> dict:
    seconds = duration(path)
    component = playback_component_status()
    if not component.get("available"):
        raise RuntimeError("Pocket Space playback component unavailable: " + json.dumps(component, ensure_ascii=False))
    command = (
        "am start -W -n "
        + shlex.quote(PLAYBACK_COMPONENT)
        + " --es file "
        + shlex.quote(str(path))
    )
    launch = run_rish(command, 20)
    lowered = launch.lower()
    if "error type" in lowered or "does not exist" in lowered or "no activity found" in lowered:
        raise RuntimeError("Pocket Space Android playback launch failed: " + launch[-2000:])
    if "status: ok" not in lowered and "starting:" not in lowered and "activity:" not in lowered:
        raise RuntimeError("Pocket Space Android playback launch was not acknowledged: " + launch[-2000:])
    time.sleep(max(0.15, seconds + 0.75))
    observed = verify_playback_log(path)
    return {
        "audioSeconds": seconds,
        "activityLaunchAcknowledged": True,
        **observed,
    }


def speak(chunks: Iterable[str], provider: str = "auto") -> dict:
    if provider == "termux":
        raise RuntimeError("BLOCKED: system TTS is not Adam")
    readiness = doctor()
    if not readiness["ok"]:
        raise RuntimeError("ADAM VOICE BLOCKED: " + readiness["blockedReason"])
    selected = profile()
    count = 0
    characters = 0
    seconds = 0.0
    files: list[Path] = []
    playback_receipts: list[dict] = []
    try:
        for index, text_chunk in enumerate(chunks):
            count += 1
            characters += len(text_chunk)
            wav = synthesize_chunk(text_chunk, index, selected)
            files.append(wav)
            playback = play_home_center(wav)
            playback_receipts.append(playback)
            seconds += float(playback["audioSeconds"])
            try:
                wav.unlink()
            except OSError:
                pass
        return {
            "ok": True,
            "provider": "pocket-home-center",
            "engine": "pocket-tts-phone",
            "transport": "shizuku-rish",
            "outputComponent": PLAYBACK_COMPONENT,
            "playbackVerified": bool(playback_receipts)
                and all(item.get("playCompletedObserved") for item in playback_receipts),
            "voiceProfile": selected["id"],
            "voice": selected["voiceValue"],
            "textChunks": count,
            "characters": characters,
            "audioSeconds": round(seconds, 3),
            "playbackReceipts": playback_receipts,
            "batching": False,
            "prefetchChunks": 0,
            "systemFallbackUsed": False,
            "cloudFallbackUsed": False,
        }
    finally:
        for wav in files:
            try:
                wav.unlink()
            except OSError:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fortress-read",
        description="Adam: Pocket Space TTS through verified Home Center Android playback",
    )
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--file")
    parser.add_argument("--provider", choices=["auto", "pocket", "termux"], default="auto")
    parser.add_argument("text", nargs="*")
    args = parser.parse_args()
    if args.doctor:
        output = doctor()
    elif args.profile:
        output = profile()
    elif args.file:
        output = speak(chunks_from_file(args.file), args.provider)
    elif args.text:
        output = speak(chunks_from_text(" ".join(args.text)), args.provider)
    else:
        output = speak(chunks_from_stdin(), args.provider)
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
