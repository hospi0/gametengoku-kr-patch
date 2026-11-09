# -*- coding: utf-8 -*-
r"""엔딩 글자 띠 «おつかれさまー» → «수고했어~»(하스피 2026-11-09)
  ENDY01·ENDY03(가로 256×64) = 같은 화소 번호(팔레트만 다름, 03 은 유키 그림과 팔레트 공유) → ENDY01 팔레트로 그려 두 파일에 같은 번호
  ENDT01·ENDT03(세로 80×224, 90° 돌려 저장, 가로판과 다른 그림) → ENDT01 팔레트로 따로
  파일 구조: [u32 n][u32 블록 오프셋…] · 블록 앞 0x200 = 팔레트 256 · 'Yc'[u16 개수][항목 8B] 다음 첫 항목 화소 = 띠(8비트)
  그림 = 주아 음절(번갈아 기울임) · 앞면 분홍 세로 그라데이션 · 청록 테 2px · 왼쪽 아래로 주황 옆면 · 바깥 노랑 1px → 그 파일 팔레트 최근접 색 번호
  python tools/ending_ko.py → work/plates/ending.pkl {파일: 새 바이트}, work/미리보기_그림/엔딩_수고했어.png(원본 | 한글, 실제 팔레트)
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from menu_logo import syl_mask
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = ['수', '고', '했', '어', '~']
TILT = [6, -5, 4, -6, 5]; DY = [1, -2, 0, -1, 1]
PINK = [(248, 168, 192), (248, 136, 168), (248, 104, 152), (248, 64, 120), (248, 24, 104), (248, 0, 80), (240, 0, 72)]
TEAL = [(176, 216, 216), (152, 192, 192), (120, 168, 152), (96, 144, 136)]
ORANGE = [(248, 152, 72), (224, 136, 56), (200, 120, 48), (184, 88, 32), (160, 80, 32), (144, 72, 16), (120, 72, 32)]
YELLOW = (248, 248, 8)
DEPTH = 5


def strip(b):
    o = struct.unpack_from('>I', b, 4)[0]; cnt = struct.unpack_from('>H', b, o + 2)[0]
    w, h, f, _ = struct.unpack_from('>HHHH', b, o + 4); p = o + 4 + 8 * cnt
    # 팔레트 = 파일 머리 [u32 n][u32 블록 오프셋(0 아닌 것만)] 바로 뒤부터 + 항목의 팔레트 번호×2 (03 은 블록이 2개라 0xC부터 — 블록 앞 0x200 으로 짚으면 엉뚱한 줄무늬)
    nb = sum(1 for i in range(struct.unpack_from('>I', b, 0)[0]) if struct.unpack_from('>I', b, 4 + 4 * i)[0])
    bank = struct.unpack_from('>H', b, o + 4 + 6)[0]
    pal = [struct.unpack_from('>H', b, 4 + 4 * nb + 2 * bank + 2 * k)[0] for k in range(256)]
    return w, h, p, [((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3) for c in pal]


def art(W, H, WX=1.05, FAT=0):
    """가로로 읽는 W×H RGBA 그림"""
    for bh in range(H - 10, 10, -1):
        ms = [syl_mask(ch, bh if ch != '~' else int(bh * 0.6), t, wx=WX, fat=2) for ch, t in zip(TEXT, TILT)]
        ms = [(m | {(a + dx, b + dy) for a, b in m for dx in range(-FAT, FAT + 1) for dy in range(-FAT, FAT + 1) if abs(dx) + abs(dy) <= FAT}, mw) for m, mw in ms]   # 원본처럼 통통하게
        ms = [({(a + FAT, b + FAT) for a, b in m}, mw + 2 * FAT) for m, mw in ms]
        tw = sum(mw for _, mw in ms) + 2 * (len(ms) - 1)
        if tw <= W - DEPTH - 8: break
    F = set(); x = (W - DEPTH - tw) // 2 + DEPTH
    top = (H - bh - DEPTH) // 2
    for (m, mw), dy, ch in zip(ms, DY, TEXT):
        yo = top + dy + (bh // 4 if ch == '~' else 0)
        F |= {(a + x, b + yo) for a, b in m}; x += mw + 2
    O = {(a + dx, b + dy) for a, b in F for dx in range(-2, 3) for dy in range(-2, 3) if abs(dx) + abs(dy) <= 2} - F
    body = F | O
    E = set()
    for k in range(1, DEPTH + 1): E |= {(a - k, b + k) for a, b in body}
    E -= body
    y0 = min(b for _, b in F); y1 = max(b for _, b in F)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); pp = im.load()
    put = lambda a, b, c: (0 <= a < W and 0 <= b < H) and pp.__setitem__((a, b), c + (255,))
    # 노랑 바깥 테는 뺌(원본은 거의 안 보임) · 색은 줄마다 이어지는 그라데이션(단계 줄무늬 없게) → 팔레트 최근접
    def lerp(R, t):
        t = min(1.0, max(0.0, t)) * (len(R) - 1); i = min(int(t), len(R) - 2); f = t - i
        return tuple(round(R[i][c] + (R[i + 1][c] - R[i][c]) * f) for c in range(3))
    for a, b in E: put(a, b, lerp(ORANGE, (b - y0) / max(1, y1 - y0 + DEPTH)))
    for a, b in O: put(a, b, lerp(TEAL, (b - y0 + 2) / max(1, y1 - y0 + 4)))
    for a, b in F: put(a, b, lerp(PINK, (b - y0) / max(1, y1 - y0)))
    over = sum(1 for a, b in body | E if not (0 <= a < W and 0 <= b < H))
    return im, over


def quantize(im, pal):
    W, H = im.size; px = im.load(); out = bytearray(W * H); cache = {}
    for y in range(H):
        for x in range(W):
            r, g, b_, a = px[x, y]
            if a == 0: continue
            k = (r, g, b_)
            if k not in cache: cache[k] = min(range(1, 256), key=lambda i: (pal[i][0] - r) ** 2 + (pal[i][1] - g) ** 2 + (pal[i][2] - b_) ** 2)
            out[y * W + x] = cache[k]
    return bytes(out)


def show(idx, w, h, pal):
    im = Image.new('RGB', (w, h), (60, 60, 60)); pp = im.load()
    for i, v in enumerate(idx):
        if v: pp[i % w, i // w] = pal[v]
    return im


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    F = {n: open(os.path.join(ROOT, 'work', 'files', n), 'rb').read() for n in ('ENDY01.BIN', 'ENDY03.BIN', 'ENDT01.BIN', 'ENDT03.BIN')}
    res = {}; rows = []
    # 가로
    w, h, p, pal = strip(F['ENDY01.BIN']); assert (w, h) == (256, 64)
    im, ov = art(256, 64); idx = quantize(im, pal); print('가로 넘침', ov)
    for n in ('ENDY01.BIN', 'ENDY03.BIN'):
        ww, hh, pp_, pl = strip(F[n]); assert F[n][pp_:pp_ + w * h] == F['ENDY01.BIN'][p:p + w * h]
        nb = bytearray(F[n]); nb[pp_:pp_ + w * h] = idx; res[n] = bytes(nb)
        rows.append((n, show(F[n][pp_:pp_ + w * h], w, h, pl), show(idx, w, h, pl)))
    # 세로: 읽는 방향 224×80 으로 그려 시계 방향으로 돌려 저장(읽을 땐 반시계)
    w, h, p, pal = strip(F['ENDT01.BIN']); assert (w, h) == (80, 224)
    im, ov = art(224, 80, WX=0.92); print('세로 넘침', ov)
    im = im.transpose(Image.ROTATE_270); idx = quantize(im, pal)
    for n in ('ENDT01.BIN', 'ENDT03.BIN'):
        ww, hh, pp_, pl = strip(F[n]); same = F[n][pp_:pp_ + w * h] == F['ENDT01.BIN'][p:p + w * h]; print(n, '원본 01 과 같은 번호', same)
        nb = bytearray(F[n]); nb[pp_:pp_ + w * h] = idx; res[n] = bytes(nb)
        rows.append((n, show(F[n][pp_:pp_ + w * h], w, h, pl).transpose(Image.ROTATE_90), show(idx, w, h, pl).transpose(Image.ROTATE_90)))
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'ending.pkl'), 'wb'))
    S = 3; W = 256 * S * 2 + 30; H = sum(a.height * S + 10 for _, a, _ in rows) + 10
    sh = Image.new('RGB', (W, H), (40, 40, 40)); y = 10
    for _, a, n in rows:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(n.resize((n.width * S, n.height * S), Image.NEAREST), (20 + 256 * S, y)); y += a.height * S + 10
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '엔딩_수고했어.png')); print(sh.size)
