# -*- coding: utf-8 -*-
r"""게임 천국 디스크 빌드(2026-11-08) — 원본 트랙 01 사본에 자막 훅 /0 을 넣는다.
  · /0(LBA 52) 을 595,088 B → 훅 블록까지 늘림(최대 472 섹터 = 다음 파일 GENESIS3.CHR LBA 524 앞까지)
  · 그 자리의 파일 9개(STAND.CHR~MOMOB2.CHR, LBA 343~523)는 트랙 1 끝 빈 섹터(71081~)로 «고정 슬롯» 이동 — 게임은 디렉터리 순번(fid)으로 부르므로 번호 불변
  · 자막 자료 파일 = ABS.TXT 레코드(fid 11, 게임이 안 읽는 설명문)를 옮긴 파일들 뒤 빈 섹터로 돌림
  · 루트 디렉터리 레코드(LBA·크기 양쪽 엔디언) 갱신, 바꾼 섹터 EDC/ECC 재계산, 되읽어 검산
  · 트랙 02~12·cue 는 원본 그대로(설치는 트랙 01 만 덮어씀)
  python tools/discbuild.py            → 미리보기(자리만)
  python tools/discbuild.py --write    → work/disc/Track01.bin  (⛔하스피 허락 받고)
  python tools/discbuild.py --install  → F:\hospi\roms\ss roms\<게임 폴더>\ 트랙 01 덮어쓰기(⛔허락)"""
import hashlib, os, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from cdrom_ecc import recalc_sector
import voicesub

NAME = 'Game Tengoku - The Game Paradise! (Japan)'
SRC = os.path.join(r'C:\claude\roms\ss\Game Tengoku - The Game Paradise (Japan)', NAME + ' (Track 01).bin')
OUT = os.path.join(ROOT, 'work', 'disc', 'Track01.bin')
F_DIR = r'F:\hospi\roms\ss roms'
EXE_LBA, EXE_MAX = 52, 524 - 52
MOVE = ['STAND.CHR', 'ITEM.COL', 'EXERION.CHR', 'PUPERA.CHR', 'ZDYNE.CHR', 'PIG.CHR', 'MOMOKO.CHR', 'MOMOB1.CHR', 'MOMOB2.CHR']
END_SLOT = 71081; TRACK1_SECS = 71381
# 같은 크기 파일 제자리 교체(2026-11-09 빌드 13~): 메뉴 그림 YKBIN(tools/ykbin_pack.py → work/build/YKBIN)
REPLACE = {n: os.path.join(ROOT, 'work', 'build', n) for n in
           ['YKBIN',                                                     # 메뉴(tools/ykbin_pack.py)
            'MN5BIN', 'DTEXBIN', 'DTFZBIN', 'DTFCBIN', 'DTMKBIN', 'DTBSBIN', 'DTPABIN',
            'BG_ETCA.BIN', 'BG_ETCAT.BIN', 'STCA.BIN', 'STCX.BIN', 'STC.BIN', 'STCONM2.BIN',   # STC = 세로 스테이지 클리어 입체(stc_ko, 빌드 31)
            'MN2LZ', 'MN4BIN', 'ENDY01.BIN', 'ENDY03.BIN', 'ENDT01.BIN', 'ENDT03.BIN',
            'OPENING.BIN', 'OPENING2.BIN', 'PROLOG.BIN',
            'MN3BIN'] + ['LOAD%02d.CHR' % i for i in range(20, 29)] + ['KASI.LZ', 'STCONS.B00', 'STCONDQ1.BIN', 'STCONDQ2.BIN', 'BGSTCONS.BIN', 'RANKA.BIN', 'OVER.BIN', 'OVERX.BIN', 'DTLD1LZ', 'NAMEA.BIN', 'BACKRAM.BIN', 'BACK1.BIN'] + ['RFP%dBIN' % i for i in range(1, 9)] + ['RFY%dBIN' % i for i in range(1, 8)]}   # 빌드 28: 게임오버(over_ko)·회상 카드/편 제목·데이터 모드 로딩/끝(rf_ko·pic_ko → rf_pack)   # 빌드 24: 로딩 일본어 줄(stcons_ko)·RPG 창(rpg_ko)   # KASI.LZ = 노래방 가사 글자(kasi_ko), 빌드 21   # 로딩 «나우 로~딩...»(loading_ko), 2026-11-09 빌드 20   # 아케이드 세로 선택 화면(arcade_tate_ko), 2026-11-09 빌드 19   # 오프닝 성우 이름(opening_ko: 그림 + 배치표 두 벌), 2026-11-09 빌드 17   # 아케이드 선택(arcade_ko·arcade2_ko)·엔딩(ending_ko), 2026-11-09 빌드 16   # 게임 중 UI·세로 화면·스테이지 클리어(tools/etca_ko·stca_ko·stcx_ko → work/build, 2026-11-09 빌드 15)   # 어레인지 선택·데이터 모드 상세(tools/other_pack.py, 2026-11-09 빌드 14)


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''): h.update(c)
    return h.hexdigest()


