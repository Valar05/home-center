#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'tools/vlad_pixel_pack.py').read_text(encoding='utf-8')
for token in ["MAGIC=b'VPX1'", "intermediateDeleted", "canonicalBytes", "src.unlink()", "Image.Dither.NONE"]:
    assert token in text, f'missing packer token: {token}'
print('Vlad pixel pack contract: PASS')
