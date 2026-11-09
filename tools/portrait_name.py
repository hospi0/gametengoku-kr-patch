# -*- coding: utf-8 -*-
r"""어레인지 플레이어 선택 초상화 이름 칸 찾기(2026-11-09) — VDP2 NBG0(16×16 칸, 256색, 1워드 맵 0x0) 에서 사각형 안 칸 → MN5BIN 첫 덩어리 풀린 자료 위치
  python tools/portrait_name.py <스테이트> <cx0> <cy0> <cx1> <cy1> → 칸 목록·파일 위치·확대 그림(work/그림추출/어레인지선택2/이름_<스테이트>.png)"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chunk0():
    lzss.INIT = 0
    b = open(os.path.join(ROOT, 'work', 'files', 'MN5BIN'), 'rb').read(); s = struct.unpack_from('>I', b, 0)[0]
    d, _ = lzss.decompress(b[:4 + s], 4, 1 << 23); return d


def cells(st, cx0, cy0, cx1, cy1, page=0):
    m = os.path.join(ROOT, 'work', 'mem', st)
    v = open(os.path.join(m, 'VDP2_VRAM.bin'), 'rb').read(); r = open(os.path.join(m, 'VDP2_REGS.bin'), 'rb').read()
    scn = struct.unpack_from('>H', r, 0x30)[0] & 31
    out = {}
    for cy in range(cy0, cy1 + 1):
        for cx in range(cx0, cx1 + 1):
            w = struct.unpack_from('>H', v, page * 0x800 + (cy * 32 + cx) * 2)[0]
            a = (((w & 0xFFF) << 2) | (scn & 3)) * 32
            out[(cx, cy)] = (w, a, v[a:a + 256].ljust(256, b'\0'))
    return out, open(os.path.join(m, 'CRAM.bin'), 'rb').read()


def px16(blk):
    o = [[0] * 16 for _ in range(16)]
    for i in range(256):
        q = i // 64; r = i % 64; o[(q // 2) * 8 + r // 8][(q % 2) * 8 + r % 8] = blk[i]
    return o


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    st = sys.argv[1]; cx0, cy0, cx1, cy1 = map(int, sys.argv[2:6]); page = int(sys.argv[6]) if len(sys.argv) > 6 else 0   # 현재 초상화 = NBG2(맵 쪽 2), NBG0 = 직전 캐릭터
    d = chunk0(); cs, cram = cells(st, cx0, cy0, cx1, cy1, page)
    C = [(lambda c: ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))(struct.unpack_from('>H', cram, 2 * i)[0]) for i in range(2048)]
    W = (cx1 - cx0 + 1) * 16; H = (cy1 - cy0 + 1) * 16; im = Image.new('RGB', (W, H)); pp = im.load()
    for (cx, cy), (w, a, blk) in cs.items():
        k = d.find(blk); n = d.count(blk) if k >= 0 else 0
        print((cx, cy), hex(w), 'VRAM', hex(a), '파일', hex(k), '같은 칸 수', n)
        P = px16(blk)
        for y in range(16):
            for x in range(16):
                if P[y][x]: pp[(cx - cx0) * 16 + x, (cy - cy0) * 16 + y] = C[P[y][x]]
    im.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(ROOT, 'work', '그림추출', '어레인지선택2', '이름_%s_p%d.png' % (st, page)))
