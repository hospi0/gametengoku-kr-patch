# -*- coding: utf-8 -*-
r"""LZSS 압축 결과를 «정확히 원하는 바이트 수»로 (2026-11-09)
  게임 A형 덩어리 = [u32 압축 바이트 수][스트림]. RFPnBIN 둘째 덩어리가 0xAD50 고정 자리라 첫째 덩어리는 원래 압축 크기와 똑같아야 안전.
  방법: lzss_opt.encode_opt(최소) → 토큰으로 풀고 → 일치 참조 끝 1글자를 글자 그대로로 떼어(+1바이트) 목표 크기까지 늘림.
  플래그 바이트(토큰 8개마다 1) 때문에 +2 로 건너뛰면 길이 3 참조를 글자 3개로 바꾸는 식으로 맞춤.
  encode_exact(data, target) → 스트림(len == target) · 되풀어 data 와 같은지 검산
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
from lzss_opt import encode_opt


def tokens(stream, data):
    """스트림 → [('L', byte) | ('M', off, len)] (data 로 참조 길이 검산)"""
    out = []; p = 0; n = 0
    while n < len(data):
        fl = stream[p]; p += 1
        for bit in range(8):
            if n >= len(data): break
            if fl >> bit & 1: out.append(('L', stream[p])); p += 1; n += 1
            else:
                b0, b1 = stream[p], stream[p + 1]; p += 2
                L = (b1 & 15) + 3; out.append(('M', ((b1 >> 4) << 8) | b0, L)); n += L
    return out


def emit(tk):
    out = bytearray()
    for i in range(0, len(tk), 8):
        fp = len(out); out.append(0); fl = 0
        for bit, t in enumerate(tk[i:i + 8]):
            if t[0] == 'L': fl |= 1 << bit; out.append(t[1])
            else: off, L = t[1], t[2]; out.append(off & 0xFF); out.append(((off >> 4) & 0xF0) | (L - 3))
        out[fp] = fl
    return bytes(out)


def size_of(nt, nl, nm):
    return (nt + 7) // 8 + nl + 2 * nm


def encode_exact(data, target):
    data = bytes(data); s = encode_opt(data)
    if len(s) > target: raise ValueError('최소 압축 %d > 목표 %d' % (len(s), target))
    tk = tokens(s, data)
    # 출력 위치 → 각 토큰 시작 위치(글자 값을 알기 위해)
    pos = []; n = 0
    for t in tk: pos.append(n); n += 1 if t[0] == 'L' else t[2]
    def attempt(order, prefer3):
        new = list(tk); npos = list(pos)
        nt = len(new); nl = sum(1 for t in new if t[0] == 'L'); nm = nt - nl; cur = size_of(nt, nl, nm)
        changed = True
        while cur < target and changed:
            changed = False
            idxs = range(len(new) - 1, -1, -1) if order == 0 else range(len(new))
            for i in list(idxs):
                if cur >= target: break
                if i >= len(new): continue
                t = new[i]
                if t[0] != 'M': continue
                off, L = t[1], t[2]; p0 = npos[i]
                ops = []
                if L >= 4: ops.append('a')
                if L == 3: ops.append('b')
                if prefer3: ops.reverse()
                for op in ops:
                    if op == 'a':
                        d = size_of(nt + 1, nl + 1, nm) - cur
                        if cur + d <= target:
                            new[i] = ('M', off, L - 1); new.insert(i + 1, ('L', data[p0 + L - 1])); npos.insert(i + 1, p0 + L - 1)
                            nt += 1; nl += 1; cur += d; changed = True; break
                    else:
                        d = size_of(nt + 2, nl + 3, nm - 1) - cur
                        if cur + d <= target:
                            new[i:i + 1] = [('L', data[p0]), ('L', data[p0 + 1]), ('L', data[p0 + 2])]
                            npos[i:i + 1] = [p0, p0 + 1, p0 + 2]; nt += 2; nl += 3; nm -= 1; cur += d; changed = True; break
        return new, cur
    for order in (0, 1):
        for prefer3 in (False, True):
            new, cur = attempt(order, prefer3)
            if cur == target: break
        if cur == target: break
    out = emit(new)
    if len(out) != target: raise ValueError('정확히 못 맞춤 %d ≠ %d' % (len(out), target))
    old = lzss.INIT; lzss.INIT = 0
    try: back = lzss.decompress(out, 0, len(data))[0]
    finally: lzss.INIT = old
    assert bytes(back) == data, '되풀이 불일치'
    return out
