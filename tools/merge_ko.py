# -*- coding: utf-8 -*-
"""하스피 번역(my files/번역, 옛 TSV 기준) + 새 TSV(my files/tsv, XA 재검사 반영) → work/voice/ko.tsv
   번호로 맞춤. 번역 KO 를 기본으로 쓰고, 재검사로 JP 가 바뀐 줄 중 손본 것만 FIX 로 덮는다.
   열: 번호 · 위치 · JP(새) · KO · 처리(빈칸=번역 그대로 / 고침 / 비움) · 참고
   python tools/merge_ko.py"""
import os, re, glob, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 번호 → (KO, 사유).  KO 빈칸 = 자막 안 냄
FIX = {
    '00207': ('', '30초 꼬리 구간 — 무음 환각(ご視聴ありがとうございました/ごめん), 자막 안 냄'),
    '00595': ('', '30초 꼬리 구간 — 무음 환각, 자막 안 냄'),
    '00381': ('리더…', '재검사 두 모델 모두 リーダー(옛 グー)'),
    '01010': ('부우우우우우우웅', '옛 KO 끝 영어 찌꺼기(hits) 지움 — 첫 6초 효과음 추정, 들어서 확인'),
    '01011': ('제이너스, 목숨이 아깝거든 그 의자에서 일어서지 마라! 다들 마찬가지야! 뭐야, 왜 그래, 피그? 젠장.',
              '재검사로 실제 대사 회수(옛 JP 환각)'),
    '01012': ('눈치채는 게 너무 늦었어. 우리가 지금 의자로 쓰고 있는 이 깡통은 지뢰다. 우리는 감쪽같이 걸려든 거야.',
              '재검사로 실제 대사 회수 — 끝 «僕は言ってねえねえ。ちょっとだけねえって»는 kotoba 에 없어 뺌, 들어서 확인'),
}


# 전체 다듬기(2026-11-08, 하스피 «용어 인물 말투 조사 총체적으로») — work/voice/ko_fix/*.tsv (번호\tKO) 가 FIX 위에 덮는다
FIXDIR = os.path.join(ROOT, 'work', 'voice', 'ko_fix')

# 용어 통일(받침 같은 쌍만 — 조사 안 바뀜. 받침 다른 쌍은 손으로 고쳐 ko_fix 에)
TERMS = [
    ('ZDINE', 'Z다인'), ('제트다인', 'Z다인'), ('EXPEL', '엑스펠'), ('익스펠', '엑스펠'),
    ('가토', '카토'), ('프로펠러', '푸페라'), ('스타 마인', '스타마인'), ('고속의 기관사', '광속의 귀공자'), ('고속의 귀공자', '광속의 귀공자'), ('고속의 로리콘', '광속의 로리콘'), ('고속의…', '광속의…'),   # 하스피 2026-11-09 «광속의»
    ('자기(自機)', '자기 기체'), ('Mark II', '마크 2'),
    ('덤 극장', '오마케 극장'), ('덤 얻었다', '오마케 얻었다'), ('보너스! 다시 만날', '오마케! 다시 만날'),   # 하스피 2026-11-09 «おまけ 는 모두 오마케»
    ('...', '…'), ('。', '.'), ('、', ', '), ('！', '!'), ('？', '?'),
]


def norm_terms(s):
    for a, b in TERMS: s = s.replace(a, b)
    # 로봇 이름 Z 홀로 쓰인 것 → 제트 (Z다인·Z9·Z-9·Z 그래비턴 같은 고유 명칭은 그대로)
    s = re.sub(r'(?<![A-Za-z0-9])Z(?![A-Za-z0-9\-]|다인| 그래비턴| 마크)', '제트', s)
    return s


def load_fixdir():
    d = {}
    if os.path.isdir(FIXDIR):
        for f in sorted(os.listdir(FIXDIR)):
            if f.endswith('.tsv'):
                for ln in open(os.path.join(FIXDIR, f), encoding='utf-8').read().split('\n'):
                    if not ln.strip(): continue
                    k, _, ko = ln.partition('\t')
                    assert re.fullmatch(r'\d{5}', k), (f, ln)
                    assert k not in d, ('ko_fix 중복', k, f)
                    d[k] = (ko.strip(), '다듬기(%s)' % f[:-4])
    return d


def load(pat):
    d = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'my files', pat))):
        for ln in open(f, encoding='utf-8-sig').read().split('\n')[1:]:
            c = ln.rstrip('\r').split('\t')
            if re.fullmatch(r'\d{5}', c[0]): d[c[0]] = c
    return d


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    old, new = load('번역/*.tsv'), load('tsv/*.tsv')
    assert sorted(old) == sorted(new), '번호 불일치'
    for k in new: assert old[k][1] == new[k][1], ('위치 다름', k)
    out = ['번호\t위치\tJP\tKO\t처리\t참고\n']; n = {'': 0, '고침': 0, '비움': 0, '용어': 0}
    fx = load_fixdir()
    for k in fx: assert k in new, ('ko_fix 번호 없음', k)
    for k in sorted(new):
        ko, how = old[k][3].strip(), ''
        if k in FIX or k in fx:
            ko, why = fx[k] if k in fx else FIX[k]; how = '고침' if ko else '비움'
            note = why
        else:
            note = new[k][4]
        t = norm_terms(ko)
        if t != ko and not how: how = '용어'
        ko = t
        n[how] += 1
        out.append('\t'.join([k, new[k][1], new[k][2], ko, how, note]) + '\n')
    p = os.path.join(ROOT, 'work', 'voice', 'ko.tsv')
    open(p, 'w', encoding='utf-8', newline='').write(''.join(out))
    print(p, len(out) - 1, '줄', n)


if __name__ == '__main__':
    main()
