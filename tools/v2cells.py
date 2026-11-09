# -*- coding: utf-8 -*-
r"""게임 천국 VDP2 NBG0~3 셀 면 렌더(2026-11-08) — 레지스터로 평면 전체(맵 A~D)를 그림. 스크롤·우선순위 무시(글자 찾기용)
  python tools/v2cells.py <work/mem 이름> → work/그림추출/vdp2/<이름>_nbgN.png (+ 정보)
  · 상태 덤프(state.py)는 VRAM·CRAM 이미 빅엔디언
  · 패턴 이름 1워드(PNCN 비트15)·2워드 모두. 1워드: 16색 = 팔레트 4비트 / 256색 = 3비트, 비트11 V뒤집기·비트10 H뒤집기, 보충 SCN
"""
import os, struct, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def render(name, n):
    d = os.path.join(ROOT, 'work', 'mem', name)
    v = open(os.path.join(d, 'VDP2_VRAM.bin'), 'rb').read()
    cram = open(os.path.join(d, 'CRAM.bin'), 'rb').read()
    r = open(os.path.join(d, 'VDP2_REGS.bin'), 'rb').read(); R = lambda o: struct.unpack_from('>H', r, o)[0]
    bgon = R(0x20)
    if not bgon >> n & 1: return None
    a, b = R(0x28), R(0x2A)
    if n == 0: chsz, bmen, chcn = a & 1, a >> 1 & 1, a >> 4 & 7
    elif n == 1: chsz, bmen, chcn = a >> 8 & 1, a >> 9 & 1, a >> 12 & 3
    elif n == 2: chsz, bmen, chcn = b & 1, 0, b >> 1 & 1
    else: chsz, bmen, chcn = b >> 4 & 1, 0, b >> 5 & 1
    if bmen:                                                             # 비트맵(NBG0·1): 크기 BMSZ, 시작 = MPOFN×0x20000, 256색 팔레트 BMPNA
        bmsz = (a >> 2 & 3) if n == 0 else (a >> 10 & 3)
        W, H = (512, 256) if bmsz == 0 else (512, 512) if bmsz == 1 else (1024, 256) if bmsz == 2 else (1024, 512)
        base = ((R(0x3C) >> (4 * n)) & 7) * 0x20000
        bpal = (R(0x2C) >> (8 * n)) & 7
        colors = {0: 16, 1: 256, 2: 2048, 3: 32768}.get(chcn, 256)
        crmd = R(0x0E) >> 12 & 3; craof = R(0xE4) >> (4 * n) & 7
        im = Image.new('RGB', (W, H)); px = im.load()
        for y in range(H):
            for x in range(W):
                if colors == 32768:
                    c = struct.unpack_from('>H', v, (base + 2 * (y * W + x)) & 0x7FFFF)[0]
                    if c & 0x8000: px[x, y] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
                    continue
                if colors == 16:
                    q = v[(base + (y * W + x) // 2) & 0x7FFFF]; p = q >> 4 if x % 2 == 0 else q & 15; ci = (bpal << 4) | p
                else:
                    p = v[(base + y * W + x) & 0x7FFFF]; ci = (bpal << 8) | p
                i = (ci + (craof << 8)) & (2047 if crmd == 1 else 1023)
                c = struct.unpack_from('>H', cram, 2 * i)[0]
                px[x, y] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
        return im, dict(bitmap=1, W=W, H=H, base=hex(base), colors=colors)
    colors = {0: 16, 1: 256, 2: 2048}.get(chcn, 256)
    pn = R(0x30 + 2 * n); one = pn >> 15 & 1; cnsm = pn >> 14 & 1; splt = pn >> 5 & 7; scn = pn & 31
    plsz = R(0x3A) >> (2 * n) & 3; mpof = R(0x3C) >> (4 * n) & 7
    maps = [R(0x40 + 4 * n) & 0x3F, R(0x40 + 4 * n) >> 8 & 0x3F, R(0x42 + 4 * n) & 0x3F, R(0x42 + 4 * n) >> 8 & 0x3F]
    craof = R(0xE4) >> (4 * n) & 7
    crmd = R(0x0E) >> 12 & 3
    cells = 32 if chsz else 64                                           # 한 쪽(page)의 글자 칸 수(한 변)
    pw = 2 if one else 4                                                 # 패턴 이름 바이트
    page_bytes = cells * cells * pw
    pages_x = 2 if plsz in (1, 3) else 1; pages_y = 2 if plsz == 3 else 1
    cpx = 16 if chsz else 8                                              # 글자 하나 화소(한 변)
    W = 2 * pages_x * cells * cpx; H = 2 * pages_y * cells * cpx         # 평면 2×2(A~D)
    im = Image.new('RGB', (W, H)); px = im.load()

    def col(i):
        i = (i + (craof << 8)) & (2047 if crmd == 1 else 1023)
        if crmd == 2:
            c = struct.unpack_from('>I', cram, 4 * i)[0]; return (c & 255, c >> 8 & 255, c >> 16 & 255)
        c = struct.unpack_from('>H', cram, 2 * i)[0]; return ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)

    for pl, mp in enumerate(maps):
        mapnum = (mpof << 6) | mp
        base = (mapnum * page_bytes) & 0x7FFFF                          # VRAM 512 KB 로 접음(MPOF 윗비트는 넘침)
        if pages_x * pages_y > 1: base &= ~(page_bytes * pages_x * pages_y - 1)
        for py in range(pages_y):
            for pxg in range(pages_x):
                pb = (base + (py * pages_x + pxg) * page_bytes) & 0x7FFFF
                for cy in range(cells):
                    for cx in range(cells):
                        o = pb + (cy * cells + cx) * pw
                        if o + pw > len(v): continue
                        if one:
                            w = struct.unpack_from('>H', v, o)[0]
                            if colors == 16: pal = (splt << 4) | (w >> 12 & 15)          # 보충 팔레트 SPLT 가 윗 3비트
                            else: pal = (w >> 12 & 7) << 4
                            vf, hf = w >> 11 & 1, w >> 10 & 1
                            if cnsm == 0:
                                ch = (w & 0x3FF) | ((scn >> 2 & 7) << 10 if chsz else (scn & 31) << 10)
                                if chsz: ch = ((w & 0x3FF) << 2) | (scn & 3) | ((scn >> 2 & 7) << 12)
                            else:
                                ch = (w & 0xFFF) | ((scn >> 2 & 7) << 12); vf = hf = 0
                                if chsz: ch = ((w & 0xFFF) << 2) | (scn & 3) | ((scn >> 4 & 1) << 14)
                            if colors != 16: pal = (w >> 12 & 7) << 4 if not cnsm else (splt << 4)
                        else:
                            w0, w1 = struct.unpack_from('>HH', v, o)
                            vf, hf = w0 >> 15 & 1, w0 >> 14 & 1; pal = w0 & 0x7F; ch = w1 & 0x7FFF
                        caddr = ch * 32
                        bx = ((pl & 1) * pages_x + pxg) * cells * cpx + cx * cpx
                        by = ((pl >> 1) * pages_y + py) * cells * cpx + cy * cpx
                        sub = [(0, 0), (8, 0), (0, 8), (8, 8)] if chsz else [(0, 0)]
                        cb = 32 if colors == 16 else 64
                        for k, (sx, sy) in enumerate(sub):
                            ca = caddr + k * cb
                            for y in range(8):
                                for x in range(8):
                                    if colors == 16:
                                        q = v[(ca + y * 4 + (x >> 1)) & 0x7FFFF]; p = (q >> 4) if x % 2 == 0 else q & 15
                                        ci = (pal << 4) | p
                                    else:
                                        p = v[(ca + y * 8 + x) & 0x7FFFF]; ci = (pal << 4) + p
                                    if p == 0: continue
                                    xx, yy = sx + x, sy + y
                                    if hf: xx = cpx - 1 - xx
                                    if vf: yy = cpx - 1 - yy
                                    px[bx + xx, by + yy] = col(ci)
    return im, dict(chsz=chsz, colors=colors, one=one, cnsm=cnsm, plsz=plsz, mpof=mpof, maps=maps, craof=craof)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    out = os.path.join(ROOT, 'work', '그림추출', 'vdp2'); os.makedirs(out, exist_ok=True)
    for nm in sys.argv[1:]:
        for n in range(4):
            res = render(nm, n)
            if res is None or res == 'bitmap': print(nm, 'NBG%d' % n, res or '꺼짐'); continue
            im, info = res; im.save(os.path.join(out, '%s_nbg%d.png' % (nm, n))); print(nm, 'NBG%d' % n, im.size, info)
