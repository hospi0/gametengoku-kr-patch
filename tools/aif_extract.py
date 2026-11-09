# -*- coding: utf-8 -*-
"""AIF 전부 꺼내기 → work/voice/aif/<경로>.AIF + wav(16 kHz 모노, 받아쓰기용) + work/voice/clips.tsv(이름·LBA·크기·비트·Hz·초)
   python tools/aif_extract.py"""
import os, re, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import iso
sys.stdout.reconfigure(encoding='utf-8')
O = 'work/voice'; os.makedirs(O + '/aif', exist_ok=True); os.makedirs(O + '/wav', exist_ok=True)
FF = 'C:/claude/utils/ps1/ffmpeg.exe'


def ext80(b):
    e = ((b[0] & 0x7F) << 8) | b[1]; m = int.from_bytes(b[2:10], 'big')
    return m * 2.0 ** (e - 16383 - 63)


rows = []
for l in open('work/filelist.txt', encoding='utf-8'):
    m = re.match(r'(\S+)\s+lba=\s*(\d+)\s+size=\s*(\d+)', l)
    if not m or not m.group(1).endswith('.AIF'): continue
    p, L, sz = m.group(1), int(m.group(2)), int(m.group(3))
    d = iso.read(L, sz); assert d[:4] == b'FORM' and d[8:12] == b'AIFF', p
    i = d.find(b'COMM'); ch, nf, bits = struct.unpack_from('>hIh', d, i + 8); hz = ext80(d[i + 16:i + 26])
    nm = p.strip('/').replace('/', '_')[:-4]
    open(f'{O}/aif/{nm}.AIF', 'wb').write(d)
    subprocess.run([FF, '-v', 'error', '-y', '-i', f'{O}/aif/{nm}.AIF', '-ar', '16000', '-ac', '1', f'{O}/wav/{nm}.wav'], check=True)
    rows.append((nm, p, L, sz, bits, int(hz), ch, round(nf / hz, 2)))
with open(O + '/clips.tsv', 'w', encoding='utf-8') as f:
    f.write('이름\t경로\tLBA\t크기\t비트\tHz\t채널\t초\n')
    for r in rows: f.write('\t'.join(map(str, r)) + '\n')
print(len(rows), '개 · 총', round(sum(r[7] for r in rows)), '초')
