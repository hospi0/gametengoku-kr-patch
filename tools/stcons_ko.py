# -*- coding: utf-8 -*-
r"""게임 중 로딩 글자(2026-11-09) — «Now Loading・・・ / ただいま ロードちゅうです»
  출처: STCONS.B00 날것 16색 8×8 칸 0x1B5BC~ 27칸(VDP2 NBG3 0x7D7E0~, 스테이트 로딩중_다다이마) · 다른 파일 사본 없음
    칸 0~12 = Now Loading・・・(영문, 그대로) · 칸 13 = g 꼬리 · 칸 14~26 = ただいま ロードちゅうです(13칸 104 px, 색 2 한 색)
  python tools/stcons_ko.py → work/plates/stcons.pkl {STCONS.B00: 새 바이트}, work/미리보기_그림/로딩글자_원본_한글.png
"""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etca_ko import get, put, pts_of, wh, F7
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = 0x1B5BC + 14 * 32; NC = 13
TEXT = '지금 로딩 중입니다'

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src = open(os.path.join(ROOT, 'work', 'files', 'STCONS.B00'), 'rb').read(); b = bytearray(src)
    P = get(src, OFF, NC, 1); W = NC * 8
    G = pts_of(F7, TEXT); w, h = wh(G)
    assert w <= W and h <= 8, (w, h)
    ox = (W - w) // 2; oy = 8 - h
    out = [[0] * W for _ in range(8)]
    for x, y in G: out[y + oy][x + ox] = 2
    put(b, OFF, out)
    assert b[:OFF] == src[:OFF] and b[OFF + NC * 32:] == src[OFF + NC * 32:]
    print('폭', w, '/', W, '높이', h)
    pickle.dump({'STCONS.B00': bytes(b)}, open(os.path.join(ROOT, 'work', 'plates', 'stcons.pkl'), 'wb'))
    S = 5; ims = []
    for d in (src, bytes(b)):
        Q = get(d, 0x1B5BC, 13, 1) + get(d, OFF, 13, 1)
        im = Image.new('RGB', (W, 16)); p = im.load()
        for y in range(16):
            for x in range(W):
                if Q[y][x]: p[x, y] = (255, 255, 255)
        ims.append(im.resize((W * S, 16 * S), Image.NEAREST))
    sh = Image.new('RGB', (W * S * 2 + 30, 16 * S + 20), (60, 60, 60))
    sh.paste(ims[0], (10, 10)); sh.paste(ims[1], (20 + W * S, 10))
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '로딩글자_원본_한글.png'))
