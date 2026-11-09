# -*- coding: utf-8 -*-
r"""어레인지 플레이어 선택 초상화 속 캐릭터 이름 한글(2026-11-09)
  초상화 = VDP2 16×16 칸 256색, 칸 자료는 MN5BIN 첫 덩어리 풀린 0x3D728~ (캐릭터마다 다른 위치) · 현재 캐릭터 = NBG2(맵 쪽 2), 직전 = NBG0
  이름 상자(화면 맵 좌표 px) 안에서: 글자색 = 상자 안에서만 주로 쓰이는 색 번호 → 지우고 둘레 색으로 메움(가까운 비글자 화소 퍼뜨림) → 같은 색으로 한글(주아)
  칸마다 풀린 자료 안 위치(같은 칸 1개인지 검사) → work/plates/portrait.pkl {풀린 오프셋: 256B}, 미리보기 work/미리보기_그림/초상화_이름.png(원본 | 한글)
  python tools/portrait_ko.py
"""
import os, sys, struct, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import portrait_name as PN
from menu_logo import syl_mask
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATE_QUAD = [(163, 206), (197, 200), (199, 214), (165, 220)]          # 모모코 팻말 안쪽(테 안, 시계 방향)
# (스테이트, 맵 쪽, 지울 상자, 쓸 상자, 지우는 방식, 한글, 기울기) — 상자 = 맵 px (x0,y0,x1,y1), 좌표 눈금 확대 그림으로 실측
#   all = 상자 안 바탕 아닌 화소 전부 · bright = 밝은 화소 · pig = 밝은 화소+분홍 효과 · plate = 팻말 테 안쪽만
NAMES = [('어레인지모드 (2)', 0, (150, 138, 239, 184), (152, 140, 238, 182), 'all', '제이너스!', 10),   # 240 열부터는 옆 배경 칸
         ('선택_세리아', 2, (174, 182, 220, 208), (174, 182, 220, 206), 'bright', '세리아', 6),
         ('선택_피그', 2, (176, 176, 222, 212), (178, 178, 220, 204), 'pig', '피그', 8),
         ('선택_모모코', 0, (152, 196, 204, 226), None, 'plate', '모모코', -8),
         ('선택_미키', 2, (252, 176, 318, 223), (258, 184, 306, 212), 'all', '미키', 8)]   # 320 열·224 행부터는 배경 무늬 칸


def plane(st, page, box):
    x0, y0, x1, y1 = box; cx0, cy0, cx1, cy1 = x0 // 16, y0 // 16, x1 // 16, y1 // 16
    cs, cram = PN.cells(st, cx0, cy0, cx1, cy1, page)
    P = {}
    for (cx, cy), (w, a, blk) in cs.items():
        g = PN.px16(blk)
        for y in range(16):
            for x in range(16): P[(cx * 16 + x, cy * 16 + y)] = g[y][x]
    return cs, cram, P


