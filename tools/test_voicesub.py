# -*- coding: utf-8 -*-
"""음성 자막 훅 검산 — 스테이트 메모리에 패치 /0 을 올려 흉내기로 돌림(GFS_Load = 자료 파일 → 버퍼 복사 흉내)
   ① 리터럴(XA 3·AIF 1·VBO·GFS_Load) ② lwrap: 서명 없으면 상주 자료 먼저 읽고 원래 GFS_Load(r4~r7 그대로) / 있으면 바로 원래 것
   ③ xwrap: 앞 음성 정지(상태 ≠ 0) → 대화 자막 VRB 로 → 원래 함수 / 표 밖 → cur −1 · awrap 표 밖 → cur 그대로
   ④ 전 음성 프레임마다: 쪽 그림 = ref_render · 색 = ref_pal · DMA 표 끝(지역 좌표+스프라이트+END) · 두 번 안 붙음 · 끝나면 cur −1
   ⑤ 상태 0 → 유예 뒤 끝 ⑥ 좌표 ⑦ 미리보기 work/check/vsub_*.png
   python tools/test_voicesub.py [스테이트이름]"""
import struct, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import sh2sim as S, voicesub as H

DMA_TBL = 0x060F0000
SYS_END = 0x0607F84A


def game_table(m, n=2):
    m.w32(H.DMA_PTR, DMA_TBL)
    for k in range(n):
        p = DMA_TBL + 12 * k
        m.w32(p, 0x1E); m.w32(p + 4, 0x25C00060 + 0x20 * k)
        m.w32(p + 8, (0x8000_0000 | SYS_END) if k == n - 1 else 0x060F53FC)
    for k in range(n, n + 5):
        for j in (0, 4, 8): m.w32(DMA_TBL + 12 * k + j, 0xAAAAAAAA)


