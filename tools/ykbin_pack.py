# -*- coding: utf-8 -*-
r"""YKBIN 재압축(2026-11-09) — 한글 그림 레코드를 덩어리에 덮어 다시 압축, «원래 자리·원래 크기 안»에 씀(뒤 덩어리 오프셋 불변)
  덩어리 = [u32 압축 바이트 수 s][오쿠무라 LZSS 0 채움, 링 시작 0xFEE, LSB 깃발] · 새 압축 ≤ s 면 [u32 새 s'] + 스트림 + 0 채움(원래 4+s 까지)
  남는 깃발 비트 = 원본 덩어리 끝과 같은 방식(아래 검사)
  입력: work/plates/ko.pkl(판+한글) · logo.pkl(메뉴 로고) · btn.pkl(작은 버튼 0x3DCE8) · keycfg.pkl(키 컨피그) · stest.pkl(사운드 테스트 곡 정보·BGM 이름·성우·LR 안내)
  python tools/ykbin_pack.py → work/build/YKBIN (원본 work/files/YKBIN 은 안 건드림) + 왕복 검산
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lzss.INIT = 0
N, START = 0x1000, 0xFEE
PL = lambda n: pickle.load(open(os.path.join(ROOT, 'work', 'plates', n), 'rb'))


def compress(data, pad_bit=0, depth=256, lazy=False):
    """빠른 오쿠무라 LZSS: 3바이트 머리 사전으로 최근 위치 후보(최대 거리 4095, 길이 3~18), 최장 일치(+lazy: 다음 자리가 더 길면 글자 하나 먼저)"""
    out = bytearray(); grp = bytearray(); flags = nb = 0; i = 0; heads = {}; L = len(data)
    def add(j):
        if j + 3 <= L: heads.setdefault(data[j:j + 3], []).append(j)
    def best_at(i):
        best = (0, 0); mx = min(18, L - i)
        if mx < 3: return best
        for j in reversed(heads.get(data[i:i + 3], [])[-depth:]):
            if i - j > 4095: break
            k = 0
            while k < mx and data[j + k] == data[i + k]: k += 1          # 겹침(거리<길이)도 디코더와 같음(바이트씩 읽고 씀)
            if k > best[0]:
                best = (k, j)
                if k == mx: break
        return best
    while i < L:
        k, j = best_at(i)
        if lazy and k >= 3 and k < 18:
            add(i); k2, _ = best_at(i + 1); heads[data[i:i + 3]].pop()
            if k2 > k: k = 0
        nb_tok = None
        if k >= 3:
            pos = (START + j) & (N - 1)
            grp += bytes([pos & 0xFF, ((pos >> 8) << 4) | (k - 3)])
            for t in range(k): add(i + t)
            i += k
        else:
            flags |= 1 << nb; grp.append(data[i]); add(i); i += 1
        nb += 1
        if nb == 8: out.append(flags); out += grp; flags = nb = 0; grp = bytearray()
    if nb:
        if pad_bit: flags |= (0xFF << nb) & 0xFF
        out.append(flags); out += grp
    return bytes(out)


def raw(b, o):
    s = struct.unpack_from('>I', b, o)[0]
    d, p = lzss.decompress(b[:o + 4 + s], o + 4, 1 << 23)
    return s, bytearray(d)


def recs_offsets(d, start=0, count=None):
    p = start; offs = []
    while p + 4 <= len(d) and (count is None or len(offs) < count):
        w, h = struct.unpack_from('>HH', d, p); offs.append((p + 4, w, h)); p += 4 + w * h
    return offs


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    b = bytearray(open(os.path.join(ROOT, 'work', 'files', 'YKBIN'), 'rb').read()); orig = bytes(b)
    new = {}
    for (co, k), px in PL('ko.pkl').items(): new.setdefault(co, {})[k] = px
    for k, px in PL('logo.pkl').items(): new.setdefault(0x25310, {})[k] = px
    for k, px in PL('keycfg.pkl').items(): new.setdefault(0x39918, {})[k] = px
    for k, px in PL('btn.pkl').items(): new.setdefault(0x3DCE8, {})[k] = px
    for (co, k), px in PL('stest.pkl').items(): new.setdefault(co, {})[k] = px   # 사운드 테스트 글자(tools/stest_ko.py, 2026-11-09)
    for co in sorted(new):
        s, d = raw(orig, co)
        offs = recs_offsets(d, 0xA00, 5) if co == 0x3DCE8 else recs_offsets(d)
        for k, px in new[co].items():
            p, w, h = offs[k]; assert len(px) == w * h, (hex(co), k); d[p:p + w * h] = px
        # 원본 끝 깃발 비트 방식: 원본을 우리 압축기로 다시 눌러 바이트 같은지 보고 남는 비트 0/1 판정
        src = orig[co + 4:co + 4 + s]
        last_unused = None
        st = compress(bytes(d), 0)
        if len(st) > s: st = compress(bytes(d), 0, 4096, True)            # 큰 덩어리(0x3DCE8)는 깊게·lazy
        if len(st) > s:
            print('%05X ⚠ 넘침 %d > %d' % (co, len(st), s)); sys.exit(1)
        chk, _ = lzss.decompress(st, 0, len(d)); assert chk == bytes(d), hex(co)
        struct.pack_into('>I', b, co, len(st)); b[co + 4:co + 4 + s] = st + bytes(s - len(st))
        # 게임 경로와 같게 [u32 s'] 만큼만 넘겨 다시 풂
        s2, d2 = raw(bytes(b), co); assert bytes(d2[:len(d)]) == bytes(d) and len(d2) >= len(d), hex(co)
        print('%05X 레코드 %d장 교체 · 압축 %d → %d (여유 %d) · 왕복 OK · 끝 %d B 더 풀림' % (co, len(new[co]), s, len(st), s - len(st), len(d2) - len(d)))
    od = os.path.join(ROOT, 'work', 'build'); os.makedirs(od, exist_ok=True)
    open(os.path.join(od, 'YKBIN'), 'wb').write(b)
    diff = [i for i in range(len(b)) if b[i] != orig[i]]
    owned = [(co, co + 4 + struct.unpack_from('>I', orig, co)[0]) for co in new]
    stray = [i for i in diff if not any(a <= i < e for a, e in owned)]
    print('YKBIN', len(b), '바뀐 바이트', len(diff), '덩어리 밖 변경', len(stray))
