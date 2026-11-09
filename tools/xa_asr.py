# -*- coding: utf-8 -*-
"""트랙 2 XA 39개 받아쓰기(위스퍼 large-v3, VAD 끔, 구간 시각 포함) → work/voice/xa_asr.tsv
   C:/claude/utils/whisper-venv/Scripts/python.exe tools/xa_asr.py"""
import sys, subprocess, numpy as np
from faster_whisper import WhisperModel
sys.stdout.reconfigure(encoding='utf-8')
m = WhisperModel('large-v3', device='cuda', compute_type='float16')
rows = [l.rstrip('\n').split('\t') for l in open('work/voice/xa.tsv', encoding='utf-8')][1:]
with open('work/voice/xa_asr.tsv', 'w', encoding='utf-8') as out:
    out.write('이름\t시작\t끝\t받아쓰기\n')
    for r in rows:
        a = np.frombuffer(subprocess.run(['C:/claude/utils/ps1/ffmpeg.exe', '-v', 'error', '-i', f'work/voice/xa/{r[0]}.wav', '-ar', '16000', '-ac', '1', '-f', 's16le', '-'],
                                         capture_output=True, check=True).stdout, '<i2').astype(np.float32) / 32768
        segs, _ = m.transcribe(a, language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=False)
        n = 0
        for s in segs:
            out.write(f'{r[0]}\t{s.start:.1f}\t{s.end:.1f}\t{s.text.strip()}\n'); n += 1
        out.flush(); print(r[0], n, flush=True)
print('끝')
