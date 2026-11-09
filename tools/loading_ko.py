# -*- coding: utf-8 -*-
r"""로딩 화면 한글(2026-11-09) — LOAD20~28.CHR 왼쪽 아래 «なう ろ～でぃんぐ…» → «나우 로~딩»(하스피 지시 그대로)
  일본어 글자 자리 = 9장에서 똑같은 화소(검은 테두리)로 둘러싸인 곳(테두리 안 채움) +1 px
  바탕 메우기: 같은 그림 영어판(LOAD1x, «Now Loading» 글자 자리 아닌 화소)이 있으면 그 색 → 없으면 cv2 inpaint(TELEA)
  한글 = 주아 한 벌을 한 번만 그려 9장에 같은 자리로 · 흰 속 + 검은 테두리 2 px + 오른쪽 아래 그림자
  색은 그 장 팔레트에서 가장 가까운 번호로 · 재압축 = lzss_opt.encode_opt, 원래 [u32 크기]+스트림 자리 안(0 채움) · 팔레트 위치 불변
  python tools/loading_ko.py → work/build/LOAD2n.CHR · work/미리보기_그림/로딩_한글.png
"""
import os, sys, struct
from collections import deque
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, lzss, load_chr
from lzss_opt import encode_opt
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JUA = r'C:/claude/utils/font/jua/Jua-Regular.ttf'
TEXT = '나우 로~딩...'                                         # 영문판처럼 ... 붙임(하스피 2026-11-09)
EN = {20: 10, 22: 12, 25: 15, 26: 16, 27: 17}          # 같은 그림 영어판(왕복 비교로 확인: 22·25·26·27 거의 같음, 20 은 팔레트만 다름)
SS = 4; FS = 30; X0, BASE = 28, 211                       # 원문 글자 x 28~259, y 186~215


def load(n):
    b = open(os.path.join(ROOT, 'work', 'files', f'LOAD{n:02d}.CHR'), 'rb').read()
    d, cols = load_chr.decode(b)
    pal = np.array([((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3) for c in cols])
    return b, bytearray(d), pal


def common_mask(ns, Y0=178, Y1=228):
    imgs = [load(n) for n in ns]
    R = np.stack([p[np.frombuffer(bytes(d[:76800]), np.uint8).reshape(240, 320)] for _, d, p in imgs]).astype(int)
    same = np.abs(R - R[0]).sum(-1).max(0) <= 16
    m = same[Y0:Y1]; H, W = m.shape; out = np.zeros_like(m); q = deque()
    for y in range(H): q += [(y, 0), (y, W - 1)]
    for x in range(W): q += [(0, x), (H - 1, x)]
    while q:
        y, x = q.popleft()
        if 0 <= y < H and 0 <= x < W and not out[y, x] and not m[y, x]:
            out[y, x] = 1; q.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    f = np.zeros((240, 320), bool); f[Y0:Y1] = ~out.astype(bool)
    return f


def dil(m, r):
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)


def ko_layers():
    """한글 한 벌: (속, 테두리, 그림자) 마스크 320×240"""
    f = ImageFont.truetype(JUA, FS * SS)
    im = Image.new('L', (320 * SS, 240 * SS)); dr = ImageDraw.Draw(im)
    body = TEXT.rstrip('.'); dots = len(TEXT) - len(body)
    dr.text((X0 * SS, BASE * SS), body, font=f, fill=255, anchor='ls')
    x = dr.textbbox((X0 * SS, BASE * SS), body, font=f, anchor='ls')[2] + 3 * SS
    for _ in range(dots):                                                   # 점은 주아 마침표가 작아 원문 크기(속 4 px)로 따로
        dr.rounded_rectangle((x, (BASE - 4) * SS, x + 4 * SS, BASE * SS), radius=SS, fill=255); x += 8 * SS
    a = np.array(im.resize((320, 240), Image.BOX)) >= 110
    edge = dil(a, 2) & ~a
    shadow = np.zeros_like(a); body = a | edge; shadow[2:, 2:] = body[:-2, :-2]; shadow &= ~body
    return a, edge, shadow


