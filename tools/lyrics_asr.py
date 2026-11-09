# -*- coding: utf-8 -*-
r"""오프닝 보컬(트랙 4) 가사 받아쓰기 — work/vocals/t04.npy(tools/sep.py) → work/voice/op_lyrics.tsv(시작·끝·large-v3·kotoba)
   C:\claude\utils\whisper-venv\Scripts\python.exe tools/lyrics_asr.py"""
import os, sys, numpy as np
from faster_whisper import WhisperModel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
a = np.load(os.path.join(ROOT, 'work', 'vocals', 't04.npy')).astype(np.float32)
a = a / max(1e-6, float(np.abs(a).max())) * 0.9
P = '歌詞。ゲーム天国のオープニングテーマ。'
out = []
for name in ('large-v3', 'kotoba-tech/kotoba-whisper-v2.0-faster'):
    try:
        m = WhisperModel(name, device='cuda', compute_type='float16')
    except Exception as e:
        print('모델 없음', name, e); continue
    seg, _ = m.transcribe(a, language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=True,
                          vad_parameters={'min_silence_duration_ms': 300}, initial_prompt=P, temperature=0)
    out.append([(s.start, s.end, s.text.strip()) for s in seg])
    print('==', name)
    for s0, s1, t in out[-1]: print('%6.1f %6.1f %s' % (s0, s1, t))
with open(os.path.join(ROOT, 'work', 'voice', 'op_lyrics.tsv'), 'w', encoding='utf-8') as f:
    f.write('모델\t시작\t끝\t가사\n')
    for k, lst in enumerate(out):
        for s0, s1, t in lst: f.write('%d\t%.2f\t%.2f\t%s\n' % (k, s0, s1, t))
