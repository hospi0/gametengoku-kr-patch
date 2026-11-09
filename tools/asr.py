# -*- coding: utf-8 -*-
"""AIF 694개 받아쓰기 — ① 위스퍼 large-v3 ② kotoba-whisper v2.0 (VAD 끔) → 둘의 글자 일치도 → work/voice/clips_asr.tsv
   C:/claude/utils/whisper-venv/Scripts/python.exe tools/asr.py"""
import sys, wave, difflib, numpy as np
from faster_whisper import WhisperModel
sys.stdout.reconfigure(encoding='utf-8')
rows = [l.rstrip('\n').split('\t') for l in open('work/voice/clips.tsv', encoding='utf-8')]
H, rows = rows[0], rows[1:]


def load(nm):
    w = wave.open(f'work/voice/wav/{nm}.wav'); a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    return np.pad(a, (0, max(0, 16000 - len(a))))


res = {}
for name in ('large', 'kotoba'):
    m = WhisperModel('large-v3' if name == 'large' else 'kotoba-tech/kotoba-whisper-v2.0-faster', device='cuda', compute_type='float16')
    for i, r in enumerate(rows):
        segs, _ = m.transcribe(load(r[0]), language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=False)
        res[(name, r[0])] = ''.join(s.text for s in segs).strip()
        if i % 100 == 0: print(name, i, r[0], res[(name, r[0])], flush=True)
    del m


def sim(a, b):
    n = lambda s: ''.join(ch for ch in s if ch not in '、。!！?？ ー～…・')
    return round(difflib.SequenceMatcher(None, n(a), n(b)).ratio(), 2) if (n(a) or n(b)) else 1.0


with open('work/voice/clips_asr.tsv', 'w', encoding='utf-8') as f:
    f.write('\t'.join(H + ['일치도', 'large', 'kotoba']) + '\n')
    for r in rows:
        a, b = res[('large', r[0])], res[('kotoba', r[0])]
        f.write('\t'.join(r + [str(sim(a, b)), a, b]) + '\n')
print('끝')
