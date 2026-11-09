# -*- coding: utf-8 -*-
r"""디스크 파일 안 LZ 덩어리 전부 풀기(2026-11-08) — 오쿠무라 LZSS(tools/lzss.py, 링 0 채움·시작 0xFEE), 덩어리 = [u32 BE 압축 크기][자료]
  구조 ① 이어 붙임: 0 에서 [크기][자료][크기][자료]… (4 B 정렬 허용)
       ② 오프셋 표: 앞 u32 들이 오름차순 오프셋(첫 값 = 표 크기) → 각 오프셋에서 ① 덩어리 또는 날것
  → work/files_dec/<파일>#<오프셋 16진>.bin  (+ work/files_dec/목록.tsv)
  python tools/unpack_all.py
"""
import os, sys, struct, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
lzss.INIT = 0
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'files_dec')


def try_chunk(b, k):
    """k 에서 [크기][LZ] 덩어리면 (풀린 것, 끝 위치)"""
    if k + 8 > len(b): return None
    s = struct.unpack_from('>I', b, k)[0]
    if s < 8 or k + 4 + s > len(b): return None
    if b[k + 4] & 1 == 0 and b[k + 4] != 0: pass
    try:
        d, used = lzss.decompress(b, k + 4, 1 << 22)
    except Exception:
        return None
    # 압축 자료를 정확히 다 써야(끝에서 3 B 안쪽) 진짜 덩어리
    if not (k + 4 + s - 3 <= used <= k + 4 + s + 1): return None
    if len(d) < s: return None
    return d, k + 4 + s


def try_chunk_b(b, k):
    """형식 B: [u32 BE 풀린 크기][LZ …] (압축 크기 없음) → (풀린 것, 끝 위치)"""
    if k + 8 > len(b): return None
    n = struct.unpack_from('>I', b, k)[0]
    if n < 16 or n > 0x200000: return None
    d, used = lzss.decompress(b, k + 4, n)
    if len(d) != n or used > len(b): return None
    return d, used


def chain_b(b, k0=0):
    out = []; k = k0
    while k < len(b) - 8:
        r = try_chunk_b(b, k)
        if not r: break
        out.append((k, r[0])); k = r[1]
        while k < len(b) and k % 4: k += 1
    return out


def table_b(b):
    n = struct.unpack_from('>I', b, 0)[0]
    if n < 8 or n % 4 or n > min(len(b), 0x4000): return []
    offs = [struct.unpack_from('>I', b, 4 * i)[0] for i in range(n // 4)]
    if any(offs[i] > offs[i + 1] for i in range(len(offs) - 1)) or offs[-1] > len(b): return []
    out = []
    for o in offs:
        r = try_chunk_b(b, o)
        if r: out.append((o, r[0]))
    return out


def chain(b, k0=0, limit=None):
    out = []; k = k0
    while True:
        r = try_chunk(b, k)
        if not r: break
        out.append((k, r[0])); k = r[1]
        while k < len(b) and k % 4 and b[k] == 0: k += 1
        if limit and k >= limit: break
    return out


def table(b):
    n = struct.unpack_from('>I', b, 0)[0]
    if n < 8 or n % 4 or n > min(len(b), 0x4000): return []
    offs = [struct.unpack_from('>I', b, 4 * i)[0] for i in range(n // 4)]
    if any(offs[i] > offs[i + 1] for i in range(len(offs) - 1)) or offs[-1] > len(b): return []
    out = []
    for i, o in enumerate(offs):
        end = offs[i + 1] if i + 1 < len(offs) else len(b)
        if end <= o: continue
        r = try_chunk(b, o)
        if r: out.append((o, r[0]))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'files', '*'))):
        nm = os.path.basename(p); b = open(p, 'rb').read()
        if len(b) < 16 or nm.upper().endswith(('.SEQ', '.TXT')) or nm.startswith(('DM', 'ST1_', 'ST2_', 'ST3_', 'ST4_', 'ST5_', 'ST6_', 'ST7_', 'ED_')) and '.' not in nm: continue
        got = chain(b) or table(b) or table_b(b) or chain_b(b)
        for k, d in got:
            fn = '%s#%06X.bin' % (nm, k)
            open(os.path.join(OUT, fn), 'wb').write(d); rows.append((nm, '%06X' % k, len(d), fn))
        if got: print(nm, len(got), '덩어리', flush=True)
    with open(os.path.join(OUT, '목록.tsv'), 'w', encoding='utf-8') as f:
        f.write('파일\t오프셋\t풀린크기\t출력\n')
        for r in rows: f.write('\t'.join(map(str, r)) + '\n')
    print('합계', len(rows))


if __name__ == '__main__':
    main()
