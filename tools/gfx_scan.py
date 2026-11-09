# -*- coding: utf-8 -*-
r"""그림 글자 출처 조사(2026-11-08) — 스테이트의 VDP1 스프라이트 텍스처를 원래 색 PNG 로 뽑고 디스크 파일에서 같은 바이트 찾기
  python tools/gfx_scan.py <work/mem 이름> [...]
  → work/그림추출/vdp1/<이름>/NNN_<주소>_<w>x<h>_m<색모드>.png · <이름>.tsv(번호·주소·크기·모드·화면 좌표·파일·오프셋)
  디스크 파일 = work/files/(원본 트랙 1에서 뽑음). 못 찾으면 압축(.LZ 등)일 수 있음.
"""
import os, struct, sys, glob, hashlib
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', '그림추출', 'vdp1')
TYPES = [(14, 4, 0x7FF), (13, 8, 0x7FF), (14, 2, 0x7FF), (13, 4, 0x7FF), (13, 4, 0x3FF), (12, 8, 0x7FF), (12, 8, 0x3FF), (12, 8, 0x1FF)]
FILES = None


def files():
    global FILES
    if FILES is None:
        FILES = [(os.path.basename(p), open(p, 'rb').read()) for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'files', '*')))]
        FILES += [('풀림:' + os.path.basename(p), open(p, 'rb').read()) for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'files_dec', '*')))]   # LZ 푼 것(오쿠무라 LZSS, 0 채움)
    return FILES


def cmds(v):
    i = 0; seen = set(); out = []
    while i not in seen and len(out) < 3000 and i * 32 < 0x80000:
        seen.add(i); c = struct.unpack_from('>16H', v, i * 32)
        if c[0] & 0x8000: break
        jp = (c[0] >> 12) & 7
        if (c[0] & 0xF) in (0, 1, 2) and not c[0] & 0x4000: out.append((i, c))
        i = c[1] // 4 if jp in (1, 2) else i + 1
    return out


def find(tex):
    """텍스처 바이트를 디스크 파일에서 — 가운데 64 B 로 찾고 전체 일치 확인"""
    if len(set(tex)) < 4: return '', -1, 0
    k = len(tex) // 2 - 32; k = max(0, k); probe = tex[k:k + 64]
    for nm, b in files():
        o = b.find(probe)
        while o >= 0:
            s = o - k
            if s >= 0 and b[s:s + len(tex)] == tex: return nm, s, 1
            o = b.find(probe, o + 1)
    for nm, b in files():                                                                 # 일부만 맞음(줄 단위 배치 등)
        o = b.find(probe)
        if o >= 0: return nm, o - k, 0
    return '', -1, 0


def scan(name):
    d = os.path.join(ROOT, 'work', 'mem', name)
    v = open(os.path.join(d, 'VDP1_VRAM.bin'), 'rb').read()
    cram = open(os.path.join(d, 'CRAM.bin'), 'rb').read()
    r = open(os.path.join(d, 'VDP2_REGS.bin'), 'rb').read(); R = lambda o: struct.unpack_from('>H', r, o)[0]
    t = R(0xE0) & 7; _, _, dcm = TYPES[t]
    ofs = ((R(0xE6) >> 4) & 7) << 8; crmd = (R(0x0E) >> 12) & 3
    def col(i):
        i = (i + ofs) & (2047 if crmd == 1 else 1023)
        if crmd == 2:
            c = struct.unpack_from('>I', cram, 4 * (i & 1023))[0]; return (c & 255, c >> 8 & 255, c >> 16 & 255)
        c = struct.unpack_from('>H', cram, 2 * i)[0]; return ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    od = os.path.join(OUT, name); os.makedirs(od, exist_ok=True)
    rows = []; done = {}
    for k, (i, c) in enumerate(cmds(v)):
        pmod, colr, srca, size = c[2], c[3], c[4] * 8, c[5]
        w = ((size >> 8) & 0x3F) * 8; h = size & 0xFF; mode = (pmod >> 3) & 7
        if w == 0 or h == 0: continue
        bpp = {0: 4, 1: 4, 2: 8, 3: 8, 4: 8, 5: 16}.get(mode, 8)
        n = w * h * bpp // 8; tex = v[srca:srca + n]
        key = (srca, w, h, mode, colr)
        if key in done: continue
        sx = struct.unpack('>h', struct.pack('>H', c[6]))[0]; sy = struct.unpack('>h', struct.pack('>H', c[7]))[0]
        im = Image.new('RGBA', (w, h))
        px = im.load()
        lut = [struct.unpack_from('>H', v, colr * 8 + 2 * j)[0] for j in range(16)] if mode == 1 else None
        for y in range(h):
            for x in range(w):
                if bpp == 4:
                    b = tex[(y * w + x) >> 1]; p = (b >> 4) if x % 2 == 0 else (b & 15)
                    if p == 0 and not pmod & 0x40: continue
                    code = lut[p] if mode == 1 else (colr & 0xFFF0) | p
                elif bpp == 8:
                    p = tex[y * w + x]
                    if p == 0 and not pmod & 0x40: continue
                    m = {2: 0x3F, 3: 0x7F, 4: 0xFF}[mode]; code = (colr & ~m) | (p & m)
                else:
                    cc = struct.unpack_from('>H', tex, 2 * (y * w + x))[0]
                    if not cc & 0x8000: continue
                    px[x, y] = ((cc & 31) << 3, (cc >> 5 & 31) << 3, (cc >> 10 & 31) << 3, 255); continue
                if mode == 1 and code & 0x8000:
                    px[x, y] = ((code & 31) << 3, (code >> 5 & 31) << 3, (code >> 10 & 31) << 3, 255); continue
                px[x, y] = col(code & dcm) + (255,)
        fn = '%03d_%05X_%dx%d_m%d.png' % (len(done), srca, w, h, mode)
        im.save(os.path.join(od, fn))
        fnm, fo, full = find(tex)
        done[key] = fn
        rows.append((len(done) - 1, '%05X' % srca, w, h, mode, '%04X' % colr, sx, sy, fnm, fo, full, fn))
    with open(os.path.join(od, name + '.tsv'), 'w', encoding='utf-8') as f:
        f.write('번호\t주소\t폭\t높이\t모드\t색\t화면x\t화면y\t파일\t오프셋\t전체일치\tPNG\n')
        for row in rows: f.write('\t'.join(map(str, row)) + '\n')
    return rows


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for nm in sys.argv[1:]:
        rs = scan(nm)
        print(nm, '스프라이트', len(rs), '파일 찾음', sum(1 for r in rs if r[8]), '전체일치', sum(1 for r in rs if r[10]))
