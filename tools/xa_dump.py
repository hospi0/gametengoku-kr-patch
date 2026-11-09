# -*- coding: utf-8 -*-
"""트랙 2 XA 39개(ST*·DM*·ED_OMAKE, 채널 1개 스테레오 37.8 kHz) → work/voice/xa/<이름>.wav (ffmpeg psxstr) + work/voice/xa.tsv
   파일 섹터 = LBA − 71381(트랙 2 시작). python tools/xa_dump.py"""
import os, re, subprocess, tempfile, shutil, wave, sys
sys.stdout.reconfigure(encoding='utf-8')
T2 = 'C:/claude/roms/ss/Game Tengoku - The Game Paradise (Japan)/Game Tengoku - The Game Paradise! (Japan) (Track 02).bin'
FF = 'C:/claude/utils/ps1/ffmpeg.exe'; O = 'work/voice/xa'; os.makedirs(O, exist_ok=True)
f = open(T2, 'rb'); tmp = tempfile.mkdtemp(); rows = []
try:
    for l in open('work/filelist.txt', encoding='utf-8'):
        m = re.match(r'/(\S+)\s+lba=\s*(\d+)\s+size=\s*(\d+)', l)
        if not m or not (71381 <= int(m.group(2)) < 140424): continue
        nm, L, sz = m.group(1), int(m.group(2)), int(m.group(3)); secs = []
        for k in range((sz + 2047) // 2048):
            f.seek((L - 71381 + k) * 2352); s = f.read(2352)
            if s[18] & 4: secs.append(s)
        p = os.path.join(tmp, 'c.str'); open(p, 'wb').write(b''.join(secs))
        w = f'{O}/{nm}.wav'
        subprocess.run([FF, '-v', 'error', '-y', '-f', 'psxstr', '-i', p, w], check=True)
        with wave.open(w) as wv: rows.append((nm, L, len(secs), wv.getframerate(), wv.getnchannels(), round(wv.getnframes() / wv.getframerate(), 1)))
finally:
    shutil.rmtree(tmp)
with open('work/voice/xa.tsv', 'w', encoding='utf-8') as o:
    o.write('이름\tLBA\t섹터\tHz\t채널\t초\n'); o.writelines('\t'.join(map(str, r)) + '\n' for r in rows)
for r in rows: print(*r)
