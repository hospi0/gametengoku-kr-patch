# -*- coding: utf-8 -*-
r"""오프닝 캐릭터 카드 성우 이름 한글(2026-11-09)
  그림: OPENING.BIN 0x4F80C 덩어리(A형) [u32 개수]+레코드 [w][h][u32 0][4비트] — 이름 조각 = 레코드 #27~64(조각 번호 36~73, 번호 = 레코드+9)
  배치표: OPENING2.BIN 0x38F0~·PROLOG.BIN 0xB0~ (같은 표 두 벌, 날것) 항목 8B [u16 조각 번호][u16 순번][s16 x][s16 y], 이름마다 FFFF×4 로 끝
  → 조각을 겹치지 않게 나란히 다시 놓고(원래 왼쪽/오른쪽 맞춤 유지) 한글 이름을 통째로 그려 조각 크기대로 잘라 넣음(카드 조각은 고정이라 안전)
  색: 흰 1 · 그림자 7(오른쪽 2·아래 1), 블랙한산스 4배로 그려 반 넘게 덮인 화소 · 기체 이름(영문)은 그대로
  python tools/opening_ko.py → work/plates/opening.pkl {'recs': {레코드: 4비트}, 'OPENING2.BIN': 바이트, 'PROLOG.BIN': 바이트}, work/미리보기_그림/오프닝_성우이름.png
"""
import os, sys, struct, pickle
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
from menu_logo import syl_mask as _syl
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BHS = r'C:/claude/utils/font/blackhansans/BlackHanSans-Regular.ttf'
CO = 0x4F80C
SS = 4
# (첫 조각 번호, 조각 수, 한글 줄들, 맞춤) — 맞춤 L = x 15 부터, R = 끝을 원래 마지막 조각 끝에
NAMES = [(36, 5, ['니시하라 쿠미코'], 'R'), (41, 3, ['세키', '토모카즈'], 'L'), (44, 5, ['카나이 미카'], 'R'), (49, 5, ['오키아유 류타로'], 'L'),
         (54, 4, ['오오츠카 아키오'], 'R'), (58, 5, ['시이나 헤키루'], 'L'), (63, 4, ['타카하시 미키'], 'R'), (67, 7, ['코오로기 사토미'], 'L')]
TABLES = {'OPENING2.BIN': 0x38F0, 'PROLOG.BIN': 0xB0}


def load():
    lzss.INIT = 0
    b = open(os.path.join(ROOT, 'work', 'files', 'OPENING.BIN'), 'rb').read(); s = struct.unpack_from('>I', b, CO)[0]
    d, _ = lzss.decompress(b[:CO + 4 + s], CO + 4, 1 << 23)
    n = struct.unpack_from('>I', d, 0)[0]; p = 4; offs = []
    for _ in range(n):
        w, h = struct.unpack_from('>HH', d, p); offs.append((p + 8, w, h)); p += 8 + w * h // 2
    return b, s, bytearray(d), offs


def entries(buf):
    """조각 번호 → (항목 위치, x, y)"""
    out = {}
    for p in range(0, len(buf) - 8, 2):
        i, k, x, y = struct.unpack_from('>HHhh', buf, p)
        if 36 <= i <= 73 and k < 8 and 0 <= x < 320 and 150 <= y <= 200 and i not in out: out[i] = (p, x, y)
    return out