def nearest(pal, rgb):
    return int(np.abs(pal - np.array(rgb)).sum(1).argmin())


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    jp = dil(common_mask(range(20, 29)), 1)
    en = dil(common_mask(sorted(set(EN.values()))), 2)        # 바탕으로 쓰는 영어판끼리만(11·18 은 글자 자리 달라 공통 테두리가 깨짐)
    a, edge, shadow = ko_layers()
    ys, xs = np.nonzero(a | edge); print('한글 범위 x', xs.min(), xs.max(), 'y', ys.min(), ys.max(), '/ 일본어 x', np.nonzero(jp)[1].min(), np.nonzero(jp)[1].max())
    os.makedirs(os.path.join(ROOT, 'work', 'build'), exist_ok=True)
    sheet = Image.new('RGB', (640 * 2 + 10, 9 * 250), (20, 20, 20))
    for row, n in enumerate(range(20, 29)):
        b, d, pal = load(n)
        idx = np.frombuffer(bytes(d[:76800]), np.uint8).reshape(240, 320).copy()
        rgb = pal[idx].astype(np.uint8); before = rgb.copy()
        # 일본어 그림자·테두리 색(원본 글자 자리에서)
        hole = jp.copy(); fixed = None
        if n in EN:
            _, d2, pal2 = load(EN[n]); src = pal2[np.frombuffer(bytes(d2[:76800]), np.uint8).reshape(240, 320)]
            ok = jp & ~en
            rgb[ok] = src[ok]; hole = jp & en
            tm = np.array([int(np.abs(pal.astype(int) - pal2[k]).sum(1).argmin()) for k in range(256)], np.uint8)   # 영어판 번호→이 장 번호 표(번호 단위로 옮겨야 압축 유지)
            fixed = (ok, tm[np.frombuffer(bytes(d2[:76800]), np.uint8).reshape(240, 320)])
        if hole.any():
            rgb = cv2.inpaint(np.ascontiguousarray(rgb[:, :, ::-1]), hole.astype(np.uint8), 3, cv2.INPAINT_TELEA)[:, :, ::-1]
        sh_rgb = (24, 24, 24)
        rgb[shadow] = (rgb[shadow].astype(int) * 0.35).astype(np.uint8)       # 그림자: 바탕 어둡게(원본처럼 반투명 느낌)
        rgb[edge] = (0, 0, 0); rgb[a] = (248, 248, 248)
        ch = jp | a | edge | shadow
        # 팔레트 번호로 되돌림(바뀐 화소만)
        P = pal.astype(int); new = idx.copy()
        for (y, x) in zip(*np.nonzero(ch)):
            new[y, x] = int(np.abs(P - rgb[y, x].astype(int)).sum(1).argmin())
        if fixed is not None:
            m_ = fixed[0] & ~(a | edge | shadow); new[m_] = fixed[1][m_]
        d[:76800] = new.tobytes()
        # 재압축
        n0 = struct.unpack_from('>I', b, 4)[0]; s = struct.unpack_from('>I', b, n0)[0]
        c = encode_opt(bytes(d))                                             # 최적 분할(빠른 압축기는 원본보다 커짐)
        assert len(c) <= s, (n, len(c), s)
        nb = bytearray(b); nb[n0:n0 + 4 + s] = struct.pack('>I', len(c)) + c + bytes(s - len(c))
        lzss.INIT = 0
        chk, _ = load_chr.decode(bytes(nb)); assert bytes(chk) == bytes(d), n
        open(os.path.join(ROOT, 'work', 'build', f'LOAD{n:02d}.CHR'), 'wb').write(nb)
        after = pal[new].astype(np.uint8)
        sheet.paste(Image.fromarray(before).resize((640, 480), Image.NEAREST).crop((0, 240, 640, 480)), (0, row * 250))
        sheet.paste(Image.fromarray(after).resize((640, 480), Image.NEAREST).crop((0, 240, 640, 480)), (650, row * 250))
        print(f'LOAD{n}', '영어판 바탕' if n in EN else 'inpaint', '구멍', int(hole.sum()), '압축', len(c), '/', s)
    sheet.save(os.path.join(ROOT, 'work', '미리보기_그림', '로딩_한글.png'))
