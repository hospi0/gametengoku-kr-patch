# -*- coding: utf-8 -*-
r"""게임오버 입체 글자 한글(2026-11-09) — OVER.BIN·OVERX.BIN(같은 내용) 조각 7개 [u16 폭][u16 높이][0x0020][0x0600] + 8비트 화소(CRAM 0x600+값)
  ★게임은 조각을 90° 돌려 찍는다(스테이트 게임오버 꼭짓점 A=왼쪽 아래) → stcx_ko.piece 로 화면 방향(폭 h·높이 w)에 그리고 눕혀 저장
  ゲ→게 · ム→임 · オ→오 · バ→버 · ー 세 조각은 비움(투명)
  색: stcx_ko 의 앞면 111·위 가장자리 115·분홍 옆면·진자주 아랫면 번호를 OVER 팔레트 번호로 바꿔 씀
  python tools/over_ko.py → work/plates/over.pkl {OVER.BIN, OVERX.BIN}, 미리보기 work/미리보기_그림/게임오버_원본_한글.png(화면 배치)
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stcx_ko as X
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (자료 오프셋, 폭, 높이, 음절 또는 None, 기울기°, 화면 왼쪽 위 x, y) — 화면 자리는 게임오버 스테이트 VDP1
# 조각끼리 겹쳐 있으므로 음절은 조각 안 «상자»(화면 방향 x, y, 폭, 높이)에만 그림 — 네 글자가 안 겹치게
PIECES = [(0x66E0C, 96, 80, '게', 5, 64, 24), (0x68C14, 56, 48, None, 0, 104, 56), (0x6969C, 72, 56, '임', -5, 136, 32),
          (0x6D9BC, 48, 64, None, 0, 192, 96), (0x6C0F4, 88, 72, '버', 5, 168, 72), (0x6A664, 80, 56, '오', -5, 96, 80),
          (0x6B7EC, 48, 48, None, 0, 136, 104)]
BOX = {0x66E0C: (0, 0, 66, 66), 0x6969C: (0, 0, 56, 66), 0x6A664: (0, 20, 56, 60), 0x6C0F4: (0, 24, 72, 64)}
DRAW = [0x66E0C, 0x68C14, 0x6969C, 0x6D9BC, 0x6C0F4, 0x6A664, 0x6B7EC]     # 게임이 그리는 순서(뒤가 위)
FRONT, EDGE = 147, 66                                                     # 앞면 · 위 가장자리
PINK = [23, 45, 51, 66, 84, 96, 105, 111]                                # 옆면 밝음→어두움
DARK = [225, 229, 231, 235, 240, 245, 248, 250, 252, 252, 252]          # 아랫면 밝음→어두움
REMAP = {111: FRONT, 115: EDGE, **{a: b for a, b in zip(X.PINK_R, PINK)}, **{a: b for a, b in zip(X.DARK_R, DARK)}}


def to_img(px, w, h, cram):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); pp = im.load()
    for y in range(h):
        for x in range(w):
            v = px[y * w + x]
            if v:
                c = struct.unpack_from('>H', cram, 2 * (0x600 + v))[0]; pp[x, y] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3, 255)
    return im


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src = {n: open(os.path.join(ROOT, 'work', 'files', n), 'rb').read() for n in ('OVER.BIN', 'OVERX.BIN')}
    orig = src['OVER.BIN']; b = bytearray(orig)          # 두 파일은 전체로는 다르고 글자 조각 자리만 같음 → 조각만 둘 다에 씀
    cram = open(os.path.join(ROOT, 'work', 'mem', '게임오버', 'CRAM.bin'), 'rb').read()
    X.DEPTH = 8                                                           # 조각이 스테이지 클리어보다 커서 옆면 두께도 키움
    for o, w, h, ch, t, sx, sy in PIECES:
        assert struct.unpack_from('>HHHH', orig, o - 8) == (w, h, 0x20, 0x600), hex(o)
        if ch is None:
            g = [[0] * h for _ in range(w)]
        else:
            bx, by, bw, bh = BOX[o]
            sub, ov = X.piece(bw, bh, ch, t); print('%x %dx%d %s 상자 %dx%d%s' % (o, w, h, ch, bw, bh, '  ⚠넘침 %d' % ov if ov else ''))
            g = [[0] * h for _ in range(w)]                               # 화면 방향: 폭 h · 높이 w
            for yy in range(bh):
                for xx in range(bw): g[by + yy][bx + xx] = REMAP.get(sub[yy][xx], sub[yy][xx])
            bad = {v for row in g for v in row} - set(REMAP.values()) - {0}
            assert not bad, bad
        b[o:o + w * h] = bytes(g[w - 1 - tx][ty] for ty in range(h) for tx in range(w))   # 화면(sx,sy) = 텍스처(w-1-sy, sx)
    assert len(b) == len(orig)
    res = {}
    for n, d in src.items():
        nb = bytearray(d)
        for o, w, h, *_ in PIECES:
            assert d[o - 8:o + w * h] == orig[o - 8:o + w * h], (n, hex(o))
            nb[o:o + w * h] = b[o:o + w * h]
        res[n] = bytes(nb)
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'over.pkl'), 'wb'))
    S = 3; sh = Image.new('RGB', (2 * 220 * S + 10, 160 * S), (40, 40, 40))
    for k, d in enumerate((orig, bytes(b))):
        sc = Image.new('RGB', (220, 160), (30, 30, 60))
        P = {p[0]: p for p in PIECES}
        for o in DRAW:
            _, w, h, _, _, sx, sy = P[o]; px = d[o:o + w * h]
            disp = [px[ty * w + (w - 1 - yy)] for yy in range(w) for ty in range(h)]
            im = to_img(disp, h, w, cram); sc.paste(im, (sx - 50, sy), im)
        sh.paste(sc.resize((220 * S, 160 * S), Image.NEAREST), (k * (220 * S + 10), 0))
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '게임오버_원본_한글.png')); print(sh.size)
