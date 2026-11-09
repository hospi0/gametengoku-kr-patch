# -*- coding: utf-8 -*-
r"""work/그림추출/vdp1/<장면>/*.png → <장면>/_모아보기.png (번호 붙여 바둑판, 회색 바탕, 2배)
  python tools/gfx_sheet.py <장면> [...]"""
import os, sys, glob
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for nm in sys.argv[1:]:
    d = os.path.join(ROOT, 'work', '그림추출', 'vdp1', nm)
    fs = sorted(f for f in glob.glob(os.path.join(d, '[0-9]*.png')))
    ims = [Image.open(f) for f in fs]
    W = 900; x = y = 0; rowh = 0; pos = []
    for im in ims:
        w, h = im.width * 2, im.height * 2 + 14
        if x + w > W: x = 0; y += rowh + 6; rowh = 0
        pos.append((x, y)); x += w + 6; rowh = max(rowh, h)
    sheet = Image.new('RGB', (W, y + rowh + 6), (96, 96, 96)); dr = ImageDraw.Draw(sheet)
    for (x, y), im, f in zip(pos, ims, fs):
        dr.text((x, y), os.path.basename(f)[:3], fill=(255, 255, 0))
        sheet.paste(im.resize((im.width * 2, im.height * 2), Image.NEAREST), (x, y + 14), im.resize((im.width * 2, im.height * 2), Image.NEAREST))
    sheet.save(os.path.join(d, '_모아보기.png')); print(nm, len(ims), sheet.size)