STEPS = [0]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    st = sys.argv[1] if len(sys.argv) > 1 else '어레인지모드시작데모'
    mem = os.path.join(ROOT, 'work', 'mem', st)
    data = H.build_data(); idx, bits, advs, aif, xa = data
    z0 = open(os.path.join(ROOT, 'work', '0.bin'), 'rb').read()
    s, sub, lab, lay = H.patch(z0, data)
    m = S.Mem()
    ram = m.add(0x06000000, 0x100000, open(os.path.join(mem, 'WorkRAMH.bin'), 'rb').read())
    m.add(0x05C00000, 0x80000, open(os.path.join(mem, 'VDP1_VRAM.bin'), 'rb').read())
    cram = open(os.path.join(mem, 'CRAM.bin'), 'rb').read(); m.add(0x05F00000, 0x1000, cram)
    m.add(0x05E00000, 0x80000, open(os.path.join(mem, 'VDP2_VRAM.bin'), 'rb').read())   # 글꼴(빌드 8, VRC)
    vreg = m.add(0x05F80000, 0x200, open(os.path.join(mem, 'VDP2_REGS.bin'), 'rb').read())   # 자막 우선순위(PRISB) 쓰기 검산
    ram[0x4000:0x4000 + len(s)] = s
    st_ram = open(os.path.join(mem, 'WorkRAMH.bin'), 'rb').read(); ram[H.TATE - 0x06000000] = st_ram[H.TATE - 0x06000000]   # 세로 깃발(BSS)은 /0 덮어쓰기로 지워지므로 스테이트 값으로
    ok = True; r = lambda a: m.r32(a)
    gfs = []; stops = []; orig = []

    def gfs_load(rr, mm):
        gfs.append(tuple(rr[4:8]))
        if rr[4] == H.SUBFID:
            b = sub[rr[5] * 2048:rr[5] * 2048 + rr[7]]
            for i in range(0, len(b), 4): mm.w32(rr[6] + i, struct.unpack_from('>I', b.ljust(len(b) + 3 & ~3, b'\0'), i)[0])
        rr[0] = rr[7]

    def stop(rr, mm): stops.append(1); mm.w8(H.STAT, 0)
    calls = {H.GFS_LOAD: gfs_load, H.STOP: stop, H.XA_FN: lambda rr, mm: orig.append(('XA', rr[4] & 0xFFFF, rr[5], rr[6], rr[7])),
             H.AIF_FN: lambda rr, mm: orig.append(('AIF', rr[4] & 0xFFFF, rr[5], rr[6], rr[7]))}

    def run(lb, r4, r5=0x2222, r6=0x3333, r7=0x4444):
        S.run(m, lab[lb], regs=[0, 0, 0, 0, r4, r5, r6, r7, 0x5555], calls=calls)

    c0 = all(r(L) == lab['xwrap'] for L in H.XA_LITS) and all(r(L) == lab['awrap'] for L in H.AIF_LITS) and r(H.VBO_LIT) == lab['vbo'] and r(H.LOAD_LIT) == lab['lwrap']         and r(H.END_LIT) == (H.TPL | 0x80000000) and m.r16(H.TPL) == 0x8000 and m.r16(H.TPL + 2) == H.CMDV >> 3
    print('① 리터럴 XA 3·AIF 1·VBO·GFS_Load·END 견본(→ 우리 견본)', c0); ok &= c0
    # ② lwrap
    m.w32(H.VRA, 0); gfs.clear()
    S.run(m, lab['lwrap'], regs=[0, 0, 0, 0, 77, 5, 0x06001000, 0x800], calls={H.GFS_LOAD: gfs_load})
    c2 = gfs == [(H.SUBFID, 0, H.VRA, lay['RES_SIZE']), (H.SUBFID, lay['RES_SIZE'] // 2048, H.VRC, lay['FRES_SIZE']), (77, 5, 0x06001000, 0x800)]         and r(H.VRA) == H.MAGIC and r(H.VRC) == H.MAGIC_F
    gfs.clear(); S.run(m, lab['lwrap'], regs=[0, 0, 0, 0, 78, 6, 0x06001000, 0x800], calls={H.GFS_LOAD: gfs_load})
    c2 &= gfs == [(78, 6, 0x06001000, 0x800)]
    print('② lwrap: 서명 없으면 상주 자료 먼저(%d B)·원래 GFS_Load 인자 그대로 / 있으면 바로' % lay['RES_SIZE'], c2); ok &= c2
    # ③ xwrap / awrap
    xf = xa[0][0]; m.w8(H.STAT, 2); gfs.clear(); stops.clear(); orig.clear()
    run('xwrap', xf)
    c3 = stops == [1] and len(gfs) == 1 and gfs[0][0] == H.SUBFID and gfs[0][2] == H.VRB and orig == [('XA', xf, 0x2222, 0x3333, 0x4444)] \
        and r(H.VAR) == 0 and r(H.VAR + 12) == H.VRB
    print('③ xwrap fid %d → 앞 음성 정지·대화 자막 VRB 로·원래 함수(r4~r7 그대로)' % xf, c3); ok &= c3
    # 표 밖 fid: 전 음성이 표에 들어가 음성 파일로는 못 함 → 음성 아닌 fid(12 AINST.BIN · 11 ABS.TXT)
    run('awrap', 12)
    c3b = r(H.VAR) == 0 and r(H.VAR + 12) == H.VRB and orig[-1][:2] == ('AIF', 12)
    run('xwrap', 11)
    c3b &= r(H.VAR) == 0xFFFFFFFF and orig[-1][:2] == ('XA', 11)
    print('   awrap 표 밖(fid 12) → cur 그대로 · xwrap 표 밖(fid 11) → cur −1', c3b); ok &= c3b
    regs_copy = bytes(ram[H.SH - 0x06000000:H.SH - 0x06000000 + 0x120])
    want_lut = H.ref_pal(regs_copy, cram)
    # ④ 전 음성
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    tot_bad = 0; worst = [0]
    QUICK = os.environ.get('QUICK')                                                       # QUICK=1 → XA 2·AIF 3 만(빠른 검산)
    for kind, lst in (('xwrap', [] if QUICK else xa), ('awrap', aif[:3] if QUICK else aif)):
        for fid, body, pages in lst:
            m.w8(H.STAT, 2 if kind == 'xwrap' else 1)
            run(kind, fid)
            if r(H.VAR) != 0: print('  ✗ 시작 못함', fid); tot_bad += 1; continue
            m.w8(H.STAT, 2 if kind == 'xwrap' else 1)
            bad = 0; seen = []; lag = 0; maxlag = 0
            ptrs = []; pp = r(H.VAR + 12) + 2
            for _ in pages: ptrs.append(pp); pp += m.r16(pp)
            for _ in range(pages[-1][1] + 3):
                game_table(m)
                n0 = [0]
                _, nst = S.run(m, lab['vbo'], calls={H.VBO_ORIG: lambda rr, mm: None}); STEPS[0] = max(STEPS[0], nst)
                fr = S.s32(r(H.VAR + 4))
                cur = next((k for k, p in enumerate(pages) if p[0] <= fr < p[1]), None)
                vc = bytes(m.r8(0x25C00000 + H.CMDV + i) for i in range(96))
                att = m.r16(H.TPL) == 0x5000 and vc == bytes(m.r8(H.LOCC + i) for i in range(96))
                if cur is None:
                    if att: bad += 1
                    continue
                shown = r(H.VAR + 8)
                if shown != ptrs[cur]:
                    lag += 1; maxlag = max(maxlag, lag); continue                          # 아직 그리는 중(앞 쪽 또는 없음)
                lag = 0
                if not att: bad += 1; continue
                if cur not in seen:
                    seen.append(cur)
                    tex = bytes(m.r8(H.TEX + i) for i in range(H.BMPSZ))
                    if tex != H.ref_render(pages[cur], bits, advs): print('  ✗ 그림 다름', fid, cur); bad += 1
                    lut = [m.r16(H.LUT + 2 * i) for i in range(4)]
                    if lut != want_lut: print('  ✗ 색 다름', lut, want_lut); bad += 1
                    save(tex, lut, cram, os.path.join(ROOT, 'work', 'check', 'vsub_%d_%02d.png' % (fid, cur)))
            glyphs = max(sum(len(gl) for _, _, gl in p[6]) for p in pages)
            if maxlag > (glyphs + H.GPF - 1) // H.GPF + 2: print('  ✗ 늦음', fid, maxlag, glyphs); bad += 1
            worst[0] = max(worst[0], maxlag)
            if not (bad == 0 and len(seen) == len(pages) and r(H.VAR) == 0xFFFFFFFF): print('  ✗ fid', fid, bad, len(seen), len(pages)); tot_bad += 1
    c4 = tot_bad == 0
    pv = struct.unpack_from('>H', ram, H.SH + 0xF2 - 0x06000000)[0]; rv = struct.unpack_from('>H', vreg, 0xF2)[0]
    c4p = (pv >> 8) & 7 == 7 and rv == pv
    print('    VBO 한 프레임 최대 명령 수 %d (약 %.2f ms @28.6MHz)' % (STEPS[0], STEPS[0] / 28636.0))
    print('④-1 자막 PR 레지스터 3 우선순위 7(SGL 사본 %04X · VDP2 %04X)' % (pv, rv), c4p); ok &= c4p
    print('④ 전 음성 XA %d·AIF %d 쪽 그림·색·견본 켜짐(쪽 사이 꺼짐)·끝 (쪽 바뀐 뒤 최대 %d 프레임 늦게 나타남, 프레임당 %d 자)' % (len(xa), len(aif), worst[0], H.GPF), c4); ok &= c4
    # ⑤
    run('xwrap', xf); m.w8(H.STAT, 0)
    for _ in range(H.KILL_GRACE + 2):
        game_table(m); S.run(m, lab['vbo'], calls={H.VBO_ORIG: lambda rr, mm: None})
    c5 = r(H.VAR) == 0xFFFFFFFF and m.r16(H.TPL) == 0x8000
    print('⑤ 재생 상태 0 → %d 프레임 뒤 끝·견본 END' % H.KILL_GRACE, c5); ok &= c5
    tv = m.r16(H.SH); x0, y0 = m.r16(H.SPR + 12), m.r16(H.SPR + 14)
    sg = lambda a: (lambda v: v - 0x10000 if v & 0x8000 else v)(m.r16(a))
    if m.r8(H.TATE) == 0:                                                                    # 세로 모드: 변형 스프라이트 90°(빌드 19)
        XL = (16 if tv & 1 else 0) + H.TATE_X; Y0 = (224 + 16 * (tv >> 4 & 3) - H.W_) // 2
        want = [XL + H.H_ - 1, Y0, XL + H.H_ - 1, Y0 + H.W_ - 1, XL, Y0 + H.W_ - 1, XL, Y0]
        got = [sg(H.SPR + 12 + 2 * i) for i in range(8)]
        c6 = m.r16(H.SPR) == 2 and got == want
        print('⑥ 세로 모드 TVMD %04X → 변형 스프라이트 꼭짓점 %s' % (tv, got), c6); ok &= c6
    else:
        c6 = m.r16(H.SPR) == 0 and (x0, y0) == ((16 if tv & 1 else 0), 224 + 16 * (tv >> 4 & 3) - H.H_ - 6)
        print('⑥ 좌표 TVMD %04X → (%d, %d)' % (tv, x0, y0), c6); ok &= c6
    print('전체', '통과' if ok else '실패')


def save(tex, lut, cram, path):
    from PIL import Image
    def rgb(v):
        if v == 0: return (40, 60, 80)
        c = struct.unpack_from('>H', cram, 2 * (v & 0x7FF))[0]
        return ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    col = [rgb(lut[i]) for i in range(4)]
    im = Image.new('RGB', (H.W_, H.H_))
    for y in range(H.H_):
        for x in range(0, H.W_, 2):
            b = tex[y * H.ROWB + x // 2]; im.putpixel((x, y), col[b >> 4]); im.putpixel((x + 1, y), col[b & 15])
    im.resize((H.W_ * 3, H.H_ * 3), Image.NEAREST).save(path)


if __name__ == '__main__':
    main()
