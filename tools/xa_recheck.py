# -*- coding: utf-8 -*-
"""XA 대화 받아쓰기 재검사(2026-11-08, 파로 워즈 nyatv_recheck.py 방식) — work/voice/xa_asr.tsv 구간마다 소리를 잘라
   ① 위스퍼 large-v3 + 용어 프롬프트 ② kotoba-whisper v2.0 으로 다시 받아쓰고, 처음 받아쓰기와 셋을 비교
   → work/voice/xa_recheck.tsv (이름·시작·끝·처음·재검·kotoba·일치도·고른 것·판정)
   고르기: 셋 중 서로 가장 비슷한 둘의 «재검(프롬프트)» 쪽 우선, 셋 다 어긋나면 재검(프롬프트) + «불확실»
   영어 낱말·«ご視聴»·같은 말 되풀이 = 환각 표시
   C:/claude/utils/whisper-venv/Scripts/python.exe tools/xa_recheck.py"""
import sys, re, wave, difflib, numpy as np
from faster_whisper import WhisperModel
sys.stdout.reconfigure(encoding='utf-8')
PROMPT = ('ゲーム天国。ジェイナス、ゼット、ゼットダイン、ももこ、桃子、ピグ、セリア、ミサト、由紀、ジーニアス山田、加藤、中村、プーペラ、'
          'エクセリオン、フォーメーションZ、フィールドコンバット、モモコ120%、ぶたさん、プラスアルファ、ジェネシス、ジャレコ、メガシステム1、ゲームセンター。')
rows = [l.rstrip('\n').split('\t') for l in open('work/voice/xa_asr.tsv', encoding='utf-8')][1:]
WAV = {}


def clip(nm, t0, t1):
    if nm not in WAV:
        w = wave.open(f'work/voice/xa/{nm}.wav'); sr = w.getframerate(); ch = w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
        a = a.reshape(-1, ch).mean(1)
        n = int(len(a) * 16000 / sr); a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)
        WAV[nm] = a
    a = WAV[nm][max(0, int((t0 - 0.15) * 16000)):int((t1 + 0.25) * 16000)]
    return np.pad(a, (0, max(0, 16000 - len(a))))


res = {}
for name, kw in (('re', dict(initial_prompt=PROMPT)), ('ko', {})):
    m = WhisperModel('large-v3' if name == 're' else 'kotoba-tech/kotoba-whisper-v2.0-faster', device='cuda', compute_type='float16')
    for i, r in enumerate(rows):
        segs, _ = m.transcribe(clip(r[0], float(r[1]), float(r[2])), language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=False, **kw)
        res[(name, i)] = ''.join(s.text for s in segs).strip()
        if i % 200 == 0: print(name, i, res[(name, i)], flush=True)
    del m


def norm(s): return ''.join(ch for ch in s if ch not in '、。,.!！?？ ー～…・「」')
def sim(a, b): return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() if (norm(a) or norm(b)) else 1.0
def halluc(s): return bool(re.search(r'[A-Za-z]{3,}', s) or 'ご視聴' in s or 'チャンネル登録' in s or re.search(r'(.{2,})\1\1', s))


out = ['이름\t시작\t끝\t처음\t재검\tkotoba\t일치도\t고른것\t판정']; stat = {}
for i, r in enumerate(rows):
    a, b, c = r[3], res[('re', i)], res[('ko', i)]
    sab, sbc, sac = sim(a, b), sim(b, c), sim(a, c)
    best = max(sab, sbc, sac)
    pick = b if (sab == best or sbc == best) else a
    if halluc(pick) and not halluc(c): pick = c
    if halluc(pick) and not halluc(a): pick = a
    v = '확실' if best >= 0.85 and not halluc(pick) else ('불확실' if not halluc(pick) else '환각')
    stat[v] = stat.get(v, 0) + 1
    out.append('\t'.join(r[:3] + [a, b, c, '%.2f' % best, pick, v]))
open('work/voice/xa_recheck.tsv', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('끝', stat)
