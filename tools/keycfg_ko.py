# -*- coding: utf-8 -*-
r"""키 컨피그 그림(YKBIN 0x39918) 한글 — 판 안 만듦: 그림·아이콘(A~G·B·C·R·L 글자 그림) 그대로, «글자 줄 사각형»만 지우고 한글
  (하스피 2026-11-09 «키컨피그는 왜 판을 쳐만들어 그림은 놔두고 글자만 교체해야지»)
  줄 사각형 안 = 그 줄 바탕색(행마다 sample 열 색)으로 지움 → 원본 글자 색(채움·테두리·그림자·줄별 그라데이션)으로 한글
  python tools/keycfg_ko.py → work/plates/keycfg.pkl, work/미리보기_그림/키컨피그.png(원본 | 한글)
"""
import os, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ykbin, bdf, menu_gfx as M
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = {'b11': os.path.join(M.FD, 'Galmuri11-Bold.bdf'), 'r11': os.path.join(M.FD, 'Galmuri11.bdf'),
         'c11': os.path.join(M.FD, 'Galmuri11-Condensed.bdf'), 'r9': os.path.join(M.FD, 'Galmuri9.bdf'), 'r7': os.path.join(M.FD, 'Galmuri7.bdf')}
FONTS = {k: bdf.Font(v) for k, v in FONTS.items()}


class Bold:                                                              # 갈무리9 + 가로 1px 굵게(원본 작은 굵은 글자 크기)
    def __init__(self, f): self.f = f
    def draw(self, t):
        pts, w = self.f.draw(t); return sorted(set(pts) | {(x + 1, y) for x, y in pts}), w + 1


FONTS['b9'] = Bold(FONTS['r9'])

# 줄 = (x0, x1, y0, y1, 바탕 견본 열, 한글, 모양 'ol'(테두리+그라데이션)|'sh'(흰 글자+그림자), 글꼴 후보)
TYPE = [(18, 44, 8, 18, 44, '타입', 'sh', ['b9', 'r9'])]
BTN = lambda t: [(16, 44, 3, 14, 45, '버튼', 'ol', ['r9'])] + ([(4, 46, 16, 25, 3, t, 'sh', ['b11', 'b9'])] if t else [])
LINES = {**{k: TYPE for k in range(7)},
         **{k: BTN('샷') for k in (8, 11, 14, 17)}, **{k: BTN('봄버') for k in (9, 12, 15, 18)}, **{k: BTN('연사') for k in (10, 13, 16, 19)},
         20: BTN(None),                                                  # R버튼 / — (아래 줄 «—» 그대로)
         21: [(28, 72, 3, 14, 71, '버튼', 'ol', ['r9'], {'fill': 1, 'outline': 163, 'shadow': None, 'left': 1}),   # L 바로 뒤에 붙임
              (3, 72, 15, 22, 2, '가로 화면일 때', 'pl', ['r9', 'r7']), (3, 72, 23, 31, 2, '점수 표시 ON/OFF', 'pl', ['r9', 'r7'])],
         22: [(3, 52, 3, 14, 4, '방향 버튼', 'ol', ['r9', 'r7'], {'fill': 1, 'outline': 163, 'shadow': None}), (3, 52, 16, 25, 2, '기체 이동', 'pl', ['r9', 'r7'])],
         23: [(3, 69, 3, 14, 4, '스타트 버튼', 'ol', ['r9', 'r7'], {'fill': 1, 'outline': 163, 'shadow': None}), (3, 69, 15, 25, 2, '일시정지 ON/OFF', 'pl', ['r9', 'r7'])]}


def line_colors(w, orig, ers, x0, x1, y0, y1):
    m = {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if orig[y * w + x] != ers[y * w + x]}
    P = lambda x, y: orig[y * w + x]
    inside = [(x, y) for x, y in m if all(p in m for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))]
    # 채움 = 바탕(마스크 밖)에 가장 덜 닿는 색 · 테두리 = 가장 많이 닿는 색 (둘 다 마스크 화소의 10% 이상)
    cnt = collections.Counter(P(x, y) for x, y in m); touch = collections.Counter()
    for x, y in m:
        if any(q not in m for q in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))): touch[P(x, y)] += 1
    big = [c for c, n in cnt.items() if n >= len(m) * 0.1] or [cnt.most_common(1)[0][0]]
    fill = min(big, key=lambda c: touch[c] / cnt[c]); outline = max(big, key=lambda c: touch[c] / cnt[c])
    fills = {c for c, n in collections.Counter(P(x, y) for x, y in inside).items() if n >= 3} | {fill}
    shc = collections.Counter(P(x, y) for x, y in m if P(x, y) not in fills and P(x, y) != outline and (x - 1, y - 1) in m)
    shadow = shc.most_common(1)[0][0] if shc else outline
    fr = {}
    for y in range(y0, y1 + 1):
        c = collections.Counter(P(x, yy) for x, yy in inside if yy == y and P(x, yy) not in (outline, shadow))
        if c: fr[y] = c.most_common(1)[0][0]
    ys = [y for _, y in m]; return fill, outline, shadow, fr, (min(ys), max(ys)) if ys else (y0, y1)


