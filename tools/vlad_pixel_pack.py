#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,struct,zlib
from pathlib import Path

MAGIC=b'VPX1'

def rle(data: bytes) -> bytes:
    out=bytearray(); i=0
    while i < len(data):
        v=data[i]; n=1
        while i+n < len(data) and data[i+n]==v and n<255: n+=1
        out.extend((n,v)); i+=n
    return bytes(out)

def main():
    ap=argparse.ArgumentParser(prog='vlad-pixel-pack')
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--size',type=int,default=32,choices=(8,16,24,32,48,64))
    ap.add_argument('--colors',type=int,default=16,choices=(2,4,8,16,32))
    ap.add_argument('--keep-png',action='store_true')
    a=ap.parse_args()
    try:
        from PIL import Image
    except Exception as exc:
        raise SystemExit(f'Pillow required for pack step: {exc}')

    src=Path(a.input); dst=Path(a.output)
    im=Image.open(src).convert('RGBA')
    im.thumbnail((a.size,a.size),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(a.size,a.size),(0,0,0,0))
    canvas.alpha_composite(im,((a.size-im.width)//2,(a.size-im.height)//2))
    pal=canvas.convert('P',palette=Image.Palette.ADAPTIVE,colors=a.colors,dither=Image.Dither.NONE)
    palette=pal.getpalette()[:a.colors*3]
    indices=bytes(pal.getdata())
    raw_rle=rle(indices)
    compressed=zlib.compress(indices,9)
    codec=1 if len(raw_rle)<=len(compressed) else 2
    body=raw_rle if codec==1 else compressed
    header=struct.pack('<4sBBBBII',MAGIC,a.size,a.size,a.colors,codec,len(indices),len(body))
    blob=header+bytes(palette)+body
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(blob)
    preview=dst.with_suffix('.png')
    pal.save(preview,optimize=True)
    receipt={
      'schema':'vlad.pixel.pack.v1','ok':True,'input':str(src),'canonical':str(dst),'preview':str(preview),
      'width':a.size,'height':a.size,'colors':a.colors,'codec':'rle' if codec==1 else 'zlib',
      'canonicalBytes':len(blob),'previewBytes':preview.stat().st_size,
      'canonicalSha256':hashlib.sha256(blob).hexdigest(),'intermediateBytes':src.stat().st_size,
      'intermediateDeleted':False,
    }
    if not a.keep_png:
        src.unlink()
        receipt['intermediateDeleted']=True
    receipt_path=dst.with_suffix(dst.suffix+'.receipt.json')
    receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__': main()
