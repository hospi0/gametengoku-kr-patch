# -*- coding: utf-8 -*-
r"""메뉴 버튼 그림 한글화(2026-11-09) — YKBIN 그림 레코드(8비트 색 번호)를 «글자만 지우고 같은 색 구조로 한글» 다시 그림
  버튼 구조: 바탕 = 줄마다 한 색(가로 띠) · 글자 = 채움 + 1px 테두리 + 오른쪽 아래 그림자(바탕보다 어두운 색, 줄마다 다름)
  ① 바탕 줄 색 bg[y] = 안쪽 왼편(열 4~8) 최빈값 ② 글자 마스크 = 안쪽에서 bg[y] 와 다른 화소 ③ 지우기 = bg[y] 로 칠함
  ④ 색 뽑기: 테두리 = 바탕과 닿는 마스크 색 최빈 · 채움 = 마스크 최빈(테두리 제외) · 그림자[bg] = 그 줄의 나머지 색 최빈
  ⑤ 한글 = 갈무리 BDF 화소 그대로(작은 버튼 11 굵게, 큰 제목 14 + 1px 굵게) → 채움 · 테두리(8방향 1px) · 그림자(+1,+1)
  ⑥ 가운데 = 원래 글자 범위의 가운데
  python tools/menu_gfx.py → work/미리보기_그림/메뉴_<덩어리>.png (원본 | 한글, 실제 색, 3배)
"""
import os, sys, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ykbin, bdf
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = r'C:\claude\utils\font\Galmuri-v2.40.3'
F11 = bdf.Font(os.path.join(FD, 'Galmuri11-Bold.bdf'))
F14 = bdf.Font(os.path.join(FD, 'Galmuri14.bdf'))
NANUM_B = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'

# 덩어리 오프셋 → {레코드 번호: 한글}
KO = {
    0x26648: {0: '키 컨피그', 1: '사운드 테스트', 2: '데이터 모드', 3: '회상 모드', 4: '게임 설정', 5: '옵션 모드'},
}


def template(recs):
    """같은 크기(폭·높이) 판들의 줄별 최빈 색 = 바탕(글자가 판 끝까지 찬 줄도 다른 판에선 깨끗함)"""
    T = {}
    for w, h, px in recs:
        for y in range(h):
            T.setdefault((w, h, y), collections.Counter()).update(px[y * w + 3:y * w + w - 3])
    out = {k: v.most_common(1)[0][0] for k, v in T.items()}
    # 줄마다 안쪽 경계 = 그 크기 판들 중 «바탕색이 가장 바깥까지» 나온 열(글자가 끝까지 찬 판도 지우게)
    for w, h, px in recs:
        for y in range(h):
            c = out.get((w, h, y)); r = px[y * w:(y + 1) * w]
            xs = [x for x in range(w) if r[x] == c]
            if not xs: continue
            k = ('L', w, h, y); out[k] = min(out.get(k, w), xs[0]); k = ('R', w, h, y); out[k] = max(out.get(k, -1), xs[-1])
    return out


