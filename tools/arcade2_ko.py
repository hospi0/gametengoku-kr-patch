# -*- coding: utf-8 -*-
r"""아케이드 선택 화면 글자판(2026-11-09)
  · MN2LZ #13·#14 모니터(136×136) 위 «ヨコ画面»·«タテ画面» → 가로 화면 / 세로 화면 (색표 은행 1 = 고름, 2 = 안 고름 — 같은 번호)
    글자 화소(은행 1에서 초록·연두) 지움: 그 열의 모니터 윗선(글자 아닌 첫 화소)보다 위면 투명, 아래면 바로 아래 글자 아닌 화소 색
    새 글자 = arcade_ko 방식 4배 입체(앞면 연두·옆면 초록), 원래 글자 상자 안, 원본처럼 살짝 기울임
  · MN4BIN #7·#8 금속판(144×128, 은행 24) «ノーマルゲーム»(분홍)·«タイムアタック»(노랑) → 노멀 게임 / 타임 어택
    글자 + 둘레 어두운 새김 테 지움 → 같은 열 위아래 가장 가까운 금속 화소(세로 결 이어짐) · 새 글자 = 글자색 채움 + 왼쪽 위 어두운 새김 · 오른쪽 아래 밝은 턱
  python tools/arcade2_ko.py → work/plates/arcade2.pkl, work/미리보기_그림/아케이드_글자판.png(원본 | 한글)
"""
import os, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcade_ko as A
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MON = {13: ('가로 화면', -4), 14: ('세로 화면', -6)}
PLATE = {7: (('노멀', '게임'), -14), 8: (('타임', '어택'), -14)}


def mask_text(m, wx, bh, tilt):
    F = set(); x = 0
    for ch in m:
        if ch == ' ': x += bh * A.SS // 3; continue
        g, mw = A._syl(ch, bh * A.SS, tilt, font=A.BHS, wx=wx, fat=0)
        F |= {(a + x, b) for a, b in g}; x += mw + A.SS
    return F


def monitor(d, o, w, h, text, tilt, P):
    px = [list(d[o + y * w:o + (y + 1) * w]) for y in range(h)]
    green = lambda v: v and (P[v][1] > P[v][0] + 8 and P[v][1] > P[v][2] + 8 or (P[v][0] > 180 and P[v][1] > 180 and P[v][2] < 100))   # 어두운 초록 옆면까지
    lab = {(x, y) for y in range(0, 34) for x in range(w) if green(px[y][x])}   # 34행 아래는 모니터 화면 속 초록
    fill = [[px[y][x] for x in range(w)] for y in range(h)]
    xs = [x for x, _ in lab]; ys = [y for _, y in lab]; bx0, bx1, by0, by1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1
    # 상자 통째로 지움: 모니터 윗선 = 상자 바로 왼쪽·오른쪽 열의 윗선(첫 불투명 행)을 이어 그은 선 · 선 위 = 투명 · 선 아래 = 상자 바로 아래 행 색
    topf = lambda x: next((y for y in range(h) if px[y][x]), h)
    tl, tr = topf(bx0 - 1), topf(bx1 + 1); mcache = {}
    for x in range(bx0, bx1 + 1):
        t = round(tl + (tr - tl) * (x - bx0) / max(1, bx1 - bx0))
        for y in range(by0, by1 + 1):
            if y < t: fill[y][x] = 0; continue
            L = px[y][bx0 - 1] or px[y][bx1 + 1]; Rr = px[y][bx1 + 1] or L   # 같은 행 상자 양옆 테두리 색을 가로로 섞음(한쪽만 쓰면 가운데 경계 — 하스피 «찌꺼기»)
            f = (x - bx0 + 1) / (bx1 - bx0 + 2)
            fill[y][x] = A.nearest(P, tuple(round(P[L][c] * (1 - f) + P[Rr][c] * f) for c in range(3)), mcache) if L and Rr else 0
    front = collections.Counter(px[y][x] for x, y in lab if P[px[y][x]][2] < 100 and P[px[y][x]][0] > 150).most_common(3)
    side = collections.Counter(px[y][x] for x, y in lab if P[px[y][x]][0] < 100).most_common(4)
    col = dict(front=[P[v] for v, _ in front][:2] or [(200, 248, 40)], right=sorted([P[v] for v, _ in side], key=sum, reverse=True) or [(0, 120, 40)], bottom=sorted([P[v] for v, _ in side], key=sum, reverse=True) or [(0, 160, 40)])
    W = bx1 - bx0 + 1; H = by1 - by0 + 1
    for bh in range(H - 4, 8, -1):
        F = mask_text(text, 0.95, bh, tilt)
        fw = max(a for a, _ in F) // A.SS + 1 + 3; fh = max(b for _, b in F) // A.SS + 1 + 3
        if fw <= W + 4 and fh <= H: break
    ox = bx0 + (W - fw) // 2; oy = by0 + (H - fh) // 2
    F = {(a + ox * A.SS, b + oy * A.SS) for a, b in F}
    img = A.down(A.shade_hi(F, col, [(1, 0), (1, 1), (2, 1), (3, 2)]), w, h)
    cache = {}
    for (x, y), c in img.items(): fill[y][x] = A.nearest(P, c, cache)
    return bytes(v for r in fill for v in r)


