# -*- coding: utf-8 -*-
r"""빈 판(tools/plates.py → work/plates/plates.pkl) 위에 한글 — 색(채움·테두리·그림자)·글자 자리는 원본 그림에서
  python tools/plates_ko.py → work/미리보기_그림/메뉴_한글.png (원본 | 한글, 실제 색, 3배)
  용어는 대사 번역(work/voice/ko.tsv)과 맞춤: 되받아치기·테마송 모음·BGM 모음·덤·잔기 수·오토 봄버·모노
"""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ykbin, plates, menu_gfx as M, bdf
FR = bdf.Font(os.path.join(M.FD, 'Galmuri11.bdf'))                  # 이름표(1px 획 — 굵기 통일)
FC = bdf.Font(os.path.join(M.FD, 'Galmuri11-Condensed.bdf'))     # 좁은 판(48폭) 마지막 수단
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KO = {
    0x25310: {5: '아케이드 모드', 6: '어레인지 모드', 7: '옵션 모드'},
    0x26648: {0: '키 컨피그', 1: '사운드 테스트', 2: '데이터 모드', 3: '회상 모드', 4: '게임 설정', 5: '옵션 모드'},
    0x349DC: {0: '1984년 엑셀리온', 1: '1984년 포메이션 Z', 2: '1985년 필드 컴뱃', 3: '1986년 모모코 120%',
              4: '1987년 부타상', 5: '1989년 플러스 알파', 6: '데이터 모드'},
    0x3C6C8: {0: '잔기 수', 1: '난이도', 2: '오토 봄버', 3: '되받아치기', 4: '사운드', 13: '없음', 14: '있음', 15: '스테레오', 16: '모노'},
    0x35FE8: {10: '오마케', 21: '회상 모드', 1: '플레이어 편', 2: '야마다 편',
              **{k: '제%d화' % (k - 2) for k in range(3, 10)}, **{k: '제%d화' % (k - 12) for k in range(13, 20)}},
    0x277AC: {0: '테마송 모음', 1: 'BGM 모음', 2: '보이스 모음', 46: '사운드 테스트',
              # 캐릭터 이름표(40×16) — 대사 번역 표기대로, Z-DYNE(#29)은 영문 그대로
              28: '제이너스', 30: '세리아', 31: '모모코', 32: '피그', 33: '미키', 34: '미사토', 35: '유키', 36: '야마다', 37: '나카무라', 38: '적 캐릭터'},
}

BANK = {0x35FE8: 0x300}                                                  # 미리보기 색 은행(회상 모드 = 0x300)
THIN = {(0x277AC, k) for k in range(28, 39)}                             # 이름표 = 갈무리11 보통(넘치면 Condensed) — 획 굵기 하나로
SMALL = {(0x35FE8, 1), (0x35FE8, 2)} | {(0x277AC, k) for k in range(28, 39)} | {(0x3C6C8, k) for k in (0, 1, 2, 3, 4, 13, 14, 15, 16)} | {(0x277AC, k) for k in (0, 1, 2)}   # 원본 글자 ~12px

NOLINE = {(0x35FE8, k) for k in [10, 1, 2] + list(range(3, 10)) + list(range(13, 20))} | {(0x277AC, k) for k in range(28, 39)}   # 이름표 = 흰 글자 + 그림자                                                 # 오마케 = 원본이 둘레 테두리 없이 오른쪽 아래 그림자만(«지저분»)
# 색 통일: 게임 설정 파란 판 = «사운드»(#4) 글자 모양·색으로(하스피 «옵션 파란판 글자가 제각각»)
CSRC = {(0x3C6C8, k): (0x3C6C8, 4) for k in (0, 1, 2, 3, 13, 14, 15, 16)}
# 데이터 모드 연표 판 그림자 고정(바탕 줄 색 → 그림자 색) — 판마다 고르면 원본 번짐색(부타상 노랑 3)·바탕색이 그림자로 잡혀 찌꺼기(하스피 2026-11-09)
SHFIX = {(0x349DC, k): {100: 114, 91: 111, 78: 107} for k in range(6)}
CSRC.update({(0x277AC, k): (0x277AC, 31) for k in range(28, 39) if k != 31})   # 이름표 색 = 모모코 기준 통일
# 회상 모드 «제n화» 판 색 = 제1화 판 기준(밝은 판 #3·어두운 판 #13) — 第四話는 획이 많아 그림자가 판 바탕 줄 색으로 잡혀 번짐(하스피 «제4화 깨짐», 2026-11-09)
CSRC.update({(0x35FE8, k): (0x35FE8, 3) for k in range(4, 10)}); CSRC.update({(0x35FE8, k): (0x35FE8, 13) for k in range(14, 20)})


