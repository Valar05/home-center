#!/usr/bin/env python3
"""Render an accepted Pocket TTS v2 artifact on THECAULDRON."""
from __future__ import annotations
import argparse,base64,json,os,pathlib
from pocket_tts_render_v2 import PocketTtsEngine

def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--request-id",required=True); parser.add_argument("--text-base64",required=True); parser.add_argument("--output-root",default=r"C:\\Users\\Public\\HomeCenterPocketTts")
    args=parser.parse_args(); text=base64.b64decode(args.text_base64,validate=True).decode("utf-8")
    safe="".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in args.request_id).strip("-")[:120]
    if not safe or not text.strip(): raise ValueError("request id and text are required")
    root=pathlib.Path(args.output_root); root.mkdir(parents=True,exist_ok=True); output=root/(safe+".wav")
    receipt=PocketTtsEngine().render(text,output,safe,backend="cauldron-computer-hands")
    print(json.dumps(receipt,separators=(",",":")),flush=True); return 0
if __name__=="__main__": raise SystemExit(main())
