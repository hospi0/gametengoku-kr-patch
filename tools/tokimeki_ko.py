# -*- coding: utf-8 -*-
r"""가정용 월드 «ときめき メモリ 対戦 あなたにメロメロ» 패러디 타이틀 한글(2026-11-09, 스테이트 work/states/가정용월드_토키메키로고.state)
  원본 STCONM2.BIN(날것, 압축 없음): [u32 조각 수 45] + 조각 [u16 w][u16 h][0x0020][0x0600] + 8비트 화소(CRAM 0x600+값)
  게임은 조각을 90° 돌려 찍음(꼭짓점 A=왼쪽 아래) → 화면 = np.rot90(텍스처, 1), 저장 = np.rot90(화면, -1)
  조각: 0x00C 対(104×112) · 0x2D94 戦(120×128) · 0x699C ときめき+メモリ+별+꼬리 빛(56×120) · 0x83E4~0xA15C あなたにメロメロ 8 · 0xA524 ゛(24×16, 비움)
  → 대 / 전(검정 채움+흰 테) · 두근두근 / 메모리(별·꼬리 빛 유지) · 당신에게메로메로 · YAMADA 줄(영어)은 그대로
  python tools/tokimeki_ko.py → work/plates/tokimeki.pkl {'STCONM2.BIN'}, 미리보기 work/미리보기_그림/토키메키_원본_한글.png
"""
import os, sys, struct, pickle
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = r'C:/claude/utils/font/'
JUA = FD + 'jua/Jua-Regular.ttf'
BRUSH = FD + 'eastseadokdo/EastSeaDokdo-Regular.ttf'
MEM = os.path.join(ROOT, 'work', 'mem', 'tokimeki')


def font_path(d, ext=('.ttf', '.otf')):
    for f in sorted(os.listdir(d)):
        if f.lower().endswith(ext): return os.path.join(d, f)


if not os.path.exists(BRUSH): BRUSH = font_path(FD + 'eastseadokdo')
if not os.path.exists(JUA): JUA = font_path(FD + 'jua')


def dil(m, r):
    if r <= 0: return m.copy()
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)


def text_mask(text, font, h, maxw, shear=0.0, sx=1.0):
    """글자 가면(높이 h, 폭 ≤ maxw) — shear = 기울임(오른쪽 위로 +), sx = 가로 배율"""
    f = ImageFont.truetype(font, 240); x0, y0, x1, y1 = f.getbbox(text)
    im = Image.new('L', (x1 - x0 + 200, y1 - y0 + 40), 0); ImageDraw.Draw(im).text((100 - x0, 20 - y0), text, font=f, fill=255)
    if shear: im = im.transform(im.size, Image.AFFINE, (1, shear, -shear * im.height / 2, 0, 1, 0), Image.BICUBIC)
    im = im.crop(im.getbbox())
    w = round(im.width * h / im.height * sx)
    if w > maxw: h = max(4, int(h * maxw / w)); w = maxw
    return np.array(im.resize((max(1, w), h), Image.LANCZOS)) >= 128


def place(H, W, m, cx=None, cy=None):
    G = np.zeros((H, W), bool); mh, mw = m.shape
    x0 = (W - mw) // 2 if cx is None else int(cx - mw / 2); y0 = (H - mh) // 2 if cy is None else int(cy - mh / 2)
    x0 = max(0, min(W - mw, x0)); y0 = max(0, min(H - mh, y0))
    G[y0:y0 + mh, x0:x0 + mw] = m[:H - y0, :W - x0]
    return G


def pieces(d):
    n = struct.unpack('>I', d[:4])[0]; o = 4; out = []
    for _ in range(n):
        w, h = struct.unpack('>HH', d[o:o + 4]); out.append((o + 8, w, h)); o += 8 + w * h
    return out


