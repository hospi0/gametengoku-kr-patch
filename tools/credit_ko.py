# -*- coding: utf-8 -*-
r"""오프닝 크레딧(캐릭터 디자인·야마다·조수) 한글(2026-11-09)
  그림: OPENING.BIN 0x1B05C 덩어리(A형, [u32 개수 54]+레코드 [w][h][u32 0][4비트]) — 조각 번호 = 레코드 번호
  배치표: OPENING2.BIN 0x3CB0~0x3E60 · PROLOG.BIN 0x470~0x620 (같은 표 두 벌) 항목 8B [번호][순번][x][y]
  → 쓸 조각만 겹치지 않게 나란히(세로줄 이름은 위아래로) 다시 놓고, 한글을 통째로 그려 조각 크기대로 잘라 넣음 · 안 쓰는 조각은 화면 밖(x −200)
  색: 흰 1 · 그림자 = 그 무리 원본에서 1 다음으로 많은 색(+2,+1)
  python tools/credit_ko.py → work/plates/credit.pkl {'recs': {번호: 4비트}, 'OPENING2.BIN': .., 'PROLOG.BIN': ..}, work/미리보기_그림/오프닝_크레딧.png
"""
import os, sys, struct, pickle
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss, opening_bin as O
from menu_logo import syl_mask as _syl
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BHS = r'C:/claude/utils/font/blackhansans/BlackHanSans-Regular.ttf'
CO = 0x1B05C; SS = 4
# (쓸 조각, 안 쓸 조각, 한글, 방향 H/V, 시작 x, 시작 y, 맞춤 L/R)
GROUPS = [([0, 2, 3, 4, 6, 7, 8, 9], [1, 5], '캐릭터 디자인', 'H', 44, 138, 'L'),
          ([10, 11, 12, 13, 14], [], '소우마 타츠야', 'H', None, 170, 'R'),
          ([31, 33, 34, 35, 36, 37], [32], '지니어스 야마다', 'V', 246, 0, 'L'),   # 0~232 줄 중 글자는 화면 안 224 줄에만
          ([38, 39, 40], [], '치바 시게루', 'V', 20, 40, 'L'),
          ([41, 42], [], '카토', 'H', 14, 4, 'L'),
          ([47, 48], [], '나카무라', 'H', None, 4, 'R'),
          ([43, 44, 45, 46], [], '스즈키 마사미', 'H', 7, 170, 'L'),
          ([49, 50, 51, 52, 53], [], '이세 쿠미코', 'H', None, 170, 'R')]
TABLES = {'OPENING2.BIN': (0x3C00, 0x3F00), 'PROLOG.BIN': (0x400, 0x700)}


def load():
    lzss.INIT = 0
    b = open(os.path.join(ROOT, 'work', 'files', 'OPENING.BIN'), 'rb').read(); s = struct.unpack_from('>I', b, CO)[0]
    d, _ = lzss.decompress(b[:CO + 4 + s], CO + 4, 1 << 23)
    n = struct.unpack_from('>I', d, 0)[0]; p = 4; offs = []
    for _ in range(n):
        w, h = struct.unpack_from('>HH', d, p); offs.append((p + 8, w, h)); p += 8 + w * h // 2
    return b, s, bytearray(d), offs


def entries(buf, lo, hi):
    out = {}
    for p in range(lo, hi, 8):
        i, k, x, y = struct.unpack_from('>HHhh', buf, p)
        if i <= 53 and k < 64 and i not in out and -50 < x < 400 and -50 < y < 260: out[i] = p
    return out


