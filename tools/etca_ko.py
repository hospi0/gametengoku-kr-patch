# -*- coding: utf-8 -*-
r"""게임 중 UI 그림 한글(2026-11-09) — BG_ETCA.BIN 날것 16색 8×8 칸(VDP2 NBG3, 팔레트 C 은행 = CRAM 0x7C0)
  캐릭터 블록 6개 × 0x2000(칸 0x285~) + 공통 꼬리 0xC000~(칸 0x377~). 맵은 코드가 만듦 → 같은 칸 사각형 안 화소만 다시 그림
  · 이름 띠  블록+0x540 16×1칸 «이름 (기체)» · 둘째 띠 블록+0x1580(가타카나·합체판, 빌드 23) — 이름 청록(채움 줄별·그림자 9) · 괄호 4/5 · 기체 줄별
  · ハイスコア!! +0x280 8×1칸(초록 4·그림자 5) · ポーズ +0x380 7×2칸 · 스테이지 이름판 +0x740 + n×0x180 4×3칸 8개
  · コンティニュー? 꼬리 0xC120 22×4칸 · する +88칸 4×2 · しない +96칸 6×2
  같은 칸 묶음이 BG_ETCAT·BG_ETC 에 통째로 있으면 같이 바꿈(ETCAT 에 ポーズ 사본)
  python tools/etca_ko.py → work/plates/etca.pkl {파일: 새 바이트}, work/미리보기_그림/게임중UI_한글.png(원본 | 한글)
"""
import os, sys, struct, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf, menu_gfx as M
from menu_logo import syl_mask
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F7 = bdf.Font(os.path.join(M.FD, 'Galmuri7.bdf'))
F9 = bdf.Font(os.path.join(M.FD, 'Galmuri9.bdf'))
F11 = bdf.Font(os.path.join(M.FD, 'Galmuri11.bdf'))
FB = bdf.Font(os.path.join(M.FD, 'Galmuri11-Bold.bdf'))
FC = bdf.Font(os.path.join(M.FD, 'Galmuri11-Condensed.bdf'))
F14 = bdf.Font(os.path.join(M.FD, 'Galmuri14.bdf'))

NAMES = {0: ('제이너스', None), 1: ('세리아', '푸페라'), 2: (None, '로봇'), 3: ('피그', '돼지'), 4: ('모모코', '초등학생'), 5: ('미키', '제네시스 3')}   # None = 원본 그대로(영문)
PLATES = ['오락실', '크레인', '슈팅', '노래방', '가정용', '드라이빙', '레트로', '폴리곤']   # 가정용 = «가정용 / 월드»(하스피 B안, 게임 뺌)


