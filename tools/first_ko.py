# -*- coding: utf-8 -*-
r"""첫 실행(저장 데이터 없음) 화면 한글(2026-11-09) — BACK1.BIN 끝 날것 8비트 VDP1 스프라이트(색 은행 0x100, 스테이트 work/states/첫실행_데이터작성.state)
  0x46630 304×80 «感謝感激»(무지개 그라데이션 채움 + 파랑 테) → 감사 감격
  0x4C530 304×112 «本体RAMにゲーム天国の / データを作成いたします! / (必要容量は「11」です)»(흰 채움 + 무지개 테) → 한글 3줄
  0x54A30 264×56 «PRESS START» 그대로
  방법: 원본을 RGB 로 풀어 채움·테 색을 «열마다» 뽑음(가로 그라데이션) → 한글을 RGB 로 그리고 → 팔레트(0번 투명 제외) 최근접
  python tools/first_ko.py → work/plates/first.pkl {BACK1.BIN}, 미리보기 work/미리보기_그림/첫실행_원본_한글.png
"""
import os, sys, pickle
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = r'C:/claude/utils/font/'
JUA = FD + 'jua/Jua-Regular.ttf'
BHS = FD + 'blackhansans/BlackHanSans-Regular.ttf'
TITLE = (0x46630, 304, 80, '감사 감격')
MSG = (0x4C530, 304, 112, ['본체 RAM에 게임 천국의', '데이터를 만들겠습니다!', '(필요 용량은 "11"입니다)'])


def dil(m, r):
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)


def text_mask(text, font, h, maxw):
    f = ImageFont.truetype(font, 200); x0, y0, x1, y1 = f.getbbox(text)
    im = Image.new('L', (x1 - x0 + 20, y1 - y0 + 20), 0); ImageDraw.Draw(im).text((10 - x0, 10 - y0), text, font=f, fill=255)
    im = im.crop(im.getbbox()); w = round(im.width * h / im.height)
    if w > maxw: h = int(h * maxw / w); w = maxw
    return np.array(im.resize((w, h), Image.LANCZOS)) >= 128


def col_colors(rgb, sel, W):
    """열마다 sel 화소 평균색 — 빈 열은 가까운 열 값"""
    out = np.zeros((W, 3)); have = np.zeros(W, bool)
    for x in range(W):
        ys = np.nonzero(sel[:, x])[0]
        if len(ys): out[x] = rgb[ys, x].mean(0); have[x] = True
    idx = np.nonzero(have)[0]
    for x in range(W):
        if not have[x]: out[x] = out[idx[np.abs(idx - x).argmin()]]
    k = 25; pad = np.pad(out, ((k, k), (0, 0)), mode='edge')                 # 열마다 뽑은 색을 부드럽게(세로 줄무늬 방지)
    return np.stack([np.convolve(pad[:, ch], np.ones(2 * k + 1) / (2 * k + 1), 'valid') for ch in range(3)], -1)


