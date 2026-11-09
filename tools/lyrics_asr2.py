# -*- coding: utf-8 -*-
r"""오프닝 보컬 가사 — 보컬 에너지로 구절 자르기 → 구절마다 large-v3·kotoba(프롬프트 없음, VAD 끔) → work/voice/op_lyrics.tsv
   C:\claude\utils\whisper-venv\Scripts\python.exe tools/lyrics_asr2.py"""
import os, sys, numpy as np
from faster_whisper import WhisperModel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
a = np.load(os.path.join(ROOT, 'work', 'vocals', 't04.npy')).astype(np.float32)
SR = 16000; hop = SR // 50
e = np.array([np.sqrt((a[i:i + hop] ** 2).mean()) for i in range(0, len(a) - hop, hop)])
thr = max(0.01, np.percentile(e, 60) * 0.5)
on = e > thr
# 0.35초 이하 틈은 메움, 0.4초 미만 구간은 버림
segs = []; i = 0; n = len(on)
while i < n:
    if on[i]:
        j = i
        while j < n and (on[j] or (j + 18 < n and on[j:j + 18].any())): j += 1
        if j - i >= 20: segs.append((i / 50, j / 50))
        i = j
    else: i += 1
print('구절', len(segs), [('%.1f-%.1f' % s) for s in segs])
ms = [WhisperModel('large-v3', device='cuda', compute_type='float16'),
      WhisperModel('kotoba-tech/kotoba-whisper-v2.0-faster', device='cuda', compute_type='float16')]
rows = []
for s0, s1 in segs:
    x = a[int(max(0, s0 - 0.2) * SR):int((s1 + 0.2) * SR)]; x = x / max(1e-6, float(np.abs(x).max())) * 0.9
    x = np.concatenate([np.zeros(SR // 2, np.float32), x, np.zeros(SR // 2, np.float32)])
    t = []
    for m in ms:
        sg, _ = m.transcribe(x, language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=False, temperature=0)
        t.append(''.join(z.text for z in sg).strip())
    rows.append((s0, s1, *t)); print('%6.1f %6.1f | %s | %s' % (s0, s1, t[0], t[1]), flush=True)
with open(os.path.join(ROOT, 'work', 'voice', 'op_lyrics.tsv'), 'w', encoding='utf-8') as f:
    f.write('시작\t끝\tlarge\tkotoba\n')
    for r in rows: f.write('%.2f\t%.2f\t%s\t%s\n' % r)
