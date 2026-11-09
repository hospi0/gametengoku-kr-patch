# -*- coding: utf-8 -*-
r"""일러스트 위 «흰 글자 + 검은 테두리» 비트맵 한글(2026-11-09) — 회상 편 제목 2장·데이터 모드 로딩/끝 2장
  그림 = A형 LZSS 풀면 131,616 B = 0x14 머리 + 팔레트 256(리틀엔디언 RGB555, 0x14~0x213) + … + 0x220~ 512×256 8비트
  · 회상 편 제목: RFPnBIN·RFYnBIN 첫째 덩어리(파일마다 같은 그림 한 벌) — 화면은 8줄 아래로 밀려 보임(SCY 8)
  · 데이터 모드 로딩 «データ検索中…» = DTLD1LZ(통째 한 덩어리) · 끝 «おしまい…» = DT{EX,FZ,FC,MK,BS,PA}BIN 안 덩어리
  방법: 글자 상자 안 흰 글자(밝음)·검은 테두리(어두움, 흰 글자 3px 안) 가면 → 2px 넓혀 cv2 inpaint(TELEA) → 팔레트 최근접 번호
        → 한글 = 블랙한산스, 원본 글자 높이·가운데에 흰 채움 + 검은 테두리 2px + 오른쪽 아래 그림자 1px
  python tools/pic_ko.py → work/plates/pic.pkl {이름: 풀린 새 그림}, 미리보기 work/미리보기_그림/회상제목_데이터모드_원본_한글.png
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BHS = r'C:/claude/utils/font/blackhansans/BlackHanSans-Regular.ttf'
DOHYEON = r'C:/claude/utils/font/dohyeon/DoHyeon-Regular.ttf'
FONT = {'데이터_끝': DOHYEON}

# 이름: (파일, 덩어리 오프셋, 한글, 글자 찾을 상자(x0, y0, x1, y1, 그림 좌표), 화면 위 밀림)
PICS = {
    '편제목_플레이어': ('RFP1BIN', 0x0, '게임 천국 플레이어 캐릭터 편', (0, 80, 320, 140), 8),
    '편제목_야마다': ('RFY1BIN', 0x0, '초천재! 지니어스 야마다 편', (0, 80, 320, 140), 8),
    '데이터_로딩': ('DTLD1LZ', 0x0, '데이터 검색 중...', (40, 90, 300, 140), 8),
    '데이터_끝': ('DTEXBIN', 0x5C5EC, '그럼 이만...', (40, 90, 300, 140), 8),   # 하스피 선택(«끝» 은 받침 비율 어색), 글꼴 도현
}


def unpack(f, o):
    b = open(os.path.join(ROOT, 'work', 'files', f), 'rb').read(); s = struct.unpack_from('>I', b, o)[0]
    old = lzss.INIT; lzss.INIT = 0
    try: d = lzss.decompress(b[:o + 4 + s], o + 4, 1 << 22)[0]
    finally: lzss.INIT = old
    assert len(d) == 131616, (f, hex(o), len(d))
    return bytes(d), s


def pal_of(d):
    p = np.frombuffer(d[0x14:0x214], '<u2').astype(int)
    return np.stack([(p & 31) << 3, (p >> 5 & 31) << 3, (p >> 10 & 31) << 3], -1)


def dil(m, r):
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)


def tight_box(rgb, box):
    """넓은 상자 안에서 흰 글자 줄 = 흰 화소가 많은 줄이 가장 길게 이어진 띠 → 그 띠의 흰 화소 열 범위"""
    x0, y0, x1, y1 = box; sub = rgb[y0:y1, x0:x1]
    white = (sub.min(-1) >= 200) & dil(sub.max(-1) <= 56, 2)          # 글자 = 검은 테두리 2px 안의 흰 화소(그림 속 흰 부분 제외)
    cnt = white.sum(1); rows = [i for i in range(len(cnt)) if cnt[i] >= 6]
    runs = []; s = p = None
    for r in rows:
        if s is None: s = p = r
        elif r - p <= 2: p = r
        else: runs.append((s, p)); s = p = r
    runs.append((s, p)); a, b = max(runs, key=lambda t: sum(cnt[t[0]:t[1] + 1]))
    cols = np.nonzero(white[a:b + 1].sum(0) >= 1)[0]
    return (x0 + int(cols[0]) - 3, y0 + a - 3, x0 + int(cols[-1]) + 4, y0 + b + 4)


def text_mask(rgb, box):
    x0, y0, x1, y1 = box = tight_box(rgb, box)
    m = np.zeros(rgb.shape[:2], bool); sub = rgb[y0:y1, x0:x1]
    dark = sub.max(-1) <= 72
    white = (sub.min(-1) >= 200) & dil(sub.max(-1) <= 56, 2)
    fill = np.zeros_like(m); fill[y0:y1, x0:x1] = white
    near = dil(fill, 3); dk = np.zeros_like(m); dk[y0:y1, x0:x1] = dark
    return fill, (fill | (dk & near))


def render(text, h, font=None):
    f = ImageFont.truetype(font or BHS, 200); x0, y0, x1, y1 = f.getbbox(text)
    im = Image.new('L', (x1 - x0 + 20, y1 - y0 + 20), 0); ImageDraw.Draw(im).text((10 - x0, 10 - y0), text, font=f, fill=255)
    im = im.crop(im.getbbox()); w = max(1, round(im.width * h / im.height))
    return np.array(im.resize((w, h), Image.LANCZOS)) >= 120


def make(d, text, box, font=None):
    a = np.frombuffer(d[0x220:], np.uint8).reshape(256, 512).copy(); P = pal_of(d)
    rgb = P[a].astype(np.uint8)
    fill, m = text_mask(rgb, box)
    ys, xs = np.nonzero(fill); tb = (xs.min(), ys.min(), xs.max(), ys.max())   # 원본 흰 글자 범위
    hole = dil(m, 2)
    fixed = cv2.inpaint(np.ascontiguousarray(rgb[:, :, ::-1]), hole.astype(np.uint8), 4, cv2.INPAINT_TELEA)[:, :, ::-1].astype(int)
    # 팔레트 최근접(구멍 안만)
    hy, hx = np.nonzero(hole)
    dist = ((fixed[hy, hx][:, None, :] - P[None, :, :]) ** 2).sum(-1); dist[:, 0] += 10 ** 9   # 0번(투명) 안 씀
    a[hy, hx] = dist.argmin(1)
    # 한글
    th = tb[3] - tb[1] + 1; G = render(text, th, font)
    if G.shape[1] > 300: G = render(text, int(th * 300 / G.shape[1]), font)
    gh, gw = G.shape; cx = (tb[0] + tb[2]) // 2; cy = (tb[1] + tb[3]) // 2
    gx, gy = cx - gw // 2, cy - gh // 2
    big = np.zeros((256, 512), bool); big[gy:gy + gh, gx:gx + gw] = G
    out = dil(big, 2) & ~big
    sh = np.zeros_like(big); sh[1:, 1:] = (big | out)[:-1, :-1]; sh &= ~(big | out)
    near = lambda c: int(((P[1:] - np.array(c)) ** 2).sum(-1).argmin()) + 1
    a[sh] = near((0, 0, 0)); a[out] = near((0, 0, 0)); a[big] = near((248, 248, 248))
    return d[:0x220] + a.tobytes(), tb


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    res = {}; ims = []
    for name, (f, o, text, box, sy) in PICS.items():
        d, s = unpack(f, o); new, tb = make(d, text, box, FONT.get(name)); res[name] = new
        print(name, f, hex(o), '원본 글자 범위', tb)
        for x in (d, new):
            a = np.frombuffer(x[0x220:], np.uint8).reshape(256, 512); ims.append(Image.fromarray(pal_of(x)[a].astype(np.uint8)[sy:sy + 224, :320]))
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'pic.pkl'), 'wb'))
    sh = Image.new('RGB', (650, 4 * 228), (50, 50, 50))
    for i, im in enumerate(ims): sh.paste(im, ((i % 2) * 330, (i // 2) * 228))
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '회상제목_데이터모드_원본_한글2.png')); print(sh.size)
