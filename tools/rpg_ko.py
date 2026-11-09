# -*- coding: utf-8 -*-
r"""가정용 월드 RPG 전투 창 한글(2026-11-09) — 스테이트 work/states/미키미사토합체.state1
  · 화면: VDP2 NBG2(맵 0x60000, 8비트 칸, 글자 = STCONDQ1.BIN 날것 → VDP2 0x40000, 칸 번호 = 맵값/2)
  · 글자 칸 두 벌(STCONDQ1): 첫째 0x40C~0x43A(처음 화면 맵용) · 둘째 0x43B~0x495(틀·▶▼ + 가나 80칸, 대사용)
      화소: 바탕 0xFD · 획 0x01(흰) · 0x02 등은 번짐
  · 대사·메뉴 = BGSTCONS.BIN(전투 코드 덩어리) 안 바이트 문자열: 글자 바이트 = 칸×2 − 0x874
      {FA xx}=열 · {F9 yy}=행 · {FD}=줄바꿈 · {FC}=버튼 대기 · {FB n} · {F8} · {FF}=끝 — 문자열 시작·끝 자리 고정, 남는 바이트는
      시작의 {FA xx} 를 되풀어(같은 열 다시 지정, 무해) 채움 · 홀수 1바이트는 ▼ 앞 빈칸
  · 처음 화면 미리 짜인 맵 = STCONDQ2.BIN 0x7BF8~(u16, 값/2 = 첫째 벌 칸) — 첫째 벌 칸에 한글 다시 그리고 맵 값을 바꿈
  python tools/rpg_ko.py → work/plates/rpg.pkl {STCONDQ1.BIN, STCONDQ2.BIN, BGSTCONS.BIN}, 미리보기 work/미리보기_그림/RPG창_원본_한글.png
"""
import os, sys, pickle, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf, menu_gfx as M
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F7 = bdf.Font(os.path.join(M.FD, 'Galmuri7.bdf'))
BG, INK = 0xFD, 0x01
KEEP = {'!', '♥', '▶', '▼', ' '}

# 둘째 벌(대사용) 원래 글자 — 칸 0x446 부터
KANA2 = 'いのちはだしガスやろうかゅもんせつくてばぐたえしヤマダがあらわれにげこき!ひよるをっけどうぐ♥メージけキングDXと※・まょャイアムトパペラギーリぴ1ヘッドミニ2'
SP2, TRI, DOWN = 0x43F, 0x444, 0x445
C2 = {'!': 0x446 + KANA2.index('!'), '♥': 0x446 + KANA2.index('♥'), ' ': SP2, '▶': TRI, '▼': DOWN}

MENU = [('▶たたかえ', '▶싸워라'), ('にげろ', '도망쳐'), ('ひよる', '쫄아라'), ('どうぐ♥', '도구♥')]
MSG = [('しんかんヤマダ が あらわれた', '신관 야마다가 나타났다'),
       ('しんかんヤマダ の こうげき!', '신관 야마다의 공격!'),
       ('しんかんヤマダ は\nあやしい しゅもん を\nと※えた', '신관 야마다는\n수상한 주문을\n외웠다'),
       ('しんかんヤマダ はにげた!', '신관 야마다는 도망쳤다!')]
# 처음 화면 맵(STCONDQ2) 줄: 원본 첫째 벌 글자열 → 한글
STATIC = [('しんかんヤマダ.が_あらわれた', '신관 야마다가 나타났다'), ('しんかんヤマダ.も.こうげき!', '신관 야마다도 공격!')]
FIRST = {0x40c: '.', 0x412: '▶', 0x413: 'た', 0x414: 'た', 0x415: 'か', 0x416: 'え', 0x418: 'し', 0x419: 'ん', 0x41a: 'ヤ', 0x41b: 'マ',
         0x41c: 'ダ', 0x41d: 'が', 0x41e: '_', 0x41f: 'あ', 0x420: 'ら', 0x421: 'わ', 0x422: 'れ', 0x423: 'た', 0x424: '_', 0x426: 'に',
         0x427: 'げ', 0x428: 'ろ', 0x429: '_', 0x42a: 'ひ', 0x42b: 'よ', 0x42c: 'る', 0x42d: 'も', 0x42e: 'こ', 0x42f: 'う', 0x430: 'き',
         0x431: '!', 0x432: 'ど', 0x433: 'う', 0x434: 'ぐ', 0x435: '♥'}
FREE1 = [c for c, k in sorted(FIRST.items()) if k not in '.▶_!♥']           # 첫째 벌에서 한글로 다시 그릴 칸


def glyph(ch):
    """8×8 칸: 갈무리7 한 음절, 칸 가운데(가로)·윗선 맞춤"""
    pts, _ = F7.draw(ch)
    out = [[BG] * 8 for _ in range(8)]
    if not pts: return out
    x0 = min(x for x, _ in pts); x1 = max(x for x, _ in pts); ox = (8 - (x1 - x0 + 1)) // 2 - x0
    y0 = YTOP
    for x, y in pts:
        X, Y = x + ox, y - y0
        assert 0 <= X < 8 and 0 <= Y < 8, (ch, X, Y)
        out[Y][X] = INK
    return out


