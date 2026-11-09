# -*- coding: utf-8 -*-
"""work/voice/ko.tsv(합친 번역) → work/voice/sub_all.tsv(voicesub 자료: 파일·시작·끝·원문·한글)
   XA «XA 이름 시작-끝» → 이름 · AIF «AIF 이름 길이s» → 이름.AIF 0~길이
   ⚠VTEST_* 는 뺌 — VTEST\ 하위 폴더 파일이라 GFS fid 가 루트 fid 와 겹침(훅이 폴더를 모름)
   python tools/mk_subdata.py"""
import os, csv, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
rows = list(csv.reader(open(os.path.join(ROOT, 'work', 'voice', 'ko.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]
out = ['파일\t시작\t끝\t원문\t한글\n']; skip = {'VTEST': 0, '빈칸': 0}
for k, loc, jp, ko, *_ in rows:
    ko = ko.strip()
    if not ko: skip['빈칸'] += 1; continue
    t = loc.split()
    if t[0] == 'XA':
        a, b = t[2].split('-'); out.append('\t'.join([t[1], a, b, jp, ko]) + '\n')
    else:
        if t[1].startswith('VTEST_'): skip['VTEST'] += 1; continue
        out.append('\t'.join([t[1] + '.AIF', '0.0', t[2].rstrip('s'), jp, ko]) + '\n')
p = os.path.join(ROOT, 'work', 'voice', 'sub_all.tsv')
open(p, 'w', encoding='utf-8', newline='').write(''.join(out))
print(p, len(out) - 1, '줄 · 뺀 것', skip)
