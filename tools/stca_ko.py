# -*- coding: utf-8 -*-
r"""세로(타테) 화면 스테이지 그림 한글(2026-11-09) — STCA.BIN 0xFD4~ 레코드 사슬 [u16 폭][u16 높이][u32 깃발<<16|색 은행][화소(4비트, 깃발=8비트)]
  그림은 90° 돌려 저장(읽을 땐 반시계로 돌림). 고치는 것:
  · 0xFD4 ステージ クリア 판(글자마다 다른 회색 = 글자별 색 바꾸기용 가면) → 스테이지 클리어(음절마다 4·6·8·a·b·d·f)
  · 0x19DC 棒ナス·0x25E4 残機·0x32EC ボンバー ストック «ボーナス» 알약 제목 → 꼬치 가지 / 잔기 / 봄버 스톡 + 보너스
  · 0x3FF4~0x5B24 이름 띠 7개(분홍 막대) · 0xB404 なし → 없음 · 0xB54C·B754·B95C «ステージ» 띠 조각 3개 → 스테이지(숫자 조각은 그대로)
  python tools/stca_ko.py → work/plates/stca.pkl {'STCA.BIN': 새 바이트}, work/미리보기_그림/세로화면_한글.png(원본 | 한글)
"""
import os, sys, struct, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf, menu_gfx as M
from menu_logo import syl_mask
import etca_ko as E
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'files', 'STCA.BIN')
FB = bdf.Font(os.path.join(M.FD, 'Galmuri11-Bold.bdf'))
STRIPS = {0x3FF4: ('제이너스', None), 0x447C: ('세리아', '푸페라'), 0x4904: (None, '로봇'), 0x4D8C: ('피그', '돼지'),
          0x5214: ('모모코', '초등학생'), 0x569C: ('미키', '제네시스 3'), 0x5B24: ('미키&미사토', '제네시스 3')}
BONUS = {0x19DC: '꼬치 가지 보너스', 0x25E4: '잔기 보너스', 0x32EC: '봄버 스톡 보너스'}


