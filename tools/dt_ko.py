# -*- coding: utf-8 -*-
r"""데이터 모드 상세 화면 글자 그림 한글(2026-11-09) — DT??BIN(EX·FZ·FC·MK·BS·PA) 첫 압축 덩어리 = [색표 3벌 0x600] + 레코드 [u16 폭][u16 높이][8비트]
  하스피 «포스터같은 자료는 한글화 안 함» → 전단·로고 그림(104×104·160×208·160×N)·DATA MODE·연도는 그대로
  고치는 것: 戻る B 버튼(64×32 #1) · 게임 이름판(128×32, 은행 1) · 설명 줄(120×16 «(宣伝用チラシ)» 등, 괄호는 원본 그대로)
  python tools/dt_ko.py → work/plates/dt.pkl {(게임, 번호): 화소}, work/미리보기_그림/데이터상세_한글.png(원본 | 한글)
"""
import os, sys, struct, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss, bdf, menu_gfx as M
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = ('EX', 'FZ', 'FC', 'MK', 'BS', 'PA')
F11 = bdf.Font(os.path.join(M.FD, 'Galmuri11.bdf'))
FB = bdf.Font(os.path.join(M.FD, 'Galmuri11-Bold.bdf'))
F14 = bdf.Font(os.path.join(M.FD, 'Galmuri14.bdf'))
FC = bdf.Font(os.path.join(M.FD, 'Galmuri11-Condensed.bdf'))
PLATE = {('EX', 5): '엑셀리온', ('EX', 6): '엑셀라이저', ('EX', 7): '게임 천국', ('FZ', 5): '포메이션 Z', ('FC', 5): '필드 컴뱃',
         ('MK', 5): '모모코 120%', ('MK', 6): '게임 천국', ('BS', 5): '부타상', ('PA', 5): '플러스 알파'}
CAPTION = {('EX', 11): '홍보용 전단', ('EX', 12): '인스트럭션 카드', ('EX', 13): '타이틀 로고', ('EX', 14): '애니메이션 설정서'}
CAP_MK = '미사용 그래픽'                                                    # MK «(没グラフィック)» — EX 에 없는 것


def path(g, base=None):
    return os.path.join(base or os.path.join(ROOT, 'work', 'files'), 'DT%sBIN' % g)


def load(g, base=None):
    lzss.INIT = 0
    b = open(path(g, base), 'rb').read(); s = struct.unpack_from('>I', b, 0)[0]; d, _ = lzss.decompress(b[:4 + s], 4, 1 << 23)
    p = 0x600; r = []
    while p + 4 <= len(d):
        w, h = struct.unpack_from('>HH', d, p)
        if not (1 <= w <= 400 and 1 <= h <= 300): break
        r.append((w, h, d[p + 4:p + 4 + w * h], p + 4)); p += 4 + w * h
    return b, s, bytearray(d), d[:0x600], r


