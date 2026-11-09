# -*- coding: utf-8 -*-
r"""랭킹 화면 그림 한글(2026-11-09) — RANKA.BIN 날것 4비트 VDP1 스프라이트(스테이트 work/states/하이스코어.state)
  · 제목 168×24(색 은행 0x20): ノーマルモード 0x8908 · タイムアタック 0x90E8 · ランキング 0x98C8
      글자마다 색 벌(채움/가장자리/밝은 줄): 노랑 e/f/4 · 하늘 a/b/6 · 분홍 c/d/7 · 주황 8/9/5 · 초록 1/2/4 · 테두리 3(진초록)
      → 주아 음절, 번갈아 기울임, 테두리 2px
  · 순위 «N位» 24×16 10장(색 은행 0x30) 0xADA8 + n×0xC0 — 숫자는 그대로, 오른쪽 位 자리(오른쪽 끝 12열)만 «위»
      줄별 색 = 원본 位 의 줄별 최빈 색, 오른쪽 가장자리 8, 아래 그림자 9
  python tools/rank_ko.py → work/plates/rank.pkl {RANKA.BIN: 새 바이트}, 미리보기 work/미리보기_그림/랭킹_원본_한글.png
"""
import os, sys, pickle, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf, menu_gfx as M
from menu_logo import syl_mask
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F7 = bdf.Font(os.path.join(M.FD, 'Galmuri7.bdf'))

TITLES = [(0x8908, '노멀 모드'), (0x90E8, '타임 어택'), (0x98C8, '랭킹')]
FAM = [(0xE, 0xF, 0x4), (0xA, 0xB, 0x6), (0xC, 0xD, 0x7), (0x8, 0x9, 0x5), (0x1, 0x2, 0x4)]   # 노랑·하늘·분홍·주황·초록
TW, TH = 168, 24
RANK0, RW, RH = 0xADA8, 24, 16


def get(b, o, w, h):
    return [[(b[o + (y * w + x) // 2] >> 4) if x % 2 == 0 else b[o + (y * w + x) // 2] & 15 for x in range(w)] for y in range(h)]


def put(b, o, P):
    h = len(P); w = len(P[0])
    for y in range(h):
        for x in range(0, w, 2): b[o + (y * w + x) // 2] = (P[y][x] << 4) | P[y][x + 1]


def title_art(text, fam0):
    """주아 음절 + 번갈아 기울임 → 168×24"""
    bh = 21
    while True:
        G = []; x = 0; k = 0
        for ch in text:
            if ch == ' ': x += 6; continue
            m, mw = syl_mask(ch, bh, 5 if k % 2 == 0 else -5, wx=1.45, fat=2)
            G.append(({(a + x, b) for a, b in m}, FAM[(fam0 + k) % len(FAM)])); x += mw + 3; k += 1
        allp = set().union(*(g for g, _ in G)); w = max(a for a, _ in allp) + 1; h = max(b for _, b in allp) + 1
        if w + 4 <= TW and h + 2 <= TH: break
        bh -= 1
    ox = 2; oy = (TH - h) // 2
    out = [[0] * TW for _ in range(TH)]
    for g, _ in G:                                                       # 테두리 3 (2px)
        for a, b in g:
            for dx in range(-1, 3):
                for dy in range(-1, 3):
                    X, Y = a + ox + dx, b + oy + dy
                    if 0 <= X < TW and 0 <= Y < TH and out[Y][X] == 0: out[Y][X] = 3
    for g, (fill, edge, hi) in G:
        for a, b in g:
            v = fill
            if (a + 1, b) not in g or (a, b + 1) not in g or (a + 1, b + 1) not in g: v = edge          # 오른쪽 아래 가장자리 = 어두운 색
            elif ((a, b - 1) not in g or (a - 1, b) not in g) and (a, b + 3) in g and (a + 3, b) in g: v = hi   # 굵은 획 왼쪽 위 = 밝은 줄
            out[b + oy][a + ox] = v
    return out, bh


def rank_art(P):
    """位 자리(오른쪽 끝 잉크 열 기준 12열) 지우고 «위»"""
    R = max(x for y in range(RH) for x in range(RW) if P[y][x]); L = R - 11
    rowc = {}
    for y in range(RH):
        c = collections.Counter(P[y][x] for x in range(L, R + 1) if P[y][x] not in (0, 8, 9))
        if c: rowc[y] = c.most_common(1)[0][0]
    out = [r[:] for r in P]
    for y in range(RH):
        for x in range(L, RW): out[y][x] = 0
    pts, _ = F7.draw('위'); x0 = min(x for x, _ in pts); y0 = min(y for _, y in pts)
    G = {(x - x0, y - y0) for x, y in pts}; G |= {(x + 1, y) for x, y in G}          # 1px 굵게
    gw = max(x for x, _ in G) + 1; gh = max(y for _, y in G) + 1
    top = min(rowc); ox = L + (12 - gw) // 2; oy = top
    G = {(x + ox, y + oy) for x, y in G}
    for x, y in G:                                                       # 그림자 9 (아래 2줄·오른쪽 아래)
        for d in ((0, 1), (0, 2), (1, 1), (1, 2)):
            q = (x + d[0], y + d[1])
            if q not in G and q[0] < RW and q[1] < RH: out[q[1]][q[0]] = 9
    for x, y in G:
        out[y][x] = 8 if (x + 1, y) not in G else rowc.get(y, rowc[max(rowc)])
    return out


def img(P, cram, bank):
    h = len(P); w = len(P[0]); im = Image.new('RGB', (w, h), (50, 50, 50)); p = im.load()
    for y in range(h):
        for x in range(w):
            if P[y][x]:
                c = struct.unpack_from('>H', cram, 2 * (bank + P[y][x]))[0]; p[x, y] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    return im


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src = open(os.path.join(ROOT, 'work', 'files', 'RANKA.BIN'), 'rb').read(); b = bytearray(src)
    cram = open(os.path.join(ROOT, 'work', 'mem', '하이스코어', 'CRAM.bin'), 'rb').read()
    pairs = []
    for i, (o, t) in enumerate(TITLES):
        P = get(src, o, TW, TH); new, bh = title_art(t, i * 2); put(b, o, new); pairs.append((P, new, 0x20)); print('제목', t, '음절 높이', bh)
    for n in range(10):
        o = RANK0 + n * 0xC0; P = get(src, o, RW, RH); new = rank_art(P); put(b, o, new); pairs.append((P, new, 0x30))
    pickle.dump({'RANKA.BIN': bytes(b)}, open(os.path.join(ROOT, 'work', 'plates', 'rank.pkl'), 'wb'))
    S = 4; W = TW * S * 2 + 30; H = 3 * (TH * S + 8) + 5 * (RH * S + 8) + 10
    sh = Image.new('RGB', (W, H), (90, 90, 90)); y = 8
    for P, N, bank in pairs[:3]:
        for k, Q in enumerate((P, N)): sh.paste(img(Q, cram, bank).resize((TW * S, TH * S), Image.NEAREST), (10 + k * (TW * S + 10), y))
        y += TH * S + 8
    for r in range(5):
        for c in range(2):
            P, N, bank = pairs[3 + r * 2 + c]
            for k, Q in enumerate((P, N)):
                sh.paste(img(Q, cram, bank).resize((RW * S, RH * S), Image.NEAREST), (10 + c * 2 * (RW * S + 10) * 2 + k * (RW * S + 10), y))
        y += RH * S + 8
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '랭킹_원본_한글.png')); print(sh.size)