def cell_put(buf, c, P):
    for y in range(8): buf[c * 64 + y * 8:c * 64 + y * 8 + 8] = bytes(P[y])


def cell_get(buf, c):
    return [list(buf[c * 64 + y * 8:c * 64 + y * 8 + 8]) for y in range(8)]


def enc2(t, cmap):
    out = bytearray()
    for ch in t:
        if ch == '\n': out.append(0xFD); continue
        out.append(cmap[ch] * 2 - 0x874)
    return bytes(out)


def dec_first2(b):
    """BGSTCONS 바이트 → 둘째 벌 원문(검산용)"""
    s = ''
    for v in b:
        if v == 0xFD: s += '\n'; continue
        c = (0x874 + v) // 2
        s += ' ' if c == SP2 else '▶' if c == TRI else '▼' if c == DOWN else KANA2[c - 0x446]
    return s


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    F = lambda n: open(os.path.join(ROOT, 'work', 'files', n), 'rb').read()
    q1o, q2o, bgo = F('STCONDQ1.BIN'), F('STCONDQ2.BIN'), F('BGSTCONS.BIN')
    q1, q2, bg = bytearray(q1o), bytearray(q2o), bytearray(bgo)
    # 윗선: 모든 음절 잉크 맨 위 공통
    allk = set(''.join(k for _, k in MENU + MSG + STATIC)) - KEEP - {'\n'}
    YTOP = min(y for ch in allk for _, y in F7.draw(ch)[0])
    # ── 둘째 벌: 한글 음절 → 칸 배정(!·♥ 칸 제외) ──
    syl2 = sorted(set(''.join(k for _, k in MENU + MSG)) - KEEP - {'\n'})
    slots = [c for c in range(0x446, 0x446 + len(KANA2)) if c not in (C2['!'], C2['♥'])]
    slots = [c for c in slots if c < 0x480]                              # 0x480~ 은 VRAM 에서 STCONDQ2(0x52000)가 덮음
    assert len(syl2) <= len(slots), len(syl2)
    cmap2 = dict(C2)
    for ch, c in zip(syl2, slots): cmap2[ch] = c; cell_put(q1, c, glyph(ch))
    print('둘째 벌 음절', len(syl2), '/', len(slots))
    # ── BGSTCONS 문자열 ──
    def rewrite(jp, ko, x_code):
        """원문 글자열 자리를 찾아 같은 바이트 수로 다시 씀; 모자란 바이트는 앞의 {FA x} 되풀이"""
        alts = []
        for ch in jp:
            if ch == '\n': alts.append([0xFD]); continue
            cs = [SP2] if ch == ' ' else [TRI] if ch == '▶' else [0x446 + i for i, c in enumerate(KANA2) if c == ch]
            alts.append([c * 2 - 0x874 for c in cs])
        pat = b''.join(b'[' + b''.join(re.escape(bytes([v])) for v in al) + b']' for al in alts)
        ms = [m.start() for m in re.finditer(pat, bgo)]; assert len(ms) == 1, (jp, ms)
        k = ms[0]; src = bgo[k:k + len(alts)]
        new = enc2(ko, cmap2); pad = len(src) - len(new); assert pad >= 0, (ko, pad)
        # 앞이 {FA x}{F9 y} 인 자리 → {FA x} 를 pad//2 번 앞에 더 넣고 원래 {FA x}{F9 y} 는 그 뒤로
        assert bg[k - 4] == 0xFA and bg[k - 2] == 0xF9, hex(k)
        head = bytes(bg[k - 4:k]); odd = pad % 2
        if odd and bg[k - 5] == 0xF8:                                    # 대사: 앞의 {F8}(창 지우기)을 한 번 더 — ▼ 앞 빈칸 대신
            body = bytes([0xF8, 0xF8]) + bytes([0xFA, bg[k - 3]]) * (pad // 2) + head + new; st = k - 5
        else:                                                            # 메뉴: 남는 1바이트 = 글자 뒤 빈칸(안 보임)
            body = bytes([0xFA, bg[k - 3]]) * (pad // 2) + head + new + (enc2(' ', cmap2) if odd else b''); st = k - 4
        bg[st:k + len(src)] = body
        assert len(body) == k + len(src) - st
        return k
    for jp, ko in MENU: rewrite(jp, ko, None)
    for jp, ko in MSG: rewrite(jp, ko, None)
    assert len(bg) == len(bgo)
    # ── 첫째 벌 + STCONDQ2 처음 화면 맵 ──
    a = list(struct.unpack('>%dH' % (len(q2o) // 2), q2o))
    syl1 = sorted(set(''.join(k for _, k in MENU + STATIC)) - KEEP - {'\n'})
    assert len(syl1) <= len(FREE1), len(syl1)
    cmap1 = {'!': 0x431, '♥': 0x435, '▶': 0x412, ' ': 0x40C}
    for ch, c in zip(syl1, FREE1): cmap1[ch] = c; cell_put(q1, c, glyph(ch))
    for c in FREE1[len(syl1):]: cell_put(q1, c, [[BG] * 8 for _ in range(8)])
    rev1 = {}
    for c, k in FIRST.items(): rev1.setdefault(k, []).append(c)
    def find_seq(jp):
        cand = [rev1[ch] for ch in jp]
        hits = [i for i in range(len(a) - len(jp)) if all(a[i + j] // 2 in cand[j] and a[i + j] < 0x1000 for j in range(len(jp)))]
        return hits
    def put_seq(jp, ko, width):
        hits = find_seq(jp); assert len(hits) == 1, (jp, hits)
        i = hits[0]; ko = ko.ljust(width)
        for j, ch in enumerate(ko): a[i + j] = (a[i + j] & 0xF000) | (cmap1[ch] * 2)
    for jp, ko in MENU: put_seq(jp, ko, len(jp))
    for jp, ko in STATIC: put_seq(jp, ko, len(jp))
    q2 = bytearray(struct.pack('>%dH' % len(a), *a))
    # 검산: 둘째 벌 칸을 가리키는 맵이 STCONDQ2 에 없는지(있으면 그 맵도 한글이 섞임)
    lo, hi = 0x446 * 2, (0x446 + len(KANA2)) * 2
    stray = sum(1 for v in struct.unpack('>%dH' % (len(q2o) // 2), q2o) if lo <= (v & 0xFFF) < hi)
    print('STCONDQ2 안 둘째 벌 참조', stray)
    print('바뀐 바이트 Q1', sum(x != y for x, y in zip(q1, q1o)), 'Q2', sum(x != y for x, y in zip(q2, q2o)), 'BG', sum(x != y for x, y in zip(bg, bgo)))
    pickle.dump({'STCONDQ1.BIN': bytes(q1), 'STCONDQ2.BIN': bytes(q2), 'BGSTCONS.BIN': bytes(bg)}, open(os.path.join(ROOT, 'work', 'plates', 'rpg.pkl'), 'wb'))

    # ── 미리보기: 창 두 개(처음 화면 맵 / 대사 4줄)를 원본|한글로 ──
    def grid(q1b, rows):
        H = len(rows) * 8; W = max(len(r) for r in rows) * 8
        im = Image.new('RGB', (W, H), (0, 0, 40)); p = im.load()
        for r, row in enumerate(rows):
            for j, c in enumerate(row):
                P = cell_get(q1b, c)
                for y in range(8):
                    for x in range(8):
                        v = P[y][x]
                        if v != BG: p[j * 8 + x, r * 8 + y] = (255, 255, 255) if v == 1 else (170, 170, 170)
        return im
    def static_rows(q2b):
        b = list(struct.unpack('>%dH' % (len(q2b) // 2), q2b)); i = 0x7BF8 // 2; out = []
        hits = [k for k in range(i, i + 400) if b[k] // 2 == 0x40D]
        start = hits[0]; W = 44
        for r in range(6): out.append([b[start + r * W + j] // 2 for j in range(26)])
        return out
    def msg_rows(bgb, q1b):
        rows = []
        for jp, _ in MENU + MSG: pass
        k = 0; out = []
        for m in range(4):
            pass
        return out
    S = 4; ims = []
    for q1b, q2b in ((q1o, q2o), (bytes(q1), bytes(q2))):
        ims.append(grid(q1b, static_rows(q2b)))
    # 대사 줄: BGSTCONS 를 해석해 글자 칸 나열
    def bg_lines(bgb):
        lines = []; i = 0
        while i < len(bgb) - 1:
            if bgb[i] == 0xFA and bgb[i + 2] == 0xF9 and bgb[i + 3] == 0x17 and bgb[i + 1] == 0x11:
                j = i; cur = []; ls = []
                while bgb[j] not in (0xFC, 0xFF):
                    v = bgb[j]
                    if v in (0xFA, 0xF9, 0xFB): j += 2; continue
                    if v == 0xFD: ls.append(cur); cur = []; j += 1; continue
                    if v == 0xF8: j += 1; continue
                    cur.append((0x874 + v) // 2); j += 1
                if cur: ls.append(cur)
                lines += [l for l in ls if l] + [[]]; i = j
            i += 1
        return lines
    ims2 = [grid(q1o, bg_lines(bgo)), grid(bytes(q1), bg_lines(bytes(bg)))]
    W = max(i.width for i in ims + ims2) * S
    H = (ims[0].height + ims2[0].height) * S + 30
    sh = Image.new('RGB', (W * 2 + 30, H), (60, 60, 60))
    for k in range(2):
        sh.paste(ims[k].resize((ims[k].width * S, ims[k].height * S), Image.NEAREST), (10 + k * (W + 10), 10))
        sh.paste(ims2[k].resize((ims2[k].width * S, ims2[k].height * S), Image.NEAREST), (10 + k * (W + 10), 20 + ims[0].height * S))
    sh.save(os.path.join(ROOT, 'work', '미리보기_그림', 'RPG창_원본_한글.png')); print(sh.size)
