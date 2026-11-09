# -*- coding: utf-8 -*-
r"""가로 화면 스테이지 클리어 입체 글자 한글(2026-11-09) — STCX.BIN 조각 7개 [u16 폭][u16 높이][0x0018][0x0400] + 8비트 화소(CRAM 0x400+값)
  조각 크기·자리(파일 앞 표)는 그대로 → 조각마다 한 음절: ス→스 テ→테 ー→이(24×16 작은 조각) ジ→지 ク→클 リ→리 ア→어
  입체 = 주아 음절(조각마다 기울임) 앞면 빨강 111 · 위 가장자리 밝은 빨강 115 · 왼쪽 옆면 분홍(107→110) · 아래 옆면 진자주(79→26, 깊을수록 어둡게)
  python tools/stcx_ko.py → work/plates/stcx.pkl {'STCX.BIN': 새 바이트}, work/미리보기_그림/스테이지클리어_한글.png(원본 | 한글, 화면 배치)
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from menu_logo import syl_mask as _syl
BHS = r'C:/claude/utils/font/blackhansans/BlackHanSans-Regular.ttf'      # 굵은 고딕(원본 입체 글자처럼 뭉툭)
syl_mask = lambda ch, bh, t, wx=1.0, fat=0: _syl(ch, bh, t, font=BHS, wx=wx, fat=fat)
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# (자료 오프셋, 폭, 높이, 음절, 기울기°, 화면 x, 화면 y) — 화면 자리는 스테이지클리어 스테이트 VDP1 명령에서
PIECES = [(1644, 40, 32, '스', 8, 85, 55), (2932, 40, 32, '테', -6, 105, 53), (4220, 24, 16, '이', 4, 133, 46),
          (7580, 40, 32, '지', 6, 146, 52), (6612, 40, 24, '클', -5, 168, 52), (5644, 40, 24, '리', 5, 190, 53), (4612, 32, 32, '어', -6, 207, 50)]
PINK = [110, 109, 108, 107, 106, 97]                                     # 왼쪽 옆면(앞에 가까울수록 밝게)
DARK = [79, 74, 65, 58, 50, 44, 32, 26]                                  # 아래 옆면(깊을수록 어둡게)
DEPTH = 4
PINK_R = [110, 109, 108, 107, 106, 97, 96, 94]                          # 분홍 옆면: 위(밝음)→아래
DARK_R = [79, 77, 74, 69, 65, 61, 58, 56, 50, 44, 38]                 # 진자주 아랫면: 왼쪽→오른쪽(어둡게)


def piece(w, h, ch, tilt):
    bh = h - DEPTH - 1
    m, mw = syl_mask(ch, bh, tilt, wx=1.0 if w > 24 else 1.1, fat=0)
    mh = max(b for _, b in m) + 1
    wx = 1.0
    while mw > w - DEPTH and w < 20 and wx > 0.55:                       # 좁은 조각(«이», 화면 16×24): 높이는 두고 가로만 좁혀 크게(하스피 «이가 너무 작다»)
        wx -= 0.05; m, mw = syl_mask(ch, bh, tilt, wx=wx, fat=0); mh = max(b for _, b in m) + 1
    while mw > w - DEPTH and bh > 8:
        bh -= 1; m, mw = syl_mask(ch, bh, tilt, wx=wx, fat=0); mh = max(b for _, b in m) + 1
    ox = DEPTH + (w - DEPTH - mw) // 2; oy = (h - DEPTH - mh) // 2
    F = {(a + ox, b + oy) for a, b in m}
    out = [[0] * w for _ in range(h)]
    # 뒤에서 앞으로: 깊이 k 만큼 왼쪽 아래로 민 모양. 면 방향 = 그 화소를 만든 앞면 화소가 왼쪽 경계면 분홍(빛 받는 옆면), 아니면 진자주(아랫면)
    #  색은 깊이 층별이 아니라 면을 따라 부드럽게(하스피 «그라데이션이 투박») — 분홍 = 위→아래, 진자주 = 왼쪽→오른쪽(오른쪽일수록 어둡게)
    ys = [b for _, b in F]; xs = [a for a, _ in F]; y0, y1 = min(ys), max(ys) + DEPTH; x0, x1 = min(xs) - DEPTH, max(xs)
    ramp = lambda R, t: R[min(len(R) - 1, max(0, int(t * len(R))))]
    # 면 종류는 앞면에 바로 붙은 층(k=1)에서 정하고(오른쪽이 앞면 = 왼쪽 옆면 분홍, 아니면 아랫면 진자주) 깊은 층은 대각선 앞 칸 것을 물려받음
    #  → 기울어진 획의 들쭉날쭉한 경계 때문에 생기던 사선 줄무늬 없음
    cls = {}
    for k in range(1, DEPTH + 1):
        for b in range(h):
            for a in range(w):
                if (a, b) in F or (a, b) in cls: continue
                if (a + k, b - k) not in F: continue
                if k == 1: cls[(a, b)] = 'P' if (a + 1, b) in F else 'D'
                else: cls[(a, b)] = cls.get((a + 1, b - 1), 'P' if (a + 1, b) in F else 'D')
    for (a, b), c in cls.items():
        out[b][a] = ramp(PINK_R, (b - y0) / max(1, y1 - y0 + 1)) if c == 'P' else ramp(DARK_R, (a - x0) / max(1, x1 - x0 + 1))
    for a, b in F:
        if 0 <= a < w and 0 <= b < h: out[b][a] = 115 if (a, b - 1) not in F else 111
    over = sum(1 for a, b in F if not (0 <= a < w and 0 <= b < h))
    return out, over


def to_img(px, w, h, cram):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); pp = im.load()
    for y in range(h):
        for x in range(w):
            v = px[y * w + x]
            if v:
                c = struct.unpack_from('>H', cram, 2 * (0x400 + v))[0]; pp[x, y] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3, 255)
    return im


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src = os.path.join(ROOT, 'work', 'files', 'STCX.BIN')
    b = bytearray(open(src, 'rb').read()); orig = bytes(b)
    cram = open(os.path.join(ROOT, 'work', 'mem', '스테이지클리어', 'CRAM.bin'), 'rb').read()
    XS = {}; x = 4
    for o, w, h, *_ in PIECES: XS[o] = x; x += h - 4
    scene = [Image.new('RGB', (230, 70), (24, 80, 150)) for _ in range(2)]
    for o, w, h, ch, t, sx, sy in PIECES:
        assert struct.unpack_from('>HH', orig, o - 8) == (w, h)
        # ★게임은 이 조각을 90° 돌려 찍는다(VDP1 꼭짓점 A=왼쪽 아래·B=왼쪽 위, 2026-11-09 하스피 «세로로 나옴») → 화면 방향(폭 h·높이 w)으로 그리고 눕혀 저장
        #   화면(sx, sy) = 텍스처(tx = w-1-sy, ty = sx)
        g, ov = piece(h, w, ch, t); print('%d %dx%d %s%s' % (o, w, h, ch, '  ⚠넘침 %d' % ov if ov else ''))
        flat = bytes(g[w - 1 - tx][ty] for ty in range(h) for tx in range(w)); b[o:o + w * h] = flat
        for i, px in enumerate((orig[o:o + w * h], flat)):
            disp = [px[ty * w + (w - 1 - sy)] for sy in range(w) for ty in range(h)]
            im = to_img(disp, h, w, cram); scene[i].paste(im, (XS[o], 70 - w - 4), im)
    assert len(b) == len(orig)
    pickle.dump({'STCX.BIN': bytes(b)}, open(os.path.join(ROOT, 'work', 'plates', 'stcx.pkl'), 'wb'))
    S = 4; sh = Image.new('RGB', (230 * S, 140 * S + 10), (40, 40, 40))
    for i, im in enumerate(scene): sh.paste(im.resize((230 * S, 70 * S), Image.NEAREST), (0, i * (70 * S + 10)))
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '스테이지클리어_한글.png')); print(sh.size)
