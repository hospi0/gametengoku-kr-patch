# -*- coding: utf-8 -*-
r"""메뉴 그림 묶음 YKBIN(2026-11-08) — 압축 덩어리 [u32 압축 바이트 수][오쿠무라 LZSS 0 채움] 안에 그림 레코드 [u16 폭][u16 높이][8비트 화소 폭×높이] 연속
  원본 찾은 길: 메뉴 코드 0x060513F0 → 풀기 준비 0x06004734(원본, 대상, 0)·풀기 0x060047C8 → 버퍼 RAM-L 0x2AE174 · 옵션 버튼 = YKBIN 0x26648
  python tools/ykbin.py [색 스테이트=옵션] → work/그림추출/메뉴/<덩어리 오프셋>/NN_WxH.png + _모아보기.png"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lzss.INIT = 0
CHUNKS = [0x25310, 0x26648, 0x277AC, 0x2A34C, 0x2CDCC, 0x2FB70, 0x349DC, 0x35FE8, 0x39918, 0x3C6C8]


def chunk(b, o):
    s = struct.unpack_from('>I', b, o)[0]
    d, _ = lzss.decompress(b[:o + 4 + s], o + 4, 1 << 23)
    p = 0; out = []
    while p + 4 <= len(d):
        w, h = struct.unpack_from('>HH', d, p); out.append((w, h, d[p + 4:p + 4 + w * h])); p += 4 + w * h
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    st = sys.argv[1] if len(sys.argv) > 1 else '옵션'
    cram = open(os.path.join(ROOT, 'work', 'mem', st, 'CRAM.bin'), 'rb').read()
    col = lambda i: (lambda c: ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))(struct.unpack_from('>H', cram, 2 * (i & 2047))[0])
    b = open(os.path.join(ROOT, 'work', 'files', 'YKBIN'), 'rb').read()
    for o in CHUNKS:
        recs = chunk(b, o); od = os.path.join(ROOT, 'work', '그림추출', '메뉴', '%05X' % o); os.makedirs(od, exist_ok=True)
        ims = []
        for k, (w, h, px) in enumerate(recs):
            im = Image.new('RGBA', (w, h)); pp = im.load()
            for i, c in enumerate(px):
                if c: pp[i % w, i // w] = col(0x200 + c) + (255,)
            im.save(os.path.join(od, '%02d_%dx%d.png' % (k, w, h))); ims.append(im)
        W = 900; x = y = rh = 0; pos = []
        for im in ims:
            if x + im.width > W: x = 0; y += rh + 16; rh = 0
            pos.append((x, y)); x += im.width + 6; rh = max(rh, im.height)
        sh = Image.new('RGB', (W, y + rh + 16), (90, 90, 90)); dr = ImageDraw.Draw(sh)
        for k, ((x, y), im) in enumerate(zip(pos, ims)): sh.paste(im, (x, y + 12), im); dr.text((x, y), '%02d' % k, fill=(255, 255, 0))
        sh.save(os.path.join(od, '_모아보기.png')); print('%05X' % o, len(recs), sh.size)
