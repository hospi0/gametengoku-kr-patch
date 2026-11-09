# -*- coding: utf-8 -*-
r"""메뉴 빈 판(판때기) — 같은 크기·같은 색 판은 «판 하나» 공유(2026-11-09 하스피 «같은 크기 같은 색 판을 왜 따로 만들어»)
  무리 = (폭, 높이, 왼쪽 4열의 줄별 색) · 빈 판 = 무리 안 화소별 최빈값(판마다 다른 글자는 사라짐)
  무리가 1장뿐이면 tools/menu_gfx.render(글자 지우기)로
  python tools/plates.py → work/미리보기_그림/빈판.png (무리마다 «원본 대표 | 빈 판 · 장 수»), work/plates/<키>.bin
"""
import os, sys, struct, collections, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ykbin, menu_gfx as M
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 판이 있는 메뉴 덩어리 → 색 스테이트
CHUNKS = {0x25310: '메인메뉴+나레이션', 0x26648: '옵션', 0x277AC: '사운드테스트', 0x349DC: '데이터모드', 0x35FE8: '회상모드',
          0x3C6C8: '게임설정', 0x3DCE8: '옵션'}
# 키 컨피그(0x39918)는 판 안 만듦 — 그림 그대로 두고 글자만 교체(하스피 «키컨피그는 왜 판을 쳐만들어»)

PILL = {(0x35FE8, 1), (0x35FE8, 2)}


