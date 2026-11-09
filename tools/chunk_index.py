# -*- coding: utf-8 -*-
r"""디스크 파일 전체의 A형 압축 덩어리([u32 압축 바이트 수][오쿠무라 LZSS 0 채움]) 후보를 전부 풀어 저장(2026-11-09)
  가짜 후보 거르기: 풀린 크기 > 압축 크기, 압축 크기 ≥ 64
  → work/chunks/<파일>@<오프셋 16진>.bin + work/chunks/목록.tsv
  찾기: python tools/chunk_index.py --find <16진 바이트>   (풀린 것 안에서 검색)"""
import os, sys, struct, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
lzss.INIT = 0
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'chunks')
SKIP = ('.AIF', '.SEQ', '.TXT')


def build():
    os.makedirs(OUT, exist_ok=True); rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'files', '*'))):
        nm = os.path.basename(p)
        if nm.upper().endswith(SKIP) or (nm.startswith(('ST1_', 'ST2_', 'ST3_', 'ST4_', 'ST5_', 'ST6_', 'ST7_', 'DM', 'ED_')) and '.' not in nm): continue
        b = open(p, 'rb').read(); L = len(b); n = 0
        for o in range(0, L - 8, 2):
            s = (b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]
            if s < 64 or o + 4 + s > L: continue
            d, _ = lzss.decompress(b[:o + 4 + s], o + 4, 1 << 22)
            if len(d) <= s: continue
            fn = '%s@%06X.bin' % (nm, o); open(os.path.join(OUT, fn), 'wb').write(d); rows.append((nm, '%06X' % o, s, len(d))); n += 1
        print(nm, n, flush=True)
    with open(os.path.join(OUT, '목록.tsv'), 'w', encoding='utf-8') as f:
        f.write('파일\t오프셋\t압축\t풀린\n')
        for r in rows: f.write('\t'.join(map(str, r)) + '\n')


def find(h):
    pr = bytes.fromhex(h)
    for p in sorted(glob.glob(os.path.join(OUT, '*.bin'))):
        k = open(p, 'rb').read().find(pr)
        if k >= 0: print(os.path.basename(p), hex(k))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) > 2 and sys.argv[1] == '--find': find(sys.argv[2])
    else: build()
