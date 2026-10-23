"""Canonical Ritsu relay -> Pocket multivoice adapter; never uses Qwen synthesis.

Voice names share the already-auditioned Pocket states, and cache keys contain
the selected immutable voice-state digest. 'upset' aliases 'somber'.
"""
import sys
import tempfile
import urllib.request
import json
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pocket_audio_cache import Store

ALIASES = {"normal": "normal", "warm": "normal", "delighted": "delighted",
           "happy": "delighted", "amused": "amused", "somber": "somber",
           "upset": "somber", "whisper": "whisper"}
HASHES = {
    "normal": "6D619A92B6F17C4DF4163919E690FAFADD48C285A0773AE01EFDE7BAA510ED07",
    "delighted": "47089F6F552D9E8FDEF599C3917B958FE4850CCD9B875662996F77214F5DD3A6",
    "amused": "6F878B05D4227E10B43BB0AA8A87C6CBDF909B9CCA0F4A845E28C6541F17D9FE",
    "somber": "51C7B4F55361082ED23ABB56E1F7E9878D4CA26DA5740349858BDBDF2A4CA0BD",
    "whisper": "B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5",
}
VERSION = "ritsu-pocket-repertoire-v2-20261023"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def resolve(text, character="ritsu", profile="normal"):
    if character.lower() != "ritsu":
        raise ValueError("No voice configured for character: " + character)
    if profile not in ALIASES:
        raise ValueError("Unknown Ritsu Pocket profile")
    selected = ALIASES[profile]
    store = Store()
    voice = "pocket:" + selected + ":" + HASHES[selected]
    settings = {"repertoire": VERSION, "profile": selected}
    hit = store.get(text, voice, settings)
    if hit:
        return str(hit), True
    body = json.dumps({"text": text, "profile": selected}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:10205/tts",
        data=body, headers={"Content-Type": "application/json"}, method="POST")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output:
        tmp = Path(output.name)
        try:
            with OPENER.open(req, timeout=180) as response:
                if response.headers.get("X-TTS-Engine") != "pocket-tts":
                    raise RuntimeError("Unexpected voice synthesis engine")
                if response.headers.get("X-Ritsu-Voice-SHA256") != HASHES[selected]:
                    raise RuntimeError("Unexpected Pocket voice state")
                while True:
                    block = response.read(65536)
                    if not block:
                        break
                    output.write(block)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    try:
        with wave.open(str(tmp), "rb") as audio:
            if not audio.getnframes() or audio.getframerate() != 24000:
                raise ValueError("Pocket returned invalid or empty WAV")
        result = store.put(tmp, text, voice, settings)
        return str(result), False
    finally:
        tmp.unlink(missing_ok=True)