def rd(f, lba, n):
    out = bytearray()
    for k in range(n):
        f.seek((lba + k) * 2352 + 16); out += f.read(2048)
    return bytes(out)


def root_records(f):
    pvd = rd(f, 16, 1); assert pvd[1:6] == b'CD001'
    rl, rs = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]
    d = bytearray(rd(f, rl, (rs + 2047) // 2048)); recs = {}; i = 0
    while i < len(d):
        ln = d[i]
        if ln == 0: i = (i // 2048 + 1) * 2048; continue
        nl = d[i + 32]; nm = d[i + 33:i + 33 + nl].split(b';')[0].decode('latin1')
        recs[nm] = (i, struct.unpack_from('<I', d, i + 2)[0], struct.unpack_from('<I', d, i + 10)[0]); i += ln
    return rl, d, recs


def plan(f):
    rl, d, recs = root_records(f)
    s, sub, lab, lay = voicesub.patch(rd(f, recs['0'][1], (recs['0'][2] + 2047) // 2048)[:recs['0'][2]])
    kp = os.path.join(ROOT, 'work', 'plates', 'kasi.pkl')                    # 노래방 가사 순서표(kasi_ko, 빌드 21~)
    if os.path.exists(kp):
        import pickle; k = pickle.load(open(kp, 'rb')); s = bytearray(s)
        assert bytes(s[0x25688:0x25688 + 208]) == k['orig'], '/0 가사 순서표 자리 불일치'
        s[0x25688:0x25688 + 208] = k['seq']; s = bytes(s)
    n = (len(s) + 2047) // 2048
    assert n <= EXE_MAX, ('/0 이 다음 파일을 덮음', n, EXE_MAX)
    moves = []; p = END_SLOT
    for nm in MOVE:
        _, lba, size = recs[nm]; k = (size + 2047) // 2048
        assert EXE_LBA < lba < EXE_LBA + EXE_MAX
        moves.append((nm, lba, size, p)); p += k
    sub_lba = p; p += len(sub) // 2048
    assert p <= TRACK1_SECS, ('트랙 1 끝을 넘음', p)
    # /0 이 덮는 범위 안의 파일은 모두 옮겨져야 함
    for nm, (_, lba, size) in recs.items():
        if nm not in ('0', '.', '..') and EXE_LBA < lba < EXE_LBA + n: assert nm in MOVE, ('안 옮긴 파일이 덮임', nm)
    return rl, d, recs, s, n, moves, sub, sub_lba


def write_sector(g, lba, data2048):
    g.seek(lba * 2352); sec = bytearray(g.read(2352))
    assert sec[15] == 1, ('MODE1 아님', lba)
    sec[16:2064] = data2048.ljust(2048, b'\0'); g.seek(lba * 2352); g.write(recalc_sector(bytes(sec)))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    write = '--write' in sys.argv; install = '--install' in sys.argv
    with open(SRC, 'rb') as f:
        rl, d, recs, s, n, moves, sub, sub_lba = plan(f)
        print('/0 %d B → %d 섹터(LBA %d~%d, 한도 %d)' % (len(s), n, EXE_LBA, EXE_LBA + n - 1, EXE_MAX))
        for nm, lba, size, to in moves: print('  옮김 %-12s %6d → %6d (%d 섹터)' % (nm, lba, to, (size + 2047) // 2048))
        print('  자막 자료(ABS.TXT 자리) %d B → LBA %d~%d (트랙 1 끝 %d)' % (len(sub), sub_lba, sub_lba + len(sub) // 2048 - 1, TRACK1_SECS - 1))
        blobs = {nm: rd(f, lba, (size + 2047) // 2048)[:size] for nm, lba, size, to in moves}
    if not (write or install): print('미리보기만(--write 로 쓰기)'); return
    if write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True); shutil.copyfile(SRC, OUT)
        with open(OUT, 'r+b') as g:
            for nm, lba, size, to in moves:
                b = blobs[nm]
                for k in range(0, len(b), 2048): write_sector(g, to + k // 2048, b[k:k + 2048])
                o = recs[nm][0]; struct.pack_into('<I', d, o + 2, to); struct.pack_into('>I', d, o + 6, to)
            for k in range(n): write_sector(g, EXE_LBA + k, s[2048 * k:2048 * (k + 1)])
            for k in range(len(sub) // 2048): write_sector(g, sub_lba + k, sub[2048 * k:2048 * (k + 1)])
            for nm, src in REPLACE.items():                              # 같은 크기 → 같은 LBA 에 덮어씀(레코드 불변)
                _, lba, size = recs[nm]; nb = open(src, 'rb').read(); assert len(nb) == size, ('크기 다름', nm, len(nb), size)
                assert nm not in MOVE and not (EXE_LBA <= lba < EXE_LBA + n), ('교체 파일 자리 겹침', nm)
                for k in range(0, size, 2048): write_sector(g, lba + k // 2048, nb[k:k + 2048])
                print('  교체 %s LBA %d %d B' % (nm, lba, size))
            o = recs['ABS.TXT'][0]
            for off, v in ((2, sub_lba), (10, len(sub))): struct.pack_into('<I', d, o + off, v); struct.pack_into('>I', d, o + off + 4, v)
            o = recs['0'][0]; struct.pack_into('<I', d, o + 10, len(s)); struct.pack_into('>I', d, o + 14, len(s))
            for k in range(len(d) // 2048): write_sector(g, rl + k, bytes(d[2048 * k:2048 * (k + 1)]))
        # 되읽기 검산
        with open(OUT, 'rb') as g:
            _, _, r2 = root_records(g)
            assert r2['0'][2] == len(s) and rd(g, r2['0'][1], n)[:len(s)] == s, '/0 되읽기'
            assert r2['ABS.TXT'][1:] == (sub_lba, len(sub)) and rd(g, sub_lba, len(sub) // 2048) == sub, '자료 되읽기'
            for nm, src in REPLACE.items():
                _, lba, size = r2[nm]; assert rd(g, lba, (size + 2047) // 2048)[:size] == open(src, 'rb').read(), ('교체 되읽기', nm)
            for nm, lba, size, to in moves: assert r2[nm][1] == to and rd(g, to, (size + 2047) // 2048)[:size] == blobs[nm], ('되읽기', nm)
            with open(SRC, 'rb') as f0:
                for nm, (o, lba, size) in r2.items():
                    if nm in ('0', '.', '..', 'ABS.TXT') or nm in MOVE: continue
                    assert (lba, size) == (recs[nm][1], recs[nm][2]), ('다른 파일 레코드 바뀜', nm)
        print('완료', OUT, md5(OUT))
    if install:
        dst = None
        for dn in os.listdir(F_DIR):
            p = os.path.join(F_DIR, dn, NAME + ' (Track 01).bin')
            if os.path.exists(p): dst = p
        assert dst, 'F: 에 원래 트랙 01 없음'
        shutil.copyfile(OUT, dst); print('설치', dst, md5(dst))


if __name__ == '__main__':
    main()
