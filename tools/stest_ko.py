# -*- coding: utf-8 -*-
r"""사운드 테스트 글자 그림 한글(2026-11-09) — 투명 바탕 위 글자만(창은 따로 그림)
  YKBIN 0x2A34C 곡 정보 6 · 0x2CDCC BGM 곡 이름 25 · 0x2FB70 성우 정보 16 · 0x277AC #45 «LR 버튼으로 캐릭터를…»
  글자 3벌(원본 색): Y 노랑(채움 130·테 135·모서리 137) · C 청록(134·141·142) · P 분홍(129·26·136)
  줄 자리 = 원본 줄 띠(행 묶음)마다: 노랑으로 시작하는 줄 = 왼쪽 맞춤(원본 왼쪽 x) · 청록 줄 = 오른쪽 맞춤(원본 오른쪽 x)
  글꼴: 띠 높이 ≥17 → 갈무리14, 아니면 갈무리11 · 줄은 통째로 한 번 그려 구간별 색만 나눔
  표기: [Y:…] [P:…] [C:…] 로 구간 색, 표시 없으면 그 줄 기본색
  python tools/stest_ko.py → work/plates/stest.pkl, work/미리보기_그림/사운드테스트_글자.png(원본 | 한글, 창 색 바탕)
"""
import os, sys, re, pickle, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ykbin, bdf, menu_gfx as M
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F11 = bdf.Font(os.path.join(M.FD, 'Galmuri11.bdf'))
F14 = bdf.Font(os.path.join(M.FD, 'Galmuri14.bdf'))
FC = bdf.Font(os.path.join(M.FD, 'Galmuri11-Condensed.bdf'))   # 넘치는 줄만
STY = {'Y': (130, 135, 137), 'C': (134, 141, 142), 'P': (129, 26, 136)}
COLSTY = {130: 'Y', 135: 'Y', 137: 'Y', 132: 'Y', 134: 'C', 141: 'C', 142: 'C', 138: 'C', 129: 'P', 26: 'P', 136: 'P'}

SONG = {   # 0x2A34C — 곡 정보(歌 = 노래)
    0: ['『천사의 날개로』', '노래/카나이 미카'],
    1: ['『러블리 스타』', '노래/타카하시 미키', '코오로기 사토미'],
    2: ['『허세가 아니야』', '노래/니시하라 쿠미코', '카나이 미카'],
    3: ['『러블리 스타』', '([P:미사토] 버전)', '노래/코오로기 사토미'],
    4: ['『러블리 스타』', '([P:미키] 버전)', '노래/타카하시 미키'],
    5: ['『싸워라!', '나만의 무테킨더 Z』', '노래/미야우치 타카유키'],
}
BGM = {    # 0x2CDCC — BGM 곡 이름(청록 한 줄, 숫자만 노랑)
    0: '오프닝 데모', 1: '셀렉트 메뉴', 2: '오락실 월드', 3: '크레인 월드', 4: '슈팅 월드', 5: '드라이빙 월드', 6: '레트로 월드',
    7: '폴리곤 월드', 8: '가정용 게임 월드 [Y:1]', 9: '가정용 게임 월드 [Y:2]', 10: '가정용 게임 월드 [Y:3]', 11: '야마다 메카 등장!',
    12: '레아 등장이다냥!', 13: '신관 야마다 출현!', 14: '바이러스 야마다 발견!', 15: '타임 어택', 16: '연습 스테이지',
    17: '아케이드 스태프 롤', 18: '네임 엔트리', 19: '시나리오 [Y:1]', 20: '시나리오 [Y:2]', 21: '하이스코어 랭킹', 22: '게임 오버',
    23: '레아가 당했다냥!', 24: '세계는 구원받았다…!',
}
VOICE = {  # 0x2FB70 — 성우 정보(声 = 성우)
    0: ['이토 유키', '성우/니시하라 쿠미코'], 1: ['제이너스', '성우/세키 토모카즈'], 2: ['세리아', '성우/카나이 미카'],
    3: ['Z-DYNE MKⅡ [P:(어레인지)]', '성우/오키아유 류타로'], 4: ['피그 [P:(어레인지)]', '성우/오오츠카 아키오'],
    5: ['모모코', '성우/시이나 헤키루'], 6: ['미키', '성우/타카하시 미키'], 7: ['미사토', '성우/코오로기 사토미'],
    8: ['지니어스 야마다', '성우/치바 시게루'], 9: ['나카무라', '성우/이세 쿠미코'], 10: ['적 캐릭터', '성우/니시하라 쿠미코'],
    11: ['적 캐릭터', '성우/치바 시게루'], 12: ['미키 [P:&] 미사토', '성우/타카하시 미키 코오로기 사토미'],
    13: ['나카무라 [P:&] 카토', '성우/이세 쿠미코 스즈키 마사미'], 14: ['Z-DYNE MKⅡ [P:(아케이드)]', '성우/치바 시게루'],
    15: ['피그 [P:(아케이드)]', '성우/？？？'],
}
LR = {45: ['[P:LR] 버튼으로', '[Y:캐릭터][C:를 바꿀 수 있습니다]']}   # 0x277AC #45


def bands(w, h, px):
    """원본 줄 띠: 글자 있는 행 묶음 → (y0, y1, x0, x1, 첫 글자 색 벌)"""
    rows = [y for y in range(h) if any(px[y * w:(y + 1) * w])]
    out = []; a = rows[0]; p = rows[0]
    for y in rows[1:] + [None]:
        if y is None or y != p + 1:
            xs = [x for yy in range(a, p + 1) for x in range(w) if px[yy * w + x]]
            x0 = min(xs); col = next(px[yy * w + x0] for yy in range(a, p + 1) if px[yy * w + x0])
            fx = [(x, px[yy * w + x]) for x in range(w) for yy in range(a, p + 1) if px[yy * w + x] in COLSTY]
            first = COLSTY[min(fx)[1]] if fx else 'C'
            out.append((a, p, x0, max(xs), first))
            if y is not None: a = y
        if y is not None: p = y
    return out


