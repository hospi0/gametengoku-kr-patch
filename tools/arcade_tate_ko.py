# -*- coding: utf-8 -*-
r"""아케이드 세로(타테) 모드 선택 화면 한글(2026-11-09) — MN3BIN = MN4BIN 과 같은 레코드 자리(0x3800~ 사슬 72)의 세로판
  · 입체 제목 조각(#0~6 モードセレクト, #12~20 プレイヤーセレクト) = 가로판 한글 조각(arcade.pkl 의 MN4)을 시계 방향으로 돌려
    MN3 색표(같은 은행: 제목 0 · 플레이어 2)의 가까운 색으로 다시 맞춤(세로판은 음영을 새로 그려 그대로 복사 안 됨)
  · 금속판(#7·#8, 은행 24) = 세로판을 반시계로 세워 arcade2_ko.plate 로 지우고 쓴 뒤 다시 시계 방향으로
  python tools/arcade_tate_ko.py → work/plates/arcade_tate.pkl {번호: 화소}, work/미리보기_그림/아케이드_세로.png(원본 | 한글)
"""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcade_ko as A, arcade2_ko as A2
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANKS = {**{k: 0 for k in range(0, 7)}, **{k: 2 for k in range(12, 21)}}


def grid(b, o, w, h): return [[b[o + y * w + x] for x in range(w)] for y in range(h)]
def rot_cw(g): h = len(g); w = len(g[0]); return [[g[h - 1 - y][x] for y in range(h)] for x in range(w)]
def rot_ccw(g): h = len(g); w = len(g[0]); return [[g[y][w - 1 - x] for y in range(h)] for x in range(w)]
def flat(g): return bytes(v for r in g for v in r)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    m4 = open(os.path.join(ROOT, 'work', 'files', 'MN4BIN'), 'rb').read(); m3 = open(os.path.join(ROOT, 'work', 'files', 'MN3BIN'), 'rb').read()
    r4 = A.chain(m4, 0x3800); r3 = A.chain(m3, 0x3800)
    ko = {k: v for (f, k), v in pickle.load(open(os.path.join(ROOT, 'work', 'plates', 'arcade.pkl'), 'rb')).items() if f == 'MN4'}
    res = {}; pairs = []
    for k, bank in BANKS.items():
        P4 = A.pal(m4, bank * 0x200); P3 = A.pal(m3, bank * 0x200); cache = {}
        o4, w4, h4 = r4[k]; o3, w3, h3 = r3[k]
        g = rot_cw(grid(ko[k], 0, w4, h4)); assert (len(g[0]), len(g)) == (w3, h3), k
        out = [[(A.nearest(P3, P4[v], cache) if v else 0) for v in row] for row in g]
        res[k] = flat(out)
        pairs.append((grid(m3, o3, w3, h3), out, P3))
    P24 = A.pal(m3, 24 * 0x200)
    for k, (lines, tilt) in A2.PLATE.items():
        o3, w3, h3 = r3[k]
        up = rot_ccw(grid(m3, o3, w3, h3)); W, H = len(up[0]), len(up)
        new, ov = A2.plate(flat(up), 0, W, H, lines, tilt, P24)
        back = rot_cw(grid(new, 0, W, H)); res[k] = flat(back)
        print('금속판', k, lines, '넘침', ov)
        pairs.append((grid(m3, o3, w3, h3), back, P24))
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'arcade_tate.pkl'), 'wb'))
    def im(g, P):
        i = Image.new('RGB', (len(g[0]), len(g)), (40, 60, 140)); pp = i.load()
        for y, r in enumerate(g):
            for x, v in enumerate(r):
                if v: pp[x, y] = P[v]
        return i.transpose(Image.ROTATE_90)                              # 읽기 쉽게 반시계로 세워 보여 줌
    S = 2; ims = [(im(a, P), im(b, P)) for a, b, P in pairs]
    W = sum(a.width * S + 6 for a, _ in ims) + 10; H = max(a.height for a, _ in ims) * S * 2 + 30
    sh = Image.new('RGB', (W, H), (30, 30, 30)); x = 10
    for a, b in ims:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (x, 10)); sh.paste(b.resize((b.width * S, b.height * S), Image.NEAREST), (x, 20 + max(q.height for q, _ in ims) * S)); x += a.width * S + 6
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '아케이드_세로.png')); print(sh.size)
