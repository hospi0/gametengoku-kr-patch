# -*- coding: utf-8 -*-
r"""노래방 월드 가사 글자 한글(2026-11-09) — 뜻 번역(하스피 «순서표 찾았으면 계획변경» → 초안 통과)
  그림: KASI.LZ = [u32 압축 크기][오쿠무라 LZSS] → [u32 3][오프셋 ×4] · 묶음0(0x14) 63장 · 묶음1(0x8010) 34장 · 묶음2 팔레트 16색
        묶음 = [u32 장수][(u32 오프셋, u16 w, u16 h) ×n] · 그림 32×32 4비트, 화면에서 보이는 모양을 «시계 반대 90° 돌린 것»이 화면(저장은 눕힘)
  순서표: 실행 파일 /0 0x25688 208 B, 1바이트 = 그림 번호(0~62 묶음0, 63~96 묶음1) — discbuild 가 voicesub 뒤에 덮어씀
  번역: work/노래방_가사_초안.tsv (원문\t한글, 소절마다 글자 수 같음, 음절 97종 이하)
  모양: 바깥선 11 · 속 = 줄마다 고정 색(원본 통계: 13→14→2→3→4→6→7→9) · 아래로 두께 4 px(11) · 그림자 1
  python tools/kasi_ko.py → work/build/KASI.LZ · work/plates/kasi.pkl {'seq': 208 B} · work/미리보기_그림/노래방_가사글자.png
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, lzss
from lzss_opt import encode_opt
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JUA = r'C:/claude/utils/font/jua/Jua-Regular.ttf'
SEQ_OFF, SEQ_LEN = 0x25688, 208
CHUNKS = (0x14, 0x8010); NCH = (63, 34)
SS = 4
ROWCOL = [13] * 5 + [14] * 2 + [2] * 3 + [3] * 3 + [4] * 2 + [6] * 2 + [7] * 3 + [9] * 12   # 갈무리 ×2 는 y 2~23 이라 아래쪽을 조금 늘림   # 화면 방향 줄 y → 속 색


def load():
    lzss.INIT = 0
    b = open(os.path.join(ROOT, 'work', 'files', 'KASI.LZ'), 'rb').read()
    s = struct.unpack_from('>I', b, 0)[0]
    d, _ = lzss.decompress(b[:4 + s], 4, 1 << 22)
    offs = []
    for co in CHUNKS:
        m = struct.unpack_from('>I', d, co)[0]
        for i in range(m):
            p, w, h = struct.unpack_from('>IHH', d, co + 4 + 8 * i); offs.append(co + p if (w, h) == (32, 32) else None)   # 91·92 = 32×128 «COOL»«DOWN» 통그림(그대로)
    pal = [struct.unpack_from('>H', d, 0xD124 + 4 + 2 * i)[0] for i in range(16)]
    return b, s, bytearray(d), offs, pal


def get(d, o):
    a = np.array([(d[o + j // 2] >> 4) if j % 2 == 0 else d[o + j // 2] & 15 for j in range(1024)]).reshape(32, 32)
    return np.rot90(a)                                                       # 화면 방향


def put(d, o, a):
    a = np.rot90(a, -1).reshape(-1)
    d[o:o + 512] = bytes((int(a[j]) << 4) | int(a[j + 1]) for j in range(0, 1024, 2))


def glyph(ch, H=22, W=26, TH=150):
    """한 음절 마스크(화면 방향 32×32, y 2~23) — 주아(하스피 «주아체로»), 획이 뭉치지 않게 크게(22 px)·문턱 높여 가늘게"""
    for fs in range(34, 10, -1):
        f = ImageFont.truetype(JUA, fs * SS)
        im = Image.new('L', (64 * SS, 64 * SS)); ImageDraw.Draw(im).text((8 * SS, 8 * SS), ch, font=f, fill=255)
        a = np.array(im.resize((64, 64), Image.BOX)) >= TH
        ys, xs = np.nonzero(a)
        if ys.max() - ys.min() + 1 <= H and xs.max() - xs.min() + 1 <= W: break
    g = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; h, w = g.shape
    m = np.zeros((32, 32), bool); y0 = 2 + (H - h) // 2; x0 = 3 + (W - w) // 2
    m[y0:y0 + h, x0:x0 + w] = g
    return m


def dil(m, r=1, cross=False):
    k = cv2.getStructuringElement(cv2.MORPH_CROSS if cross else cv2.MORPH_RECT, (2 * r + 1, 2 * r + 1))
    return cv2.dilate(m.astype(np.uint8), k).astype(bool)


def shift(m, dx, dy):
    o = np.zeros_like(m); H, W = m.shape
    o[max(dy, 0):H + min(dy, 0), max(dx, 0):W + min(dx, 0)] = m[max(-dy, 0):H + min(-dy, 0), max(-dx, 0):W + min(-dx, 0)]
    return o


def render(ch):
    """원본 팔레트: 11 = 노란 가장자리·두께, 속 = 줄 색(분홍→노랑), 1 = 진한 그림자
    획 사이 틈(×2 → 2 px)이 메워지지 않게: 바깥으로 안 불리고 글자 가장자리 1 px 를 11, 두께는 1 px, 남는 틈·둘레는 1(진한색)"""
    g = glyph(ch)
    er = cv2.erode(g.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))).astype(bool)
    ext = shift(g, 0, 1) & ~g
    body = g | ext
    sh = (dil(body, 1, True) | shift(body, 1, 1)) & ~body
    a = np.zeros((32, 32), int)
    a[sh] = 1; a[body] = 11
    for y, x in zip(*np.nonzero(er)): a[y, x] = ROWCOL[y]
    return a


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', '노래방_가사_초안.tsv'), encoding='utf-8') if l.strip()]
    jp = ''.join(r[0] for r in rows); ko = ''.join(r[1] for r in rows)
    assert len(jp) == len(ko) == SEQ_LEN, (len(jp), len(ko))
    b, s, d, offs, pal = load()
    exe = open(os.path.join(ROOT, 'work', 'files', '0'), 'rb').read()
    orig_seq = exe[SEQ_OFF:SEQ_OFF + SEQ_LEN]
    slots = [k for k in range(len(offs)) if offs[k] is not None]             # 32×32 칸(95)
    syl = [c for c in dict.fromkeys(ko) if c not in '①②']; assert len(syl) <= len(slots), len(syl)
    idx = {c: slots[i] for i, c in enumerate(syl)}; idx['①'] = 91; idx['②'] = 92   # 처음 나온 순서대로(원본도 그렇게 놓임)
    order = {k: c for c, k in idx.items()}
    seq = bytes(idx[c] for c in ko)
    old = {k: get(d, offs[k]) for k in slots}
    dash = old[orig_seq[3]]                                                  # 원본 «ー» 그림(ラブリー 의 4번째)
    blank = np.zeros((32, 32), int)
    for k in slots:
        c_ = order.get(k)
        put(d, offs[k], blank if c_ is None else dash if c_ == 'ー' else render(c_))
    c = encode_opt(bytes(d)); assert len(c) <= s, (len(c), s)
    nb = bytearray(b); nb[:4 + s] = struct.pack('>I', len(c)) + c + bytes(s - len(c))
    lzss.INIT = 0; chk, _ = lzss.decompress(bytes(nb[:4 + len(c)]), 4, 1 << 22); assert bytes(chk[:len(d)]) == bytes(d)
    os.makedirs(os.path.join(ROOT, 'work', 'build'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'build', 'KASI.LZ'), 'wb').write(nb)
    pickle.dump({'seq': seq, 'orig': orig_seq}, open(os.path.join(ROOT, 'work', 'plates', 'kasi.pkl'), 'wb'))
    print('음절', len(syl), '· 압축', len(c), '/', s, '· 순서표', SEQ_LEN, 'B')
    # 글자판 미리보기(원본 | 한글), 원래 색
    rgb = lambda v: ((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3)
    P = np.array([rgb(v) for v in pal], np.uint8); P[0] = (30, 30, 40); Z = 3     # 0 = 투명(바탕색으로)
    def tile(a): return Image.fromarray(P[a]).resize((32 * Z, 32 * Z), Image.NEAREST)
    n = len(slots); cols = 12; rh = (32 * Z + 6)
    sheet = Image.new('RGB', (cols * (32 * Z + 4) * 2 + 20, ((n + cols - 1) // cols) * rh), (30, 30, 40))
    for i, k in enumerate(slots):
        x = (i % cols) * (32 * Z + 4); y = (i // cols) * rh
        sheet.paste(tile(old[k]), (x, y)); sheet.paste(tile(get(d, offs[k])), (x + cols * (32 * Z + 4) + 20, y))
    sheet.save(os.path.join(ROOT, 'work', '미리보기_그림', '노래방_가사글자.png'))
    # 가사 줄 미리보기
    line = Image.new('RGB', (len(max(rows, key=lambda r: len(r[1]))[1]) * 34 + 8, len(rows) * 36 + 8), (30, 30, 40)); i = 0
    for r, (_, k) in enumerate(rows):
        for j, ch in enumerate(k):
            if offs[seq[i]] is not None: line.paste(Image.fromarray(P[get(d, offs[seq[i]])]), (4 + j * 34, 4 + r * 36))
            i += 1
    line.resize((line.width * 2, line.height * 2), Image.NEAREST).save(os.path.join(ROOT, 'work', '미리보기_그림', '노래방_가사줄.png'))