def build(w, h, px, lines):
    out = bytearray(px); info = []
    for x0, x1, y0, y1, sc, text, style, fonts, *opt in lines:
        ers = bytearray(out)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): ers[y * w + x] = out[y * w + sc]          # 줄 바탕 = 견본 열 색
        fill, outline, shadow, fr, (my0, my1) = line_colors(w, px, ers, x0, x1, y0, y1)
        if opt:                                                          # 색 직접 지정(자동 판정이 채움·테두리를 뒤집는 줄)
            fill = opt[0].get('fill', fill); outline = opt[0].get('outline', outline); shadow = opt[0].get('shadow', shadow); fr = {}
        if style == 'sh' and not opt: shadow = outline                   # 흰 글자 줄 그림자 = 바탕에 가장 많이 닿는 색(버튼 색마다 하나로 일정)
        pad = 1 if style == 'ol' else 0
        for f in fonts:
            pts, _ = FONTS[f].draw(text)
            if f == 'b11' and style == 'sh': pass
            ext = 2 * pad + (1 if style != 'pl' else 0)                  # 테두리 양쪽 + 그림자 1
            if (max(x for x, _ in pts) - min(x for x, _ in pts) + 1 + ext <= x1 - x0 + 1 and
                    max(y for _, y in pts) - min(y for _, y in pts) + 1 + ext <= y1 - y0 + 1): break
        ix0 = min(x for x, _ in pts); ix1 = max(x for x, _ in pts); iy0 = min(y for _, y in pts); iy1 = max(y for _, y in pts)
        ox = round((x0 + x1) / 2 - (ix0 + ix1) / 2); oy = round((my0 + my1) / 2 - (iy0 + iy1) / 2)
        if opt and opt[0].get('left'): ox = x0 + opt[0]['left'] + pad - ix0
        lo = pad; hi = pad + (1 if style != 'pl' else 0)                 # 사각형 안으로 밀어 넣기(테두리·그림자 포함)
        ox = max(x0 + lo - ix0, min(ox, x1 - hi - ix1)); oy = max(y0 + lo - iy0, min(oy, y1 - hi - iy1))
        G = {(x + ox, y + oy) for x, y in pts}
        if style == 'ol':
            O = {(x + dx, y + dy) for x, y in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G
            S = {(x + 1, y + 1) for x, y in G | O} - G - O if shadow is not None else set()
        elif style == 'pl':                                              # 설명 줄 = 한 색 1px 글자(테두리·그림자 없음)
            O = set(); S = set(); fill = collections.Counter(px[y * w + x] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if px[y * w + x] != ers[y * w + x]).most_common(1)[0][0]
        else:
            O = set(); S = {(x + 1, y + 1) for x, y in G} - G
        ok = lambda x, y: x0 <= x <= x1 and y0 <= y <= y1
        for x, y in S:
            if ok(x, y): ers[y * w + x] = shadow
        for x, y in O:
            if ok(x, y): ers[y * w + x] = outline
        gh = iy1 - iy0 + 1; ry = sorted(fr)
        for x, y in G:
            if not ok(x, y): continue
            c = fill
            if style == 'ol' and len(ry) >= 3:                           # 원본 줄별 그라데이션을 새 글자 높이에 늘려 씀
                c = fr[ry[min(int((y - oy - iy0) * len(ry) / gh), len(ry) - 1)]]
            ers[y * w + x] = c
        over = sum(1 for p in G | O | S if not ok(*p))
        info.append((text, f, over)); out = ers
    return bytes(out), info


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = open(os.path.join(ROOT, 'work', 'files', 'YKBIN'), 'rb').read(); recs = ykbin.chunk(b, 0x39918)
    cram = open(os.path.join(ROOT, 'work', 'mem', '키컨피그', 'CRAM.bin'), 'rb').read()
    new = {}; rows = []
    # A~F타입 글자 색 = G타입(#6) 색으로 통일(하스피 «탑을 g타입의 색깔로 통일»)
    x0, x1, y0, y1, sc = TYPE[0][:5]; w, h, px = recs[6]; ers = bytearray(px)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1): ers[y * w + x] = px[y * w + sc]
    gf, go, gs, *_ = line_colors(w, px, ers, x0, x1, y0, y1)
    gf, go = 1, 88                                                       # G타입 원본 = 흰 글자(1) + 어두운 그림자(88) (자동 판정은 번짐 색을 채움으로 잡음)
    for k in range(7): LINES[k] = [TYPE[0] + ({'fill': gf, 'outline': go, 'shadow': go},)]
    for k, lines in LINES.items():
        w, h, px = recs[k]; new[k], info = build(w, h, px, lines); print(k, info)
        bank = 0x100 if 8 <= k <= 20 else 0x200
        rows.append((M.to_img(w, h, px, cram, bank), M.to_img(w, h, new[k], cram, bank)))
    pickle.dump(new, open(os.path.join(ROOT, 'work', 'plates', 'keycfg.pkl'), 'wb'))
    S = 3; Wd = max(a.width for a, _ in rows) * S * 2 + 30; Hd = sum(a.height * S + 8 for a, _ in rows) + 8
    sh = Image.new('RGB', (Wd, Hd), (40, 40, 40)); y = 8
    for a, n in rows:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(n.resize((n.width * S, n.height * S), Image.NEAREST), (20 + a.width * S, y)); y += a.height * S + 8
    for n in range(1, 50):                                               # 사용자가 열어 둔 미리보기는 잠김 → 번호 붙여 새로
        fn = os.path.join(ROOT, 'work', '미리보기_그림', '키컨피그%s.png' % ('' if n == 1 else '_%d' % n))
        try: sh.save(fn); break
        except OSError: continue
    print(fn, sh.size)
