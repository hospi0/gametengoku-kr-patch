# -*- coding: utf-8 -*-
"""번역 TSV(2026-11-08) — 음성 받아쓰기 → my files/tsv/gt_NNN.tsv (UTF-8, 18 KB 단위, 자투리 합침)
   열: 번호 · 위치 · JP · KO · 참고
   위치: «XA 파일 시작-끝»(트랙 2 대화극, 초) / «AIF 파일 길이»(낱개 음성, VTEST_ = 사운드 테스트 폴더)
   참고: 두 받아쓰기 모델(large-v3·kotoba)이 어긋나면 kotoba 결과를 적어 둠(일치도 < 0.8) — JP 는 large-v3
   python tools/mk_tsv.py"""
import os, sys, csv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'my files', 'tsv')
LIMIT = 18 * 1024
HEAD = '번호\t위치\tJP\tKO\t참고\n'


def rows():
    out = []
    xa_order = [l.split('\t')[0] for l in open(os.path.join(ROOT, 'work', 'voice', 'xa.tsv'), encoding='utf-8')][1:]
    xa = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'voice', 'xa_asr.tsv'), encoding='utf-8'), delimiter='\t'):
        xa.setdefault(r['이름'], []).append(r)
    rc = {}                                                                                  # 재검사(tools/xa_recheck.py) 결과가 있으면 그걸로
    p = os.path.join(ROOT, 'work', 'voice', 'xa_recheck.tsv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'): rc[(r['이름'], r['시작'])] = r
    for nm in xa_order:
        for r in xa.get(nm, []):
            t = r['받아쓰기'].strip(); note = ''
            c = rc.get((nm, r['시작']))
            if c:
                t = c['고른것'].strip() or t
                others = [x for x in (c['처음'], c['재검'], c['kotoba']) if x.strip() and x.strip() != t]
                if c['판정'] == '불확실': note = '받아쓰기 불확실 — 다른 후보: ' + ' / '.join(dict.fromkeys(others))[:120]
                elif c['판정'] == '환각': note = '같은 말 되풀이 — 들어서 확인'
            if t: out.append(('XA %s %s-%s' % (nm, r['시작'], r['끝']), t, note))
    for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'voice', 'clips_asr.tsv'), encoding='utf-8'), delimiter='\t'):
        a, k = r['large'].strip(), r['kotoba'].strip()
        note = '' if float(r['일치도']) >= 0.8 else ('받아쓰기 불확실 — kotoba: %s' % (k or '(빈칸)'))
        if not a: a = k
        out.append(('AIF %s %ss' % (r['이름'], r['초']), a, note))
    return out


def keep_ko():
    """이미 채운 KO 보존(번호 → KO)"""
    ko = {}
    if os.path.isdir(OUT):
        for f in sorted(os.listdir(OUT)):
            if f.startswith('gt_') and f.endswith('.tsv'):
                for l in open(os.path.join(OUT, f), encoding='utf-8').readlines()[1:]:
                    c = l.rstrip('\n').split('\t')
                    if len(c) > 3 and c[3].strip(): ko[c[0]] = c[3]
    return ko


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rs = rows(); ko = keep_ko()
    lines = ['%05d\t%s\t%s\t%s\t%s\n' % (i + 1, loc, jp.replace('\t', ' '), ko.get('%05d' % (i + 1), ''), note) for i, (loc, jp, note) in enumerate(rs)]
    chunks = [[]]; size = len(HEAD.encode())
    for l in lines:
        b = len(l.encode())
        if chunks[-1] and size + b > LIMIT: chunks.append([]); size = len(HEAD.encode())
        chunks[-1].append(l); size += b
    if len(chunks) > 1 and sum(len(l.encode()) for l in chunks[-2] + chunks[-1]) + len(HEAD.encode()) <= LIMIT:
        last = chunks.pop(); chunks[-1] += last                       # 자투리 합침(pop 먼저)
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.startswith('gt_') and f.endswith('.tsv'): os.remove(os.path.join(OUT, f))
    for k, c in enumerate(chunks):
        open(os.path.join(OUT, 'gt_%03d.tsv' % (k + 1)), 'w', encoding='utf-8', newline='').write(HEAD + ''.join(c))
    # 검산: 번호 연속·고유
    nums = [int(l.split('\t')[0]) for f in sorted(os.listdir(OUT)) if f.startswith('gt_') for l in open(os.path.join(OUT, f), encoding='utf-8').readlines()[1:]]
    assert nums == list(range(1, len(rs) + 1)), '번호 연속 검산 실패'
    print('보존한 KO', len(ko), '줄', len(rs), '파일', len(chunks), [os.path.getsize(os.path.join(OUT, 'gt_%03d.tsv' % (k + 1))) for k in range(len(chunks))])


if __name__ == '__main__':
    main()