def rgb(ct, bk, c):
    e = struct.unpack_from('>H', ct, bk * 0x200 + 2 * c)[0]; return ((e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3)


def place(pts, cx, cy):
    x0 = min(x for x, _ in pts); x1 = max(x for x, _ in pts); y0 = min(y for _, y in pts); y1 = max(y for _, y in pts)
    ox = round(cx - (x0 + x1) / 2); oy = round(cy - (y0 + y1) / 2)
    return {(x + ox, y + oy) for x, y in pts}


def back(w, h, px):
    """戻る B(64×32): 글자 칸 x6~33·y8~22 → 바탕 46, 흰 47 «취소»(다른 메뉴 戻る = 취소와 같게)"""
    out = bytearray(px)
    for y in range(8, 23):
        for x in range(6, 34): out[y * w + x] = 46
    for x, y in place(F11.draw('취소')[0], 20, 15): out[y * w + x] = 47
    return bytes(out)


def plate(w, h, px, text):
    """이름판(128×32): 안쪽 x4~123·y4~27 = 단색 바탕 → 글자 화소를 바탕으로 · 원본 색(채움·테·모서리) 그대로 굵은 갈무리11"""
    inner = [(x, y) for y in range(4, 28) for x in range(4, 124)]
    bg = collections.Counter(px[y * w + x] for x, y in inner).most_common(1)[0][0]
    ink = {(x, y) for x, y in inner if px[y * w + x] != bg}
    near = lambda x, y, ds: any((x + dx, y + dy) not in ink for dx, dy in ds)
    D4 = ((1, 0), (-1, 0), (0, 1), (0, -1)); D8d = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    ol = collections.Counter(px[y * w + x] for x, y in ink if near(x, y, D4))
    outline = ol.most_common(1)[0][0]
    fill = collections.Counter(px[y * w + x] for x, y in ink if px[y * w + x] != outline).most_common(1)[0][0]
    cn = collections.Counter(px[y * w + x] for x, y in ink if px[y * w + x] not in (outline, fill))
    corner = cn.most_common(1)[0][0] if cn else outline
    out = bytearray(px)
    for x, y in ink: out[y * w + x] = bg
    p14 = F14.draw(text)[0]; G = place(sorted(set(p14) | {(x + 1, y) for x, y in p14}), 63.5, 15.5)   # 갈무리14 + 1px 굵게(원본 글자 14px·2px 획)
    for x, y in G:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if q in G or not (4 <= q[0] <= 123 and 4 <= q[1] <= 27): continue
                v = outline if dx == 0 or dy == 0 else corner
                if out[q[1] * w + q[0]] in (bg, corner): out[q[1] * w + q[0]] = v
    for x, y in G: out[y * w + x] = fill
    over = sum(1 for x, y in G if not (6 <= x <= 121 and 5 <= y <= 26))
    return bytes(out), over


_PAREN = None


def paren():
    """괄호 그림 = EX #11 «(宣伝用チラシ)» 양끝 6열(빈 열로 깨끗이 갈리는 것) — 모든 설명 줄에 같은 괄호"""
    global _PAREN
    if _PAREN is None:
        w, h, px, _ = load('EX')[4][11]
        col = [any(px[y * w + x] for y in range(h)) for x in range(w)]
        l0 = next(x for x in range(w) if col[x]); r1 = next(x for x in range(w - 1, -1, -1) if col[x])
        L = [[px[y * w + x] for x in range(l0, l0 + 6)] for y in range(h)]
        R = [[px[y * w + x] for x in range(r1 - 5, r1 + 1)] for y in range(h)]
        _PAREN = (L, R)
    return _PAREN


def caption(w, h, px, text):
    """설명 줄(120×16): 통째로 지우고 가운데 한글(채움 97·테 99 8방향) + 원본 괄호를 글자 양옆 2px 띄워 붙임(원본 괄호 자리는 너무 벌어짐)"""
    L, R = paren()
    out = bytearray(w * h)
    G = place(F11.draw(text)[0], w / 2 - 0.5, 7.5)
    if max(x for x, _ in G) - min(x for x, _ in G) + 1 > w - 2 * (6 + 4): G = place(FC.draw(text)[0], w / 2 - 0.5, 7.5)   # 넘치면 좁은 글꼴
    x0 = min(x for x, _ in G); x1 = max(x for x, _ in G)
    la = max(0, x0 - 3 - 6); ra = min(w - 6, x1 + 4)
    for y in range(h):
        for i in range(6):
            if L[y][i]: out[y * w + la + i] = L[y][i]
            if R[y][i]: out[y * w + ra + i] = R[y][i]
    for x, y in G:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if q not in G and 0 <= q[0] < w and 0 <= q[1] < h: out[q[1] * w + q[0]] = 99
    for x, y in G: out[y * w + x] = 97
    over = sum(1 for x, y in G if not (la + 6 <= x < ra))
    return bytes(out), over


def jobs():
    """(게임, 번호) → ('back'|'plate'|'cap', 글) — 설명 줄은 EX 것과 바이트 비교로 짝"""
    _, _, _, _, ex = load('EX'); excap = {ex[k][2]: t for (g, k), t in CAPTION.items()}
    J = {}
    for g in GAMES:
        _, _, _, _, r = load(g)
        for k, (w, h, px, _) in enumerate(r):
            if (w, h) == (64, 32): J[(g, k)] = ('back', '취소')
            elif (g, k) in PLATE: J[(g, k)] = ('plate', PLATE[(g, k)])
            elif (w, h) == (120, 16): J[(g, k)] = ('cap', excap.get(px, CAP_MK if g == 'MK' else None))
            elif (w, h) == (128, 32): raise SystemExit('이름판 번역 빠짐 %s #%d' % (g, k))
    return J


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    J = jobs(); res = {}; pairs = []
    for g in GAMES:
        _, _, _, ct, r = load(g)
        for k, (w, h, px, _) in enumerate(r):
            if (g, k) not in J: continue
            kind, t = J[(g, k)]; assert t, (g, k)
            if kind == 'back': new, ov, bk = back(w, h, px), 0, 0
            elif kind == 'plate': (new, ov), bk = plate(w, h, px, t), 1
            else: (new, ov), bk = caption(w, h, px, t), 0
            res[(g, k)] = new; print('%s #%d %s %s%s' % (g, k, kind, t, '  ⚠넘침 %d' % ov if ov else ''))
            im = lambda q: (lambda o: ([o.putpixel((i % w, i // w), rgb(ct, bk, c)) for i, c in enumerate(q) if c], o)[1])(Image.new('RGB', (w, h), (150, 110, 220)))
            pairs.append((im(px), im(new)))
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'dt.pkl'), 'wb'))
    S = 3; W = 128 * S * 2 + 30; H = sum(a.height * S + 6 for a, _ in pairs) + 6
    sh = Image.new('RGB', (W, H), (40, 40, 40)); y = 6
    for a, n in pairs:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(n.resize((n.width * S, n.height * S), Image.NEAREST), (20 + 128 * S, y)); y += a.height * S + 6
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '데이터상세_한글.png')); print(sh.size)
