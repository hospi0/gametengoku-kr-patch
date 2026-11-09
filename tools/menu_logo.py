# -*- coding: utf-8 -*-
r"""메인 메뉴 「メニュー」 로고 → 「메뉴」(2026-11-09)
  YKBIN 0x25310 #0~3 = 글자 조각(メ 40×40 · ニ ュ ー 32×32), #4 = 통짜 로고 144×40(조각 + 노란 띠)
  조각 위치(#4 안): #0 (17,0) · #1 (48,0) · #2 (76,0) · #3 (98,0)
  한글 2자 → #1 = 메(ニ 주황 그라데이션) · #2 = 뉴(ュ 보라 그라데이션) · #0·#3 = 투명. 띠 가운데(72) ≈ 두 조각 가운데(78)
  글자 구조(원본 그대로): 채움 = 줄별 그라데이션 · 흰 테두리(색 1) 2px · 검은 그림자(색 211) 테두리 모양 (+3,+3)
  글꼴 = 갈무리11 ×2(원본처럼 굵고 각진 막대 획)
  python tools/menu_logo.py → work/plates/logo.pkl, work/미리보기_그림/메뉴로고.png(원본 | 한글, 색 은행 0x100)
"""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ykbin, bdf, menu_gfx as M
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = bdf.Font(os.path.join(M.FD, 'Galmuri11.bdf'))
POS = {0: (17, 0), 1: (48, 0), 2: (76, 0), 3: (98, 0)}
WHITE, SHADOW = 1, 211
KO = {1: '메', 2: '뉴'}
JUA = r'C:/claude/utils/font/jua/Jua-Regular.ttf'


def gradient(w, h, px):
    """원본 조각 줄별 채움 색(위→아래, 테두리·그림자·투명 제외 최빈)"""
    import collections
    out = []
    for y in range(h):
        c = collections.Counter(v for v in px[y * w:(y + 1) * w] if v not in (0, WHITE, SHADOW, 32, 122))
        if c and c.most_common(1)[0][1] >= 8: out.append(c.most_common(1)[0][0])
    return out


def piece(w, h, ch, grad, S=2, ol=2, sd=3):
    pts, _ = F.draw(ch)
    x0 = min(x for x, _ in pts); y0 = min(y for _, y in pts)
    G = {((x - x0) * S + dx, (y - y0) * S + dy) for x, y in pts for dx in range(S) for dy in range(S)}
    gw = max(x for x, _ in G) + 1; gh = max(y for _, y in G) + 1
    ox = (w - sd - gw) // 2 + 1; oy = 2 + ol                             # 원본처럼 위 2줄 비우고 테두리부터
    G = {(x + ox, y + oy) for x, y in G}
    O = {(x + dx, y + dy) for x, y in G for dx in range(-ol, ol + 1) for dy in range(-ol, ol + 1)} - G
    Sh = {(x + sd, y + sd) for x, y in G | O} - G - O
    out = bytearray(w * h)
    for x, y in Sh:
        if 0 <= x < w and 0 <= y < h: out[y * w + x] = SHADOW
    for x, y in O:
        if 0 <= x < w and 0 <= y < h: out[y * w + x] = WHITE
    for x, y in G:
        if 0 <= x < w and 0 <= y < h:
            i = int((y - oy) * len(grad) / gh); out[y * w + x] = grad[min(i, len(grad) - 1)]
    clip = sum(1 for x, y in G | O | Sh if not (0 <= x < w and 0 <= y < h))
    return bytes(out), clip


def word_mask(text, bw, bh, font=None):
    """주아(둥글고 장난스러운 — 하스피 «원본처럼 부드럽고 살짝 장난스러운걸로»)로 크게 그려 (bw×bh) 상자로 줄임 → 굵은 막대 획(원본 로고처럼)"""
    from PIL import ImageFont, ImageDraw
    f = ImageFont.truetype(font or JUA, 120); x0, y0, x1, y1 = f.getbbox(text)
    im = Image.new('L', (x1 - x0, y1 - y0), 0); ImageDraw.Draw(im).text((-x0, -y0), text, font=f, fill=255)
    im = im.resize((bw, bh), Image.LANCZOS)
    return {(x, y) for y in range(bh) for x in range(bw) if im.getpixel((x, y)) >= 128}


