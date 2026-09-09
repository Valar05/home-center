#!/usr/bin/env python3
"""Timing016 deterministic abstract ASCII Motion Dungeon builder. Source art is never read or embedded."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
M=json.loads((ROOT/"motion.json").read_text())
assert M["render"]["connective_motion"].startswith("NONE")
print(json.dumps({"specimen_id":M["specimen_id"],"frames":M["render"]["total_frames"],"media_sha256":M["render"]["media_sha256"],"source_art_embedded":False},sort_keys=True))