def text_mask(t, W, H):
    """한 줄 글자를 W×H 안에 가장 크게(4배로 그려 반 넘게 덮인 화소)"""
    for bh in range(H - 3, 8, -1):
        for wx in (1.0, 0.92, 0.85, 0.78, 0.7):
            F = set(); x = 0
            for ch in t:
                if ch == ' ': x += bh * SS // 3; continue
                m, mw = _syl(ch, bh * SS, 0, font=BHS, wx=wx, fat=0)
                F |= {(a + x, b) for a, b in m}; x += mw + SS * 2
            cnt = Counter((a // SS, b // SS) for a, b in F)
            G = {p for p, n in cnt.items() if n >= SS * SS // 2}
            gw = max(a for a, _ in G) + 1; gh = max(b for _, b in G) - min(b for _, b in G) + 1
            if gw + 3 <= W and gh + 2 <= H:
                y0 = min(b for _, b in G)
                return {(a + (W - gw - 2) // 2, b - y0 + (H - gh - 1) // 2) for a, b in G}
    raise SystemExit('안 들어감 ' + t)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b, s, d, offs = load()
    tabs = {n: bytearray(open(os.path.join(ROOT, 'work', 'files', n), 'rb').read()) for n in TABLES}
    E = entries(tabs['OPENING2.BIN']); E2 = entries(tabs['PROLOG.BIN'])
    assert set(E) == set(E2) == set(range(36, 74))
    cram = open(os.path.join(ROOT, 'work', 'mem', '그림_오프닝카드', 'CRAM.bin'), 'rb').read()
    col = lambda i: (lambda c: ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))(struct.unpack_from('>H', cram, 2 * i)[0])
    recs = {}; rows = []
    for first, n, lines, al in NAMES:
        ids = list(range(first, first + n)); sz = [offs[i - 9][1:] for i in ids]
        # 새 배치(캔버스 안 좌표): 기본 = 한 줄로 나란히, 높이 48 보다 작은 조각은 세로 가운데 · 関智一 = 두 줄(마지막 조각을 아랫줄 오른쪽)
        if len(lines) == 2:
            pos = [(0, 0), (sz[0][0], 0), (sz[0][0] + sz[1][0], 48 - sz[2][1])]
        else:
            x = 0; pos = []
            for w, h in sz: pos.append((x, (48 - h) // 2)); x += w
        W = max(px + w for (px, _), (w, h) in zip(pos, sz)); H = 48
        cover = {(px + i, py + j) for (px, py), (w, h) in zip(pos, sz) for i in range(w) for j in range(h)}
        G = set()
        if len(lines) == 2:
            G |= text_mask(lines[0], sz[0][0] + sz[1][0], 24)
            G |= {(a, b + 24) for a, b in text_mask(lines[1], W, 24)}
        else:
            top = max(py for _, py in pos); bot = min(py + h for (_, py), (w, h) in zip(pos, sz))   # 모든 조각이 덮는 세로 범위
            G = {(a, b + top) for a, b in text_mask(lines[0], W, bot - top)}
        canvas = {}
        for a, b_ in G:
            for dx, dy in ((2, 1), (1, 1), (2, 0)):
                q = (a + dx, b_ + dy)
                if q not in G: canvas[q] = 7
        for p in G: canvas[p] = 1
        lost = sum(1 for p in canvas if p not in cover)
        # 표 x·y
        ox_old = [E[i][1] for i in ids]; end_old = max(E[i][1] + sz[k][0] for k, i in enumerate(ids))
        X0 = 15 if al == 'L' else end_old - W
        for k, i in enumerate(ids):
            for tb, EE in (('OPENING2.BIN', E), ('PROLOG.BIN', E2)):
                struct.pack_into('>hh', tabs[tb], EE[i][0] + 4, X0 + pos[k][0], 170 + pos[k][1])
            w, h = sz[k]; px = [canvas.get((pos[k][0] + x, pos[k][1] + y), 0) for y in range(h) for x in range(w)]
            recs[i - 9] = bytes((px[j] << 4) | px[j + 1] for j in range(0, w * h, 2))
        print(' / '.join(lines), '조각', n, '폭', W, '맞춤', al, 'x', X0, '잘림', lost)
        # 미리보기: 원본 배치 | 새 배치 (화면 320 폭)
        bef = Image.new('RGB', (320, 52), (150, 150, 40)); aft = Image.new('RGB', (320, 52), (150, 150, 40))
        for k, i in enumerate(ids):
            o, w, h = offs[i - 9]
            for y in range(h):
                for x in range(w):
                    q = d[o + (y * w + x) // 2]; v = q >> 4 if (y * w + x) % 2 == 0 else q & 15
                    if v and 0 <= E[i][1] + x < 320: bef.putpixel((E[i][1] + x, E[i][2] - 168 + y), col(v))
            for y in range(h):
                for x in range(w):
                    v = canvas.get((pos[k][0] + x, pos[k][1] + y), 0)
                    if v and 0 <= X0 + pos[k][0] + x < 320: aft.putpixel((X0 + pos[k][0] + x, pos[k][1] + 2 + y), col(v))
        rows.append((bef, aft))
    pickle.dump({'recs': recs, **{n: bytes(t) for n, t in tabs.items()}}, open(os.path.join(ROOT, 'work', 'plates', 'opening.pkl'), 'wb'))
    S = 2; sh = Image.new('RGB', (320 * S * 2 + 30, sum(52 * S + 8 for _ in rows) + 8), (40, 40, 40)); y = 8
    for a, n_ in rows:
        sh.paste(a.resize((320 * S, 52 * S), Image.NEAREST), (10, y)); sh.paste(n_.resize((320 * S, 52 * S), Image.NEAREST), (20 + 320 * S, y)); y += 52 * S + 8
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '오프닝_성우이름.png')); print(sh.size)
