# -*- coding: utf-8 -*-
r"""선택·결정·취소 작은 버튼(YKBIN 0x3DCE8 #0~4, 64×32) — 판 안 만듦: 그림(아이콘) 그대로, 왼쪽 글자 칸만 지우고 한글
  글자 칸 = x 3~37, y 6~25 (아이콘 테 207 은 x≥38) · 바탕 219 · 원본 글자 = 흰색 30 + 번짐 136, 1px 획 → 갈무리11(1px 획) 흰색
  python tools/btn_ko.py → work/plates/btn.pkl, work/미리보기_그림/작은버튼.png(원본 | 한글, 색 은행 0x100)
"""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plates, bdf, menu_gfx as M
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = bdf.Font(os.path.join(M.FD, 'Galmuri11.bdf'))
KO = {0: '선택', 1: '선택', 2: '선택', 3: '결정', 4: '취소'}
BG, INK = 219, 30
X0, X1, Y0, Y1 = 3, 37, 6, 25


def build(w, h, px, text):
    out = bytearray(px)
    for y in range(Y0, Y1 + 1):
        for x in range(X0, X1 + 1):
            if out[y * w + x] != BG: out[y * w + x] = BG
    pts, _ = F.draw(text)
    ix0 = min(x for x, _ in pts); ix1 = max(x for x, _ in pts); iy0 = min(y for _, y in pts); iy1 = max(y for _, y in pts)
    ox = round(20.5 - (ix0 + ix1) / 2); oy = round(15 - (iy0 + iy1) / 2)   # 원본 글자 가운데(20.5, 15)
    for x, y in pts:
        X, Y = x + ox, y + oy
        if X0 <= X <= X1 and Y0 <= Y <= Y1: out[Y * w + X] = INK
    return bytes(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = open(os.path.join(ROOT, 'work', 'files', 'YKBIN'), 'rb').read(); recs = plates.chunk_3dce8(b)
    cram = open(os.path.join(ROOT, 'work', 'mem', '옵션', 'CRAM.bin'), 'rb').read()
    new = {k: build(*recs[k], t) for k, t in KO.items()}
    pickle.dump(new, open(os.path.join(ROOT, 'work', 'plates', 'btn.pkl'), 'wb'))
    S = 4; rows = [(M.to_img(*recs[k], cram, 0x100), M.to_img(recs[k][0], recs[k][1], new[k], cram, 0x100)) for k in KO]
    sh = Image.new('RGB', (64 * S * 2 + 30, len(rows) * (32 * S + 10) + 10), (40, 40, 40)); y = 10
    for a, n in rows:
        sh.paste(a.resize((64 * S, 32 * S), Image.NEAREST), (10, y)); sh.paste(n.resize((64 * S, 32 * S), Image.NEAREST), (20 + 64 * S, y)); y += 32 * S + 10
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '작은버튼.png')); print(sh.size)
