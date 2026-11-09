# -*- coding: utf-8 -*-
r"""이름 입력판 한글(2026-11-09) — NAMEA.BIN(날것) + RANKA.BIN(이름 글꼴 사본)
  · 이름 = 8바이트 «칸 번호»(0xDF 빈칸). 판 배치표 10열×7줄 = 70칸: 영문 0x000 · 히라가나 0x100 · 가타카나 0x200
  · 이름 글꼴 16×16 4비트(0x80 B): 칸 c 글자 = NAMEA 0xA764 − (252−c)×0x80 · RANKA 0x8B08 − (252−c)×0x80
      색: 3 노랑 채움 · 1 빨강 테두리 · 5 청록 그림자(오른쪽 아래)
  · 글자판 그림 176×120 4비트: 영문 0x19764 · 히라가나 0x1C0A4 · 가타카나 0x1E9E4 — 바탕 15 · 채움 3 · 테두리 1
      칸 왼쪽 위 x = 6+16i(i<5) / 94+16(i−5) · y = 6+16r(r<5) / 88(r=5) / 101(r=6)
  한글: 음절 128개(work/그림추출/이름입력/음절_128.txt) → 칸 0x3E~0xBD. 히라가나 판 = «한글1»(앞 63) · 가타카나 판 = «한글2»(뒤 65)
        7번째 줄 특수문자(히라 ・+*/=() 7칸 · 가타 ♥★♂♀♪ 5칸)는 원본 그대로(하스피 «특수문자 놔두기»), 나머지 = 음절(탁점 단추 자리 포함)
  python tools/name_ko.py → work/plates/name.pkl {NAMEA.BIN, RANKA.BIN}, 미리보기 work/미리보기_그림/이름입력판_원본_한글.png
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf, menu_gfx as M
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FB = bdf.Font(os.path.join(M.FD, 'Galmuri11-Bold.bdf'))
SYL = open(os.path.join(ROOT, 'work', '그림추출', '이름입력', '음절_128.txt'), encoding='utf-8').read().strip()
assert len(SYL) == 128
CELL0 = 0x3E
FONT_BASE = {'NAMEA.BIN': 0xA764, 'RANKA.BIN': 0x8B08}
BOARDS = [(0x100, 0x1C0A4, SYL[:63], 7), (0x200, 0x1E9E4, SYL[63:], 5)]   # (배치표, 판 그림, 음절, 7번째 줄 앞에서 남길 특수문자 칸 수 — 히라 ・+*/=() 7 · 가타 ♥★♂♀♪ 5)


def glyph_pts(ch):
    pts, _ = FB.draw(ch)
    x0 = min(x for x, _ in pts); y0 = min(y for _, y in pts)
    return {(x - x0, y - y0) for x, y in pts}


def font_glyph(ch):
    """16×16: 채움 3 · 테두리 1(1px 둘레) · 그림자 5(테두리 오른쪽 아래)"""
    G = glyph_pts(ch); w = max(x for x, _ in G) + 1; h = max(y for _, y in G) + 1
    ox = (14 - w) // 2 + 1; oy = 2 + (11 - h) // 2
    G = {(x + ox, y + oy) for x, y in G}
    O = {(x + dx, y + dy) for x, y in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G
    S = {(x + 1, y + 1) for x, y in G | O} - G - O
    a = np.zeros((16, 16), np.uint8)
    for st, v in ((S, 5), (O, 1), (G, 3)):
        for x, y in st:
            if 0 <= x < 16 and 0 <= y < 16: a[y, x] = v
    return a


def board_cell(ch):
    """판 칸 14×13: 채움 3 · 테두리 1"""
    G = glyph_pts(ch); w = max(x for x, _ in G) + 1; h = max(y for _, y in G) + 1
    ox = (14 - w) // 2; oy = (13 - h) // 2
    G = {(x + ox, y + oy) for x, y in G}
    O = {(x + dx, y + dy) for x, y in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G
    a = np.full((13, 14), 15, np.uint8)
    for st, v in ((O, 1), (G, 3)):
        for x, y in st:
            if 0 <= x < 14 and 0 <= y < 13: a[y, x] = v
    return a


def cell_xy(i, r):
    x = 6 + 16 * i if i < 5 else 94 + 16 * (i - 5)
    y = 6 + 16 * r if r < 5 else (88 if r == 5 else 101)
    return x - 1, y - 1                                                   # 원본 글자는 칸 안 1px 안쪽부터


def get4(b, o, w, h):
    d = np.frombuffer(b[o:o + w * h // 2], np.uint8); return np.stack([d >> 4, d & 15], 1).reshape(h, w).copy()


def put4(b, o, a):
    h, w = a.shape; f = a.reshape(-1); b[o:o + w * h // 2] = bytes(((f[0::2] << 4) | f[1::2]).astype(np.uint8))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src = {n: open(os.path.join(ROOT, 'work', 'files', n), 'rb').read() for n in ('NAMEA.BIN', 'RANKA.BIN')}
    out = {n: bytearray(b) for n, b in src.items()}
    na = out['NAMEA.BIN']; cellof = {}
    for k, ch in enumerate(SYL):
        c = CELL0 + k; cellof[ch] = c; g = font_glyph(ch)
        for n, base in FONT_BASE.items(): put4(out[n], base - (252 - c) * 0x80, g)
    pv = []
    for tbl, img, syl, keep in BOARDS:
        a = get4(src['NAMEA.BIN'], img, 176, 120); orig = a.copy(); k = 0
        order = [(r, i) for r in range(6) for i in range(5)] + [(r, i) for r in range(6) for i in range(5, 10)]   # 원본 50음처럼 왼쪽 덩어리(줄마다 왼→오) 위→아래, 다음 오른쪽 덩어리
        order += [(6, i) for i in range(keep, 10)]
        for r, i in order:
                p = tbl + r * 10 + i
                ch = syl[k]; k += 1; na[p] = cellof[ch]
                x, y = cell_xy(i, r)
                if r == 6 and i >= 8: a[y - 2:min(118, y + 16), x - 2:x + 16] = 15   # 탁점 단추 동그라미(16×16)는 칸보다 큼
                a[y:y + 13, x:x + 14] = board_cell(ch)
        assert k == len(syl)
        put4(na, img, a); pv.append((orig, a))
        print('판', hex(tbl), syl[0], '~', syl[-1])
    pickle.dump({n: bytes(b) for n, b in out.items()}, open(os.path.join(ROOT, 'work', 'plates', 'name.pkl'), 'wb'))
    pickle.dump(cellof, open(os.path.join(ROOT, 'work', 'plates', 'name_cells.pkl'), 'wb'))
    # 미리보기: 판(원본|한글) + 글꼴 줄
    cram = open(os.path.join(ROOT, 'work', 'mem', '이름입력_가타카나', 'CRAM.bin'), 'rb').read()
    pal = lambda bank: [(lambda e: ((e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3))(struct.unpack_from('>H', cram, 2 * (bank + i))[0]) for i in range(16)]
    P30 = np.array(pal(0x30), np.uint8)
    rc = open(os.path.join(ROOT, 'work', 'mem', '하이스코어', 'CRAM.bin'), 'rb').read()
    P10 = np.array([(lambda e: ((e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3))(struct.unpack_from('>H', rc, 2 * (0x10 + i))[0]) for i in range(16)], np.uint8)
    sh = Image.new('RGB', (2 * 180 + 10, 2 * 124 + 10 + 13 * 18), (40, 40, 40))
    for j, (o, n) in enumerate(pv):
        sh.paste(Image.fromarray(P30[o]), (0, j * 124)); sh.paste(Image.fromarray(P30[n]), (186, j * 124))
    y0 = 2 * 124 + 6
    for k in range(len(SYL)):
        g = get4(out['RANKA.BIN'], FONT_BASE['RANKA.BIN'] - (252 - (CELL0 + k)) * 0x80, 16, 16)
        im = P10[g].copy(); im[g == 0] = (40, 40, 40)
        sh.paste(Image.fromarray(im), ((k % 20) * 18, y0 + (k // 20) * 18))
    sh.resize((sh.width * 3, sh.height * 3), Image.NEAREST).save(os.path.join(ROOT, 'work', '미리보기_그림', '이름입력판_원본_한글.png')); print(sh.size)
