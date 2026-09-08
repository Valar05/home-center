#!/usr/bin/env python3
from PIL import Image, ImageDraw
import build as B

def compact_render_png(txt, path):
    font = B.get_font(5)
    im = Image.new('RGB', (320, 180), 'black')
    d = ImageDraw.Draw(im)
    d.multiline_text((4, 3), txt, font=font, fill='white', spacing=0)
    im.save(path)

B.render_png = compact_render_png

if __name__ == '__main__':
    B.main()
