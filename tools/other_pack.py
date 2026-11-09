# -*- coding: utf-8 -*-
r"""YKBIN 밖 그림 파일 재압축(2026-11-09) — 덩어리 하나를 «원래 자리·원래 압축 크기 안»에 다시 씀(ykbin_pack.compress 재사용)
  MN5BIN 0x39938(어레인지 모드 선택, work/plates/mn5.pkl) · DT{EX,FZ,FC,MK,BS,PA}BIN 0x0(데이터 모드 상세, work/plates/dt.pkl)
  python tools/other_pack.py → work/build/<파일> + 왕복 검산 · 덩어리 밖 변경 0 검사
"""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss
from ykbin_pack import compress, raw, recs_offsets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lzss.INIT = 0
PL = lambda n: pickle.load(open(os.path.join(ROOT, 'work', 'plates', n), 'rb'))


CUR = {}                                                                  # 한 파일에 덩어리 여럿 고칠 때 앞 결과 위에 이어서(빌드 17: MN5BIN 0x0 + 0x39938)


def pack(name, co, start, new):
    src = os.path.join(ROOT, 'work', 'files', name)
    b = bytearray(CUR.get(name) or open(src, 'rb').read()); orig = bytes(b)
    s, d = raw(orig, co)
    offs = recs_offsets(d, start, max(new) + 1)
    for k, px in new.items():
        p, w, h = offs[k]; assert len(px) == w * h, (name, k); d[p:p + w * h] = px
    st = compress(bytes(d), 0)
    if len(st) > s: st = compress(bytes(d), 0, 4096, True)
    assert len(st) <= s, ('%s 넘침 %d > %d' % (name, len(st), s))
    chk, _ = lzss.decompress(st, 0, len(d)); assert chk == bytes(d), name
    struct.pack_into('>I', b, co, len(st)); b[co + 4:co + 4 + s] = st + bytes(s - len(st))
    s2, d2 = raw(bytes(b), co); assert bytes(d2[:len(d)]) == bytes(d), name
    stray = [i for i in range(len(b)) if b[i] != orig[i] and not (co <= i < co + 4 + s)]
    assert not stray and len(b) == len(orig), (name, '덩어리 밖 변경', len(stray))
    od = os.path.join(ROOT, 'work', 'build'); os.makedirs(od, exist_ok=True)
    open(os.path.join(od, name), 'wb').write(b); CUR[name] = bytes(b)
    print('%s %05X 레코드 %d장 · 압축 %d → %d (여유 %d) · 왕복 OK · 덩어리 밖 변경 0' % (name, co, len(new), s, len(st), s - len(st)))


def pack4(name, co, new):
    """4비트 레코드 덩어리([u32 개수]+[w][h][u32 0][w*h/2])"""
    src = os.path.join(ROOT, 'work', 'files', name)
    b = bytearray(CUR.get(name) or open(src, 'rb').read()); orig = bytes(b)
    s, d = raw(orig, co)
    n = struct.unpack_from('>I', d, 0)[0]; p = 4; offs = []
    for _ in range(n):
        w, h = struct.unpack_from('>HH', d, p); offs.append((p + 8, w, h)); p += 8 + w * h // 2
    for k, px in new.items():
        o, w, h = offs[k]; assert len(px) == w * h // 2; d[o:o + len(px)] = px
    st = compress(bytes(d), 0)
    if len(st) > s: st = compress(bytes(d), 0, 4096, True)
    assert len(st) <= s, (name, len(st), s)
    chk, _ = lzss.decompress(st, 0, len(d)); assert chk == bytes(d)
    struct.pack_into('>I', b, co, len(st)); b[co + 4:co + 4 + s] = st + bytes(s - len(st))
    s2, d2 = raw(bytes(b), co); assert bytes(d2[:len(d)]) == bytes(d)
    assert not [i for i in range(len(b)) if b[i] != orig[i] and not (co <= i < co + 4 + s)]
    open(os.path.join(ROOT, 'work', 'build', name), 'wb').write(b); CUR[name] = bytes(b)
    print('%s %05X 레코드 %d장 · 압축 %d → %d · 왕복 OK · 덩어리 밖 변경 0' % (name, co, len(new), s, len(st)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    pack('MN5BIN', 0x39938, 0x600, PL('mn5.pkl'))
    pack('MN5BIN', 0x0, 0x2E00, PL('mn5_0.pkl'))                            # 어레인지 플레이어 셀렉트 제목·버튼(빌드 17)
    # 아케이드 선택(MN2LZ 덩어리 하나 = 0x0, [색표 0x600]+레코드)
    a = {**PL('arcade.pkl'), **PL('arcade2.pkl')}
    pack('MN2LZ', 0x0, 0x600, {k: v for (f, k), v in a.items() if f == 'MN2'})
    # 오프닝 성우 이름(OPENING.BIN 0x4F80C, [u32 개수]+레코드 [w][h][u32 0][4비트])
    op = PL('opening.pkl'); pack4('OPENING.BIN', 0x4F80C, op['recs'])
    cr = PL('credit.pkl'); pack4('OPENING.BIN', 0x1B05C, cr['recs'])        # 오프닝 크레딧 카드(credit_ko, 빌드 20)
    for tb in ('OPENING2.BIN', 'PROLOG.BIN'):                                # 배치표 = 성우 이름 표 위에 크레딧 표 바뀐 바이트만 겹침
        org = open(os.path.join(ROOT, 'work', 'files', tb), 'rb').read(); t = bytearray(op[tb])
        dif = [i for i in range(len(org)) if cr[tb][i] != org[i]]
        assert not [i for i in dif if op[tb][i] != org[i]], tb + ' 두 표가 같은 바이트를 고침'
        for i in dif: t[i] = cr[tb][i]
        open(os.path.join(ROOT, 'work', 'build', tb), 'wb').write(t); print(tb, '성우', sum(a != b for a, b in zip(op[tb], org)), '+ 크레딧', len(dif), '바이트')
    dt = PL('dt.pkl')
    for g in ('EX', 'FZ', 'FC', 'MK', 'BS', 'PA'):
        pack('DT%sBIN' % g, 0, 0x600, {k: v for (gg, k), v in dt.items() if gg == g})
