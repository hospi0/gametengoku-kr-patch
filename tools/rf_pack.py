# -*- coding: utf-8 -*-
r"""회상 카드·편 제목·데이터 모드 로딩/끝 재압축·제자리 포장(2026-11-09)
  입력: work/plates/rf.pkl(화 카드, rf_ko) · pic.pkl(편 제목·데이터 모드, pic_ko)
  각 A형 덩어리 = [u32 압축 바이트 수][스트림] → lz_exact.encode_exact 로 «원래 압축 크기와 정확히 같게»(뒤 덩어리 자리·크기 필드 불변)
  · RFPnBIN(1~8): 0x0 편 제목(플레이어) · 0xAD50 화 카드 / RFYnBIN(1~7): 0x0 편 제목(야마다) · 0xC328 화 카드
  · DTLD1LZ 0x0 = 로딩 / DT{EX,FZ,FC,MK,BS,PA}BIN 끝 그림 덩어리(파일마다 오프셋) — DT 는 work/build 의 기존 판(other_pack) 위에 덮음
  python tools/rf_pack.py → work/build/<파일>
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lz_exact import encode_exact
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DTEND = {'DTEXBIN': 0x5C5EC, 'DTFZBIN': 0x2102C, 'DTFCBIN': 0x21F80, 'DTMKBIN': 0x3666C, 'DTBSBIN': 0x24A58, 'DTPABIN': 0x216E4}
CACHE = {}


def put(buf, o, data):
    s = struct.unpack_from('>I', buf, o)[0]
    key = (hash(data), s)
    if key not in CACHE: CACHE[key] = encode_exact(data, s)
    buf[o + 4:o + 4 + s] = CACHE[key]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    rf = pickle.load(open(os.path.join(ROOT, 'work', 'plates', 'rf.pkl'), 'rb'))
    pic = pickle.load(open(os.path.join(ROOT, 'work', 'plates', 'pic.pkl'), 'rb'))
    src = lambda n: bytearray(open(os.path.join(ROOT, 'work', 'files', n), 'rb').read())
    bld = lambda n: os.path.join(ROOT, 'work', 'build', n)
    for n in ['RFP%dBIN' % i for i in range(1, 9)] + ['RFY%dBIN' % i for i in range(1, 8)]:
        b = src(n); L = len(b)
        put(b, 0, pic['편제목_플레이어' if n.startswith('RFP') else '편제목_야마다'])
        o2 = 0xAD50 if n.startswith('RFP') else 0xC328; put(b, o2, rf[(n, o2)])
        assert len(b) == L; open(bld(n), 'wb').write(b); print(n, '완료')
    b = src('DTLD1LZ'); L = len(b); put(b, 0, pic['데이터_로딩']); assert len(b) == L; open(bld('DTLD1LZ'), 'wb').write(b); print('DTLD1LZ 완료')
    for n, o in DTEND.items():
        p = bld(n); b = bytearray(open(p, 'rb').read()) if os.path.exists(p) else src(n); L = len(b)
        orig = src(n); s = struct.unpack_from('>I', orig, o)[0]
        if b[o:o + 4 + s] != orig[o:o + 4 + s]:                          # 이미 넣은 판(빌드 28~)이면 원본 덩어리로 되돌린 뒤 다시
            b[o:o + 4 + s] = orig[o:o + 4 + s]
        put(b, o, pic['데이터_끝']); assert len(b) == L; open(p, 'wb').write(b); print(n, '완료')