def groups():
    b = open(os.path.join(ROOT, 'work', 'files', 'YKBIN'), 'rb').read()
    G = collections.OrderedDict()
    for co, st in CHUNKS.items():
        for k, (w, h, px) in enumerate(ykbin.chunk(b, co) if co != 0x3DCE8 else chunk_3dce8(b)):
            key = (w, h, bytes(px[y * w + 1] for y in range(h)) + bytes(px[y * w + w - 2] for y in range(h)) + bytes([collections.Counter(px[(h // 6) * w:(h // 6 + 1) * w]).most_common(1)[0][0]]))   # 양 끝 테두리 열(글자 안 닿음)
            G.setdefault(key, []).append((co, k, px, st))
    return G


def chunk_3dce8(b):
    """YKBIN 0x3DCE8 = [색표 0xA00] + 레코드(작은 버튼 0~4 만 판)"""
    import lzss
    lzss.INIT = 0; o = 0x3DCE8; s = struct.unpack_from('>I', b, o)[0]
    d, _ = lzss.decompress(b[:o + 4 + s], o + 4, 1 << 23); p = 0xA00; out = []
    for _ in range(5):
        w, h = struct.unpack_from('>HH', d, p); out.append((w, h, d[p + 4:p + 4 + w * h])); p += 4 + w * h
    return out


def plate(key, members):
    w, h, _ = key
    px0 = members[0][2]
    if len(members) == 1:
        try: px0 = M.render(w, h, px0, None)[0]                      # 띠 위 글자는 render 가 지움 → 띠 판정은 지운 결과로
        except Exception: pass
    uni = [len(set(v for v in px0[y * w:(y + 1) * w] if v)) == 1 and sum(1 for v in px0[y * w:(y + 1) * w] if v) >= w * 3 // 4 for y in range(h)]
    runs = []; y = 0
    while y < h:
        if uni[y]:
            y0 = y
            while y < h and uni[y]: y += 1
            runs.append((y - y0, y0, y - 1))
        else: y += 1
    best = max(runs) if runs else (0, 0, -1)
    if len(members) == 1 and best[0] >= 6 and w >= 64 and best[1] >= h // 2 and any(px0[:best[1] * w]):
        # 판 = 한 색 띠(メニュー 제목 노란 띠) + 그 위로 튀어나온 글자 → 띠 줄만 남기고 나머지(글자 찌꺼기)는 투명(하스피 «판은 됐고 찌꺼기만 밀면 되잖아»)
        out = bytearray(w * h)
        for y in range(best[1], best[2] + 1): out[y * w:(y + 1) * w] = px0[y * w:(y + 1) * w]
        return bytes(out)
    if (members[0][0], members[0][1]) in PILL:                            # 알약 탭(회상 모드 편 고르기): 줄마다 최빈 색으로 안쪽(끝 2칸 테 제외) 통째로
        src = members[0][2]; out = bytearray(src); ok = set()
        for y in range(h):                                               # 판 색 = 줄 양 끝 3칸에 나오는 색(글자 흰색·그림자 제외)
            r = src[y * w:(y + 1) * w]; xs = [x for x in range(w) if r[x]]
            if xs: ok |= set(r[xs[0]:xs[0] + 3]) | set(r[xs[-1] - 2:xs[-1] + 1])
        for y in range(h):
            r = src[y * w:(y + 1) * w]; xs = [x for x in range(w) if r[x]]
            if not xs: continue
            c = collections.Counter(v for v in r[xs[0]:xs[-1] + 1] if v in ok).most_common(1)[0][0]
            hp = max(yy for yy in range(h) if any(src[yy * w:(yy + 1) * w]))   # 알약은 위아래 대칭 — 아래 반은 위 반 거울 줄 색
            if y > hp // 2: c = out[(hp - y) * w + w // 2]
            for x in range(xs[0] + 2, xs[-1] - 1): out[y * w + x] = c
        return bytes(out)
    if len(members) == 1:
        try:
            new, _ = M.render(w, h, members[0][2], None)
            out = bytearray(new)                                         # 판정 못 한 줄(글자 그림자 줄) = 왼쪽·오른쪽 끝 같은 색 3칸 구간 사이를 그 색으로
            for y in range(h):
                r = out[y * w:(y + 1) * w]
                l = next((x for x in range(w // 3) if r[x] == r[x + 1] == r[x + 2] and r[x]), None)
                if l is None: continue
                c = r[l]; rr = next((x for x in range(w - 1, 2 * w // 3, -1) if r[x] == r[x - 1] == r[x - 2] == c), None)
                if rr is not None:
                    for x in range(l, rr + 1): out[y * w + x] = c
            return bytes(out)
        except Exception:
            return members[0][2]                                         # 줄무늬 판이 아님(색 상자·아이콘) — 그대로
    out = bytearray(w * h)
    for i in range(w * h): out[i] = collections.Counter(m[2][i] for m in members).most_common(1)[0][0]
    # 판 = 줄마다 한 색: 줄 색 = 무리 전체 그 줄(가운데 90%) 최빈 → 화소 최빈 판에서 그 색이 이어지는 안쪽을 통째로 그 색
    for y in range(h):
        r = out[y * w:(y + 1) * w]
        # 줄 색 = 판 안쪽 첫 열(1·2열이 같은 색이면 그 색 — 글자가 안 닿는 곳). 아니면 무리 전체 최빈
        lx = next((x for x in range(w // 4) if r[x] == r[x + 1] == r[x + 2] and r[x]), None)   # 테두리 안쪽 첫 3칸 연속 구간
        c = r[lx] if lx is not None else collections.Counter(v for m in members for v in m[2][y * w + w // 20:y * w + w - w // 20]).most_common(1)[0][0]
        l = next((x for x in range(w - 1) if r[x] == c and r[x + 1] == c), None)
        rr = next((x for x in range(w - 1, 0, -1) if r[x] == c and r[x - 1] == c), None)
        if l is None or rr is None or rr - l < w // 3: continue
        for x in range(l, rr + 1): out[y * w + x] = c
    return bytes(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    G = groups(); rows = []; os.makedirs(os.path.join(ROOT, 'work', 'plates'), exist_ok=True); saved = {}
    for n, (key, mem) in enumerate(G.items()):
        w, h, _ = key; pl = plate(key, mem); co, k, px, st = mem[0]
        cram = open(os.path.join(ROOT, 'work', 'mem', st, 'CRAM.bin'), 'rb').read()
        if pl != px: rows.append((M.to_img(w, h, px, cram), M.to_img(w, h, pl, cram), len(mem), '%05X#%d' % (co, k)))   # 글자 없는 것(아이콘·상자)은 미리보기에서 뺌
        saved[n] = dict(key=(w, h), members=[(c, kk) for c, kk, _, _ in mem], plate=pl)
        print(n, w, h, len(mem), [(('%05X' % c), kk) for c, kk, _, _ in mem][:8])
    pickle.dump(saved, open(os.path.join(ROOT, 'work', 'plates', 'plates.pkl'), 'wb'))
    S = 3; W = 2 * max(a.width for a, *_ in rows) * S + 140; H = sum(a.height * S + 12 for a, *_ in rows) + 12
    sh = Image.new('RGB', (W, H), (40, 40, 40)); dr = ImageDraw.Draw(sh); y = 12
    for n, (a, p, c, tag) in enumerate(rows):
        dr.text((4, y), '%d (%d장)' % (n, c), fill=(255, 255, 0))
        sh.paste(a.resize((a.width * S, a.height * S), Image.NEAREST), (70, y)); sh.paste(p.resize((p.width * S, p.height * S), Image.NEAREST), (80 + a.width * S, y)); y += a.height * S + 12
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', '빈판.png')); print('무리', len(rows), sh.size)