def row_grad(s, fillsel, G):
    """새 글자 G 의 각 행 채움 = 원본 채움 화소의 행별 최빈 색 번호(원본 글자 높이 ↔ 새 글자 높이 비례)"""
    ys = np.nonzero(fillsel.any(1))[0]; gy = np.nonzero(G.any(1))[0]
    out = np.zeros(G.shape, np.uint8)
    if not len(ys) or not len(gy): return out
    for y in gy:
        t = (y - gy[0]) / max(1, gy[-1] - gy[0]); oy = int(round(ys[0] + t * (ys[-1] - ys[0])))
        best = None
        for dy in range(0, 40):
            for yy in (oy - dy, oy + dy):
                if 0 <= yy < s.shape[0] and fillsel[yy].any():
                    v = s[yy][fillsel[yy]]; best = np.bincount(v).argmax(); break
            if best is not None: break
        out[y][G[y]] = best
    return out


def row_smooth(s, fillsel, G, pal, k=4):
    # (s, fillsel) = 색을 딸 원본 조각 — 메로메로는 8조각 모두 «な» 조각 하나로(하스피 «에만 색이 흐려»: 조각마다 따면 음절마다 색이 다름)
    """메로메로용(하스피 «가로줄 없애줘»): 원본 행별 평균색을 위아래 k 행 이동 평균 → 새 글자 행에 비례 대응 → 그 조각 채움 색 중 최근접(너무 밝은 칸 제외)"""
    out = np.zeros(G.shape, np.uint8); ys = np.nonzero(fillsel.any(1))[0]; gy = np.nonzero(G.any(1))[0]
    if not len(ys) or not len(gy): return out
    rows = np.array([pal[s[y][fillsel[y]]].mean(0) if fillsel[y].any() else [np.nan] * 3 for y in range(ys[0], ys[-1] + 1)], float)
    ok = ~np.isnan(rows[:, 0]); idx = np.arange(len(rows))
    for ch in range(3): rows[:, ch] = np.interp(idx, idx[ok], rows[ok, ch])
    sm = np.array([rows[max(0, i - k):i + k + 1].mean(0) for i in range(len(rows))])
    cand = np.unique(s[fillsel]); cand = cand[pal[cand].sum(1) < 600]
    B = np.array([[0, 2], [3, 1]]) / 4 + 0.125                              # 2×2 점 섞기 — 두 후보 사이를 행 띠 없이
    for y in gy:
        t = (y - gy[0]) / max(1, gy[-1] - gy[0]); want = sm[int(round(t * (len(sm) - 1)))]
        dd = ((pal[cand] - want) ** 2).sum(1); o2 = np.argsort(dd)[:2]
        c1, c2 = cand[o2[0]], cand[o2[-1]]; p1, p2 = pal[c1].astype(float), pal[c2].astype(float)
        seg = p2 - p1; r = 0.0 if not seg.any() else float(np.clip(((want - p1) * seg).sum() / (seg * seg).sum(), 0, 1))
        for x in np.nonzero(G[y])[0]: out[y, x] = c2 if r > B[y % 2, x % 2] else c1
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    src = open(os.path.join(ROOT, 'work', 'files', 'STCONM2.BIN'), 'rb').read(); b = bytearray(src)
    c = np.frombuffer(open(os.path.join(MEM, 'CRAM.bin'), 'rb').read(), '>u2').astype(int)[0x600:0x700]
    pal = np.stack([(c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3], -1)
    lum = pal.sum(1); sat = pal.max(1) - pal.min(1)
    P = {o: (w, h) for o, w, h in pieces(src)}
    get = lambda o: np.rot90(np.frombuffer(src[o:o + P[o][0] * P[o][1]], np.uint8).reshape(P[o][1], P[o][0]).astype(int), 1)
    new = {}

    def put(o, scr):
        w, h = P[o]; assert scr.shape == (w, h), (hex(o), scr.shape, (w, h))
        t = np.ascontiguousarray(np.rot90(scr.astype(np.uint8), -1)); b[o:o + w * h] = t.tobytes(); new[o] = scr

    # ── 対 → 대 · 戦 → 전 : 붓글씨(동해 독도), 검정 244 + 흰 테 2px(1) + 회색 바깥 1px(117)
    for o, ch in ((0xC, '대'), (0x2D94, '전')):
        s = get(o); H, W = s.shape
        m = text_mask(ch, BRUSH, H - 6, W - 6); G = dil(place(H, W, m), 1)
        O = dil(G, 2) & ~G; O2 = dil(G, 3) & ~G & ~O
        out = np.zeros((H, W), np.uint8); out[O2] = 117; out[O] = 1; out[G] = 244
        put(o, out)

    # ── あなたにメロメロ → 당신에게메로메로 : 조각마다 한 음절, 채움 = 원본 행별 색(청록→초록), 진파랑 테 1px + 흰 테 2px(10)
    MERO = [0x83E4, 0x87AC, 0x8C34, 0x90BC, 0x9544, 0x990C, 0x9CD4, 0xA15C]
    rs = get(0x87AC); rfill = (rs != 0) & (lum[rs] < 690) & ~((pal[rs][..., 2] >= 180) & (lum[rs] < 360)) & (pal[rs][..., 1] >= 200)
    for o, ch in zip(MERO, '당신에게메로메로'):
        s = get(o); H, W = s.shape
        white = (lum[s] >= 690) & (s != 0); dark = (pal[s][..., 2] >= 180) & (lum[s] < 360) & (s != 0)
        fill = (s != 0) & ~white & ~dark & (pal[s][..., 1] >= 200)              # 몸통 = 청록·초록(초록 성분 높음)만 — 가운데 파랑 칸이 섞이면 가로 띠
        darkc = np.bincount(s[dark]).argmax() if dark.any() else 220
        m = text_mask(ch, JUA, H - 7, W - 8, shear=0.12, sx=0.62); G = place(H, W, m)
        O = dil(G, 1) & ~G; Wt = dil(G, 2) & ~G & ~O
        out = row_smooth(rs, rfill, G, pal); out[O] = 220; out[Wt] = 10        # 윤곽 = 진파랑 220 고정(조각마다 따면 «에» 만 연한 파랑 174 — 하스피 «에가 흐려»)
        put(o, out)
    put(0xA524, np.zeros(get(0xA524).shape, np.uint8))                      # ゛ 조각 비움

    # ── ときめき+メモリ 조각: 별(노랑)·꼬리 빛(위 오른쪽)은 유지, 글자 둘은 새로
    o = 0x699C; s = get(o); H, W = s.shape
    yellow = np.isin(s, [36, 250, 251, 252, 253])
    xx = np.arange(W)[None, :].repeat(H, 0); yy = np.arange(H)[:, None].repeat(W, 1)
    star = dil(yellow, 3) & (s != 0) & (xx < 24)
    tail = (s != 0) & (yy <= 15) & (xx >= 78)
    out = np.zeros((H, W), np.uint8); out[tail] = s[tail]
    # 메모리: 분홍 행별 색 + 흰 테 1 + 진파랑 테 1 + 아래로 6px 흰 입체(진파랑 윤곽)
    pink = (pal[s][..., 0] >= 200) & (pal[s][..., 1] <= 190) & (s != 0) & (yy >= 22)
    # 메모리: 음절 따로 그려 사이 3px · 분홍 행별 색 + 진파랑 윤곽 1px(획 가름) + 아래 4px 흰 입체 + 흰 바깥 테 1px
    #   (하스피 «가늘게 해서 획이 살도록» — 흰 안쪽 테가 ㅁ 속·글자 사이를 메워 뭉갰음)
    ms = [text_mask(ch, JUA, 23, 30, shear=0.10) for ch in '메모리']
    tw = sum(m.shape[1] for m in ms) + 3 * 2; x = 60 - tw // 2; M = np.zeros((H, W), bool)
    for m in ms:
        mh, mw = m.shape; y0 = 33 - mh // 2 - 2; M[y0:y0 + mh, x:x + mw] |= m; x += mw + 3
    M = cv2.erode(M.astype(np.uint8), np.ones((2, 2), np.uint8)).astype(bool)   # 가로·세로 1px 만 깎음(하스피 «아주 조금만 굵게» — 십자 깎기는 2px 라 너무 가늚)
    E = np.zeros_like(M)                                                    # 흰 입체 대신 진파랑 그림자(오른쪽 아래 2px) — 가는 획에 흰 입체는 획마다 줄이 생김
    for k in range(1, 3): E[k:, k:] |= M[:-k, :-k]
    Ln = (dil(M, 1) & ~M) | E
    Bo = dil(M | Ln, 1) & ~(M | Ln)
    mm = np.zeros((H, W), np.uint8)
    mm[Bo] = 6; mm[Ln] = 210
    g = row_grad(s, pink, M); mm[M] = g[M]
    sel = mm != 0; out[sel] = mm[sel]
    # 두근두근: 하늘색 채움 + 파랑 테 1 + 흰 테 1, 꼬리 빛 앞쪽(왼쪽 위)
    cy_ = (pal[s][..., 2] >= 200) & (pal[s][..., 0] <= 180) & (pal[s][..., 1] >= 200) & (yy <= 24) & (xx < 80) & (s != 0)
    m = text_mask('두근두근', JUA, 17, 62, shear=0.18); T = place(H, W, m, cx=52, cy=13)
    Ot = dil(T, 1) & ~T; Wt = dil(T, 2) & ~T & ~Ot
    tt = np.zeros((H, W), np.uint8); tt[Wt] = 7; tt[Ot] = 177; g = row_grad(s, cy_, T); tt[T] = g[T]
    sel = tt != 0; out[sel] = tt[sel]
    out[star] = s[star]
    put(o, out)

    assert len(b) == len(src)
    pickle.dump({'STCONM2.BIN': bytes(b)}, open(os.path.join(ROOT, 'work', 'plates', 'tokimeki.pkl'), 'wb'))
    # 미리보기: 스테이트 VDP1 명령 자리대로 화면 합성(원본 | 한글)
    v = open(os.path.join(MEM, 'VDP1_VRAM.bin'), 'rb').read()
    cmds = []
    for a in range(0, 0x800, 0x20):
        ctrl, link, pmod, colr, srca, size = struct.unpack('>6H', v[a:a + 12])
        if ctrl & 0x8000: break
        if (ctrl & 0xF) <= 2: xy = struct.unpack('>8h', v[a + 12:a + 28]); cmds.append((srca * 8, min(xy[0::2]), min(xy[1::2])))
    where = {}
    for o, (w, h) in P.items():
        k = v.find(src[o + w * h // 3:o + w * h // 3 + 32])
        if k >= 0: where[k - w * h // 3] = o
    sh = Image.new('RGB', (2 * 330, 230), (40, 40, 40))
    bgimg = Image.open(os.path.join(ROOT, 'work', 'mem', 'tokimeki', 'bg.png')) if os.path.exists(os.path.join(MEM, 'bg.png')) else None
    for i in range(2):
        scene = Image.new('RGB', (320, 224), (150, 110, 140))
        for sa, x, y in cmds:
            o = where.get(sa)
            if o is None: continue
            arr = get(o) if i == 0 else new.get(o, get(o))
            rgb = pal[arr].astype(np.uint8); al = (arr != 0).astype(np.uint8) * 255
            im = Image.fromarray(np.dstack([rgb, al]), 'RGBA'); scene.paste(im, (x, y), im)
        sh.paste(scene, (i * 330, 3))
    sh.resize((sh.width * 3, sh.height * 3), Image.NEAREST).save(os.path.join(ROOT, 'work', '미리보기_그림', '토키메키_원본_한글.png'))
    print('완료', len(new), '조각')
