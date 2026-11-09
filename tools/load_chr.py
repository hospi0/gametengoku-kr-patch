# -*- coding: utf-8 -*-
r"""로딩 화면 LOADnn.CHR → PNG (2026-11-08)
  구조: u32 덩어리 수(2) · u32 오프셋[3](그림·팔레트·끝) · 그림 = [u32 압축 크기][오쿠무라 LZSS 0 채움] → 8비트 320×240(+머리 12 B?) · 팔레트 = [u32 256][u16 RGB555 ×256]
  python tools/load_chr.py → work/그림추출/로딩/LOADnn.png"""
import os, sys, struct, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lzss.INIT = 0


def decode(b):
    n = struct.unpack_from('>I', b, 0)[0]; offs = [struct.unpack_from('>I', b, 4 + 4 * i)[0] for i in range(n + 1)]
    s = struct.unpack_from('>I', b, offs[0])[0]
    d, _ = lzss.decompress(b[:offs[0] + 4 + s], offs[0] + 4, 1 << 22)
    pal = b[offs[1]:offs[2]]; cols = [struct.unpack_from('>H', pal, 4 + 2 * i)[0] for i in range(256)]
    return d, cols


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'files', 'LOAD*.CHR'))):
        d, cols = decode(open(p, 'rb').read())
        w = 320; h = len(d) // w; extra = len(d) - w * h
        im = Image.new('RGB', (w, h)); px = im.load()
        for i in range(w * h):
            e = cols[d[i]]; px[i % w, i // w] = ((e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3)
        out = os.path.join(ROOT, 'work', '그림추출', '로딩', os.path.basename(p)[:-4] + '.png'); im.save(out)
        print(os.path.basename(p), len(d), '남는 바이트', extra)
