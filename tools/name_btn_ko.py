# -*- coding: utf-8 -*-
r"""이름 입력 화면 단추·제목·순위 한글(2026-11-09) — NAMEA.BIN 날것 4비트 스프라이트 (name_ko 결과 위에 덮음)
  · 판 바꾸기 32×16(색 은행 0x20): ひらがな 0x19164 → 한글1 · カタカナ 0x19264 → 한글2 (ABC 0x19364 그대로) — 바탕 4 · 글자 6 · 테 5
  · 終了 0x19664 32×16 → 끝 — 바탕 7 · 글자 d · 테 f
  · n位 32×16(은행 0x40) 0x21DA4 + n×0x100 (1~10) → n위 — 位 자리(오른쪽 21열)만, 갈무리11 굵게 채움 1 · 테 4
  · 選ぶ 0x227A4 · 決定 0x22BA4 · 一文字消す 0x22FA4 64×32(은행 0x50) → 선택 · 결정 · 한 글자/지우기 — 바탕 d · 글자 9 · 그림자 7 (오른쪽 단추 그림 그대로)
  · ネームエントリー 0x233A4 176×24(은행 0x60, 랭킹 제목과 같은 색 배치) → 네임 엔트리 (rank_ko.title_art)
  python tools/name_btn_ko.py → work/plates/name.pkl 의 NAMEA.BIN 갱신 + BACKRAM.BIN(기본 이름), 미리보기 work/미리보기_그림/이름입력_단추_원본_한글.png
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf, menu_gfx as M, rank_ko
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F7 = bdf.Font(os.path.join(M.FD, 'Galmuri7.bdf'))
F9 = bdf.Font(os.path.join(M.FD, 'Galmuri9.bdf'))
FB = bdf.Font(os.path.join(M.FD, 'Galmuri11-Bold.bdf'))
F11 = bdf.Font(os.path.join(M.FD, 'Galmuri11.bdf'))

# 기본 랭킹 이름(가나 21개) — BACKRAM.BIN 8 B 레코드
NAMES = {0x178: '키메라비스트', 0x180: '컴뱃Q', 0x190: '간바론', 0x198: '무쿠무쿠퐁!', 0x1A0: '스트라이크앨리', 0x1B0: '스트리트잼',
         0x1C0: '솔리드블레이드', 0x1D0: '타케다신겐', 0x1D8: '킥오프', 0x1E0: '이가닌', 0x1E8: '텐세이류', 0x1F8: '플러스알파',
         0x200: '로드오브킹', 0x208: '로드랜드', 0x218: '슈~퍼~EDF', 0x220: '데드댄스', 0x230: '슈~퍼~이카리', 0x238: '킨추',
         0x240: '솔담', 0x248: '파이어~ F.', 0x250: '랏신슈라', 0x258: '스~치~', 0x260: 'S닌자군'}


def get4(b, o, w, h):
    d = np.frombuffer(bytes(b[o:o + w * h // 2]), np.uint8); return np.stack([d >> 4, d & 15], 1).reshape(h, w).copy()


def put4(b, o, a):
    f = a.reshape(-1).astype(np.uint8); b[o:o + a.size // 2] = bytes((f[0::2] << 4) | f[1::2])


def pts(font, t, bold=False):
    p = font.draw(t)[0]
    if bold: p = list(set(p) | {(x + 1, y) for x, y in p})
    x0 = min(x for x, _ in p); y0 = min(y for _, y in p)
    return {(x - x0, y - y0) for x, y in p}


def stamp(a, G, ox, oy, fill, out=None, shadow=None):
    G = {(x + ox, y + oy) for x, y in G}; H, W = a.shape
    O = ({(x + dx, y + dy) for x, y in G for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - G) if out is not None else set()
    S = ({(x + 1, y + 1) for x, y in G | O} - G - O) if shadow is not None else set()
    for st, v in ((S, shadow), (O, out), (G, fill)):
        for x, y in st:
            if 0 <= x < W and 0 <= y < H: a[y, x] = v


def wh(G):
    return max(x for x, _ in G) + 1, max(y for _, y in G) + 1


def switch_btn(a, text):
    """보라 알약: 안쪽(4줄~11줄, 2~29열) 비우고 갈무리7 글자 6 + 그림자 5"""
    a[4:12, 2:30] = 4
    G = pts(F7, text); w, h = wh(G); stamp(a, G, (32 - w) // 2, 4 + (8 - h) // 2, 6, shadow=5)
    return a


def end_btn(a):
    a[1:15, 1:31][a[1:15, 1:31] != 7] = 7
    G = pts(FB, '끝'); w, h = wh(G); stamp(a, G, (32 - w) // 2, (16 - h) // 2, 0xD, out=0xF)
    return a


def rank_lbl(a, L):
    """位 = L열부터 끝까지(1~9位 L=11, 10位 L=15 — 숫자 두 자리에 位 가 붙어 있음)"""
    a[:, L:] = 0
    G = pts(FB, '위'); w, h = wh(G); stamp(a, G, L + (32 - L - w) // 2, (16 - h) // 2, 1, out=4)
    return a


def big_btn(a, lines):
    a[5:27, 4:38][np.isin(a[5:27, 4:38], [7, 9])] = 0xD
    if len(lines) == 1:
        G = pts(F11, lines[0], bold=True); w, h = wh(G); stamp(a, G, 4 + (34 - w) // 2, (32 - h) // 2, 9, shadow=7)
    else:
        for k, t in enumerate(lines):
            G = pts(F9, t); w, h = wh(G); stamp(a, G, 4 + (34 - w) // 2, 6 + k * 11, 9, shadow=7)
    return a


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    pk = os.path.join(ROOT, 'work', 'plates', 'name.pkl'); res = pickle.load(open(pk, 'rb'))
    src = open(os.path.join(ROOT, 'work', 'files', 'NAMEA.BIN'), 'rb').read()
    na = bytearray(res['NAMEA.BIN']); items = []
    def do(o, w, h, fn, bank):
        old = get4(src, o, w, h); new = fn(old.copy()); put4(na, o, new); items.append((old, new, bank))
    do(0x19164, 32, 16, lambda a: switch_btn(a, '한글1'), 0x20)
    do(0x19264, 32, 16, lambda a: switch_btn(a, '한글2'), 0x20)
    do(0x19664, 32, 16, end_btn, 0x20)
    for n in range(10): do(0x21DA4 + n * 0x100, 32, 16, lambda a, n=n: rank_lbl(a, 15 if n == 9 else 11), 0x40)
    do(0x227A4, 64, 32, lambda a: big_btn(a, ['선택']), 0x50)
    do(0x22BA4, 64, 32, lambda a: big_btn(a, ['결정']), 0x50)
    do(0x22FA4, 64, 32, lambda a: big_btn(a, ['한 글자', '지우기']), 0x50)
    do(0x233A4, 176, 24, lambda a: np.array(rank_ko.title_art('네임 엔트리', 0)[0], np.uint8), 0x60)
    res['NAMEA.BIN'] = bytes(na)
    # 기본 이름(BACKRAM): 칸 번호로 다시 씀
    cellof = pickle.load(open(os.path.join(ROOT, 'work', 'plates', 'name_cells.pkl'), 'rb'))
    up = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for i, c in enumerate(up): cellof[c] = i
    for i, c in enumerate(up.lower()): cellof[c] = 0x1A + i
    for i, c in enumerate('1234567890'): cellof[c] = 0x34 + i
    cellof.update({' ': 0xDF, '.': 0xE0, '!': 0xE1, '?': 0xE2, '~': 0xE6})
    bk = bytearray(open(os.path.join(ROOT, 'work', 'files', 'BACKRAM.BIN'), 'rb').read())
    for o, t in NAMES.items():
        assert len(t) <= 8, t
        bk[o:o + 8] = bytes([cellof[c] for c in t] + [0xDF] * (8 - len(t)))
    res['BACKRAM.BIN'] = bytes(bk)
    pickle.dump(res, open(pk, 'wb'))
    c = open(os.path.join(ROOT, 'work', 'mem', '이름입력', 'CRAM.bin'), 'rb').read()
    pal = lambda bank: np.array([(lambda e: ((e & 31) << 3, (e >> 5 & 31) << 3, (e >> 10 & 31) << 3))(struct.unpack_from('>H', c, 2 * (bank + i))[0]) for i in range(16)], np.uint8)
    sh = Image.new('RGB', (2 * 180 + 10, 16 * 18 + 80), (50, 50, 50)); y = 0
    for old, new, bank in items:
        for k, a in enumerate((old, new)):
            im = pal(bank)[a]; im[a == 0] = (50, 50, 50); sh.paste(Image.fromarray(im), (k * 186, y))
        y += a.shape[0] + 2
    sh.crop((0, 0, sh.width, y)).resize((sh.width * 3, y * 3), Image.NEAREST).save(os.path.join(ROOT, 'work', '미리보기_그림', '이름입력_단추_원본_한글.png'))
    print('완료')
