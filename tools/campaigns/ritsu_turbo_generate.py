#!/usr/bin/env python3
"""Ritsu Chatterbox Turbo: pinned voice, explicit text, verified WAV."""
import argparse
import hashlib
import json
import wave
from pathlib import Path
import torch
import torchaudio
from chatterbox.tts_turbo import ChatterboxTurboTTS

BASE = Path(r"C:\Users\dclar\workspace\ritsu-chatterbox-turbo")
REFERENCE = Path(r"C:\Users\dclar\Documents\Codex\Venice\PocketTTS\speech_store\cache\c427230b53740062dfc343cb7142d446c71c44e5ae9eca9a8926c014cd855ce0.wav")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not args.text.strip():
        parser.error("text must be nonempty")
    if not REFERENCE.is_file():
        raise SystemExit(f"BLOCKED: pinned reference missing: {REFERENCE}")
    if not torch.cuda.is_available():
        raise SystemExit("BLOCKED: CUDA unavailable; no silent CPU fallback")
    info = torchaudio.info(str(REFERENCE))
    if info.num_frames / info.sample_rate <= 5:
        raise SystemExit("BLOCKED: pinned voice reference must exceed 5 seconds")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit(f"BLOCKED: output exists: {output}")
    model = ChatterboxTurboTTS.from_pretrained(device="cuda")
    audio = model.generate(args.text, audio_prompt_path=str(REFERENCE))
    torchaudio.save(str(output), audio.cpu(), model.sr)
    with wave.open(str(output), "rb") as wav:
        frames, rate, channels = wav.getnframes(), wav.getframerate(), wav.getnchannels()
    if frames == 0 or output.stat().st_size <= 44:
        raise SystemExit("BLOCKED: empty WAV")
    receipt = {"status":"GENERATED_NOT_PLAYED","output":str(output),"bytes":output.stat().st_size,
        "sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"sample_rate":rate,
        "channels":channels,"duration_seconds":round(frames/rate,3),
        "reference":str(REFERENCE),"torch":torch.__version__,"engine":"ChatterboxTurboTTS"}
    print(json.dumps(receipt, indent=2))
    output.with_suffix(output.suffix+".receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")

if __name__ == "__main__":
    main()