def syl(ch, bh, wx):
    m, mw = _syl(ch, bh * SS, 0, font=BHS, wx=wx, fat=0)
    cnt = Counter((a // SS, b // SS) for a, b in m)
    return {p for p, n in cnt.items() if n >= SS * SS // 2}


def text_h(t, W, H):
    """가로 한 줄을 W×H 안에 가장 크게"""
    for bh in range(H - 3, 8, -1):
        for wx in (1.0, 0.9, 0.8, 0.7):
            G = set(); x = 0
            for ch in t:
                if ch == ' ': x += bh // 3; continue
                g = syl(ch, bh, wx); G |= {(a + x, b) for a, b in g}; x += max(a for a, _ in g) + 2
            gw = max(a for a, _ in G) + 1; y0 = min(b for _, b in G); gh = max(b for _, b in G) - y0 + 1
            if gw + 3 <= W and gh + 2 <= H: return {(a + (W - gw - 2) // 2, b - y0 + (H - gh - 1) // 2) for a, b in G}
    raise SystemExit(t)


def text_v(t, W, H):
    """세로쓰기: 음절을 위에서 아래로(띄어쓰기 = 반 칸)"""
    syls = [c for c in t if c != ' ']; n = len(syls) + 0.5 * t.count(' ')
    for bh in range(int(H / n) - 1, 8, -1):
        cells = []; ok = True
        for ch in syls:
            g = syl(ch, bh, 1.0)
            if max(a for a, _ in g) + 3 > W: g = syl(ch, bh, 0.85)
            cells.append(g)
        step = bh + 1; tot = step * len(syls) + (step // 2) * t.count(' ')
        if tot <= H - 2: break
    G = set(); y = (H - tot) // 2; i = 0
    for ch in t:
        if ch == ' ': y += step // 2; continue
        g = cells[i]; i += 1; gw = max(a for a, _ in g) + 1; y0 = min(b for _, b in g)
        G |= {(a + (W - gw - 2) // 2, b - y0 + y) for a, b in g}; y += step
    return G


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b, s, d, offs = load()
    tabs = {n: bytearray(open(os.path.join(ROOT, 'work', 'files', n), 'rb').read()) for n in TABLES}
    E = {n: entries(tabs[n], *TABLES[n]) for n in TABLES}
    cram = open(os.path.join(ROOT, 'work', 'mem', '오프닝_조수', 'CRAM.bin'), 'rb').read()
    col = lambda i: (lambda c: ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))(struct.unpack_from('>H', cram, 2 * (0x10 + i))[0])
    px4 = lambda k: [(d[offs[k][0] + i // 2] >> 4) if i % 2 == 0 else d[offs[k][0] + i // 2] & 15 for i in range(offs[k][1] * offs[k][2])]
    recs = {}; cards = {}
    CARD = [0, 0, 1, 1, 2, 2, 2, 2]
    for gi, (use, hide, ko, dr, x0, y0, al) in enumerate(GROUPS):
        before, after = cards.setdefault(CARD[gi], (Image.new('RGB', (352, 240), (40, 40, 60)), Image.new('RGB', (352, 240), (40, 40, 60))))
        sz = [offs[k][1:] for k in use]
        sh = Counter(v for k in use for v in px4(k) if v not in (0, 1)).most_common(1)[0][0]
        if dr == 'H':
            pos = []; x = 0
            HM = max(h for _, h in sz)
            for w, h in sz: pos.append((x, (HM - h) // 2)); x += w                   # 무리 안 가장 큰 조각 높이 기준(48 기준이면 32px 줄이 아래로 밀려 이름 줄과 겹침)
            W, H = x, max(h for _, h in sz)
            top = max(py for _, py in pos); bot = min(py + h for (_, py), (w, h) in zip(pos, sz))
            G = {(a, b + top) for a, b in text_h(ko, W, bot - top)}
        else:
            pos = []; y = 0
            for w, h in sz: pos.append(((48 - w) // 2, y)); y += h
            W, H = max(w for w, _ in sz), y
            G = text_v(ko, W, min(H, 224 - y0))
        canvas = {}
        for a, c in G:
            for dx, dy in ((2, 1), (1, 1), (2, 0)):
                if (a + dx, c + dy) not in G: canvas[(a + dx, c + dy)] = sh
        for p in G: canvas[p] = 1
        cover = {(px + i, py + j) for (px, py), (w, h) in zip(pos, sz) for i in range(w) for j in range(h)}
        lost = sum(1 for p in canvas if p not in cover)
        # 원래 자리(미리보기)·새 자리
        old = {k: struct.unpack_from('>hh', tabs['OPENING2.BIN'], E['OPENING2.BIN'][k] + 4) for k in use + hide}
        if x0 is None:                                                       # 오른쪽 맞춤: 원래 오른쪽 끝
            end = max(old[k][0] + offs[k][1] for k in use); x0 = end - W
        for k in use + hide:
            w, h = offs[k][1:]; v = px4(k)
            for i, c in enumerate(v):
                if c and 0 <= old[k][0] + i % w < 352 and 0 <= old[k][1] + i // w < 240: before.putpixel((old[k][0] + i % w, old[k][1] + i // w), col(c))
        for k, (px, py), (w, h) in zip(use, pos, sz):
            for tb in TABLES: struct.pack_into('>hh', tabs[tb], E[tb][k] + 4, x0 + px, y0 + py)
            v = [canvas.get((px + i, py + j), 0) for j in range(h) for i in range(w)]
            recs[k] = bytes((v[j] << 4) | v[j + 1] for j in range(0, w * h, 2))
            for i, c in enumerate(v):
                X, Y = x0 + px + i % w, y0 + py + i // w
                if c and 0 <= X < 352 and 0 <= Y < 240: after.putpixel((X, Y), col(c))
        for k in hide:
            for tb in TABLES: struct.pack_into('>hh', tabs[tb], E[tb][k] + 4, -200, -200)
            recs[k] = bytes(offs[k][1] * offs[k][2] // 2)
        print(ko, '조각', len(use), '숨김', hide, '캔버스', W, H, '잘림', lost, '그림자색', sh)
    pickle.dump({'recs': recs, **{n: bytes(t) for n, t in tabs.items()}}, open(os.path.join(ROOT, 'work', 'plates', 'credit.pkl'), 'wb'))
    sh_ = Image.new('RGB', (352 * 4 + 20, 3 * 490), (20, 20, 20))
    for i, (bf, af) in sorted(cards.items()):
        sh_.paste(bf.resize((704, 480), Image.NEAREST), (0, i * 490)); sh_.paste(af.resize((704, 480), Image.NEAREST), (724, i * 490))
    sh_.save(os.path.join(ROOT, 'work', '미리보기_그림', '오프닝_크레딧.png')); print(sh_.size)