def colors(w, h, orig, x0=0, x1=None, plate=None):
    """원본 글자 색: 채움 = 사방이 글자인 «안쪽» 화소 최빈 · 테두리 = 채움에 붙은 다른 글자 색 최빈 · 그림자 = 나머지(바탕 줄별)
      줄별 채움(세로 그라데이션)은 그 줄 안쪽 화소가 3개 이상이고 테두리·그림자 색이 아닐 때만. x0~x1 = 그 구간만(연도/제목 색 따로)"""
    import collections
    P, bg, rows, _, mask, _, _, _, box, L, Rr = M.analyse(w, h, orig)
    if plate is not None:                                                # 글자 마스크 = 원본 ≠ 빈 판(줄무늬 판에서 정확)
        _, bg, rows, *_ = M.analyse(w, h, plate)
        mask = [[orig[y * w + x] != plate[y * w + x] for x in range(w)] for y in range(h)]
        ys = [y for y in range(h) if any(mask[y])]; xm = [x for y in ys for x in range(w) if mask[y][x]]
        box = (min(xm), min(ys), max(xm), max(ys))
    x1 = w if x1 is None else x1
    inside = lambda y, x: 0 < y < h - 1 and 0 < x < w - 1 and mask[y][x] and mask[y - 1][x] and mask[y + 1][x] and mask[y][x - 1] and mask[y][x + 1]
    xs = range(max(x0, 0), min(x1, w))
    inn = collections.Counter(P[y][x] for y in rows for x in xs if inside(y, x))
    fill = inn.most_common(1)[0][0]
    fills = {c for c, n in inn.items() if n >= 5}                         # 안쪽에 나오는 색(연도 흰색·제목 색) = 그림자 후보 아님
    ol = collections.Counter(P[y][x] for y in rows for x in xs if mask[y][x] and P[y][x] != fill and any(
        0 <= y + dy < h and 0 <= x + dx < w and mask[y + dy][x + dx] and P[y + dy][x + dx] == fill for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))))
    outline = ol.most_common(1)[0][0] if ol else fill
    # 그림자[바탕색] = 그 바탕 줄들에만 나오는 글자 색(여러 바탕 줄에 걸쳐 나오는 색 = 채움·테두리·번짐)
    sh = {}; where = collections.defaultdict(set)
    for y in rows:
        for x in xs:
            if mask[y][x]: where[P[y][x]].add(bg[y])
    for y in rows:
        for x in xs:
            c = P[y][x]
            if mask[y][x] and len(where[c]) == 1 and c not in (fill, outline): sh.setdefault(bg[y], collections.Counter())[c] += 1
    shadow = {k: v.most_common(1)[0][0] for k, v in sh.items()}
    # 2026-11-09 다시 짬(하스피 «회상 모드 탭 줄무늬·부타상 찌꺼기»): 위 방식은 다른 줄 바탕색·번짐색이 그림자로 잡히고, 못 찾은 줄은 테두리 색으로 칠해짐
    #  → 그림자 = 원본 글자(채움·테두리) 화소의 바로 오른쪽 아래에 있는 글자 화소 색, 판 바탕색 제외 · 바탕 줄마다 최빈 · 못 찾은 바탕 줄 = 가장 가까운 줄 값
    bgset = {bg[y] for y in rows}
    sh2 = collections.defaultdict(collections.Counter)
    for y in rows:
        for x in xs:
            c = P[y][x]
            if not mask[y][x] or c in (fill, outline) or c in bgset or c in fills: continue
            if y > 0 and x > 0 and mask[y - 1][x - 1] and P[y - 1][x - 1] in (fill, outline): sh2[bg[y]][c] += 1
    if sh2:
        shadow = {k: v.most_common(1)[0][0] for k, v in sh2.items()}
        have = [y for y in rows if bg[y] in shadow]
        for y in rows:
            if bg[y] not in shadow and have: shadow[bg[y]] = shadow[bg[min(have, key=lambda q: abs(q - y))]]
    bad = {outline} | set(shadow.values())
    fr = {}
    for y in rows:
        c = collections.Counter(P[y][x] for x in xs if inside(y, x) and P[y][x] not in bad)
        if h >= 32 and c and c.most_common(1)[0][1] >= 3: fr[y] = c.most_common(1)[0][0]   # 그라데이션은 큰 버튼만(작은 판은 줄무늬 얼룩)
    # 한두 줄에만 나오는 줄 색 = 원본 글자의 하이라이트·번짐 → 줄 전체에 칠하면 가로줄(하스피 2026-11-09 «배경 판때기 줄색으로 줄 그어짐»)
    rowcnt = collections.Counter(fr.values())
    fr = {y: c for y, c in fr.items() if rowcnt[c] >= 4}
    return fr, fill, outline, shadow, box


