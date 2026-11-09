# -*- coding: utf-8 -*-
r"""오프닝 그림 OPENING.BIN(2026-11-09) — A형 압축 덩어리([u32 압축 바이트 수][오쿠무라 LZSS 0 채움]) 4B 정렬로 이어짐
  덩어리 풀면 [u32 개수] + 레코드 [u16 폭][u16 높이][u32 0][4비트 화소 폭×높이/2] (캐릭터 카드 = 0x4F80C 덩어리, 성우 이름 48×48·기체 이름 32×40)
  python tools/opening_bin.py [색 스테이트=그림_오프닝카드] → work/그림추출/오프닝/<덩어리>/NN_WxH.png + _모아보기.png"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lzss.INIT = 0


def chunks(b):
    """끝에서부터 거꾸로 사슬 찾기 + 앞에서 정방향 — 둘을 합침"""
    L = len(b); found = set()
    o = 0
    while o < L - 8:                                                     # 정방향
        s = struct.unpack_from('>I', b, o)[0]
        if not (16 < s and o + 4 + s <= L) or s > 0x18000: break
        found.add(o); o = (o + 4 + s + 3) & ~3
    tgt = (L + 3) & ~3                                                   # 역방향(끝 = 파일 끝)
    for _ in range(200):
        hit = None
        for q in range(max(0, tgt - 0x18000), tgt - 8, 4):
            s = struct.unpack_from('>I', b, q)[0]
            if ((q + 4 + s + 3) & ~3) == tgt and s > 16: hit = q; break
        if hit is None: break
        found.add(hit); tgt = hit
    return sorted(found)


def records(d):
    if len(d) < 4: return []
    n = struct.unpack_from('>I', d, 0)[0]; p = 4; out = []
    for _ in range(min(n, 4096)):
        if p + 8 > len(d): break
        w, h = struct.unpack_from('>HH', d, p)
        if not (0 < w <= 512 and 0 < h <= 512) or p + 8 + w * h // 2 > len(d): break
        out.append((w, h, d[p + 8:p + 8 + w * h // 2])); p += 8 + w * h // 2
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    st = sys.argv[1] if len(sys.argv) > 1 else '그림_오프닝카드'
    cram = open(os.path.join(ROOT, 'work', 'mem', st, 'CRAM.bin'), 'rb').read()
    col = lambda i: (lambda c: ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3))(struct.unpack_from('>H', cram, 2 * (i & 2047))[0])
    b = open(os.path.join(ROOT, 'work', 'files', 'OPENING.BIN'), 'rb').read()
    for o in chunks(b):
        s = struct.unpack_from('>I', b, o)[0]
        d, _ = lzss.decompress(b[:o + 4 + s], o + 4, 1 << 23); rs = records(d)
        print('%05X 압축 %X 풀린 %d 레코드 %d' % (o, s, len(d), len(rs)))
        if not rs: continue
        od = os.path.join(ROOT, 'work', '그림추출', '오프닝', '%05X' % o); os.makedirs(od, exist_ok=True); ims = []
        for k, (w, h, px) in enumerate(rs):
            im = Image.new('RGBA', (w, h)); pp = im.load()
            for i in range(w * h):
                q = px[i >> 1]; c = q >> 4 if i % 2 == 0 else q & 15
                if c: pp[i % w, i // w] = col(c) + (255,)
            im.save(os.path.join(od, '%02d_%dx%d.png' % (k, w, h))); ims.append(im)
        W = 900; x = y = rh = 0; pos = []
        for im in ims:
            if x + im.width > W: x = 0; y += rh + 16; rh = 0
            pos.append((x, y)); x += im.width + 6; rh = max(rh, im.height)
        sh = Image.new('RGB', (W, y + rh + 16), (90, 90, 90)); dr = ImageDraw.Draw(sh)
        for k, ((x, y), im) in enumerate(zip(pos, ims)): sh.paste(im, (x, y + 12), im); dr.text((x, y), '%02d' % k, fill=(255, 255, 0))
        sh.save(os.path.join(od, '_모아보기.png'))