def run(st, page, ebox, dbox, mode, text, tilt, d):
    x0, y0, x1, y1 = ebox
    cs, cram, P = plane(st, page, ebox)
    C = [(lambda c: ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))(struct.unpack_from('>H', cram, 2 * i)[0]) for i in range(2048)]
    lum = lambda v: sum(C[v])
    inb = lambda p, bx: bx[0] <= p[0] <= bx[2] and bx[1] <= p[1] <= bx[3]
    box = [p for p in P if inb(p, ebox)]
    bg = collections.Counter(P[p] for p in box).most_common(1)[0][0]
    if mode == 'all':
        T = {p for p in box if P[p] != bg}
    elif mode == 'bright':
        ls = sorted(lum(P[p]) for p in box); hi = ls[int(len(ls) * 0.7)]
        T = {p for p in box if lum(P[p]) >= max(hi, lum(bg) + 60)}
        T |= {(a + dx, b + dy) for a, b in T for dx in (-1, 0, 1) for dy in (-1, 0, 1) if inb((a + dx, b + dy), ebox) and P[(a + dx, b + dy)] != bg}
    elif mode == 'pig':
        ls = sorted(lum(P[p]) for p in box); hi = ls[int(len(ls) * 0.75)]
        T = {p for p in box if lum(P[p]) >= hi or C[P[p]][0] > C[P[p]][2] + 20}
        T |= {(a + dx, b + dy) for a, b in T for dx in (-1, 0, 1) for dy in (-1, 0, 1) if inb((a + dx, b + dy), ebox)}
    else:                                                                # plate: 팻말 안쪽 사변형(좌표 눈금 실측) 안의 검정 = 글자 → 팻말색
        Q = PLATE_QUAD
        def inside(p):
            x, y = p; sgn = []
            for i in range(4):
                ax, ay = Q[i]; bx, by = Q[(i + 1) % 4]
                sgn.append((bx - ax) * (y - ay) - (by - ay) * (x - ax) >= 0)
            return all(sgn) or not any(sgn)
        dark = lambda p: lum(P[p]) < 120
        inner = [p for p in box if inside(p)]
        T = {p for p in inner if dark(p)}
        plate_c = collections.Counter(P[p] for p in inner if not dark(p)).most_common(1)[0][0]
        xs = [p[0] for p in inner]; ys = [p[1] for p in inner]
        dbox = (min(xs) + 1, min(ys) + 2, max(xs) - 1, max(ys) - 2)
    cnt = collections.Counter(P[p] for p in T)
    if mode != 'plate': inner = []
    out = dict(P)
    if mode == 'plate':
        for p in T: out[p] = plate_c
    else:
        todo = set(T)
        if mode in ('all', 'bright'):
            for p in T: out[p] = bg
            todo = set()
        while todo:
            nxt = set()
            for p in todo:
                nb = [out[q] for q in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)) if q in out and q not in todo]
                if nb: out[p] = collections.Counter(nb).most_common(1)[0][0]
                else: nxt.add(p)
            if nxt == todo: break
            todo = nxt
    # 색: 글자 채움 = 지운 화소 중 많고 밝은 것, 테 = 지운 화소 중 어두운 것(팻말은 검정 글자)
    if mode == 'plate':
        fill = collections.Counter(P[p] for p in T).most_common(1)[0][0]; edge = None
    else:
        br = [v for v, n in cnt.most_common() if lum(v) > lum(bg) + 120]
        fill = max(br[:4], key=lum) if br else cnt.most_common(1)[0][0]
        if mode == 'pig': fill = max(cnt, key=lum)                          # 피그: 흰 글자(바탕이 밝아 문턱 비교가 안 됨)
        dk = [v for v, n in cnt.most_common() if v != fill and lum(v) < lum(fill) - (40 if mode == 'pig' else 120) and v != bg]
        edge = dk[0] if dk else None
    X0, Y0, X1, Y1 = dbox; W = X1 - X0 + 1; H = Y1 - Y0 + 1
    if mode == 'plate':                                                  # 작은 팻말 = 비트맵 굵은 갈무리11(주아 줄이면 뭉개짐)
        import bdf, menu_gfx as M
        FB = bdf.Font(os.path.join(M.FD, 'Galmuri11-Bold.bdf')); pts = FB.draw(text)[0]
        gx0 = min(a for a, _ in pts); gy0 = min(b for _, b in pts); gw = max(a for a, _ in pts) - gx0 + 1; gh = max(b for _, b in pts) - gy0 + 1
        G = {(a - gx0 + X0 + (W - gw) // 2, b - gy0 + Y0 + (H - gh) // 2) for a, b in pts}
    else:
     for bh in range(H - (2 if edge else 0), 6, -1):
        G = set(); x = 0
        for i, ch in enumerate(text):
            m, mw = syl_mask(ch, bh, tilt if i % 2 == 0 else tilt - 5, wx=1.0, fat=1)
            G |= {(a + x, b) for a, b in m}; x += mw + 1
        gw = max(a for a, _ in G) + 1; gh = max(b for _, b in G) - min(b for _, b in G) + 1
        if gw + (2 if edge else 0) <= W and gh + (2 if edge else 0) <= H: break
     yb = min(b for _, b in G); G = {(a + X0 + (W - gw) // 2, b - yb + Y0 + (H - gh) // 2) for a, b in G}
    if edge is not None:
        for p in {(a + dx, b + dy) for a, b in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G:
            if p in out and inb(p, ebox): out[p] = edge
    for p in G:
        if p in out and (mode != 'plate' or p in set(inner)): out[p] = fill
    res = {}; bad = []
    for (cx, cy), (w, a, blk) in cs.items():
        nb = bytearray(256)
        for i in range(256):
            q = i // 64; r = i % 64; x = (q % 2) * 8 + r % 8; y = (q // 2) * 8 + r // 8
            nb[i] = out[(cx * 16 + x, cy * 16 + y)]
        if bytes(nb) == blk: continue
        k = d.find(blk)
        if k < 0 or d.count(blk) != 1: bad.append((cx, cy)); continue
        res[k] = bytes(nb)
    W2, H2 = x1 - x0 + 17, y1 - y0 + 17
    img = lambda Q: (lambda im: ([im.putpixel((p[0] - x0 + 8, p[1] - y0 + 8), C[v]) for p, v in Q.items() if v and 0 <= p[0] - x0 + 8 < W2 and 0 <= p[1] - y0 + 8 < H2], im)[1])(Image.new('RGB', (W2, H2)))
    return res, bad, img(P), img(out), (fill, edge, bg)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    d = PN.chunk0(); allres = {}; rows = []
    for st, page, ebox, dbox, mode, text, tilt in NAMES:
        res, bad, a, b, ti = run(st, page, ebox, dbox, mode, text, tilt, d)
        print(text, '칸', len(res), '못 쓴 칸(공유·못 찾음)', bad, '채움·테·바탕', ti)
        allres.update(res); rows.append((a, b))
    pickle.dump(allres, open(os.path.join(ROOT, 'work', 'plates', 'portrait.pkl'), 'wb'))
    S = 4; Wd = max(a.width for a, _ in rows) * S * 2 + 30; Hd = sum(a.height * S + 10 for a, _ in rows) + 10
    sh = Image.new('RGB', (Wd, Hd), (40, 40, 40)); y = 10
    for a, b in rows:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(b.resize((b.width * S, b.height * S), Image.NEAREST), (20 + max(r.width for r, _ in rows) * S, y)); y += a.height * S + 10
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '초상화_이름.png')); print(sh.size)