def syl_mask(ch, bh, tilt=0.0, font=None, wx=1.45, fat=1):
    """음절 하나 = 주아 비율 그대로 높이 bh, 살짝 기울임(원본 글자처럼 통통 튀는 느낌)"""
    from PIL import ImageFont, ImageDraw
    f = ImageFont.truetype(font or JUA, 160); x0, y0, x1, y1 = f.getbbox(ch)
    im = Image.new('L', (x1 - x0 + 40, y1 - y0 + 40), 0); ImageDraw.Draw(im).text((20 - x0, 20 - y0), ch, font=f, fill=255)
    if tilt: im = im.rotate(tilt, resample=Image.BICUBIC, expand=True)
    im = im.crop(im.getbbox()); sc = bh / im.height; im = im.resize((max(1, round(im.width * sc * wx)), bh), Image.LANCZOS)   # 가로로 넓혀 원본처럼 통통하게
    m = {(x, y) for y in range(bh) for x in range(im.width) if im.getpixel((x, y)) >= 128}
    for _ in range(fat): m |= {(x + dx, y) for x, y in m for dx in (1,)}                     # 세로획 1px 굵게
    return m, im.width + fat


LAYOUT = [('메', 5.0, 0), ('뉴', -5.0, -1)]                                 # (음절, 기울기°, 세로 어긋남) — 원본 メニュー 처럼 번갈아 기울임


def logo(recs, cx=72, top=3, bh=23, gap=7, ol=2, sd=3):   # 글자 사이 7(하스피 «살짝 띄우자»)
    """음절별로 그려 이어 붙인 뒤 조각 사각형으로 잘라 나눔(조각 겹치는 곳은 양쪽에 같은 화소). 색 = 음절별 그라데이션(메=メ 파랑, 뉴=ニ 주황)"""
    grads = [gradient(*recs[0]), gradient(*recs[1])]
    ms = [syl_mask(ch, bh, t) for ch, t, _ in LAYOUT]
    tw = sum(w for _, w in ms) + gap * (len(ms) - 1); x = cx - tw // 2
    canvas = {}; G = {}
    for (m, w), (_, _, dy), g in zip(ms, LAYOUT, grads):
        for px, py in m: G[(px + x, py + top + dy)] = g[min(int(py * len(g) / bh), len(g) - 1)]
        x += w + gap
    O = {(a + dx, b + dy) for a, b in G for dx in range(-ol, ol + 1) for dy in range(-ol, ol + 1)} - set(G)
    Sh = {(a + sd, b + sd) for a, b in set(G) | O} - set(G) - O
    for p in Sh: canvas[p] = SHADOW
    for p in O: canvas[p] = WHITE
    canvas.update(G)
    out = {}; miss = 0
    for k in range(4):
        w, h, _ = recs[k]; ox, oy = POS[k]; b = bytearray(w * h)
        for (x, y), v in canvas.items():
            if ox <= x < ox + w and oy <= y < oy + h: b[(y - oy) * w + x - ox] = v
        out[k] = bytes(b)
    for (x, y) in canvas:
        if not any(POS[k][0] <= x < POS[k][0] + recs[k][0] and POS[k][1] <= y < POS[k][1] + recs[k][1] for k in range(4)): miss += 1
    return out, canvas, miss


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = open(os.path.join(ROOT, 'work', 'files', 'YKBIN'), 'rb').read(); recs = ykbin.chunk(b, 0x25310)
    cram = open(os.path.join(ROOT, 'work', 'mem', '메인메뉴+나레이션', 'CRAM.bin'), 'rb').read()
    new, canvas, miss = logo(recs); print('조각 밖 화소', miss)
    # 통짜 로고 = 띠(빈 판 #4) 위에 조각 그대로 겹침
    saved = pickle.load(open(os.path.join(ROOT, 'work', 'plates', 'plates.pkl'), 'rb'))
    bar = next(v['plate'] for v in saved.values() if (0x25310, 4) in v['members'])
    W, H, _ = recs[4]; big = bytearray(bar)
    for k in (0, 1, 2, 3):
        pass
    for (x, y), v in canvas.items():
        if 0 <= x < W and 0 <= y < H: big[y * W + x] = v
    new[4] = bytes(big)
    pickle.dump(new, open(os.path.join(ROOT, 'work', 'plates', 'logo.pkl'), 'wb'))
    S = 4; rows = []
    for k in range(5):
        w, h, px = recs[k]; rows.append((M.to_img(w, h, px, cram, 0x100), M.to_img(w, h, new[k], cram, 0x100)))
    Wd = max(a.width for a, _ in rows) * S * 2 + 30; Hd = sum(a.height * S + 10 for a, _ in rows) + 10
    sh = Image.new('RGB', (Wd, Hd), (40, 40, 40)); y = 10
    for a, n in rows:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(n.resize((n.width * S, n.height * S), Image.NEAREST), (20 + a.width * S, y)); y += a.height * S + 10
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '메뉴로고_간격.png')); print(sh.size)