def recs(b):
    p = 0xFD4; out = []
    while p + 8 <= len(b):
        w, h, x = struct.unpack_from('>HHI', b, p)
        if not (8 <= w <= 320 and 8 <= h <= 256 and w % 8 == 0): break
        e8 = x >> 16; sz = w * h if e8 else w * h // 2; d = b[p + 8:p + 8 + sz]
        px = [d[i] if e8 else (d[i // 2] >> 4 if i % 2 == 0 else d[i // 2] & 15) for i in range(w * h)]
        out.append(dict(off=p, w=w, h=h, x=x, e8=e8, px=px)); p += 8 + sz
    return out


def readable(r):
    w, h, px = r['w'], r['h'], r['px']
    return [[px[x * w + (w - 1 - y)] for x in range(h)] for y in range(w)]


def store(b, r, g):
    w, h = r['w'], r['h']; px = [0] * (w * h)
    for y in range(w):
        for x in range(h): px[x * w + (w - 1 - y)] = g[y][x]
    assert not r['e8']
    o = r['off'] + 8
    for i in range(0, w * h, 2): b[o + i // 2] = (px[i] << 4) | px[i + 1]


def jua_mask(text, bh, wx=1.0, tilt=0.0, gap=1, tilts=None, dys=None):
    """음절마다 그려 이어 붙임. tilts/dys = 음절별 기울기°·세로 어긋남(원본 ステージクリア 처럼 통통 튀게)"""
    G = set(); x = 0; spans = []; i = 0
    for ch in text:
        if ch == ' ': x += bh // 3; continue
        t = tilts[i % len(tilts)] if tilts else tilt; dy = dys[i % len(dys)] if dys else 0
        m, mw = syl_mask(ch, bh, t, wx=wx, fat=1)
        G |= {(a + x, b + dy) for a, b in m}; spans.append((ch, x, x + mw)); x += mw + gap; i += 1
    return G, spans


def stencil(g):
    """160×32 글자별 회색 가면: 음절마다 채움 4·6·8·a·b·d·f, 테 1(1px) + 바깥 3(1px)"""
    H = len(g); W = len(g[0]); fills = [4, 6, 8, 0xA, 0xB, 0xD, 0xF]
    # 주아를 옆으로 짜부라뜨리면 각져 보임(하스피 «폰트 주아로») → 가로 비율 1.0 유지, 들어갈 때까지 높이를 줄임
    for bh in range(26, 14, -1):
        G, spans = jua_mask('스테이지 클리어', bh, 1.05, tilts=[10, -8, 6, -10, 9, -6, 8], dys=[1, -1, 2, 0, -1, 2, 0], gap=0)   # 하스피 «너무 정자» → 번갈아 기울임
        w = max(a for a, _ in G) + 1
        if w <= W - 6: break
    print('  가면 주아 높이', bh)
    G = {(a, b - min(bb for _, bb in G)) for a, b in G}; hh = max(b for _, b in G) + 1
    ox = (W - w) // 2; oy = max(2, (H - hh) // 2)
    out = [[0] * W for _ in range(H)]
    GG = {(a + ox, b + oy) for a, b in G}
    O1 = {(a + dx, b + dy) for a, b in GG for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - GG
    O2 = {(a + dx, b + dy) for a, b in GG | O1 for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - GG - O1
    over = 0
    for a, b in O2:
        if 0 <= a < W and 0 <= b < H: out[b][a] = 3
        else: over += 1
    for a, b in O1:
        if 0 <= a < W and 0 <= b < H: out[b][a] = 1
        else: over += 1
    for a, b in GG:
        if not (0 <= a < W and 0 <= b < H): over += 1; continue
        k = next(i for i, (_, x0, x1) in enumerate(spans) if x0 + ox <= a < x1 + ox + 1) if any(x0 + ox <= a < x1 + ox + 1 for _, x0, x1 in spans) else 0
        out[b][a] = fills[min(k, 6)]
    return out, over


def bonus(g, text):
    """알약 제목 탭: 세 판 모두 같은 색 번호(바탕 b=11 · 채움 7 · 속 8 · 테 9 · 모서리 a, 색은 판마다 은행이 다름)
      탭 안(7줄에서 b 인 열 범위) 글자 화소(7~a)를 b 로 지우고 굵은 갈무리11 채움 7·테 9·모서리 a"""
    H = len(g); W = len(g[0])
    xs = [x for x in range(W) if g[7][x] == 11]; L, R = min(xs), max(xs)
    out = [row[:] for row in g]
    for y in range(1, 15):
        for x in range(L, R + 1):
            if out[y][x] in (7, 8, 9, 10): out[y][x] = 11
    G = E.pts_of(FB, text); w, h = E.wh(G); ox = (L + R + 1 - w) // 2; oy = 8 - (h + 1) // 2
    over = 0; GG = {(a + ox, b + oy) for a, b in G}
    for a, b in GG:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (a + dx, b + dy)
                if q in GG: continue
                if not (L <= q[0] <= R and 1 <= q[1] <= 14): over += 1; continue
                v = 9 if dx == 0 or dy == 0 else 10
                if out[q[1]][q[0]] in (11, 10): out[q[1]][q[0]] = v
    for a, b in GG:
        if L <= a <= R and 1 <= b <= 14: out[b][a] = 7
    return out, over


def strip(g, name, mach):
    """144×16 분홍 막대 이름 띠: 글자(4~13줄)를 막대 바탕(오른쪽 끝 136열 색)으로 지우고 HUD 와 같은 방식(etca_ko.name_strip)으로 다시 씀"""
    H = len(g); W = len(g[0]); col = [g[y][136] for y in range(H)]
    rows = range(4, 12)                                                  # 글자 8줄(이름 띠 원본: 4~11줄 + 그림자)
    P = [[g[y][x] if g[y][x] != col[y] else 0 for x in range(W)] for y in rows]
    # 막대 바탕 위 글자만 남긴 8줄짜리로 HUD 이름 띠 그리기 재사용(괄호 = 5/6)
    P = [[(v if v in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12) else 0) for v in r] for r in P]
    new8, ov = name_strip16(P, name, mach)
    out = [row[:] for row in g]
    for y in range(4, 14):
        for x in range(2, W - 2):
            if out[y][x] not in (15,) or y >= 6: out[y][x] = col[y] if col[y] else out[y][x]
    for y in (4, 5):
        for x in range(W):
            if g[y][x] and g[y][x] != 15: out[y][x] = 0
    for i, y in enumerate(rows):
        for x in range(W):
            if new8[i][x]: out[y][x] = new8[i][x]
    return out, ov


def name_strip16(P, name, mach):
    """etca_ko.name_strip 과 같되 괄호 색 5/6 · 그림자 색은 구간에서 계산(막대 위 그림자 d 는 지운 뒤라 글자 색만)"""
    W = len(P[0])
    cols = [any(P[y][x] for y in range(8)) for x in range(W)]
    pcol = [x for x in range(W) if any(P[y][x] in (5, 6) for y in range(8))]
    groups = []
    for x in pcol:
        if groups and x - groups[-1][-1] <= 1: groups[-1].append(x)
        else: groups.append([x])
    L, R = groups[-2], groups[-1]                                         # 괄호 = 마지막 두 묶음(みき&みさと 의 & 도 초록)
    nx = [x for x in range(0, L[0]) if cols[x]]; mx = [x for x in range(L[-1] + 1, R[0]) if cols[x]]
    nst = E.seg_style(P, [x for x in nx if not any(P[y][x] in (5, 6) for y in range(8))]); mst = E.seg_style(P, mx)
    out = [[0] * W for _ in range(8)]
    def blit(xs, at):
        for i, x in enumerate(xs):
            for y in range(8):
                if P[y][x] and 0 <= at + i < W: out[y][at + i] = P[y][x]
        return at + len(xs)
    def draw(t, style, at):
        G = E.pts_of(E.F7, t); fill, shade = style; w, h = E.wh(G)
        for x, y in G:
            q = (x + 1 + at, y + 1)
            if (x + 1, y + 1) not in G and q[0] < W and q[1] < 8: out[q[1]][q[0]] = shade
        for x, y in G:
            if x + at < W: out[y][x + at] = fill.get(y, fill[min(fill, key=lambda k: abs(k - y))])
        return at + w + 1
    x = nx[0]
    x = blit(list(range(nx[0], nx[-1] + 1)), x) if name is None else draw(name, nst, x)
    x += 3; x = blit(list(range(L[0], L[-1] + 1)), x) + 1
    x = blit(list(range(mx[0], mx[-1] + 1)), x) if mach is None else draw(mach, mst, x)
    x += 1; end = blit(list(range(R[0], R[-1] + 1)), x)
    return out, end > W - 4


def nashi(g):
    """40×16 なし → 없음: 빨간 알약(e) 안 글자(1·2·3)를 e 로, 흰 1 · 테 3"""
    H = len(g); W = len(g[0]); out = [row[:] for row in g]
    for y in range(H):
        for x in range(W):
            if out[y][x] in (1, 2, 3): out[y][x] = 14 if 3 <= y <= 9 and 1 <= x <= 35 else 0
    G = E.pts_of(FB, '없음'); w, h = E.wh(G); ox = (36 - w) // 2; oy = (13 - h) // 2
    GG = {(a + ox, b + oy) for a, b in G}
    for a, b in GG:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (a + dx, b + dy)
                if q not in GG and 0 <= q[0] < W and 0 <= q[1] < H: out[q[1]][q[0]] = 3
    for a, b in GG: out[b][a] = 1
    return out, 0


def banner(gs):
    """«ステージ» 띠 조각 3개(32×32씩 이어 96×32): 바탕 1(어두움) · 띠 f(7~25줄), 왼쪽 끝 둥근 모서리는 원본 0~4열
      글자 = 주아 «스테이지», 채움 5 · 왼쪽/위 가장자리 4 · 테 3 2px · 띠 위 바깥 모서리 e"""
    W = 96; H = 32
    out = [[(15 if 7 <= y <= 25 else 1) for x in range(W)] for y in range(H)]
    for y in range(H):
        for x in range(5):
            if gs[0][y][x] in (1, 15): out[y][x] = gs[0][y][x]
    for wx in (1.15, 1.05, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7):
        G, _ = jua_mask('스테이지', 23, wx, gap=2)
        w = max(a for a, _ in G) + 1; h = max(b for _, b in G) + 1
        if w <= W - 4 - 6: break
    ox = 4 + (W - 4 - w) // 2; oy = (H - h) // 2 + 1
    GG = {(a + ox, b + oy) for a, b in G}
    O = {(a + dx, b + dy) for a, b in GG for dx in range(-2, 3) for dy in range(-2, 3) if abs(dx) + abs(dy) <= 3} - GG
    over = 0
    for a, b in O:
        if 0 <= a < W and 0 <= b < H: out[b][a] = 3
        else: over += 1
    for a, b in GG:
        if not (0 <= a < W and 0 <= b < H): over += 1; continue
        out[b][a] = 4 if ((a - 1, b) not in GG or (a, b - 1) not in GG) else 5
    return [[out[y][x0:x0 + 32] for y in range(H)] for x0 in (0, 32, 64)], over


def to_img(g, cram, bank):
    H = len(g); W = len(g[0]); im = Image.new('RGB', (W, H), (60, 60, 60)); pp = im.load()
    for y in range(H):
        for x in range(W):
            if g[y][x]:
                c = struct.unpack_from('>H', cram, 2 * (bank + g[y][x]))[0]; pp[x, y] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    return im


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = bytearray(open(SRC, 'rb').read()); orig = bytes(b)
    R = {r['off']: r for r in recs(orig)}
    cram = open(os.path.join(ROOT, 'work', 'mem', '그림_포즈2', 'CRAM.bin'), 'rb').read()
    pairs = []
    def do(o, new, ov, label):
        r = R[o]; store(b, r, new); pairs.append((to_img(readable(r), cram, r['x'] & 0xFFF), to_img(new, cram, r['x'] & 0xFFF)))
        print('%05X %s%s' % (o, label, '  ⚠넘침 %d' % ov if ov else ''))
    do(0xFD4, *stencil(readable(R[0xFD4])), '스테이지 클리어 가면')
    for o, t in BONUS.items(): do(o, *bonus(readable(R[o]), t), t)
    for o, (n, m) in STRIPS.items(): do(o, *strip(readable(R[o]), n, m), '이름 띠 %s (%s)' % (n, m))
    do(0xB404, *nashi(readable(R[0xB404])), '없음')
    pieces, ov = banner([readable(R[o]) for o in (0xB54C, 0xB754, 0xB95C)])
    for o, g in zip((0xB54C, 0xB754, 0xB95C), pieces): do(o, g, ov, '스테이지 띠')
    stray = [i for i in range(len(b)) if b[i] != orig[i] and not any(r['off'] + 8 <= i < r['off'] + 8 + r['w'] * r['h'] // 2 for r in R.values())]
    assert not stray
    pickle.dump({'STCA.BIN': bytes(b)}, open(os.path.join(ROOT, 'work', 'plates', 'stca.pkl'), 'wb'))
    S = 3; W = 192 * S * 2 + 30; H = sum(a.height * S + 8 for a, _ in pairs) + 8
    sh = Image.new('RGB', (W, H), (40, 40, 40)); y = 8
    for a, n in pairs:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(n.resize((n.width * S, n.height * S), Image.NEAREST), (20 + 192 * S, y)); y += a.height * S + 8
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '세로화면_한글.png')); print(sh.size)
