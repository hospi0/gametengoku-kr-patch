# -*- coding: utf-8 -*-
r"""아케이드 모드 선택 화면 입체 제목 한글(2026-11-09)
  · 画面モードセレクト! (MN2LZ 압축 덩어리 #0 = [색표 0x600] + 레코드 [w][h][8비트], 조각 #0~9) → 화면 모드 셀렉트!
  · モードセレクト (MN4BIN 날것 0x3800~ 레코드 사슬, 조각 #0~6) → 모드 셀렉트
  · プレイヤーセレクト (MN4BIN 조각 #12~20) → 플레이어 셀렉트
  조각마다 한 글자가 아니라 «제목 통째로 그려 조각 화면 자리(스테이트 VDP1 명령)대로 잘라 나눔» (메뉴 로고 방식, 그림자 조각은 같은 화소를 다른 색 은행으로 찍음)
  입체 = 블랙한산스 + 오른쪽 아래로 옆면(오른쪽 면 어둡게·아랫면 밝게) — 원본 색(파일 색표 은행 0) 최근접 번호
  python tools/arcade_ko.py → work/plates/arcade.pkl {('MN2', k)|('MN4', k): 화소}, work/미리보기_그림/아케이드_제목.png
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from menu_logo import syl_mask as _syl
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BHS = r'C:/claude/utils/font/blackhansans/BlackHanSans-Regular.ttf'

# (파일, 조각 번호, 화면 x, 화면 y) — 그림자 아닌 조각(색 0000)의 정지 자리
TITLES = {
    '화면 모드 셀렉트!': ('MN2', [(0, 60, 38), (1, 90, 38), (2, 117, 38), (3, 135, 40), (4, 158, 37), (5, 185, 39), (6, 206, 39), (7, 230, 37), (8, 251, 38), (9, 269, 37)],
                     dict(front=[(248, 248, 8), (248, 240, 8), (240, 224, 8), (224, 192, 16)], right=[(168, 80, 32), (144, 64, 32), (120, 48, 24), (96, 32, 24)], bottom=[(248, 192, 184), (240, 160, 150)])),
    '모드 셀렉트': ('MN4', [(0, 80, 44), (1, 104, 44), (2, 132, 44), (3, 156, 44), (4, 188, 44), (5, 212, 44), (6, 240, 44)],
               dict(front=[(248, 0, 0)], right=[(176, 40, 112), (168, 32, 104), (120, 16, 88), (96, 8, 80)], bottom=[(248, 184, 216), (248, 152, 208), (224, 56, 136)])),
    '플레이어 셀렉트': ('MN4', [(12, 88, 31), (13, 108, 35), (14, 124, 35), (15, 144, 35), (16, 164, 35), (17, 188, 35), (18, 208, 35), (19, 232, 35), (20, 256, 35)],
                 dict(front=[(248, 0, 0)], right=[(176, 40, 112), (168, 32, 104), (120, 16, 88), (96, 8, 80)], bottom=[(248, 184, 216), (248, 152, 208), (224, 56, 136)])),
}
DEPTH = 4
OFFS = [(1, 0), (1, 1), (2, 1), (3, 1), (4, 2)]                       # 원본처럼 오른쪽 옆면이 두껍게
WX = {'플레이어 셀렉트': 0.8}                                                # 7음절이라 폭에 걸림 → 좁혀서 키움
WX_CUR = [1.0]
BANK = {'플레이어 셀렉트': 2}                                                # MN4BIN 색표 은행(0x200씩) — 플레이어 셀렉트 조각은 2번(최빈 번호 11 = 빨강)
TILTS = [5, -4, 6, -5, 4, -6, 5, -4, 6]


def chain(d, p):
    out = []
    while p + 4 <= len(d):
        w, h = struct.unpack_from('>HH', d, p)
        if not (1 <= w <= 400 and 1 <= h <= 400): break
        out.append((p + 4, w, h)); p += 4 + w * h
    return out


def load():
    import lzss; lzss.INIT = 0
    mn2 = open(os.path.join(ROOT, 'work', 'files', 'MN2LZ'), 'rb').read()
    s = struct.unpack_from('>I', mn2, 0)[0]; d2, _ = lzss.decompress(mn2[:4 + s], 4, 1 << 23)
    mn4 = open(os.path.join(ROOT, 'work', 'files', 'MN4BIN'), 'rb').read()
    return {'MN2': (bytearray(d2), chain(d2, 0x600), 0), 'MN4': (bytearray(mn4), chain(mn4, 0x3800), 0)}, mn2, mn4


def pal(d, base):
    return [(lambda c: ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))(struct.unpack_from('>H', d, base + 2 * i)[0]) for i in range(256)]


SS = 4                                                                    # 4배로 그려 줄임(하스피 «너무너무 거칠다»)


def syl_hi(ch, bh, tilt, wx):
    """음절 하나를 SS 배 크기 마스크로(주변 여백 없이)"""
    m, mw = _syl(ch, bh * SS, tilt, font=BHS, wx=wx, fat=0)           # 굵게 하면 «셀렉트»·«화» 속이 메워짐 → 그대로
    return m, mw


def shade_hi(F, col, offs):
    """SS 배 입체: 앞면 F 를 offs(원래 화소 단위 방향)로 연속해서 밀어 옆면 — 오른쪽 경계에서 나온 면 R(어둡게), 아래 경계 B(밝게), 색은 면 따라 부드럽게"""
    img = {}
    ys = [b for _, b in F]; y0, y1 = min(ys), max(ys)
    lerp = lambda R, t: tuple(R[min(len(R) - 2, int(max(0, min(1, t)) * (len(R) - 1)))][c] + (R[min(len(R) - 1, int(max(0, min(1, t)) * (len(R) - 1)) + 1)][c] - R[min(len(R) - 2, int(max(0, min(1, t)) * (len(R) - 1)))][c]) * ((max(0, min(1, t)) * (len(R) - 1)) % 1) for c in range(3)) if len(R) > 1 else R[0]
    ex, ey = offs[-1]; n = max(abs(ex), abs(ey)) * SS
    for t in range(n, 0, -1):                                            # 뒤에서 앞으로
        dx = round(ex * SS * t / n); dy = round(ey * SS * t / n)
        for a, b in F:
            p = (a + dx, b + dy)
            if p in F: continue
            right = (a + SS, b) not in F
            img[p] = lerp(col['right'], (b - y0) / max(1, y1 - y0)) if right else lerp(col['bottom'], (b - y0) / max(1, y1 - y0))
    for a, b in F: img[(a, b)] = lerp(col['front'], (b - y0) / max(1, y1 - y0))
    return img


def down(img, W, H):
    """SS×SS 평균 → (색, 덮임 비율) · 덮임 ≥ 0.5 만 불투명"""
    acc = {}
    for (a, b), c in img.items():
        k = (a // SS, b // SS)
        if 0 <= k[0] < W and 0 <= k[1] < H:
            s = acc.setdefault(k, [0, 0, 0, 0]); s[0] += c[0]; s[1] += c[1]; s[2] += c[2]; s[3] += 1
    return {k: (round(v[0] / v[3]), round(v[1] / v[3]), round(v[2] / v[3])) for k, v in acc.items() if v[3] >= SS * SS // 2}


def render(text, cover, ox, oy, W, H, col):
    """음절마다 조각이 덮는 자리 안에 «잘림 0» 으로 놓음. 높이(기준선)는 모두 같게, 가로만 필요한 만큼 밀기.
      시작 x 를 여러 개 시도해 전체가 가운데에 가장 가깝게 · 안 되면 글자를 줄임"""
    import numpy as np
    C = np.zeros((H + 8, W + 8), bool)
    for a, b in cover: C[b, a] = True
    best_all = None
    for bh in range(H - 6, 12, -1):
        masks = []; i = 0
        for ch in text:
            if ch == ' ': masks.append(None); continue
            m, mw = syl_hi(ch, bh, TILTS[i % len(TILTS)], WX_CUR[0]); i += 1
            low = {(a // SS, b // SS) for a, b in m}
            ext = low | {(a + dx, b + dy) for a, b in low for dx, dy in OFFS}
            arr = np.array(sorted(ext)); masks.append((m, arr, arr[:, 0].max() + 1, arr[:, 1].max() + 1))
        for dy in sorted(range(0, H - max(mk[3] for mk in masks if mk) + 1), key=lambda v: abs(v - (H - max(mk[3] for mk in masks if mk)) // 2)):
            for x0 in range(0, 41, 2):
                x = x0; placed = []; ok = True; gap = 0
                for mk in masks:
                    if mk is None: x += bh // 3; continue
                    m, arr, lw, lh = mk; found = None
                    for dx in range(x, min(W - lw, x + 12) + 1):
                        xs = arr[:, 0] + dx; ys = arr[:, 1] + dy
                        if xs.max() < W + 8 and ys.max() < H + 8 and C[ys, xs].all(): found = dx; break
                    if found is None: ok = False; break
                    gap += found - x; placed.append((m, found, dy)); x = found + lw - OFFS[-1][0] + 1
                if not ok: continue
                tw = x; cost = gap * 3 + abs((W - tw) / 2 - x0)
                if best_all is None or cost < best_all[0]: best_all = (cost, placed)
            if best_all: break
        if best_all: break
    F = set()
    for m, dx, dy in best_all[1]: F |= {(a + dx * SS, b + dy * SS) for a, b in m}
    img = down(shade_hi(F, col, OFFS), W, H)
    return img, 0


def nearest(P, c, cache):
    if c not in cache: cache[c] = min(range(1, 256), key=lambda i: sum((P[i][j] - c[j]) ** 2 for j in range(3)))
    return cache[c]


# ★실기(빌드 16): 조각이 따로 출렁임 → 한 음절을 여러 조각에 자르면 깨짐(하스피 «제목 좌표가 안 맞나봐»). 조각마다 온전한 한 음절(남는 조각은 비움)
ASSIGN = {'화면 모드 셀렉트!': ['화', '면', '모', None, '드', '셀', '렉', '트', None, '!'],   # 좁은 ー·ト 조각을 비움(하스피 «크기 간격 제각각»)
          '모드 셀렉트': ['모', None, '드', None, '셀', '렉', '트'],
          '플레이어 셀렉트': ['플', '레', '이', '어', None, '셀', '렉', '트', None]}


def piece_glyph(ch, w, h, col, bh, wx, lim):
    """조각 하나(w×h)에 음절 하나 입체 — 폭 lim(다음 글자 조각까지) 안 가운데(조각끼리 겹쳐 뒤 조각이 앞 글자를 가리지 않게)"""
    m, mw = syl_hi(ch, bh, 0, wx)
    gw = mw // SS + 1; gh = max(b for _, b in m) // SS + 1; ex = OFFS[-1]
    ox = max(0, (min(w, lim) - gw - ex[0]) // 2); oy = (h - gh - ex[1]) // 2
    F = {(a + ox * SS, b + oy * SS) for a, b in m}
    return down(shade_hi(F, col, OFFS), w, h)


def fit(ch, w, h):
    """이 칸(w = 쓸 수 있는 폭)에 들어가는 가장 큰 (높이, 가로비)"""
    ex = OFFS[-1]
    for bh in range(h - ex[1] - 1, 8, -1):
        for wx in (1.0, 0.9, 0.8, 0.7, 0.62, 0.55, 0.48):
            m, mw = syl_hi(ch, bh, 0, wx)
            if mw // SS + 1 + ex[0] <= w and max(b for _, b in m) // SS + 1 + ex[1] <= h - 1: return bh, wx
    return 8, 0.6


def fit2(ch, w, h, BH):
    ex = OFFS[-1]
    for bh in range(min(BH, h - ex[1] - 1), 8, -1):
        for wx in (1.0, 0.9, 0.8, 0.7, 0.62, 0.55, 0.48):
            m, mw = syl_hi(ch, bh, 0, wx)
            if mw // SS + 1 + ex[0] <= w and max(b for _, b in m) // SS + 1 + ex[1] <= h - 1: return bh, wx
    return 8, 0.55


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    F, mn2, mn4 = load(); res = {}; rows = []
    for text, (fk, pieces, col) in TITLES.items():
        d, recs, _ = F[fk]; P = pal(d, BANK.get(text, 0) * 0x200); cache = {}
        X0 = min(x for _, x, _ in pieces); Y0 = min(y for _, _, y in pieces)
        X1 = max(x + recs[k][1] for k, x, _ in pieces); Y1 = max(y + recs[k][2] for k, _, y in pieces)
        W, H = X1 - X0, Y1 - Y0
        chs = ASSIGN[text]
        # 제목 전체 글자 높이 하나로(큰 조각 기준 최솟값), 가로비는 조각마다
        xs_used = [x for (k, x, _), ch in zip(pieces, chs) if ch]
        lims = []
        for (k, x, _), ch in zip(pieces, chs):
            nxt = [xx for xx in xs_used if xx > x]
            lims.append(min(recs[k][1], (min(nxt) - x + 2) if nxt else recs[k][1]))
        fits = [fit(ch, lim, recs[k][2]) if ch else None for (k, _, _), ch, lim in zip(pieces, chs, lims)]
        big = [f[0] for (k, _, _), f, ch in zip(pieces, fits, chs) if f and ch not in ('!',) and recs[k][2] >= 32]
        # 한 제목 안 음절은 모두 같은 높이·같은 가로비(하스피 «글씨 크기 간격 너무 제각각») — 가장 좁은 칸에 맞춤('!' 는 따로)
        best = None
        for bh in range(max(recs[k][2] for k, _, _ in pieces), 10, -1):
            for wx in (1.0, 0.92, 0.85, 0.78, 0.72, 0.66, 0.6):
                ok = True
                for (k, _, _), ch, lim in zip(pieces, chs, lims):
                    if not ch or ch == '!': continue
                    m, mw = syl_hi(ch, bh, 0, wx)
                    if mw // SS + 1 + OFFS[-1][0] > lim or max(b for _, b in m) // SS + 1 + OFFS[-1][1] > recs[k][2] - 1: ok = False; break
                if ok: best = (bh, wx); break
            if best: break
        BH = best[0]
        fits = [(best if ch != '!' else fit2(ch, lim, recs[k][2], BH)) if ch else None for (k, _, _), ch, lim in zip(pieces, chs, lims)]
        before = Image.new('RGB', (W, H), (40, 60, 140)); after = Image.new('RGB', (W, H), (40, 60, 140))
        for (k, x, y), ch, f, lim in zip(pieces, chs, fits, lims):
            o, w, h = recs[k]
            for j in range(h):
                for i in range(w):
                    ov = d[o + j * w + i]
                    if ov: before.putpixel((x - X0 + i, y - Y0 + j), P[ov])
            new = bytearray(w * h)
            if ch:
                img = piece_glyph(ch, w, h, col, f[0], f[1], lim)
                for (i, j), c in img.items(): new[j * w + i] = nearest(P, c, cache)
            res[(fk, k)] = bytes(new)
            for j in range(h):
                for i in range(w):
                    if new[j * w + i]: after.putpixel((x - X0 + i, y - Y0 + j), P[new[j * w + i]])
        print(text, '조각', len(pieces), '글자 높이', BH)
        rows.append((before, after))
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'arcade.pkl'), 'wb'))
    S = 3; Wd = max(a.width for a, _ in rows) * S + 20; Hd = sum(a.height * S * 2 + 30 for a, _ in rows) + 10
    sh = Image.new('RGB', (Wd, Hd), (30, 30, 30)); y = 10
    for a, b in rows:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); y += a.height * S + 6
        sh.paste(b.resize((b.width * S, b.height * S), Image.NEAREST), (10, y)); y += b.height * S + 24
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '아케이드_제목.png')); print(sh.size)