def parse(line, base):
    segs = []
    for m in re.finditer(r'\[([YCP]):([^\]]*)\]|([^\[]+)', line):
        segs.append((m.group(2), m.group(1)) if m.group(1) else (m.group(3), base))
    return segs


def draw_line(out, w, h, segs, font, align, ax, yc):
    text = ''.join(t for t, _ in segs)
    pts, _ = font.draw(text)
    miss = [c for c in text if c != ' ' and not font.draw(c)[0]]
    assert not miss, ('글꼴에 없는 글자', miss)
    # 구간 경계 x = 앞부분만 그린 폭(한 번에 렌더한 결과에서 자름)
    bounds = []; acc = ''
    for t, s in segs:
        acc += t; p2, _ = font.draw(acc.rstrip()) if acc.strip() else ([], 0)
        bounds.append((max(x for x, _ in p2) if p2 else -1, s))
    x0 = min(x for x, _ in pts); x1 = max(x for x, _ in pts); y0 = min(y for _, y in pts); y1 = max(y for _, y in pts)
    ox = (ax - x0) if align == 'L' else (ax - x1)
    ox = max(1 - x0, min(ox, w - 2 - x1)); oy = round(yc - (y0 + y1) / 2)
    def sty(x):
        for bx, s in bounds:
            if x <= bx: return s
        return bounds[-1][1]
    G = {(x + ox, y + oy): sty(x) for x, y in pts}
    over = 0
    for (x, y), s in G.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if q in G: continue
                if not (0 <= q[0] < w and 0 <= q[1] < h): over += 1; continue
                v = STY[s][1] if dx == 0 or dy == 0 else STY[s][2]
                cur = out[q[1] * w + q[0]]
                if cur in (0,) or (cur == STY[s][2] and v == STY[s][1]) or (cur in (137, 142, 136) and v in (135, 141, 26)): out[q[1] * w + q[0]] = v
    for (x, y), s in G.items():
        if 0 <= x < w and 0 <= y < h: out[y * w + x] = STY[s][0]
        else: over += 1
    return over


ALIGN = {0x2CDCC: 'L', 0x277AC: 'L'}                                   # BGM 곡 이름·LR 안내 = 원본처럼 전부 왼쪽 맞춤


def build(w, h, px, lines, force=None):
    bd = bands(w, h, px)
    # 원본 줄 수와 번역 줄 수가 다르면(곡 #5 두 줄 제목 등) 원본 띠 순서대로 짝, 남는 번역 줄은 마지막 띠 아래로
    out = bytearray(w * h); over = 0
    for i, line in enumerate(lines):
        y0, y1, x0, x1, first = bd[min(i, len(bd) - 1)]
        base = 'Y' if first == 'Y' else 'C'
        segs = parse(line, base)
        font = F14 if y1 - y0 + 1 >= 17 else F11
        tw = (lambda p: max(x for x, _ in p) - min(x for x, _ in p) + 3)(font.draw(''.join(t for t, _ in segs))[0])
        if tw > w - 2: font = F11 if font is F14 else FC
        align = force or ('L' if base == 'Y' or len(bd) == 1 else 'R')           # 한 줄짜리(BGM 곡 이름)는 원본처럼 왼쪽 맞춤
        over += draw_line(out, w, h, segs, font, align, x0 + 1 if align == 'L' else x1 - 1, (y0 + y1) / 2)   # 원본 띠 = 테 포함 → 글자 획은 1px 안쪽
    return bytes(out), over, len(bd)


def to_img(w, h, px, cram, bk=0x200):
    im = Image.new('RGB', (w, h), (72, 64, 152)); pp = im.load()                 # 창 바탕(보라) 비슷하게
    for i, c in enumerate(px):
        if c:
            e = struct.unpack_from('>H', cram, 2 * ((bk + c) & 2047))[0]; pp[i % w, i // w] = ((e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3)
    return im


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = open(os.path.join(ROOT, 'work', 'files', 'YKBIN'), 'rb').read()
    cram = open(os.path.join(ROOT, 'work', 'mem', '사운드테스트', 'CRAM.bin'), 'rb').read()
    res = {}; pairs = []
    for co, tab in ((0x2A34C, SONG), (0x2CDCC, BGM), (0x2FB70, VOICE), (0x277AC, LR)):
        recs = ykbin.chunk(b, co)
        for k, lines in tab.items():
            w, h, px = recs[k]
            if isinstance(lines, str): lines = [lines]
            new, over, nb = build(w, h, px, lines, ALIGN.get(co)); res[(co, k)] = new
            warn = ('  ⚠넘침 %d' % over if over else '') + ('  ⚠줄 수 원본 %d·번역 %d' % (nb, len(lines)) if nb != len(lines) else '')
            print('%05X #%d %dx%d %s%s' % (co, k, w, h, ' / '.join(lines), warn))
            pairs.append((to_img(w, h, px, cram), to_img(w, h, new, cram)))
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'stest.pkl'), 'wb'))
    S = 3; W = 192 * S * 2 + 30; H = sum(a.height * S + 6 for a, _ in pairs) + 6
    sh = Image.new('RGB', (W, H), (40, 40, 40)); y = 6
    for a, n in pairs:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(n.resize((n.width * S, n.height * S), Image.NEAREST), (20 + 192 * S, y)); y += a.height * S + 6
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '사운드테스트_글자.png')); print(sh.size)