# ── 칸 ↔ 화소 ──
def get(e, off, cw, ch):
    P = [[0] * (cw * 8) for _ in range(ch * 8)]
    for cy in range(ch):
        for cx in range(cw):
            k = off + (cy * cw + cx) * 32
            for y in range(8):
                for x in range(8):
                    q = e[k + y * 4 + x // 2]; P[cy * 8 + y][cx * 8 + x] = q >> 4 if x % 2 == 0 else q & 15
    return P


def put(e, off, P):
    ch = len(P) // 8; cw = len(P[0]) // 8
    for cy in range(ch):
        for cx in range(cw):
            k = off + (cy * cw + cx) * 32
            for y in range(8):
                for x in range(0, 8, 2): e[k + y * 4 + x // 2] = (P[cy * 8 + y][cx * 8 + x] << 4) | P[cy * 8 + y][cx * 8 + x + 1]


def pts_of(font, t, bold=False):
    p = font.draw(t)[0]
    if bold: p = sorted(set(p) | {(x + 1, y) for x, y in p})
    x0 = min(x for x, _ in p); y0 = min(y for _, y in p)
    return {(x - x0, y - y0) for x, y in p}


def smart_bold(G):
    """오른쪽으로 1px 굵게 — 단 1px 틈 두고 붙은 획(ㅔ·ㅐ)은 안 메움(하스피 «글자에 빈틈 있어서 흐려»)"""
    return G | {(x + 1, y) for x, y in G if (x + 2, y) not in G and (x + 1, y) not in G}


def wh(G):
    return max(x for x, _ in G) + 1, max(y for _, y in G) + 1


# ── 이름 띠 ──
def seg_style(P, xs):
    """원본 구간(열 범위)의 줄별 채움 색·그림자 색: 그림자 = 왼쪽 위(대각)·왼쪽·위에 잉크가 있고 오른쪽 아래엔 없는 화소에 많은 색"""
    ink = {(x, y) for y in range(8) for x in xs if P[y][x]}
    edge = collections.Counter(P[y][x] for x, y in ink if (x + 1, y + 1) not in ink and (x + 1, y) not in ink and (x, y + 1) not in ink)
    shade = edge.most_common(1)[0][0]
    fill = {}
    for y in range(8):
        c = collections.Counter(P[y][x] for x in xs if P[y][x] and P[y][x] != shade)
        if c: fill[y] = c.most_common(1)[0][0]
    return fill, shade


def name_strip(P, name, mach):
    W = len(P[0])
    cols = [any(P[y][x] for y in range(8)) for x in range(W)]
    pcol = [x for x in range(W) if any(P[y][x] in (4, 5) for y in range(8))]
    # 괄호 = 4/5 열 묶음 첫·마지막
    groups = [];
    for x in pcol:
        if groups and x - groups[-1][-1] <= 1: groups[-1].append(x)
        else: groups.append([x])
    L, R = groups[-2], groups[-1]                                         # 여는 괄호 = 닫는 괄호 바로 앞 묶음(«みき&みさと» 의 & 도 4/5 색)
    nx = [x for x in range(0, L[0]) if cols[x]]; mx = [x for x in range(L[-1] + 1, R[0]) if cols[x]]
    nstyle = seg_style(P, nx); mstyle = seg_style(P, mx)
    out = [[0] * W for _ in range(8)]
    def blit(xs, at):                                                    # 원본 열 그대로 옮김
        for i, x in enumerate(xs):
            for y in range(8):
                if P[y][x] and 0 <= at + i < W: out[y][at + i] = P[y][x]
        return at + len(xs)
    def draw(t, style, at):
        G = pts_of(F7, t); fill, shade = style; w, h = wh(G); oy = 0
        for x, y in G:
            for d in ((1, 1),):
                q = (x + d[0] + at, y + d[1] + oy)
                if (x + d[0], y + d[1]) not in G and q[0] < W and q[1] < 8: out[q[1]][q[0]] = shade
        for x, y in G:
            if x + at < W: out[y + oy][x + at] = fill.get(y + oy, fill[min(fill, key=lambda k: abs(k - y - oy))])
        return at + w + 1
    x = nx[0]
    x = blit(list(range(nx[0], nx[-1] + 1)), x) if name is None else draw(name, nstyle, x)
    x += 3
    x = blit(list(range(L[0], L[-1] + 1)), x) + 1
    x = blit(list(range(mx[0], mx[-1] + 1)), x) if mach is None else draw(mach, mstyle, x)
    x += 1
    end = blit(list(range(R[0], R[-1] + 1)), x)
    return out, end > W


# ── 한 줄 글자(그림자형) ──
def simple(W, H, t, fill, shade, font=F7):
    out = [[0] * W for _ in range(H)]; G = pts_of(font, t); w, h = wh(G)
    ox = 1; oy = (H - h - 1) // 2 + (1 if H == 8 else 0) - (1 if H == 8 else 0)
    for x, y in G:
        q = (x + 1 + ox, y + 1 + oy)
        if (x + 1, y + 1) not in G and q[0] < W and q[1] < H: out[q[1]][q[0]] = shade
    for x, y in G: out[y + oy][x + ox] = fill
    return out, w + 2 > W


# ── 굵은 테 글자(포즈·스테이지 판·컨티뉴 버튼) ──
def shadowed(W, H, G, ox, oy, fillrow, shade, out):
    """1px 획 글자 + 오른쪽 아래 그림자(테두리 두르면 9px 한글이 뭉개짐)"""
    G = {(x + ox, y + oy) for x, y in G}; over = 0
    for x, y in G:
        q = (x + 1, y + 1)
        if q not in G and 0 <= q[0] < W and 0 <= q[1] < H: out[q[1]][q[0]] = shade
    for x, y in G:
        if 0 <= x < W and 0 <= y < H: out[y][x] = fillrow(y)
        else: over += 1
    return out, over


def outlined(W, H, G, ox, oy, fillrow, outline, corner=None, out=None):
    out = out or [[0] * W for _ in range(H)]
    G = {(x + ox, y + oy) for x, y in G}
    for x, y in G:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if q in G or not (0 <= q[0] < W and 0 <= q[1] < H): continue
                v = outline if (dx == 0 or dy == 0 or corner is None) else corner
                if out[q[1]][q[0]] in (0, corner, 15): out[q[1]][q[0]] = v
    over = 0
    for x, y in G:
        if 0 <= x < W and 0 <= y < H: out[y][x] = fillrow(y)
        else: over += 1
    return out, over


def pause_art():
    """56×16 «포즈»: 주아(원본 ポーズ 처럼 칸 가득), 채움 a · 위 가장자리 b · 노랑 테 1"""
    G = set(); x = 0
    for ch, t in (('포', 3), ('즈', -3)):
        m, mw = syl_mask(ch, 13, t, wx=1.35, fat=1)
        G |= {(a + x, b) for a, b in m}; x += mw + 3
    w, h = wh(G); ox = (56 - w) // 2; oy = (16 - h) // 2
    out, over = outlined(56, 16, G, ox, oy, lambda y: 0xA, 1)
    GG = {(x + ox, y + oy) for x, y in G}
    for x, y in GG:
        if (x, y - 1) not in GG or (x - 1, y) not in GG: out[y][x] = 0xB
    return out, over


def plate_art(P, word):
    """32×24: 바탕 f · 위 낱말 주황(줄별 채움 a/6/d·테 7·모서리 e) 0~12줄 · 아래 «월드» 청록(채움 8/c·테 9) 13~23줄, 둘 다 갈무리9
      두 줄 낱말(가정용/게임)은 원본 家庭用/ゲーム/ワールド 처럼 갈무리7 세 줄 · 드라이빙은 갈무리7 한 줄"""
    top = {}; bot = {}
    for y in range(16):
        c = collections.Counter(v for v in P[y] if v in (6, 0xA, 0xD)); top[y] = c.most_common(1)[0][0] if c else 6
    for y in range(16, 24):
        c = collections.Counter(v for v in P[y] if v in (8, 0xC)); bot[y] = c.most_common(1)[0][0] if c else 8
    tf = lambda y: 6;   # 하스피 «월드 이름 주황색은 그라데이션 넣지 말고 단색»(2026-11-09)
    bf = lambda y: bot.get(16 + min(7, max(0, int((y - 13) * 7 / 10))), 8)
    out = [[15] * 32 for _ in range(24)]; over = 0
    if isinstance(word, tuple):
        for i, t in enumerate(word):
            G = pts_of(F7, t); w, h = wh(G)
            out, ov = shadowed(32, 24, G, (32 - w) // 2, 1 + i * 8, lambda y: 6, 7, out); over += ov
        G = pts_of(F7, '월드'); w, h = wh(G)
        out, ov = shadowed(32, 24, G, (32 - w) // 2, 16, lambda y: bot.get(y, 8), 9, out); over += ov
        return out, over
    G = smart_bold(pts_of(F9, word)); w, h = wh(G)
    if w > 31: G = pts_of(FC, word); w, h = wh(G)          # 드라이빙: 7px 굵게는 «드리이빙»으로 보임(하스피) → 갈무리11 좁은 꼴
    out, ov = shadowed(32, 24, G, (32 - w) // 2, (13 - h) // 2, tf, 7, out); over += ov
    G = smart_bold(pts_of(F9, '월드')); w, h = wh(G)
    out, ov = shadowed(32, 24, G, (32 - w) // 2, 13 + (11 - h) // 2, bf, 9, out); over += ov
    return out, over


def continue_art(P):
    """176×32 «컨티뉴?»: 주아, 채움 6 · 위 가장자리 d/b 밝게 · 오른쪽 아래 가장자리 a · 테 7 2px · 그림자(+2,+2) 7"""
    G = {}; x = 6
    for ch, t in (('컨', 4), ('티', -4), ('뉴', 4), ('?', -6)):
        m, mw = syl_mask(ch, 25, t, wx=1.25, fat=2)
        for a, b in m: G[(a + x, b + 3)] = 1
        x += mw + 6
    Gs = set(G); w = max(a for a, _ in Gs) + 1
    sh = (176 - 4 - w) // 2 - 6; Gs = {(a + sh, b) for a, b in Gs}
    out = [[0] * 176 for _ in range(32)]; over = 0
    O = {(a + dx, b + dy) for a, b in Gs for dx in range(-2, 3) for dy in range(-2, 3)} - Gs
    S = {(a + d, b + d) for a, b in Gs | O for d in (1, 2)} - Gs - O
    for a, b in S | O:
        if 0 <= a < 176 and 0 <= b < 32: out[b][a] = 7
        else: over += 1
    for a, b in Gs:
        if not (0 <= a < 176 and 0 <= b < 32): over += 1; continue
        v = 6
        if (a, b - 1) not in Gs: v = 0xD
        elif (a, b - 2) not in Gs or (a - 1, b) not in Gs: v = 0xB
        elif (a + 1, b) not in Gs or (a, b + 1) not in Gs: v = 0xA
        out[b][a] = v
    return out, over


def button(P, t):
    """する(32×16)·しない(48×16): 둥근 바탕(9)·흰 글자(2) — 바깥 투명 모서리 원본 그대로"""
    H = len(P); W = len(P[0])
    out = [[(9 if P[y][x] else 0) for x in range(W)] for y in range(H)]
    G = pts_of(FB, t); w, h = wh(G); ox = (W - w) // 2; oy = (H - h) // 2
    for x, y in G: out[y + oy][x + ox] = 2
    return out, int(w > W - 2)


def to_img(P, cram):
    H = len(P); W = len(P[0]); im = Image.new('RGB', (W, H), (0, 0, 0)); pp = im.load()
    for y in range(H):
        for x in range(W):
            if P[y][x]:
                c = struct.unpack_from('>H', cram, 2 * (0x7C0 + P[y][x]))[0]; pp[x, y] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    return im


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src = {n: open(os.path.join(ROOT, 'work', 'files', n), 'rb').read() for n in ('BG_ETCA.BIN', 'BG_ETCAT.BIN', 'BG_ETC.BIN')}
    e = bytearray(src['BG_ETCA.BIN']); orig = bytes(e)
    cram = open(os.path.join(ROOT, 'work', 'mem', '그림_컨티뉴', 'CRAM.bin'), 'rb').read()
    pairs = []; regions = []                                             # (원본 오프셋, 칸 폭, 칸 높이, 새 화소)
    for c in range(6):
        P = get(orig, c * 0x2000 + 0x540, 16, 1); new, ov = name_strip(P, *NAMES[c])
        print('이름 띠 %d %s%s' % (c, NAMES[c], '  ⚠넘침' if ov else '')); regions.append((c * 0x2000 + 0x540, new)); pairs.append((P, new))
    for c in range(6):                                                   # 둘째 이름 띠 블록+0x1580(가타카나판·미키는 «みき&みさと» 합체판) — 게임 중엔 이쪽이 쓰여 일본어가 보임(빌드 23, 하스피)
        nm = ('미키&미사토', '제네시스 3') if c == 5 else NAMES[c]
        P = get(orig, c * 0x2000 + 0x1580, 16, 1); new, ov = name_strip(P, *nm)
        print('이름 띠2 %d %s%s' % (c, nm, '  ⚠넘침' if ov else '')); regions.append((c * 0x2000 + 0x1580, new)); pairs.append((P, new))
    common = []
    P = get(orig, 0x280, 8, 1); new, ov = simple(64, 8, '하이스코어!!', 4, 5); common.append((0x280, new)); pairs.append((P, new)); print('하이스코어', ov)
    P = get(orig, 0x380, 7, 2); new, ov = pause_art(); common.append((0x380, new)); pairs.append((P, new)); print('포즈 넘침', ov)
    for i, wd in enumerate(PLATES):
        o = 0x740 + i * 0x180; P = get(orig, o, 4, 3); new, ov = plate_art(P, wd); common.append((o, new)); pairs.append((P, new)); print('판', i, wd, '넘침', ov)
    for c in range(6):
        for o, new in common: regions.append((c * 0x2000 + o, new))
    P = get(orig, 0xC120, 22, 4); new, ov = continue_art(P); regions.append((0xC120, new)); pairs.append((P, new)); print('컨티뉴 넘침', ov)
    P = get(orig, 0xC120 + 88 * 32, 4, 2); new, ov = button(P, '한다'); regions.append((0xC120 + 88 * 32, new)); pairs.append((P, new))
    P = get(orig, 0xC120 + 96 * 32, 6, 2); new, ov = button(P, '안 한다'); regions.append((0xC120 + 96 * 32, new)); pairs.append((P, new))
    for o, new in regions: put(e, o, new)
    res = {'BG_ETCA.BIN': bytes(e)}
    # 같은 칸 묶음이 다른 파일에 통째로 있으면 같이(원본 바이트 → 새 바이트)
    for fn in ('BG_ETCAT.BIN', 'BG_ETC.BIN'):
        b = bytearray(src[fn]); n = 0
        for o, new in regions:
            ln = len(new) // 8 * len(new[0]) // 8 * 32; old = orig[o:o + ln]; k = b.find(old)
            while k >= 0:
                b[k:k + ln] = e[o:o + ln]; n += 1; k = b.find(old, k + ln)
        if n: res[fn] = bytes(b); print(fn, '사본 바꿈', n)
    # 세로(타테) 이름 칸 BG_ETCAT 0x8C0~ 33칸 1줄 — 이름마다 8px 칸 단위로 딱 나뉨(빈 열 실측), 자기 칸 안에서만 다시 그림
    #   (칸 시작, 칸 끝(포함), 한글) · Z-DYNE MKⅡ(칸 12~20)는 원본 그대로
    b = bytearray(res.get('BG_ETCAT.BIN', src['BG_ETCAT.BIN'])); ot = src['BG_ETCAT.BIN']
    for c0, c1, t in ((0, 4, '제이너스'), (5, 8, '세리아'), (9, 11, '피그'), (21, 24, '모모코'), (25, 32, '미키&미사토')):
        o = 0x8C0 + c0 * 32; P = get(ot, o, c1 - c0 + 1, 1); W = len(P[0])
        fill, shade = seg_style(P, [x for x in range(W) if any(P[y][x] for y in range(8))])
        out = [[0] * W for _ in range(8)]; at = 0
        for part in t.split('&'):
            if at:                                                       # «&» = 원본 초록(4/5) 글자 열 그대로
                amp = [x for x in range(W) if any(P[y][x] in (4, 5) for y in range(8))]
                for i, x in enumerate(range(amp[0], amp[-1] + 1)):
                    for y in range(8):
                        if P[y][x]: out[y][at + i] = P[y][x]
                at += len(amp) + 1
            G = pts_of(F7, part); w, h = wh(G)
            for x, y in G:
                if (x + 1, y + 1) not in G and at + x + 1 < W and y + 1 < 8: out[y + 1][at + x + 1] = shade
            for x, y in G: out[y][at + x] = fill.get(y, fill[min(fill, key=lambda k: abs(k - y))])
            at += w + 2
        print('세로 이름 %s 폭 %d/%d%s' % (t, at - 1, W, '  ⚠넘침' if at - 1 > W else ''))
        put(b, o, out); pairs.append((P, out))
    res['BG_ETCAT.BIN'] = bytes(b)
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'etca.pkl'), 'wb'))
    S = 4; ims = [(to_img(a, cram), to_img(b, cram)) for a, b in pairs]
    W = 176 * S * 2 + 30; H = sum(a.height * S + 8 for a, _ in ims) + 8
    sh = Image.new('RGB', (W, H), (60, 60, 60)); y = 8
    for a, b in ims:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(b.resize((b.width * S, b.height * S), Image.NEAREST), (20 + 176 * S, y)); y += a.height * S + 8
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '게임중UI_한글.png')); print(sh.size)
