# -*- coding: utf-8 -*-
r"""어레인지 모드 «게임 모드 셀렉트» 화면 그림 한글(2026-11-09) — MN5BIN 0x39938 = [색표 3벌 0x600] + 레코드 14 [u16 폭][u16 높이][8비트]
  은행: 0 = 제목·選ぶ/決定戻る 버튼 · 1 = 작은 버튼·큰 로고(밝음) · 2 = 같은 그림 어둡게(안 고른 것)
  #0 제목 208×32 · #8 = 제목 그림자(같은 모양, 색 242) · #1~5 작은 버튼 88×24 · #6 選ぶ 80×32 · #7 決定·戻る 128×32
  #9·#10 그림자 상자 · #11 ノーマルモード · #12 タイムアタック(112×72) · #13 고름 테
  python tools/mn5_ko.py → work/plates/mn5.pkl, work/미리보기_그림/어레인지선택_한글.png(원본 | 한글, 실제 색)
"""
import os, sys, struct, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss, bdf, menu_gfx as M
from menu_logo import syl_mask
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
O = 0x39938
F11 = bdf.Font(os.path.join(M.FD, 'Galmuri11.bdf'))


def load(path=None):
    lzss.INIT = 0
    b = open(path or os.path.join(ROOT, 'work', 'files', 'MN5BIN'), 'rb').read()
    s = struct.unpack_from('>I', b, O)[0]; d, _ = lzss.decompress(b[:O + 4 + s], O + 4, 1 << 23)
    ct = d[:0x600]; p = 0x600; recs = []
    for _ in range(14):
        w, h = struct.unpack_from('>HH', d, p); recs.append((w, h, d[p + 4:p + 4 + w * h])); p += 4 + w * h
    return ct, recs