def quant(rgb, pal):
    d = ((rgb[..., None, :].astype(int) - pal[None, None, 1:, :]) ** 2).sum(-1)
    return d.argmin(-1) + 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src = open(os.path.join(ROOT, 'work', 'files', 'BACK1.BIN'), 'rb').read(); b = bytearray(src)
    c = np.frombuffer(open(os.path.join(ROOT, 'work', 'mem', '첫실행', 'CRAM.bin'), 'rb').read(), '>u2').astype(int)[0x100:0x200]
    pal = np.stack([(c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3], -1)
    pv = []
    # ── 큰 제목: 채움 = 파랑이 아닌 밝은 안쪽 화소, 테 = 파랑 계열
    o, W, H, t = TITLE
    a = np.frombuffer(src[o:o + W * H], np.uint8).reshape(H, W); rgb = pal[a]
    ink = a != 0; blue = (rgb[..., 2] > rgb[..., 0] + 40) & (rgb[..., 2] > rgb[..., 1] + 20)
    fillc = col_colors(rgb, ink & ~blue & ~dil(~ink, 2), W)
    bluec = np.median(rgb[ink & blue], 0)
    m = text_mask(t, JUA, H - 14, W - 14); mh, mw = m.shape
    G = np.zeros((H, W), bool); y0 = (H - mh) // 2; x0 = (W - mw) // 2; G[y0:y0 + mh, x0:x0 + mw] = m
    G = dil(G, 2)                                                         # 원본처럼 굵게
    O = dil(G, 3) & ~G
    # ★채움 = 원본 채움 화소의 «색 번호»를 가장 가까운 자리에서 그대로 복사 — 열 평균 → 팔레트 최근접은 열마다 다른 칸이 골라져 세로 줄무늬(하스피 실기 2026-11-09)
    #   원본 채움은 디더(여러 칸 섞기)라 → 원본 채움색을 2차원으로 부드럽게 퍼뜨린 색 지도 + 원본 채움에 쓰인 칸만으로 오차 확산
    src_fill = ink & ~blue & ~dil(~ink, 2)
    acc = np.zeros((H, W, 3)); wgt = np.zeros((H, W))
    acc[src_fill] = rgb[src_fill]; wgt[src_fill] = 1
    s = 9
    field = np.stack([cv2.GaussianBlur(acc[..., ch], (0, 0), s) for ch in range(3)], -1)
    wb = cv2.GaussianBlur(wgt, (0, 0), s)
    for s2 in (18, 36, 72):                                                 # 원본 글자가 없는 먼 자리는 더 넓게
        far = wb < 0.02
        if not far.any(): break
        f2 = np.stack([cv2.GaussianBlur(acc[..., ch], (0, 0), s2) for ch in range(3)], -1); w2 = cv2.GaussianBlur(wgt, (0, 0), s2)
        field[far] = f2[far]; wb[far] = w2[far]
    field = field / np.maximum(wb, 1e-6)[..., None]
    used = np.unique(a[src_fill]); cnt = np.bincount(a[src_fill], minlength=256); used = used[cnt[used] >= 8]
    up = pal[used].astype(float)
    na = np.zeros((H, W), np.uint8); err = np.zeros((H, W, 3))
    for y in range(H):
        for x in range(W):
            if not G[y, x]: continue
            want = field[y, x] + err[y, x]
            k = ((up - want) ** 2).sum(1).argmin(); na[y, x] = used[k]; e = want - up[k]
            for dx, dy, f in ((1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < W and yy < H and G[yy, xx]: err[yy, xx] += e * f / 16
    new = np.zeros((H, W, 3)); new[O] = bluec
    na[O] = quant(new, pal)[O]
    b[o:o + W * H] = na.tobytes(); pv.append((a, na))
    # ── 문구 3줄: 흰 채움 + 무지개 테(열마다)
    o, W, H, lines = MSG
    a = np.frombuffer(src[o:o + W * H], np.uint8).reshape(H, W); rgb = pal[a]
    ink = a != 0; white = rgb.min(-1) >= 232
    ring = ink & ~white & dil(white, 2)
    ringc = col_colors(rgb, ring, W)
    G = np.zeros((H, W), bool); ys = [4, 41, 78]
    for k, t in enumerate(lines):
        m = text_mask(t, BHS, 26, W - 10); mh, mw = m.shape; x0 = (W - mw) // 2
        G[ys[k] + (28 - mh) // 2: ys[k] + (28 - mh) // 2 + mh, x0:x0 + mw] |= m
    O = dil(G, 2) & ~G
    new = np.zeros((H, W, 3)); new[G] = (248, 248, 248); new[O] = ringc[np.nonzero(O)[1]] * 0.85
    na = np.where(G | O, quant(new, pal), 0).astype(np.uint8); b[o:o + W * H] = na.tobytes(); pv.append((a, na))
    assert len(b) == len(src)
    pickle.dump({'BACK1.BIN': bytes(b)}, open(os.path.join(ROOT, 'work', 'plates', 'first.pkl'), 'wb'))
    sh = Image.new('RGB', (2 * 310, 200), (40, 40, 40)); y = 0
    for a, na in pv:
        for k, x in enumerate((a, na)):
            im = pal[x].astype(np.uint8); im[x == 0] = (40, 40, 40); sh.paste(Image.fromarray(im), (k * 310, y))
        y += a.shape[0] + 4
    sh.resize((sh.width * 2, sh.height * 2), Image.NEAREST).save(os.path.join(ROOT, 'work', '미리보기_그림', '첫실행_원본_한글.png')); print('완료')