def plate(d, o, w, h, lines, tilt, P):
    px = [list(d[o + y * w:o + (y + 1) * w]) for y in range(h)]
    lum = lambda v: sum(P[v]) / 3
    sat = lambda v: v and (max(P[v]) - min(P[v]) > 90)
    fillc = collections.Counter(px[y][x] for y in range(h) for x in range(w) if sat(px[y][x])).most_common(1)[0][0]
    fc = P[fillc]
    like = lambda v: v and max(P[v]) - min(P[v]) > 40 and P[v][2] <= max(P[v][0], P[v][1]) - 20 and (P[v][0] - P[v][1]) * (fc[0] - fc[1]) >= 0   # 글자색 계열(파란 나사 빼고)
    T = {(x, y) for y in range(h) for x in range(w) if like(px[y][x])}
    # 새김 테 = 글자 둘레 3px 안의 어두운 화소
    near = {(x + dx, y + dy) for x, y in T for dx in range(-3, 4) for dy in range(-3, 4)}
    metal = [lum(px[y][x]) for y in range(h) for x in range(w) if px[y][x] and (x, y) not in near]
    mid = sorted(metal)[len(metal) // 2]
    E = {(x, y) for x, y in near - T if 0 <= x < w and 0 <= y < h and px[y][x] and lum(px[y][x]) < mid - 45}
    R = T | E | {(x + dx, y + dy) for x, y in T for dx in range(-2, 3) for dy in range(-2, 3) if 0 <= x + dx < w and 0 <= y + dy < h and px[y + dy][x + dx] and lum(px[y + dy][x + dx]) > mid - 70}   # 섞인 가장자리 2px(판 테두리 어두운 데는 빼고)
    out = [r[:] for r in px]
    okm = lambda v: v and abs(lum(v) - mid) < 50 and max(P[v]) - min(P[v]) < 40   # 금속 결 화소만(나사·어두운 테를 끌어오면 세로 줄 찌꺼기 — 하스피 «타 왼쪽 위 찌꺼기»)
    blue = [(x, y) for y in range(h) for x in range(w) if px[y][x] and P[px[y][x]][2] > max(P[px[y][x]][0], P[px[y][x]][1]) + 30]   # 나사 머리(파랑)
    bolt = {(x + dx, y + dy) for x, y in blue for dx in range(-6, 7) for dy in range(-4, 9)}                                          # 나사 둘레(아래로 더) = 메움 재료에서 뺌
    for x, y in R:
        up = next((yy for yy in range(y - 1, -1, -1) if (x, yy) not in R and (x, yy) not in bolt and okm(px[yy][x])), None); dn = next((yy for yy in range(y + 1, h) if (x, yy) not in R and (x, yy) not in bolt and okm(px[yy][x])), None)
        cand = [yy for yy in (up, dn) if yy is not None and px[yy][x]]
        out[y][x] = px[min(cand, key=lambda yy: abs(yy - y))][x] if cand else 0
    # 새 글자: 두 줄, 판 기울기대로
    xs = [x for x, _ in T]; ys = [y for _, y in T]; bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    W = bx1 - bx0 + 1; H = by1 - by0 + 1
    dark = min((v for v in set(px[y][x] for x, y in E)), key=lum) if E else min(set(out[y][x] for y in range(h) for x in range(w) if out[y][x]), key=lum)
    light = max(set(out[y][x] for y in range(h) for x in range(w) if out[y][x]), key=lum)
    inside = lambda x, y: 0 <= x < w and 0 <= y < h and out[y][x] and all(0 <= x + dx < w and 0 <= y + dy < h and out[y + dy][x + dx] for dx in (-4, 4) for dy in (-4, 4))
    for bh in range(H // 2 + 6, 8, -1):                                  # 판 안(가장자리 4px 여유)에 다 들 때까지 줄임
        Ms = [mask_text(t, 1.0, bh, tilt) for t in lines]
        lw = [max(a for a, _ in M) // A.SS + 1 for M in Ms]; lh = bh + 3
        G = set()
        for i, M in enumerate(Ms):
            ox = bx0 + (W - lw[i]) // 2 + (5 if i else -5); oy = by0 + (H - 2 * lh) // 2 + i * lh
            cnt = collections.Counter((a // A.SS + ox, b // A.SS + oy) for a, b in M)
            G |= {p for p, n in cnt.items() if n >= A.SS * A.SS // 2}
        if all(inside(x, y) for x, y in G): break
    over = 0
    for x, y in G:
        for dx, dy, v in ((-1, -1, dark), (-1, 0, dark), (0, -1, dark), (-2, -1, dark), (-1, -2, dark), (1, 1, light)):
            q = (x + dx, y + dy)
            if q not in G and 0 <= q[0] < w and 0 <= q[1] < h and out[q[1]][q[0]]: out[q[1]][q[0]] = v
    for x, y in G:
        if 0 <= x < w and 0 <= y < h and out[y][x]: out[y][x] = fillc
        else: over += 1
    return bytes(v for r in out for v in r), over


def show(b, w, h, P):
    im = Image.new('RGB', (w, h), (40, 60, 140)); pp = im.load()
    for i, v in enumerate(b):
        if v: pp[i % w, i // w] = P[v]
    return im


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    F, _, _ = A.load(); res = {}; pairs = []
    d, recs, _ = F['MN2']; P1 = A.pal(d, 0x200)
    for k, (t, tilt) in MON.items():
        o, w, h = recs[k]; new = monitor(d, o, w, h, t, tilt, P1); res[('MN2', k)] = new
        pairs.append((show(d[o:o + w * h], w, h, P1), show(new, w, h, P1))); print('모니터', k, t)
    d4, r4, _ = F['MN4']; P24 = A.pal(d4, 24 * 0x200)
    for k, (ls, tilt) in PLATE.items():
        o, w, h = r4[k]; new, ov = plate(d4, o, w, h, ls, tilt, P24); res[('MN4', k)] = new
        pairs.append((show(d4[o:o + w * h], w, h, P24), show(new, w, h, P24))); print('금속판', k, ls, '넘침', ov)
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'arcade2.pkl'), 'wb'))
    S = 3; Wd = 2 * 150 * S + 30; Hd = sum(a.height * S + 10 for a, _ in pairs) + 10
    sh = Image.new('RGB', (Wd, Hd), (30, 30, 30)); y = 10
    for a, b in pairs:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(b.resize((b.width * S, b.height * S), Image.NEAREST), (20 + 150 * S, y)); y += a.height * S + 10
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '아케이드_글자판.png')); print(sh.size)
