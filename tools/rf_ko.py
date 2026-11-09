# -*- coding: utf-8 -*-
r"""회상 모드 화 제목 카드 한글(2026-11-09) — RFPnBIN(플레이어 편 1~7, 8 = 오마케)·RFYnBIN(야마다 편 1~7) 둘째 A형 LZSS 덩어리
  풀면 131,616 B = 0x220 머리(팔레트 포함) + 512×256 8비트 비트맵(NBG0). 보이는 범위 x<320·y<224
  색: 12 = 붉은 바탕 · 1 = 회색 글자(한 색) · 2·3·4 = 드문 잡티 → 글자(1~4) 지우고 12, 한글은 1 한 색
  배치(원본 실측): «第n話» (56~179, 10~31) · 큰 제목 (10~310, 35~196) · «上映時間» (172~276, 200~215)
  글꼴: 제n화·상영 시간 = 블랙한산스 · 큰 제목 = 동해 독도체(붓) · 오마케 카드 = 주아
  python tools/rf_ko.py → work/plates/rf.pkl {(파일, 오프셋): 풀린 새 덩어리}, 미리보기 work/미리보기_그림/회상카드_원본_한글.png
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FD = r'C:/claude/utils/font'
BHS = FD + '/blackhansans/BlackHanSans-Regular.ttf'
DOKDO = FD + '/eastseadokdo/EastSeaDokdo-Regular.ttf'
JUA = FD + '/jua/Jua-Regular.ttf'
BG, INK = 12, 1

# 파일 → (제n화, [제목 줄들], [줄 높이 비율], 상영 시간)
CARDS = {
    'RFP1BIN': ('제1화', ['리더는', '누구냐?'], [0.42, 0.58], '4분 46초'),
    'RFP2BIN': ('제2화', ['인간 착각'], [1.0], '4분 32초'),
    'RFP3BIN': ('제3화', ['멋진', '동료'], [0.4, 0.6], '2분 13초'),
    'RFP4BIN': ('제4화', ['재회,', '언니와 동생'], [0.45, 0.55], '2분 54초'),
    'RFP5BIN': ('제5화', ['불행의', '연애편지'], [0.42, 0.58], '3분 40초'),
    'RFP6BIN': ('제6화', ['잘 가라', '친구여'], [0.42, 0.58], '3분 13초'),
    'RFP7BIN': ('제7화', ['전멸의', '만찬'], [0.4, 0.6], '6분 13초'),
    'RFY1BIN': ('제1화', ['움직이기 시작한', '음모'], [0.36, 0.64], '1분 30초'),
    'RFY2BIN': ('제2화', ['거대 로봇의', '비밀'], [0.4, 0.6], '1분 38초'),
    'RFY3BIN': ('제3화', ['어둠 속에 꿈틀대는', '하얀 망령'], [0.42, 0.58], '2분 09초'),
    'RFY4BIN': ('제4화', ['불행 소녀', '나카무라'], [0.42, 0.58], '1분 11초'),
    'RFY5BIN': ('제5화', ['천재의', '증명'], [0.4, 0.6], '2분 30초'),
    'RFY6BIN': ('제6화', ['운도', '실력'], [0.45, 0.55], '1분 10초'),
    'RFY7BIN': ('제7화', ['더 게임', '파라다이스'], [0.42, 0.58], '2분 40초'),
}
OMAKE = ('RFP8BIN', '오마케', ['다시', '만날 날까지...'], '2분 21초')   # 주아엔 «…» 글리프 없음


def chunk_off(f):
    return 0xAD50 if f.startswith('RFP') else 0xC328


def load(f):
    b = open(os.path.join(ROOT, 'work', 'files', f), 'rb').read(); o = chunk_off(f)
    s = struct.unpack_from('>I', b, o)[0]
    old = lzss.INIT; lzss.INIT = 0
    try: d = lzss.decompress(b[:o + 4 + s], o + 4, 1 << 22)[0]
    finally: lzss.INIT = old
    assert len(d) == 131616, (f, len(d))
    return bytes(d), o, s


def mask_text(text, font, h):
    """글자 잉크 마스크(높이 h 로 맞춤, 비율 유지) — 4배로 그려 줄인 뒤 문턱"""
    f = ImageFont.truetype(font, 200)
    x0, y0, x1, y1 = f.getbbox(text)
    im = Image.new('L', (x1 - x0 + 20, y1 - y0 + 20), 0); ImageDraw.Draw(im).text((10 - x0, 10 - y0), text, font=f, fill=255)
    im = im.crop(im.getbbox())
    w = max(1, round(im.width * h / im.height))
    return np.array(im.resize((w, h), Image.LANCZOS)) >= 110


def fatten(m, r):
    """획 굵게(원본 붓글씨처럼) — 반지름 r 원판으로 넓힘"""
    if r <= 0: return m
    h, w = m.shape; o = np.zeros((h + 2 * r, w + 2 * r), bool)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r + r: o[r + dy:r + dy + h, r + dx:r + dx + w] |= m
    return o


def fit(text, font, maxw, maxh, fat=0):
    m = fatten(mask_text(text, font, maxh - 2 * fat), fat)
    if m.shape[1] > maxw: m = fatten(mask_text(text, font, max(6, int((maxh - 2 * fat) * maxw / m.shape[1]))), fat)
    return m


def stamp(a, m, x, y):
    h, w = m.shape; a[y:y + h, x:x + w][m] = INK


def make(d, ep, lines, ratios, run, omake=False):
    a = np.frombuffer(d[0x220:], np.uint8).reshape(256, 512).copy()
    vis = a[:224, :320]; vis[np.isin(vis, [1, 2, 3, 4])] = BG
    m = fit(ep, BHS if not omake else JUA, 124, 21); stamp(a, m, 56 if not omake else 62, 10 + (21 - m.shape[0]) // 2)
    if omake:
        m1 = fit(lines[0], JUA, 120, 40); stamp(a, m1, 23, 59)
        m2 = fit(lines[1], JUA, 280, 40); stamp(a, m2, 23, 121)
    else:
        top, bot, L, R = 36, 196, 8, 312
        gap = 2; H = bot - top - gap * (len(lines) - 1)
        ms = []
        for t, r in zip(lines, ratios):
            m = fit(t, DOKDO, R - L, int(H * r))                         # 먼저 맞춘 높이로 굵기 정함 — 작은 줄은 굵히면 뭉개짐
            hh = m.shape[0]; fat = 2 if hh >= 72 else 1 if hh >= 52 else 0
            ms.append(fit(t, DOKDO, R - L, hh + 2 * fat, fat=fat) if fat else m)
        tot = sum(m.shape[0] for m in ms) + gap * (len(ms) - 1); y = top + (bot - top - tot) // 2
        for k, m in enumerate(ms):
            x = L + (R - L - m.shape[1]) // 2
            if len(ms) == 2: x += (-14 if k == 0 else 14)                 # 원본처럼 윗줄은 왼쪽·아랫줄은 오른쪽으로 살짝
            x = max(L, min(R - m.shape[1], x))
            stamp(a, m, x, y); y += m.shape[0] + gap
    m = fit('상영 시간 ' + run, BHS, 150, 15); stamp(a, m, 300 - m.shape[1], 200)
    return d[:0x220] + a.tobytes()


def rgb(d, cram):
    a = np.frombuffer(d[0x220:], np.uint8).reshape(256, 512).astype(int)
    e = cram[a]; return Image.fromarray(np.stack([(e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3], -1).astype(np.uint8)[:224, :320])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    cram = np.frombuffer(open(os.path.join(ROOT, 'work', 'mem', '회상모드_s1', 'CRAM.bin'), 'rb').read(), '>u2').astype(int)
    res = {}; pairs = []
    order = ['RFP%dBIN' % i for i in range(1, 8)] + ['RFP8BIN'] + ['RFY%dBIN' % i for i in range(1, 8)]
    for f in order:
        d, o, s = load(f)
        if f == OMAKE[0]: new = make(d, OMAKE[1], OMAKE[2], None, OMAKE[3], omake=True)
        else: ep, lines, ratios, run = CARDS[f]; new = make(d, ep, lines, ratios, run)
        res[(f, o)] = new; pairs.append((f, rgb(d, cram), rgb(new, cram)))
        print(f, '완료')
    pickle.dump(res, open(os.path.join(ROOT, 'work', 'plates', 'rf.pkl'), 'wb'))
    C = 2; sh = Image.new('RGB', (C * (640 + 30), ((len(pairs) + C - 1) // C) * 232), (50, 50, 50))
    for i, (f, a, b) in enumerate(pairs):
        x = (i % C) * 670; y = (i // C) * 232
        sh.paste(a, (x, y)); sh.paste(b, (x + 325, y))
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '회상카드_원본_한글.png')); print(sh.size)
