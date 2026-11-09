# -*- coding: utf-8 -*-
r"""세로 화면 스테이지 클리어 입체 글자 한글(2026-11-09) — STC.BIN(가로용 STCX.BIN 의 큰 판, 머리 표 같음)
  조각 7개 [u16 폭][u16 높이][0x0018][0x0400] + 8비트 화소(CRAM 0x400+값, 팔레트 STCX 와 같음 — 스테이트 대조)
  게임 = 세로(타테) 화면이라 원래 VDP1 꼭짓점(A=왼위)으로 찍어도 플레이어 화면에선 STCX 와 같은 공식:
    플레이어 화면(px, py) = 텍스처(tx = w-1-py, ty = px)  → stcx_ko.piece 로 플레이어 방향(폭 h·높이 w)으로 그리고 눕혀 저장
  화면 자리(스테이트 work/states/스테이지클리어_세로_입체.state VDP1 0x14E0~): 플레이어 x = YA, y = 319 − XB
  python tools/stc_ko.py → work/plates/stc.pkl {'STC.BIN'}, work/미리보기_그림/스테이지클리어_세로_한글.png(원본 | 한글)
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stcx_ko
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# (머리 오프셋, 폭, 높이, 음절, 기울기°, 플레이어 x, 플레이어 y)
PIECES = [(1644, 64, 48, '스', 8, 8, 12), (4724, 64, 48, '테', -6, 32, 12), (7804, 40, 24, '이', 4, 72, 20),
          (16988, 72, 48, '지', 6, 88, 4), (14420, 64, 40, '클', -5, 120, 12), (11852, 64, 40, '리', 5, 144, 12), (8772, 64, 48, '어', -6, 168, 12)]
# 조각끼리 겹쳐 찍힘(뒤 명령이 위) → 음절마다 겹치지 않는 플레이어 x 칸 [x0, x1) 안에만 그림
SLOT = {'스': (8, 36), '테': (36, 68), '이': (72, 92), '지': (92, 124), '클': (124, 152), '리': (152, 182), '어': (182, 215)}

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = bytearray(open(os.path.join(ROOT, 'work', 'files', 'STC.BIN'), 'rb').read()); orig = bytes(b)
    cram = open(os.path.join(ROOT, 'work', 'mem', 'stclr_tate', 'CRAM.bin'), 'rb').read()
    scene = [Image.new('RGB', (230, 90), (24, 80, 150)) for _ in range(2)]
    for o, w, h, ch, t, sx, sy in PIECES:
        assert struct.unpack_from('>HH', orig, o - 8) == (w, h)
        x0, x1 = SLOT[ch]; gs, ov = stcx_ko.piece(x1 - x0, w, ch, t, squeeze=0.6)
        g = [[0] * h for _ in range(w)]
        for yy in range(w):
            for xx in range(x1 - x0): g[yy][x0 - sx + xx] = gs[yy][xx]
        print('%d %dx%d %s%s' % (o, w, h, ch, '  ⚠넘침 %d' % ov if ov else ''))
        flat = bytes(g[w - 1 - tx][ty] for ty in range(h) for tx in range(w)); b[o:o + w * h] = flat
        for i, px in enumerate((orig[o:o + w * h], flat)):
            disp = [px[ty * w + (w - 1 - py)] for py in range(w) for ty in range(h)]
            im = stcx_ko.to_img(disp, h, w, cram); scene[i].paste(im, (sx, sy), im)
    assert len(b) == len(orig)
    pickle.dump({'STC.BIN': bytes(b)}, open(os.path.join(ROOT, 'work', 'plates', 'stc.pkl'), 'wb'))
    S = 4; sh = Image.new('RGB', (230 * S, 180 * S + 10), (40, 40, 40))
    for i, im in enumerate(scene): sh.paste(im.resize((230 * S, 90 * S), Image.NEAREST), (0, i * (90 * S + 10)))
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '스테이지클리어_세로_한글.png')); print(sh.size)