def draw(w, h, orig, plate, text, small=False, csrc=None, noline=False, co_k=None):
    _, bg, rows, _, _, _, _, _, _, L, Rr = M.analyse(w, h, plate)       # 판 안쪽 범위 = 깨끗한 빈 판에서
    out = [list(plate[y * w:(y + 1) * w]) for y in range(h)]
    fr, f0, outline, shadow, box = colors(w, h, orig, plate=plate)
    if csrc is not None:                                                 # 색 통일(같은 화면 판은 기준 버튼 색으로)
        fr, f0, outline, shadow, _ = colors(*csrc)
    if co_k in SHFIX: shadow = SHFIX[co_k]
    parts = [(text, fr, f0)]
    import re
    m = re.match(r'(\d+년 )(.*)', text)
    if m:                                                                # «1984년 제목» = 연도 흰색 · 제목 색 따로(원본대로)
        fa, a0, *_ = colors(w, h, orig, 0, 44, plate); fb, b0, *_ = colors(w, h, orig, 50, None, plate)
        parts = [(m.group(1), fa, a0), (m.group(2), fb, b0)]
    ym = (box[1] + box[3]) // 2
    if ym not in rows: ym = rows[len(rows) // 2]
    room = Rr[ym] - L[ym] - 4
    def font(t, f):
        if f == 'n': return M.nanum(t, 19)
        if f == 14: pts, _ = M.F14.draw(t); return sorted(set(pts) | {(x + 1, y) for x, y in pts})
        if f == 11: return M.F11.draw(t)[0]
        if f == 'r': return FR.draw(t)[0]
        return FC.draw(t)[0]
    for f in (['n'] if h >= 32 else (['r', 'c'] if (co_k in THIN) else [11, 'c'] if small else [14, 11, 'c'])):   # 파랑·보라 작은 판 = 원본 글자 작음 → 갈무리11
        full = font(text, f)
        if max(x for x, _ in full) - min(x for x, _ in full) + 1 <= room: break
    # 부분별 글자 위치 = 통째로 그린 것에서 앞부분 폭만큼(한 번에 렌더 — 크기 어긋남 방지)
    cut = None
    if len(parts) == 2:
        pre = font(parts[0][0].rstrip(), f); cut = max(x for x, _ in pre) + 2
    pts = full
    iy0 = min(y for _, y in pts); iy1 = max(y for _, y in pts); ix0 = min(x for x, _ in pts); ix1 = max(x for x, _ in pts)
    nz = [x for x in range(w) if plate[ym * w + x]]; ox = int(round((nz[0] + nz[-1]) / 2 - (ix0 + ix1) / 2)); oy = int(round((box[1] + box[3]) / 2 - (iy0 + iy1) / 2))   # 가로 가운데 = 그 줄 판 전체(투명 제외) 가운데
    G = {(x + ox, y + oy) for x, y in pts}
    if noline:                                                           # 테두리 없는 글자(오마케): 흰 글자 + 오른쪽 아래 그림자 1px(바탕 줄 색마다 다른 그림자 색)
        O = set()
        S = {(x + 1, y + 1) for x, y in G} - G
    else:
        O = {(x + dx, y + dy) for x, y in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G
        S = {(x + 1, y + 1) for x, y in G | O} - G - O
    ok = lambda x, y: y in rows and L[y] <= x <= Rr[y]
    for x, y in S:
        if ok(x, y): out[y][x] = shadow.get(plate[y * w + L[y]], outline)
    for x, y in O:
        if ok(x, y): out[y][x] = outline
    for x, y in G:
        if not ok(x, y): continue
        _, frr, ff = parts[1] if cut is not None and x - ox > cut else parts[0]
        out[y][x] = frr.get(y, ff)
    over = sum(1 for x, y in G | O if not ok(x, y))
    return bytes(c for r in out for c in r), over


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = open(os.path.join(ROOT, 'work', 'files', 'YKBIN'), 'rb').read()
    saved = pickle.load(open(os.path.join(ROOT, 'work', 'plates', 'plates.pkl'), 'rb'))
    pmap = {m: v['plate'] for v in saved.values() for m in v['members']}
    pairs = []; res = {}
    for co, tr in KO.items():
        recs = ykbin.chunk(b, co); cram = open(os.path.join(ROOT, 'work', 'mem', plates.CHUNKS[co], 'CRAM.bin'), 'rb').read()
        for k, ko in tr.items():
            w, h, px = recs[k]; pl = pmap[(co, k)]
            new, over = draw(w, h, px, pl, ko, (co, k) in SMALL, (lambda c: c and (recs[c[1]][0], recs[c[1]][1], recs[c[1]][2], 0, None, pmap[c]))(CSRC.get((co, k))), (co, k) in NOLINE, (co, k)); res[(co, k)] = new
            print('%05X #%d %dx%d %s%s' % (co, k, w, h, ko, '  ⚠넘침 %d' % over if over else ''))
            bk = BANK.get(co, 0x200); pairs.append((M.to_img(w, h, px, cram, bk), M.to_img(w, h, new, cram, bk)))
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'ko.pkl'), 'wb'))
    S = 3; W = max(a.width for a, _ in pairs) * S * 2 + 30; H = sum(a.height * S + 8 for a, _ in pairs) + 8
    sh = Image.new('RGB', (W, H), (40, 40, 40)); y = 8
    for a, n in pairs:
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(n.resize((n.width * S, n.height * S), Image.NEAREST), (20 + a.width * S, y)); y += a.height * S + 8
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '메뉴_한글.png')); print(sh.size)