def rgb(ct, bank, c):
    e = struct.unpack_from('>H', ct, bank * 0x200 + 2 * c)[0]; return ((e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3)


def text_pts(t, font=F11):
    pts, _ = font.draw(t); return pts


def place(pts, cx, cy):
    x0 = min(x for x, _ in pts); x1 = max(x for x, _ in pts); y0 = min(y for _, y in pts); y1 = max(y for _, y in pts)
    ox = round(cx - (x0 + x1) / 2); oy = round(cy - (y0 + y1) / 2)
    return [(x + ox, y + oy) for x, y in pts]


# ── 작은 버튼 #1~5(88×24): 안쪽 x4~83·y6~18 = 바탕 157, 흰 글자 159, «있음/없음» 초록 133, ①② 동그라미(x≥63)는 원본 그대로
SMALL = {1: [('대화 데모 ', 159), ('있음', 133)], 2: [('대화 데모 ', 159), ('없음', 133)], 3: [('연습 스테이지', 159)],
         4: [('스테이지', 159)], 5: [('스테이지', 159)]}


def small(w, h, px, parts, k):
    out = bytearray(px); x1 = 61 if k in (4, 5) else 83
    for y in range(6, 19):
        for x in range(4, x1 + 1): out[y * w + x] = 157
    full = text_pts(''.join(t for t, _ in parts))
    cx = (4 + x1) / 2 + (2 if k in (4, 5) else 0)
    pts = place(full, cx, 12)
    cut = None
    if len(parts) == 2:
        pre = text_pts(parts[0][0].rstrip()); cut = min(x for x, _ in pts) + max(x for x, _ in pre) - min(x for x, _ in pre) + 2
    over = 0
    for x, y in pts:
        if not (4 <= x <= x1 and 6 <= y <= 18): over += 1; continue
        out[y * w + x] = parts[1][1] if cut is not None and x > cut else parts[0][1]
    return bytes(out), over


# ── 選ぶ #6 · 決定/戻る #7: 원본 글자(초록 225 + 청록 테 231 계열)만 바탕 237 로 지우고 같은 색으로 한글(갈무리11 + 테 1px)
TXT_COLS = {225, 231, 233, 234, 235, 218, 209}
FILLC = (225, 209)                                                       # 글자 채움: 決定·戻る = 225(초록) · 選ぶ = 209(연노랑)
BTN = {6: [('선택', None)], 7: [('결정', 0), ('취소', 1)]}


def fillc(w, h, px):
    c = collections.Counter(px[y * w + x] for y in range(6, 23) for x in range(w) if px[y * w + x] in FILLC)
    return c.most_common(1)[0][0]


def text_runs(w, h, px):
    fc = fillc(w, h, px)
    xs = sorted({x for y in range(6, 23) for x in range(w) if px[y * w + x] == fc and not (x < 30 and w == 80)})
    runs = []; a = xs[0]; p = xs[0]
    for x in xs[1:]:
        if x - p > 6: runs.append((a, p)); a = x
        p = x
    runs.append((a, p)); return runs


def button(w, h, px, items):
    out = bytearray(px); runs = text_runs(w, h, px); fc = fillc(w, h, px)
    for (a, b) in runs:
        for y in range(6, 23):
            for x in range(a - 2, b + 3):
                if out[y * w + x] in TXT_COLS: out[y * w + x] = 237
    over = 0
    for (t, _), (a, b) in zip(items, runs):
        pts = place(text_pts(t), (a + b) / 2, 14)
        G = set(pts); OL = {(x + dx, y + dy) for x, y in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G
        for x, y in OL:
            if 6 <= y <= 22 and a - 3 <= x <= b + 3: out[y * w + x] = 231
            else: over += 1
        for x, y in G: out[y * w + x] = fc
    return bytes(out), over


# ── 큰 로고 #11·#12(112×72): 판 = 줄마다 한 색(세로 그라데이션), 둥근 모서리 · 글자 = 주아 2줄, 흰 테 2px, 진보라 그림자(+3,+3), 채움 = 원본 줄별 색
BIG = {11: (('노멀', -4.0), ('모드', 4.0)), 12: (('타임', -4.0), ('어택', 4.0))}
WHITE = 1


def plate_rows(recs):
    """판 줄 색·범위 = #11·#12 두 그림에서 줄 왼쪽 끝 색(글자 안 닿음), 범위 = 그 색이 나오는 최소~최대 x(두 그림 합)"""
    w, h, _ = recs[11]; rows = {}
    for y in range(h):
        cs = [recs[k][2][y * w + x] for k in (11, 12) for x in range(w) if recs[k][2][y * w + x]]
        if not cs: continue
        c = next((recs[11][2][y * w + x] for x in range(w) if recs[11][2][y * w + x]), 0)
        xs = [x for k in (11, 12) for x in range(w) if recs[k][2][y * w + x] == c]
        rows[y] = (c, min(xs), max(xs))
    return rows


def big(ct, w, h, px, k, rows):
    isfill = (lambda c: rgb(ct, 1, c)[2] <= 64) if k == 11 else (lambda c: (lambda r: r[2] == 248 and r[0] <= 160 and r[1] >= 56)(rgb(ct, 1, c)))
    isshadow = lambda c: rgb(ct, 1, c)[2] == 120
    fill = {}; shad = {}
    for y in range(h):
        cf = collections.Counter(c for c in px[y * w:(y + 1) * w] if c and isfill(c))
        cs = collections.Counter(c for c in px[y * w:(y + 1) * w] if c and isshadow(c))
        if cf: fill[y] = cf.most_common(1)[0][0]
        if cs: shad[y] = cs.most_common(1)[0][0]
    fy = sorted(fill); sy = sorted(shad)
    near = lambda d, ks, y: d[min(ks, key=lambda q: abs(q - y))]
    out = bytearray(w * h)
    for y, (c, a, b) in rows.items():
        for x in range(a, b + 1): out[y * w + x] = c
    G = {}
    lines = BIG[k]; bh = 29; top = [3, 33]; lx = [5, 27]
    for i, (t, tilt) in enumerate(lines):
        x = lx[i]
        for ch in t:
            m, mw = syl_mask(ch, bh, tilt, wx=1.18, fat=2)
            for a, b in m: G[(a + x, b + top[i])] = None
            x += mw + 1
    O2 = {(a + dx, b + dy) for a, b in G for dx in range(-2, 3) for dy in range(-2, 3)} - set(G)
    Sh = {(a + d, b + d) for a, b in set(G) | O2 for d in (1, 2, 3)} - set(G) - O2
    over = 0
    inside = lambda x, y: y in rows and rows[y][1] <= x <= rows[y][2]
    for x, y in Sh:
        if inside(x, y): out[y * w + x] = near(shad, sy, y)
        else: over += 1
    for x, y in O2:
        if inside(x, y): out[y * w + x] = WHITE
        else: over += 1
    for x, y in G:
        if inside(x, y): out[y * w + x] = near(fill, fy, y)
        else: over += 1
    return bytes(out), over


# ── 제목 #0(208×32) «게임 모드 셀렉트»: 노랑 채움(원본 줄별) + 파랑 테 189 1px, 음절마다 번갈아 기울임 · #8 그림자 = 같은 모양 242
TITLE = [('게', 4, 1), ('임', -4, -1), (' ', 0, 0), ('모', 4, 1), ('드', -4, -1), (' ', 0, 0), ('셀', 4, 1), ('렉', -4, -1), ('트', 4, 1)]


def title(ct, recs):
    w, h, px = recs[0]
    fill = {}
    for y in range(h):
        c = collections.Counter(v for v in px[y * w:(y + 1) * w] if v and rgb(ct, 0, v)[2] <= 8 and rgb(ct, 0, v)[1] >= 200)
        if c: fill[y] = c.most_common(1)[0][0]
    fy = sorted(fill)
    bh = 26; gap = 0; sp = 5
    ms = [(syl_mask(ch, bh, t, wx=0.95, fat=2) if ch != ' ' else (set(), sp), dy) for ch, t, dy in TITLE]
    tw = sum(mw for (_, mw), _ in ms) + gap * (len(ms) - 1); x = (w - tw) // 2
    G = set()
    for (m, mw), dy in ms:
        G |= {(a + x, b + 2 + dy) for a, b in m}; x += mw + gap
    OL = {(a + dx, b + dy) for a, b in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G
    out = bytearray(w * h); over = 0
    for x, y in OL:
        if 0 <= x < w and 0 <= y < h: out[y * w + x] = 189
        else: over += 1
    for x, y in G:
        if 0 <= x < w and 0 <= y < h: out[y * w + x] = fill[min(fy, key=lambda q: abs(q - y))]
        else: over += 1
    sh = bytes(242 if c else 0 for c in out)
    return bytes(out), sh, over


def to_img(ct, bank, w, h, px):
    im = Image.new('RGB', (w, h), (150, 200, 120)); pp = im.load()            # 바탕 = 화면 연두(실제 배경 비슷하게)
    for i, c in enumerate(px):
        if c: pp[i % w, i // w] = rgb(ct, bank, c)
    return im


# ── MN5BIN 첫 덩어리(0x0, 풀면 581,396 B): 0x2E00 부터 레코드 사슬 26개 — 어레인지 «플레이어 셀렉트» 화면(2026-11-09 하스피 «이 화면 하나도 안 됐어»)
#   #3 決定/戻る 버튼 112×32 · #5 プレイヤーセレクト 제목 224×40(연두 테 노랑 글자) · 색표 은행 0 = 0x0 (CRAM 은행 1)
def load0():
    lzss.INIT = 0
    b = open(os.path.join(ROOT, 'work', 'files', 'MN5BIN'), 'rb').read(); s = struct.unpack_from('>I', b, 0)[0]
    d, _ = lzss.decompress(b[:4 + s], 4, 1 << 23); p = 0x2E00; recs = []
    while True:
        w, h = struct.unpack_from('>HH', d, p)
        if not (1 <= w <= 400 and 1 <= h <= 400): break
        recs.append((w, h, d[p + 4:p + 4 + w * h])); p += 4 + w * h
    return d[:0x200], recs


def btn0(w, h, px):
    """C 決定 B 戻る(112×32): 글자 칸 x24~56·x76~106, y6~19 를 바탕 170 으로 지우고 굵은 갈무리11 청록 163"""
    out = bytearray(px)
    y0, y1 = 9, 22                                                       # 글자 행(원본 실측 — 위아래 테두리 4~8·24~28 행은 안 건드림)
    for (x0, x1), t in (((24, 56), '결정'), ((76, 106), '취소')):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if out[y * w + x] not in (0,): out[y * w + x] = 170
        pts = place(text_pts(t, FB0), (x0 + x1) / 2, (y0 + y1) / 2)
        for x, y in pts: out[y * w + x] = 163
    return bytes(out)


def title0(w, h, px, P):
    """224×40 «플레이어 셀렉트»: 주아 음절 번갈아 기울임, 노랑 채움(원본 줄별) · 연두 테 1(115) · 진초록 테 1+그림자(153)"""
    fill = {}
    for y in range(h):
        c = collections.Counter(v for v in px[y * w:(y + 1) * w] if v and P[v][2] < 40 and P[v][0] > 200)
        if c: fill[y] = c.most_common(1)[0][0]
    fy = sorted(fill)
    for bh in range(32, 14, -1):
        G = set(); x = 0; i = 0
        for ch in '플레이어 셀렉트':
            if ch == ' ': x += bh // 3; continue
            m, mw = syl_mask(ch, bh, [5, -4, 4, -5][i % 4], wx=1.0, fat=1); i += 1
            G |= {(a + x, b + (1 if i % 2 else -1)) for a, b in m}; x += mw + 1
        gw = max(a for a, _ in G) + 1; gh = max(b for _, b in G) - min(b for _, b in G) + 1
        if gw + 6 <= w and gh + 6 <= h: break
    y0 = min(b for _, b in G); G = {(a + (w - gw) // 2 - 1, b - y0 + (h - gh) // 2 - 1) for a, b in G}
    O1 = {(a + dx, b + dy) for a, b in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G
    O2 = {(a + dx, b + dy) for a, b in G | O1 for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G - O1
    Sh = {(a + 1, b + 1) for a, b in G | O1 | O2} - G - O1 - O2
    out = bytearray(w * h)
    for S_, v in ((Sh, 153), (O2, 153), (O1, 115)):
        for a, b in S_:
            if 0 <= a < w and 0 <= b < h: out[b * w + a] = v
    for a, b in G:
        if 0 <= a < w and 0 <= b < h: out[b * w + a] = fill[min(fy, key=lambda q: abs(q - b))]
    return bytes(out)


FB0 = bdf.Font(os.path.join(M.FD, 'Galmuri11-Bold.bdf'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    ct, recs = load(); new = {}
    t0, t8, ov = title(ct, recs); new[0] = t0; new[8] = t8; print('#0 제목 넘침', ov)
    for k, parts in SMALL.items():
        new[k], ov = small(*recs[k], parts, k); print('#%d 넘침 %d' % (k, ov))
    for k, items in BTN.items():
        new[k], ov = button(*recs[k], items); print('#%d 넘침 %d' % (k, ov))
    rows = plate_rows(recs)
    for k in BIG:
        new[k], ov = big(ct, *recs[k], k, rows); print('#%d 넘침 %d' % (k, ov))
    pal0, r0 = load0(); P0 = [rgb(pal0, 0, i) for i in range(256)]
    n0 = {3: btn0(*r0[3]), 5: title0(*r0[5], P0)}
    pickle.dump(n0, open(os.path.join(ROOT, 'work', 'plates', 'mn5_0.pkl'), 'wb'))
    S0 = 3; sh0 = Image.new('RGB', (224 * S0 * 2 + 30, (40 + 32) * S0 + 30), (200, 180, 140))
    for i, k in enumerate((5, 3)):
        w, h, px = r0[k]
        for j, src in enumerate((px, n0[k])):
            im = Image.new('RGB', (w, h), (210, 190, 150)); pp = im.load()
            for q, c in enumerate(src):
                if c: pp[q % w, q // w] = P0[c]
            sh0.paste(im.resize((w * S0, h * S0), Image.NEAREST), (10 + j * (224 * S0 + 10), 10 + i * (40 * S0 + 10)))
    sh0.save(os.path.join(ROOT, 'work', '미리보기_그림', '어레인지_플레이어선택.png'))
    pickle.dump(new, open(os.path.join(ROOT, 'work', 'plates', 'mn5.pkl'), 'wb'))
    S = 3; show = [(0, 0), (8, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 0), (7, 0), (11, 1), (12, 1), (11, 2), (12, 2)]
    pairs = [(to_img(ct, bk, recs[k][0], recs[k][1], recs[k][2]), to_img(ct, bk, recs[k][0], recs[k][1], new[k])) for k, bk in show]
    W = 208 * S * 2 + 30; H = sum(a.height * S + 8 for a, _ in pairs) + 8
    sh = Image.new('RGB', (W, H), (40, 40, 40)); y = 8
    for a, n in pairs:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(n.resize((n.width * S, n.height * S), Image.NEAREST), (20 + 208 * S, y)); y += a.height * S + 8
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '어레인지선택_한글.png')); print(sh.size)