def flat(w, h, px):
    """단색 판(키 컨피그 설명 상자): 판 색 = 안쪽 최빈 → 줄마다 판 색 첫·끝 사이의 다른 색을 판 색으로"""
    P = [list(px[y * w:(y + 1) * w]) for y in range(h)]
    c = collections.Counter(px[(h // 4) * w:(3 * h // 4) * w]).most_common(1)[0][0]
    for y in range(h):
        xs = [x for x in range(w) if P[y][x] == c]
        if len(xs) < w // 3: continue
        for x in range(xs[0], xs[-1] + 1): P[y][x] = c
    return bytes(v for r in P for v in r)


def analyse(w, h, px, tmpl=None):
    P = [list(px[y * w:(y + 1) * w]) for y in range(h)]
    if tmpl is not None:
        bg = [0] * h; L = [0] * h; Rr = [-1] * h; rows = []
        for y in range(h):
            c = tmpl.get((w, h, y), 0)
            if not c: continue
            r = P[y]
            l = tmpl.get(('L', w, h, y)); rr = tmpl.get(('R', w, h, y))
            if l is None or rr is None or rr - l < w // 3: continue
            bg[y], L[y], Rr[y] = c, l, rr; rows.append(y)
        return _finish(P, w, h, bg, rows, L, Rr)
    # 줄마다 바탕 = 왼쪽에서 «같은 색 3칸 이상» 처음 나오는 구간(테두리 화소는 칸마다 바뀜), 오른쪽도 같은 색 구간이어야 안쪽 줄
    bg = [0] * h; L = [0] * h; Rr = [-1] * h; rows = []
    for y in range(h):
        r = P[y]
        l = next((x for x in range(w // 3) if r[x] == r[x + 1] == r[x + 2] and r[x] != 0), None)
        if l is None: continue
        c = r[l]
        rr = next((x for x in range(w - 1, 2 * w // 3, -1) if r[x] == r[x - 1] == r[x - 2] == c), None)
        if rr is None: continue
        bg[y], L[y], Rr[y] = c, l, rr; rows.append(y)
    return _finish(P, w, h, bg, rows, L, Rr)


def _finish(P, w, h, bg, rows, L, Rr):
    # 테두리 줄(글자 없는 바깥 띠)도 rows 에 들 수 있음 — 글자 마스크가 없으니 무해
    x0 = min(L[y] for y in rows); x1 = max(Rr[y] for y in rows)
    mask = [[False] * w for _ in range(h)]
    for y in rows:
        for x in range(L[y], Rr[y] + 1):
            if P[y][x] != bg[y]: mask[y][x] = True
    edge = collections.Counter(); allc = collections.Counter()
    for y in rows:
        for x in range(x0, x1 + 1):
            if not mask[y][x]: continue
            c = P[y][x]; allc[c] += 1
            if any(0 <= y + dy < h and not mask[y + dy][x + dx] and P[y + dy][x + dx] == bg[y + dy] for dy, dx in ((-1, 0), (0, -1))): edge[c] += 1
    outline = edge.most_common(1)[0][0] if edge else 0
    fill = next((c for c, _ in allc.most_common() if c != outline), 0)
    sh = {}
    for y in rows:
        cc = collections.Counter(P[y][x] for x in range(x0, x1 + 1) if mask[y][x] and P[y][x] not in (fill, outline))
        # 그림자 = 오른쪽 아래가 바탕인 글자 둘레 바깥 화소 중 최빈
        if cc: sh.setdefault(bg[y], collections.Counter()).update(cc)
    shadow = {k: v.most_common(1)[0][0] for k, v in sh.items()}
    ys = [y for y in rows if any(mask[y])]; xm = [x for y in rows for x in range(w) if mask[y][x]]
    box = (min(xm), min(ys), max(xm), max(ys)) if xm else (x0, rows[0], x1, rows[-1])
    return P, bg, rows, (x0, x1), mask, fill, outline, shadow, box, L, Rr


def nanum(text, size):
    """나눔고딕 굵게 → 1비트 화소(큰 제목용)"""
    from PIL import ImageFont
    f = ImageFont.truetype(NANUM_B, size); x0, y0, x1, y1 = f.getbbox(text)
    im = Image.new('L', (x1 + 4, y1 + 4), 0); ImageDraw.Draw(im).text((2, 2), text, font=f, fill=255)
    return [(x, y) for y in range(im.height) for x in range(im.width) if im.getpixel((x, y)) >= 128]


def render(w, h, px, text=None, tmpl=None):
    P, bg, rows, (x0, x1), mask, fill, outline, shadow, box, L, Rr = analyse(w, h, px, tmpl)
    out = [r[:] for r in P]
    for y in rows:
        for x in range(x0, x1 + 1):
            if mask[y][x]: out[y][x] = bg[y]
    if text is None:                                                     # 판때기(글자만 지운 빈 판)
        return bytes(c for r in out for c in r), dict(fill=fill, outline=outline, box=box)
    big = h >= 32
    if big:
        pts = nanum(text, 19)                                            # 큰 제목 = 나눔고딕 굵게
    else:
        pts, tw = F14.draw(text); pts = sorted(set(pts) | {(x + 1, y) for x, y in pts})   # 갈무리14 + 1px 굵게
    ink = set(pts)
    iy0 = min(y for _, y in pts); iy1 = max(y for _, y in pts); ix0 = min(x for x, _ in pts); ix1 = max(x for x, _ in pts)
    cx = (box[0] + box[2]) / 2; cy = (box[1] + box[3]) / 2
    ox = int(round(cx - (ix0 + ix1) / 2)); oy = int(round(cy - (iy0 + iy1) / 2))
    G = {(x + ox, y + oy) for x, y in ink}
    O = {(x + dx, y + dy) for x, y in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G
    S = {(x + 1, y + 1) for x, y in G | O} - G - O
    def put(x, y, c):
        if y in rows and L[y] <= x <= Rr[y]: out[y][x] = c
    for x, y in S:
        if 0 <= y < h: put(x, y, shadow.get(bg[y], outline))
    for x, y in O: put(x, y, outline)
    for x, y in G: put(x, y, fill)
    over = [(x, y) for x, y in G | O if not (y in rows and L[y] <= x <= Rr[y])]
    return bytes(c for r in out for c in r), dict(fill=fill, outline=outline, shadow=shadow, box=box, over=len(over))


def to_img(w, h, px, cram, bank=0x200):
    im = Image.new('RGB', (w, h), (64, 64, 64)); pp = im.load()
    for i, c in enumerate(px):
        if c:
            e = struct.unpack_from('>H', cram, 2 * ((bank + c) & 2047))[0]; pp[i % w, i // w] = ((e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3)
    return im


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    cram = open(os.path.join(ROOT, 'work', 'mem', '옵션', 'CRAM.bin'), 'rb').read()
    b = open(os.path.join(ROOT, 'work', 'files', 'YKBIN'), 'rb').read()
    od = os.path.join(ROOT, 'work', '미리보기_그림'); os.makedirs(od, exist_ok=True)
    for co, tr in KO.items():
        recs = ykbin.chunk(b, co); pairs = []
        for k, ko in tr.items():
            w, h, px = recs[k]; new, info = render(w, h, px, ko)
            print('%05X #%d %s %s' % (co, k, ko, info))
            pairs.append((to_img(w, h, px, cram), to_img(w, h, new, cram)))
        S = 3; W = max(a.width for a, _ in pairs) * S * 2 + 30; H = sum(a.height * S + 10 for a, _ in pairs) + 10
        sh = Image.new('RGB', (W, H), (40, 40, 40)); y = 10
        for a, n in pairs:
            sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (10, y)); sh.paste(n.resize((n.width * S, n.height * S), Image.NEAREST), (20 + a.width * S, y)); y += a.height * S + 10
        sh.save(os.path.join(od, '메뉴_%05X.png' % co))
