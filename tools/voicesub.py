# -*- coding: utf-8 -*-
r"""게임 천국 음성 자막 훅(2026-11-08, 모노모노 tools/voicesub.py 를 옮김 — 같은 SGL 2.11)
  ■ 게임(/0, 램 0x06004000, BSS 0x06095490~0x060E40E8 — 시작 루프 0x060614A8 가 지움)
    · XA 대화 재생 시작 0x0603DA6C(r4 = fid) — 리터럴 3곳 · AIF 재생 시작 0x0603D83C(r4 = fid) — 리터럴 1곳(큐 꺼냄 0x0603DF28)
    · 재생 상태 바이트 0x060CA2C4(0 없음 · 1 AIF · 2 XA)
    · SGL VBlank-OUT 처리기 0x0607E67A(등록 리터럴 0x0607E88C) · 간접 DMA 표 포인터 0x060953F0(→ 0x060F0000, 항목 12 B {0x1E, VDP1 쓸 곳, 읽을 곳|끝 비트31})
    · SGL VDP2 레지스터 사본 0x060FFCC0(SPCTL +0xE0 · CRAOFB +0xE6 · RAMCTL +0x0E · PRISA~D +0xF0)
  ■ 훅: XA 리터럴 → xwrap(fid 가 표에 있으면 cur = 번호·프레임 0, 없으면 cur = −1) → 원래 함수
        AIF 리터럴 → awrap(표에 있을 때만 cur 바꿈) → 원래 함수
        VBO 리터럴 → vbo: sub(프레임 +1 · 상태 0 이고 30 프레임 지나면 끝 · 쪽 찾아 그림 · DMA 표 끝에 우리 스프라이트+END) → 원래 처리기
  ■ 색: 이 게임은 모든 장면이 SPCTL SPCLMD=0(스프라이트 = 팔레트 전용) — RGB 를 넣으면 안 보임.
        쪽을 새로 그릴 때 pal: SPCTL 타입 → PR 비트 자리·DC 폭, PRIS 중 가장 높은 우선순위 레지스터 번호, CRAM(스프라이트 색 오프셋 반영)에서
        가장 어두운 칸·가장 밝은 칸 → 색 참조표 {0 투명, 1 띠 = 어둠, 2 글자 = 밝음, 3 그림자 = 어둠}
  ■ 그림: VDP1 VRAM 0x28000(320×40 4비트) — 29 장면 모두 불변인 SGL 명령 여분 구역 0xE200~0x2C000
  ■ 자리: BLOCK 0x060E4100(BSS 끝 0x060E40E8 ~ 0x060E8000, 참조 0·전 스테이트 0) → /0 을 0 으로 늘려 붙임(디스크에서 뒤 파일 9개를 트랙 1 끝으로)
  ■ 자료: work/voice/sub_poc.tsv(파일·시작·끝·한글) — 쪽 = 두 줄(폭 ≤ 300 px)
  python tools/voicesub.py   → 검산은 tools/test_voicesub.py"""
import csv, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from sh2asm import A

BIN_BASE = 0x06004000
BLOCK = 0x060E4100; BLOCK_END = 0x060E8000
VAR = BLOCK + 0x10                                  # 0 cur · 4 frame · 8 shown · 12 쪽 목록 주소
LYR = BLOCK + 0xBF8                                 # 가사 재생 중 깃발(1 = 음성 상태 바이트로 안 끔) — XA 표 뒤 빈칸
LOCC = BLOCK + 0x20                                 # 지역 좌표 (0,0) 명령 — 게임이 장면마다 원점을 바꿈(1차 실기: 자막이 왼쪽 위로 밀려 잘림)
SPR = BLOCK + 0x40; ENDC = BLOCK + 0x60
TATE = 0x060D72C8; TATE_X = 4                      # 세로 모드 깃발(바이트 0 = 세로) · 세로 자막 화면 왼쪽 여백(빌드 19, 하스피 «세로모드에서 자막 세로로 화면 왼쪽»)
CODE = BLOCK + 0x80
XA_FN = 0x0603DA6C; XA_LITS = (0x06040148, 0x06049694, 0x0604EDDC)
AIF_FN = 0x0603D83C; AIF_LITS = (0x0603DFA8,)
STAT = 0x060CA2C4
CDC_W = 0x060637D8; CDC_LIT = 0x06063798            # CD 명령 CR1~4 쓰기(r4 = 명령 배열) — 부르는 리터럴 1곳(명령 실행기 0x060636E4 안)
LYR_FID = 0xFFF4                                    # 가사 = 상주 AIF 표의 마지막 항목(가짜 fid — 게임 fid 와 안 겹침)
T04_FAD = (145450 + 150, 154901 + 150)              # 트랙 4 FAD 범위(인덱스 0 부터) — 큐 시트 트랙 길이로 셈
LYR_DELAY = 15                                      # CD 탐색 지연 보정(프레임) — 실기로 맞출 것
LYR_TSV = 'op_lyrics_ko.tsv'                        # 오프닝 노래 가사(work/voice)
DMA_PTR = 0x060953F0
VBO_ORIG = 0x0607E67A; VBO_LIT = 0x0607E88C
END_LIT = 0x0607F864; END_ORIG = 0x8607F84A          # SGL 이 DMA 표 마지막 항목에 넣는 END 견본(비트31 = 마지막) — 빌드 4 깜빡임: 표를 VBO 뒤에 만드는 프레임엔 우리 덧붙임이 빠짐
# ── VDP1 안전 구역 0xE200~0x19F00 (빌드 8): 그림 0xE200 · 색표 0xFB00 · 명령 0xFB20 · XA 쪽 0xFC00 · AIF 상주 0x10C00
#    ⚠0x19F20~0x2A000 은 어레인지 시작 장면에서 게임 텍스처(빌드 7 글자 깨짐·그림/명령도 겹쳤음)
CMDV = 0xFB20                                       # VDP1 VRAM: 지역 좌표·스프라이트·END 명령(32 B × 3)
SH = 0x060FFCC0
CRAM = 0x25F00000
W_, H_ = 320, 40; ROWB = W_ // 2; BMPSZ = ROWB * H_
TEXO = 0xE200; LUTO = TEXO + BMPSZ                  # 0xE200 + 0x1900 = 0xFB00(색표 32 B → 0xFB20 = CMDV)
TEX = 0x25C00000 + TEXO; LUT = 0x25C00000 + LUTO
GROWS = 12                                          # 글꼴 칸 줄 수(갈무리9 잉크 9 + 위아래 여백) — 하스피 2026-11-08 «갈무리 9»
FROW0, FROWS = 1, 10                                # 글꼴 칸 12줄 중 1~10줄만 저장(0·11 줄은 전 글자 비어 있음) — 디스크·VRAM 20 B/자
FONT_B = FROWS + 2                                  # 12 B/자(빌드 22): 줄마다 1 B(0~7열) + 9번째 열 비트 u16(bit15 = 첫 줄) — 잉크는 9열뿐
XA, YA = 0, 224 - H_ - 6                            # 절대 좌표(지역 좌표 0,0 명령 뒤) — 실행 중 TVMD 로 다시 씀
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf'
NANUM = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
MAXW = 208; FPS = 60                                 # 게임 중 가로 화면은 VDP2 스프라이트 창 x 48~271(224 px) 밖을 지움(빌드 6 좌우 잘림)
SUB_TSV = 'sub_all.tsv'                               # 자막 자료(tools/mk_subdata.py 가 ko.tsv 로 만듦 · 시험판 sub_poc.tsv)
LY = (6, 20)                                        # 두 줄 y(한 줄이면 아래 줄 자리)
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) (?! )')    # 문장부호 뒤 공백 1칸 지움(전 프로젝트 규칙)
# 스프라이트 타입(팔레트 형식) → (PR 비트 시작, PR 개수, DC 마스크)
TYPES = [(14, 4, 0x7FF), (13, 8, 0x7FF), (14, 2, 0x7FF), (13, 4, 0x7FF), (13, 4, 0x3FF), (12, 8, 0x7FF), (12, 8, 0x3FF), (12, 8, 0x1FF)]
KILL_GRACE = 30                                     # 재생 시작 뒤 이 프레임 동안은 상태 0 이어도 안 끔
# 자막 자료 파일(디스크: ABS.TXT 레코드를 트랙 1 끝 빈 섹터로 돌림 — 게임이 안 읽는 설명문, fid 11)
SUBFID = 11
GFS_LOAD = 0x06063FC4; LOAD_LIT = 0x060043C0          # GFS_Load(fid, 섹터, 버퍼, 크기) — 게임 적재 함수가 부르는 리터럴 1곳
STOP = 0x0603E3B8                                   # 재생 정지(XA 함수가 시작 전에 부르는 것)
VRB = 0x25C0FC00; VRB_MAX = 0x1000                  # XA 대화 자막 쪽(재생 때마다 읽음)
VRA = 0x25C10C00; VRA_MAX = 0x9300                  # 상주 AIF 쪽 자료(→ 0x19F00)
VRC = 0x060DFC00; VRC_MAX = 0x43C0                  # 상주 글꼴·폭(전 글자) — 작업 RAM-H BSS 안 0x060DFAA9~0x060E3FC0(스테이트 59장 전부 0)
                                                    # ★빌드 22: 옛 자리 VDP2 0x3AB00 은 노래방 스테이지 NBG1 비트맵(0x20000~0x3FFFF) 아래 줄 → 글꼴이 노이즈로 보이고 보스 격파 때 게임이 지워 자막 깨짐(하스피)
MAGIC_F = 0x47544654                                # 'GTFT' (VRC 서명)
MAGIC = 0x47545342                                  # 'GTSB'


class S(A):
    """A + 중간 리터럴 풀(ltorg) — 마리카 subhook.S"""
    def __init__(s, base): super().__init__(base); s.pools = []; s.cur = []
    def ld(s, rn, val): s.fix.append((len(s.c), 'lit', (rn, val, len(s.pools)))); s.c.append(0); s.cur.append(val)
    def ltorg(s):
        if (s.base + 2 * len(s.c)) % 4: s.c.append(0x0009)
        vals = list(dict.fromkeys(s.cur)); s.pools.append((len(s.c), vals)); s.c.extend([0, 0] * len(vals)); s.cur = []
    def build(s):
        if s.cur: s.ltorg()
        def val(v): return s.lab[v] if isinstance(v, str) else v
        for k, (at, vals) in enumerate(s.pools):
            for j, v in enumerate(vals):
                x = val(v) & 0xFFFFFFFF; s.c[at + 2 * j] = x >> 16; s.c[at + 2 * j + 1] = x & 0xFFFF
        for i, op, a in s.fix:
            pc = s.base + 2 * i
            if op == 'lit':
                rn, v, pk = a; at, vals = s.pools[pk]
                la = s.base + 2 * at + 4 * vals.index(v)
                d = la - ((pc & ~3) + 4); assert d >= 0 and d % 4 == 0 and d // 4 < 256, (hex(pc), d); s.c[i] = 0xD000 | (rn << 8) | d // 4
            else:
                d = (s.lab[a] - (pc + 4)) // 2
                if op in ('bra', 'bsr'): assert -2048 <= d < 2048; s.c[i] = (0xA000 if op == 'bra' else 0xB000) | (d & 0xFFF)
                else: assert -128 <= d < 128, (op, a, d); s.c[i] = {'bt': 0x8900, 'bf': 0x8B00, 'bts': 0x8D00, 'bfs': 0x8F00}[op] | (d & 0xFF)
        return b''.join(struct.pack('>H', x) for x in s.c)

    def mov(s, m, n): s.w(0x6003 | n << 8 | m << 4)
    def movi(s, i, n): s.w(0xE000 | n << 8 | (i & 0xFF))
    def addi(s, i, n): s.w(0x7000 | n << 8 | (i & 0xFF))
    def add(s, m, n): s.w(0x300C | n << 8 | m << 4)
    def sub(s, m, n): s.w(0x3008 | n << 8 | m << 4)
    def ldb(s, m, n): s.w(0x6000 | n << 8 | m << 4)
    def ldw(s, m, n): s.w(0x6001 | n << 8 | m << 4)
    def ldl(s, m, n): s.w(0x6002 | n << 8 | m << 4)
    def ldwp(s, m, n): s.w(0x6005 | n << 8 | m << 4)
    def ldbp(s, m, n): s.w(0x6004 | n << 8 | m << 4)
    def ldbx(s, m, n): s.w(0x000C | n << 8 | m << 4)         # mov.b @(R0,Rm),Rn
    def ldwx(s, m, n): s.w(0x000D | n << 8 | m << 4)         # mov.w @(R0,Rm),Rn
    def stb(s, m, n): s.w(0x2000 | n << 8 | m << 4)
    def stw(s, m, n): s.w(0x2001 | n << 8 | m << 4)
    def stl(s, m, n): s.w(0x2002 | n << 8 | m << 4)
    def ldld(s, d, m, n): assert d % 4 == 0 and d < 64; s.w(0x5000 | n << 8 | m << 4 | d // 4)
    def stld(s, m, d, n): assert d % 4 == 0 and d < 64; s.w(0x1000 | n << 8 | m << 4 | d // 4)
    def ldwd(s, d, m): assert d % 2 == 0 and d < 32; s.w(0x8500 | m << 4 | d // 2)
    def extub(s, m, n): s.w(0x600C | n << 8 | m << 4)
    def extuw(s, m, n): s.w(0x600D | n << 8 | m << 4)
    def cmpeq(s, m, n): s.w(0x3000 | n << 8 | m << 4)
    def cmphs(s, m, n): s.w(0x3002 | n << 8 | m << 4)
    def cmphi(s, m, n): s.w(0x3006 | n << 8 | m << 4)
    def cmpgt(s, m, n): s.w(0x3007 | n << 8 | m << 4)
    def cmpge(s, m, n): s.w(0x3003 | n << 8 | m << 4)
    def cmppz(s, n): s.w(0x4011 | n << 8)
    def tst(s, m, n): s.w(0x2008 | n << 8 | m << 4)
    def and_(s, m, n): s.w(0x2009 | n << 8 | m << 4)
    def or_(s, m, n): s.w(0x200B | n << 8 | m << 4)
    def andi(s, i): s.w(0xC900 | i)
    def tsti(s, i): s.w(0xC800 | i)
    def cmpeqi(s, i): s.w(0x8800 | (i & 0xFF))
    def shll(s, n): s.w(0x4000 | n << 8)
    def shlr(s, n): s.w(0x4001 | n << 8)
    def shll2(s, n): s.w(0x4008 | n << 8)
    def shlr2(s, n): s.w(0x4009 | n << 8)
    def shll8(s, n): s.w(0x4018 | n << 8)
    def shlr8(s, n): s.w(0x4019 | n << 8)
    def shll16(s, n): s.w(0x4028 | n << 8)
    def dt(s, n): s.w(0x4010 | n << 8)
    def push(s, n): s.w(0x2F06 | n << 4)
    def pop(s, n): s.w(0x60F6 | n << 8)
    def pushpr(s): s.w(0x4F22)
    def poppr(s): s.w(0x4F26)
    def jsr(s, m): s.w(0x400B | m << 8)
    def jmp(s, m): s.w(0x402B | m << 8)
    def rts(s): s.w(0x000B)
    def nop(s): s.w(0x0009)


def code(lay):
    a = S(CODE)
    # ── ldres: 상주 자료 서명 없으면 GFS_Load(자료, 0, VRA, 크기). r0~r7 망가짐
    a.L('ldres'); a.ld(1, VRA); a.ldl(1, 0); a.ld(2, MAGIC); a.cmpeq(2, 0); a.br('bf', 'lrld')
    a.ld(1, VRC); a.ldl(1, 0); a.ld(2, MAGIC_F); a.cmpeq(2, 0); a.br('bt', 'lrok')
    a.L('lrld'); a.pushpr()
    a.movi(SUBFID, 4); a.movi(0, 5); a.ld(6, VRA); a.ld(7, lay['RES_SIZE']); a.ld(0, GFS_LOAD); a.jsr(0); a.nop()
    a.movi(SUBFID, 4); a.ld(5, lay['RES_SIZE'] // 2048); a.ld(6, VRC); a.ld(7, lay['FRES_SIZE']); a.ld(0, GFS_LOAD); a.jsr(0); a.nop()
    a.poppr()
    a.L('lrok'); a.rts(); a.nop()
    # ── lwrap: 게임 적재 함수의 GFS_Load 호출 → ldres → 원래 GFS_Load(r4~r7 그대로)
    a.L('lwrap'); a.pushpr()
    for n in (4, 5, 6, 7): a.push(n)
    a.br('bsr', 'ldres'); a.nop()
    for n in (7, 6, 5, 4): a.pop(n)
    a.poppr(); a.ld(0, GFS_LOAD); a.jmp(0); a.nop()
    a.ltorg()
    # ── xwrap: XA 표에서 fid 찾으면 앞 음성 정지 → 그 대화 자막 쪽을 VRB 로 → cur 0. 없으면 cur −1. → 원래 함수(r4~r7 그대로)
    a.L('xwrap'); a.pushpr()
    for n in (4, 5, 6, 7, 8): a.push(n)
    a.ld(1, VAR); a.movi(-1, 0); a.stl(0, 1)                                             # 읽는 동안 그리지 않게
    a.ld(1, LYR); a.movi(0, 0); a.stl(0, 1)
    a.ld(1, lay['XTAB']); a.ld(2, lay['NX']); a.extuw(4, 3)
    a.L('xl'); a.tst(2, 2); a.br('bt', 'xnf')
    a.ldw(1, 8); a.extuw(8, 8); a.cmpeq(3, 8); a.br('bt', 'xf')
    a.addi(12, 1); a.addi(-1, 2); a.br('bra', 'xl'); a.nop()
    a.L('xf'); a.mov(1, 8)
    a.br('bsr', 'ldres'); a.nop()
    a.ld(1, VRA); a.ldl(1, 0); a.ld(2, MAGIC); a.cmpeq(2, 0); a.br('bf', 'xnf')         # 상주 자료 없음 → 자막 없이
    a.ld(1, STAT); a.ldb(1, 0); a.extub(0, 0); a.tst(0, 0); a.br('bt', 'xns')
    a.ld(0, STOP); a.jsr(0); a.nop()
    a.L('xns'); a.movi(SUBFID, 4); a.ldld(4, 8, 5); a.ld(6, VRB); a.ldld(8, 8, 7); a.ld(0, GFS_LOAD); a.jsr(0); a.nop()
    a.br('bsr', 'pal'); a.nop()                                                          # 색 고르기는 VBlank 밖에서(재생 시작 때 한 번)
    a.ld(1, lay['ST']); a.movi(0, 0); a.stl(0, 1)
    a.ld(1, VAR); a.ld(0, VRB); a.stld(0, 12, 1); a.movi(0, 0); a.stld(0, 4, 1); a.stld(0, 8, 1); a.stl(0, 1)
    a.br('bra', 'xo'); a.nop()
    a.L('xnf'); a.ld(1, VAR); a.movi(-1, 0); a.stl(0, 1)
    a.L('xo')
    for n in (8, 7, 6, 5, 4): a.pop(n)
    a.poppr(); a.ld(0, XA_FN); a.jmp(0); a.nop()
    a.ltorg()
    # ── awrap: 상주 AIF 표에서 fid 찾으면 cur 0·쪽 목록(없으면 cur 그대로) → 원래 함수
    a.L('awrap'); a.pushpr()
    for n in (4, 5, 6, 7, 8): a.push(n)
    a.br('bsr', 'ldres'); a.nop()
    a.ld(1, VRA); a.ldl(1, 0); a.ld(2, MAGIC); a.cmpeq(2, 0); a.br('bf', 'ao')
    a.ldld(16, 15, 3); a.extuw(3, 3)                                                     # 저장해 둔 r4 = fid(스택: r8 r7 r6 r5 r4 pr)
    a.ld(1, lay['A_FIDS']); a.ld(2, lay['NA']); a.movi(0, 0)
    a.L('al'); a.tst(2, 2); a.br('bt', 'ao')
    a.ldwp(1, 5); a.extuw(5, 5); a.cmpeq(3, 5); a.br('bt', 'af')
    a.addi(1, 0); a.addi(-1, 2); a.br('bra', 'al'); a.nop()
    a.L('af'); a.shll2(0); a.ld(1, lay['A_IDX']); a.add(1, 0); a.ldl(0, 8)
    a.ld(1, VAR); a.movi(-1, 0); a.stl(0, 1); a.ld(1, LYR); a.movi(0, 0); a.stl(0, 1)
    a.br('bsr', 'pal'); a.nop()
    a.ld(1, lay['ST']); a.movi(0, 0); a.stl(0, 1)
    a.ld(1, VAR); a.stld(8, 12, 1); a.movi(0, 0); a.stld(0, 4, 1); a.stld(0, 8, 1); a.stl(0, 1)
    a.L('ao')
    for n in (8, 7, 6, 5, 4): a.pop(n)
    a.poppr(); a.ld(0, AIF_FN); a.jmp(0); a.nop()
    a.ltorg()
    # ── cwrap: CD 명령 CR1~4 쓰기 감쌈(인터럽트 막힌 채 불림 — 가볍게, 아무것도 부르지 않음). 원래 함수는 r1·r2·r4 만 씀 → r0·r3·r5 보존
    a.L('cwrap'); a.push(0); a.push(3); a.push(5)
    a.ldw(4, 1); a.mov(1, 0); a.shlr8(0); a.andi(0xFF)
    a.cmpeqi(0x10); a.br('bt', 'cplay')
    a.cmpeqi(0x11); a.br('bf', 'cout')
    a.L('cstop'); a.ld(1, LYR); a.ldl(1, 0); a.tst(0, 0); a.br('bt', 'cout')                 # 가사 중에 다른 재생·탐색 → 끔
    a.movi(0, 0); a.stl(0, 1); a.ld(1, VAR); a.movi(-1, 0); a.stl(0, 1); a.movi(0, 0); a.stld(0, 8, 1)
    a.ld(1, lay['ST']); a.stl(0, 1); a.br('bra', 'cout'); a.nop()
    a.L('cplay'); a.mov(1, 0); a.andi(0xFF); a.shll16(0); a.mov(0, 3)
    a.ldwd(2, 4); a.extuw(0, 0); a.or_(3, 0)                                              # r0 = 시작 위치(24비트)
    a.ld(3, 0x0401); a.cmpeq(3, 0); a.br('bt', 'cmatch')
    a.ld(3, 0x0400); a.cmpeq(3, 0); a.br('bt', 'cmatch')
    a.ld(3, 0x800000 | T04_FAD[0]); a.cmphs(3, 0); a.br('bf', 'cstop')
    a.ld(3, 0x800000 | T04_FAD[1]); a.cmphs(3, 0); a.br('bt', 'cstop')
    a.L('cmatch'); a.ld(1, lay['A_IDX'] + 4 * (lay['NA'] - 1)); a.ldl(1, 0)              # 가사 쪽 목록(상주 AIF 표 마지막)
    a.ld(1, VAR); a.stld(0, 12, 1); a.movi(-LYR_DELAY, 0); a.stld(0, 4, 1); a.movi(0, 0); a.stld(0, 8, 1); a.stl(0, 1)
    a.ld(1, lay['ST']); a.stl(0, 1); a.ld(1, LYR); a.movi(1, 0); a.stl(0, 1)
    a.L('cout'); a.pop(5); a.pop(3); a.pop(0); a.ld(1, CDC_W); a.jmp(1); a.nop()
    a.ltorg()
    # ── vbo: sub → 원래 처리기
    a.L('vbo'); a.pushpr(); a.br('bsr', 'sub'); a.nop(); a.ld(0, VBO_ORIG); a.jsr(0); a.nop(); a.poppr(); a.rts(); a.nop()
    a.ltorg()
    # ── sub
    a.L('sub'); a.ld(1, TPL); a.ld(0, 0x8000); a.stw(0, 1); a.ld(6, VAR)
    a.ldld(0, 6, 7); a.cmppz(7); a.br('bt', 'sub1'); a.rts(); a.nop()                  # cur < 0 → 돌아감(bf ret 은 세로 분기 넣은 뒤 범위 밖)
    a.L('sub1')
    a.ldld(4, 6, 3); a.addi(1, 3); a.stld(3, 4, 6)                                       # r3 = 프레임
    a.ld(1, LYR); a.ldl(1, 0); a.tst(0, 0); a.br('bf', 'alive')                         # 가사 중 → 음성 상태 무시(쪽 끝나면 끝)
    a.ld(1, STAT); a.ldb(1, 0); a.extub(0, 0); a.tst(0, 0); a.br('bf', 'alive')
    a.movi(KILL_GRACE, 0); a.cmpgt(0, 3); a.br('bt', 'kill')                            # 상태 0 이고 프레임 > 유예 → 끝
    a.L('alive')
    a.ldld(12, 6, 1); a.tst(1, 1); a.br('bt', 'kill')
    a.ldwp(1, 5); a.extuw(5, 5)                                                           # r5 = 쪽 수, r1 = 첫 쪽
    a.L('pl'); a.tst(5, 5); a.br('bt', 'kill')
    a.ldwd(2, 1); a.cmpge(0, 3); a.br('bf', 'gap')                                       # 프레임 < 시작 → 쪽 사이(안 그림)
    a.ldwd(4, 1); a.cmpgt(3, 0); a.br('bt', 'found')                                     # 끝 > 프레임 → 이 쪽
    a.ldwd(0, 1); a.extuw(0, 0); a.add(0, 1); a.addi(-1, 5); a.br('bra', 'pl'); a.nop()
    a.L('found')
    a.ldld(8, 6, 0); a.cmpeq(1, 0); a.br('bt', 'patch')                                  # 이미 그린 쪽 → 보여 줌
    a.ld(2, lay['ST']); a.ldl(2, 0); a.cmpeq(1, 0); a.br('bt', 'step')                   # 그리는 중인 쪽 → 이어서
    a.pushpr(); a.push(1); a.mov(1, 4); a.br('bsr', 'rstart'); a.nop(); a.pop(1); a.poppr()
    a.L('step'); a.ld(2, lay['ST']); a.movi(GPF, 0); a.stld(0, 24, 2)
    a.pushpr(); a.push(1); a.br('bsr', 'rstep'); a.nop(); a.pop(1); a.poppr()
    a.ld(6, VAR); a.tst(0, 0); a.br('bt', 'nd')
    a.stld(1, 8, 6); a.ld(2, lay['ST']); a.movi(0, 0); a.stl(0, 2)                      # 다 그림 → 보여 줄 쪽 = 이것
    a.ld(1, lay['COMP']); a.ld(2, TEX); a.ld(5, BMPSZ // 4)
    a.L('cp'); a.ldl(1, 0); a.stl(0, 2); a.addi(4, 1); a.addi(4, 2); a.dt(5); a.br('bf', 'cp')
    a.br('bra', 'patch'); a.nop()
    a.L('nd'); a.ldld(8, 6, 0); a.tst(0, 0); a.br('bt', 'ret')                           # 아직 → 앞 쪽 그림 있으면 그대로 보여 줌
    # 화면 아래 가운데 절대 좌표(TVMD: HRESO 비트0 → 352 폭, VRES → 224/240/256) → RAM 견본 스프라이트
    # 색 다시 고르기 — 게임 중엔 팔레트가 순환해 재생 시작 때 고른 칸 색이 바뀜(빌드 6 «여러 색으로 반짝»). 보이는 동안 4 프레임마다
    a.L('patch'); a.ld(1, VAR); a.ldld(4, 1, 0); a.tsti(3); a.br('bf', 'nopal')            # 4 프레임마다(2,048 칸 훑기 ≈ 1.8 ms)
    a.pushpr(); a.br('bsr', 'pal'); a.nop(); a.poppr()
    a.L('nopal')
    a.ld(1, SH); a.ldw(1, 0); a.mov(0, 3); a.andi(1); a.shll2(0); a.shll2(0)          # X0 = 0 / 16
    a.ld(1, SPR + 12); a.stw(0, 1)
    a.mov(3, 0); a.shlr2(0); a.shlr2(0); a.andi(3); a.shll2(0); a.shll2(0); a.ld(2, 224 - H_ - 6); a.add(2, 0)
    a.ld(1, SPR + 14); a.stw(0, 1)
    # 세로(타테) 모드(게임 변수 0x060D72C8 = 0, 가로 = 1 — 스테이트 55장 실측) → 변형 스프라이트로 90° 세워 화면 왼쪽(플레이어 기준 아래)
    #   글자 위쪽이 화면 오른쪽을 보게: 그림 (u,v) → 화면 (XL + H−1 − v, Y0 + u) · A=왼위 B=오른위 C=오른아래 D=왼아래(그림 기준)
    a.mov(3, 0); a.pushpr(); a.br('bsr', 'tatepos'); a.nop(); a.poppr()                 # 세로 모드면 변형 스프라이트로(서브루틴 — 안에 두면 앞 bf ret 이 닿는 범위를 넘음)
    # 지역 좌표·스프라이트·END(RAM 0x20~0x7F) → VDP1 CMDV, 견본 = 건너뛰고 CMDV 로
    a.ld(1, LOCC); a.ld(2, 0x25C00000 + CMDV); a.movi(24, 5)
    a.L('cc'); a.ldl(1, 0); a.stl(0, 2); a.addi(4, 1); a.addi(4, 2); a.dt(5); a.br('bf', 'cc')
    a.ld(1, TPL); a.ld(0, 0x5000); a.stw(0, 1)
    # 자막 PR 레지스터 3(PRISB 윗바이트) 우선순위 = 7 — 오프닝 RBG0 6·스테이지 NBG3 7 위로(같으면 스프라이트가 위). SGL 사본 + 실제 레지스터
    a.ld(1, SH + 0xF2); a.ldw(1, 0); a.ld(2, 0xF8FF); a.and_(2, 0); a.ld(2, 0x0700); a.or_(2, 0); a.stw(0, 1)
    a.ld(1, 0x25F800F2); a.stw(0, 1)
    a.L('ret'); a.rts(); a.nop()
    a.L('gap'); a.movi(0, 0); a.stld(0, 8, 6); a.br('bra', 'ret'); a.nop()                # 쪽 사이 → 보여 줄 쪽 비움(빌드 9 «어떡하지 앞에 앞 쪽이 반짝»: 새 쪽 그리는 동안 끝난 쪽이 다시 보임)
    a.L('kill'); a.movi(-1, 0); a.stld(0, 0, 6); a.movi(0, 0); a.stld(0, 8, 6); a.ld(1, lay['ST']); a.stl(0, 1)
    a.ld(1, LYR); a.stl(0, 1); a.rts(); a.nop()
    a.L('tatepos')                                                                         # r3 = TVMD 사본, r0·r1·r2·r4·r5 망가짐
    a.ld(1, TATE); a.ldb(1, 0); a.tst(0, 0); a.br('bf', 'yoko')
    a.ld(1, SPR); a.movi(2, 0); a.stw(0, 1)                                                # CMDCTRL = 변형 스프라이트
    a.mov(3, 0); a.andi(1); a.shll2(0); a.shll2(0); a.addi(TATE_X, 0); a.mov(0, 4)       # r4 = XL (352 폭이면 +16)
    a.mov(3, 0); a.shlr2(0); a.shlr2(0); a.andi(3); a.shll2(0); a.shll(0); a.ld(2, (224 - W_) // 2); a.add(2, 0); a.mov(0, 5)   # r5 = Y0 = (화면 높이 − 320)/2
    a.mov(4, 0); a.addi(H_ - 1, 0); a.ld(1, SPR + 12); a.stw(0, 1); a.ld(1, SPR + 16); a.stw(0, 1)   # XA = XB = XL + H − 1
    a.ld(1, SPR + 20); a.stw(4, 1); a.ld(1, SPR + 24); a.stw(4, 1)                                  # XC = XD = XL
    a.ld(1, SPR + 14); a.stw(5, 1); a.ld(1, SPR + 26); a.stw(5, 1)                                  # YA = YD = Y0
    a.mov(5, 0); a.ld(2, W_ - 1); a.add(2, 0); a.ld(1, SPR + 18); a.stw(0, 1); a.ld(1, SPR + 22); a.stw(0, 1)   # YB = YC = Y0 + W − 1
    a.rts(); a.nop()
    a.L('yoko'); a.ld(1, SPR); a.movi(0, 0); a.stw(0, 1); a.rts(); a.nop()                 # 가로 = 일반 스프라이트
    a.ltorg()

    # ── pal: 장면 레지스터·CRAM → 색 참조표(4 칸). r8~r13 보존
    a.L('pal')
    for n in (8, 9, 10, 11, 12, 13): a.push(n)
    a.ld(1, SH + 0xE0); a.ldw(1, 0); a.andi(7); a.mov(0, 2)                                 # r2 = 타입
    a.ld(1, lay['TSH']); a.ldbx(1, 8); a.extub(8, 8)                                       # r8 = PR 비트 시작
    a.ld(1, lay['TCN']); a.mov(2, 0); a.ldbx(1, 9); a.extub(9, 9)                          # r9 = PR 개수
    a.ld(1, lay['TDC']); a.mov(2, 0); a.shll(0); a.ldwx(1, 5); a.extuw(5, 5)              # r5 = DC 마스크
    # PR 레지스터 = min(3, 개수−1) 고정 — 게임 스프라이트는 0~2 만 씀(31 장면 전수, 2026-11-08). 우선순위는 보일 때 7 로(sub)
    a.mov(9, 10); a.addi(-1, 10); a.movi(3, 0); a.cmpgt(0, 10); a.br('bf', 'pdone'); a.mov(0, 10)
    a.L('pdone'); a.tst(8, 8); a.br('bt', 'shd')
    a.L('sl'); a.shll(10); a.dt(8); a.br('bf', 'sl')
    a.L('shd')                                                                             # r10 = PR 비트 값
    a.ld(1, SH + 0xE6); a.ldw(1, 0); a.shlr2(0); a.shlr2(0); a.andi(7); a.shll8(0); a.mov(0, 6)   # r6 = 색 오프셋
    a.ld(1, SH + 0x0E); a.ldw(1, 0); a.extuw(0, 0); a.shlr8(0); a.shlr2(0); a.shlr2(0); a.andi(3)
    a.ld(7, 2047); a.tst(0, 0); a.br('bf', 'nm'); a.ld(7, 1023)
    a.L('nm'); a.movi(1, 4); a.ld(8, 0x7FFF); a.movi(1, 9); a.movi(-1, 11); a.movi(1, 12); a.ld(13, CRAM)
    a.L('sc'); a.cmphi(5, 4); a.br('bt', 'scd')                                             # i > DC 마스크 → 끝
    a.mov(6, 0); a.add(4, 0); a.and_(7, 0); a.shll(0); a.add(13, 0); a.ldw(0, 1); a.extuw(1, 1)
    a.mov(1, 0); a.andi(31); a.mov(0, 2)
    a.mov(1, 0); a.shlr2(0); a.shlr2(0); a.shlr(0); a.andi(31); a.add(0, 2)
    a.mov(1, 0); a.shlr8(0); a.shlr2(0); a.andi(31); a.add(0, 2)
    a.cmpgt(2, 8); a.br('bf', 'nmin'); a.mov(2, 8); a.mov(4, 9)                            # 더 어두움
    a.L('nmin'); a.cmpgt(11, 2); a.br('bf', 'nmax'); a.mov(2, 11); a.mov(4, 12)            # 더 밝음
    a.L('nmax'); a.addi(1, 4); a.br('bra', 'sc'); a.nop()
    a.L('scd'); a.ld(1, LUT)
    a.movi(0, 0); a.stw(0, 1)
    a.mov(10, 0); a.or_(9, 0); a.mov(1, 2); a.addi(2, 2); a.stw(0, 2); a.addi(4, 2); a.stw(0, 2)
    a.mov(10, 0); a.or_(12, 0); a.mov(1, 2); a.addi(4, 2); a.stw(0, 2)
    for n in (13, 12, 11, 10, 9, 8): a.pop(n)
    a.rts(); a.nop()
    a.ltorg()

    # ── rstart(r4 = 쪽): 그림 버퍼 지우고 띠 칠함 · 이어 그리기 상태 시작. r8~r14 보존
    a.L('rstart')
    for n in (8, 9, 10, 11, 12, 13, 14): a.push(n)
    a.mov(4, 14)
    a.ld(1, lay['COMP']); a.ld(2, BMPSZ // 4); a.movi(0, 0)
    a.L('rc'); a.stl(0, 1); a.addi(4, 1); a.dt(2); a.br('bf', 'rc')
    a.ldwd(8, 14); a.extuw(0, 8); a.ldwd(10, 14); a.extuw(0, 9); a.ldwd(12, 14); a.extuw(0, 10); a.ldwd(14, 14); a.extuw(0, 11)
    a.mov(10, 1); a.shll2(1); a.shll2(1); a.shll(1); a.mov(1, 0); a.shll2(0); a.add(1, 0)   # by0×160
    a.ld(12, lay['COMP']); a.add(0, 12)
    a.mov(11, 13); a.sub(10, 13); a.ld(3, 0x11)
    a.L('brow'); a.mov(12, 1); a.add(8, 1); a.mov(9, 2); a.sub(8, 2)
    a.L('bcol'); a.stb(3, 1); a.addi(1, 1); a.dt(2); a.br('bf', 'bcol')
    a.ld(0, ROWB); a.add(0, 12); a.dt(13); a.br('bf', 'brow')
    a.ld(1, lay['ST']); a.stl(14, 1)                                                       # 그리는 쪽
    a.mov(14, 0); a.addi(16, 0); a.stld(0, 4, 1)                                           # 첫 줄 머리
    a.ldwd(6, 14); a.extuw(0, 0); a.stld(0, 8, 1)                                          # 남은 줄
    a.movi(0, 0); a.stld(0, 12, 1)                                                         # 남은 글자 0 → 다음 줄부터
    for n in (14, 13, 12, 11, 10, 9, 8): a.pop(n)
    a.rts(); a.nop()
    a.ltorg()
    # ── rstep: 이번 프레임 몫(ST+24 글자)만 그림 → r0 = 1 다 그림 / 0 아직. r8~r14 보존
    a.L('rstep')
    for n in (8, 9, 10, 11, 12, 13, 14): a.push(n)
    a.pushpr()
    a.ld(1, lay['ST']); a.ldld(4, 1, 12); a.ldld(12, 1, 13); a.ldld(16, 1, 8)
    a.L('s0'); a.tst(13, 13); a.br('bf', 'shg')
    a.ld(1, lay['ST']); a.ldld(8, 1, 0); a.tst(0, 0); a.br('bt', 'sdone')                 # 줄 다 씀 → 끝
    a.addi(-1, 0); a.stld(0, 8, 1)
    a.ldwp(12, 8); a.extuw(8, 8); a.ldwp(12, 0); a.extuw(0, 0); a.stld(0, 20, 1); a.ldwp(12, 13); a.extuw(13, 13)
    a.br('bra', 's0'); a.nop()
    a.L('shg'); a.ld(1, lay['ST']); a.ldld(24, 1, 0); a.tst(0, 0); a.br('bt', 'spause')   # 이번 프레임 몫 다 씀
    a.addi(-1, 0); a.stld(0, 24, 1)
    a.ldld(20, 1, 9)                                                                       # 줄 y
    a.ldw(12, 0); a.extuw(0, 0)
    a.mov(0, 1); a.shll2(1); a.shll2(0); a.shll(0); a.add(1, 0)                           # 번호×12 (= 8n + 4n)
    a.ld(10, lay['FONT']); a.add(0, 10); a.movi(FROWS, 11); a.addi(FROW0, 9)
    a.mov(10, 0); a.addi(FROWS, 0); a.ldw(0, 0); a.shll16(0); a.ld(1, lay['ST']); a.stld(0, 28, 1)   # 9번째 열 비트 → ST+28
    a.L('grow'); a.ldbp(10, 14); a.extub(14, 14); a.shll16(14); a.shll8(14)
    a.ld(1, lay['ST']); a.ldld(28, 1, 0); a.shll(0); a.stld(0, 28, 1); a.br('bf', 'gc8')
    a.ld(0, 0x00800000); a.or_(0, 14)
    a.L('gc8'); a.tst(14, 14); a.br('bt', 'gnext')
    a.mov(8, 4)
    a.L('gcol'); a.shll(14); a.br('bf', 'gskip')
    a.mov(4, 0); a.push(0); a.addi(1, 4); a.mov(9, 5); a.addi(1, 5); a.movi(3, 6); a.movi(1, 7); a.br('bsr', 'pix'); a.nop()
    a.pop(4); a.mov(9, 5); a.movi(2, 6); a.movi(0, 7); a.br('bsr', 'pix'); a.nop()
    a.L('gskip'); a.addi(1, 4); a.tst(14, 14); a.br('bf', 'gcol')
    a.L('gnext'); a.addi(1, 9); a.dt(11); a.br('bf', 'grow')
    a.ldw(12, 0); a.extuw(0, 0); a.shll(0); a.ld(1, lay['ADV']); a.add(0, 1); a.ldw(1, 0); a.extuw(0, 0); a.add(0, 8)
    a.addi(2, 12); a.addi(-1, 13); a.br('bra', 's0'); a.nop()
    a.L('spause'); a.stld(12, 4, 1); a.stld(13, 12, 1); a.stld(8, 16, 1); a.movi(0, 0); a.br('bra', 'sret'); a.nop()
    a.L('sdone'); a.movi(1, 0)
    a.L('sret'); a.poppr()
    for n in (14, 13, 12, 11, 10, 9, 8): a.pop(n)
    a.rts(); a.nop()
    a.ltorg()
    a.L('pix'); a.ld(0, W_); a.cmphs(0, 4); a.br('bt', 'pret'); a.movi(H_, 0); a.cmphs(0, 5); a.br('bt', 'pret')
    a.mov(5, 1); a.shll2(1); a.shll2(1); a.shll(1); a.mov(1, 0); a.shll2(0); a.add(1, 0)
    a.mov(4, 1); a.shlr(1); a.add(1, 0); a.ld(2, lay['COMP']); a.add(0, 2)
    a.ldb(2, 1); a.extub(1, 1); a.mov(4, 0); a.tsti(1); a.br('bf', 'podd')
    a.mov(1, 3); a.shlr2(3); a.shlr2(3)
    a.tst(7, 7); a.br('bt', 'pe1'); a.movi(1, 0); a.cmpeq(0, 3); a.br('bf', 'pret')
    a.L('pe1'); a.mov(1, 0); a.andi(0x0F); a.mov(6, 3); a.shll2(3); a.shll2(3); a.or_(3, 0); a.stb(0, 2); a.rts(); a.nop()
    a.L('podd'); a.mov(1, 0); a.andi(0x0F); a.mov(0, 3)
    a.tst(7, 7); a.br('bt', 'po1'); a.movi(1, 0); a.cmpeq(0, 3); a.br('bf', 'pret')
    a.L('po1'); a.mov(1, 0); a.andi(0xF0); a.or_(6, 0); a.stb(0, 2)
    a.L('pret'); a.rts(); a.nop()
    return a


CODE_MAX = 0x940
ST = BLOCK + 0x9E0                                  # 이어 그리기 상태: +0 그리는 쪽 · +4 글자 위치 · +8 남은 줄 · +12 남은 글자 · +16 x · +20 y · +24 이번 프레임 남은 글자
GPF = 3                                             # 프레임마다 그리는 글자 수(길면 깜빡임 — 하스피 2026-11-08)
TSH, TCN, TDC = BLOCK + 0x9C0, BLOCK + 0x9C8, BLOCK + 0x9D0     # 스프라이트 타입별 PR 비트 시작·개수·DC 마스크
TPL = BLOCK + 0xA00                                 # SGL END 견본 대신(리터럴 0x0607F864 를 돌림): 보일 때 «건너뛰고 CMDV 로», 안 보일 때 END
XTAB = BLOCK + 0xA20                                # XA 표: 항목 12 B {fid u16, 0, 섹터 u32, 크기 u32}
COMP = BLOCK + 0xC00                                # 그림 만들 곳(RAM) → VDP1 0x28000 으로 복사


def res_layout(nfont, na, pages_len):
    """상주 자료(VRA) 배치: +0 서명 · +4 개수 · +8 AIF fid(u16) · AIF 쪽 목록 주소(u32) · 쪽들 · 글꼴 · 폭(u16)"""
    r = {'NA': na}; p = VRA + 8
    r['A_FIDS'] = p; p += (2 * na + 3) & ~3
    r['A_IDX'] = p; p += 4 * na
    r['A_PAGES'] = p; p += (pages_len + 3) & ~3
    r['RES_SIZE'] = (p - VRA + 2047) & ~2047
    assert p - VRA <= VRA_MAX, ('상주 쪽 자료가 VDP1 안전 구역(0x19F00)을 넘음', hex(p - VRA))
    q = VRC + 8                                                                          # 작업 RAM: 서명 'GTFT' · 글자 수 · 폭 · 글꼴(12 B/자)
    r['ADV'] = q; q += (2 * nfont + 3) & ~3
    r['FONT'] = q; q += FONT_B * nfont
    r['FRES_SIZE'] = (q - VRC + 2047) & ~2047
    assert (q - VRC + 2047) & ~2047 <= VRC_MAX, ('글꼴이 빈 구역을 넘음(읽기는 2048 단위)', hex(q - VRC))
    return r


def layout(nfont, na, pages_len, nx):
    lay = res_layout(nfont, na, pages_len); lay.update({'NX': nx, 'XTAB': XTAB, 'COMP': COMP, 'TSH': TSH, 'TCN': TCN, 'TDC': TDC, 'ST': ST})
    a = code(lay); c = a.build(); assert len(c) <= CODE_MAX, ('코드가 길다', len(c))
    assert XTAB + 12 * nx <= LYR and COMP + BMPSZ <= BLOCK_END and TSH + 0x20 <= ST and ST + 32 <= TPL
    lay['END'] = COMP + BMPSZ
    return lay, a, c


def build_sub(data):
    """→ (RAM 블록, 자료 파일 바이트, 라벨, 배치)"""
    idx, bits, advs, aif, xa = data
    abody = b''; aoffs = []
    for fid, body, _ in aif:
        aoffs.append(len(abody)); abody += body + (b'\0\0' if len(body) & 2 else b'')
    lay, a, c = layout(len(advs), len(aif), len(abody), len(xa))
    res = bytearray(lay['RES_SIZE'])
    o = lambda addr: addr - VRA
    struct.pack_into('>II', res, 0, MAGIC, len(aif))
    for k, (fid, body, _) in enumerate(aif):
        struct.pack_into('>H', res, o(lay['A_FIDS']) + 2 * k, fid)
        struct.pack_into('>I', res, o(lay['A_IDX']) + 4 * k, lay['A_PAGES'] + aoffs[k])
    res[o(lay['A_PAGES']):o(lay['A_PAGES']) + len(abody)] = abody
    fres = bytearray(lay['FRES_SIZE']); f = lambda addr: addr - VRC
    struct.pack_into('>II', fres, 0, MAGIC_F, len(advs))
    for i, g in enumerate(bits):
        assert not any(g[:2 * FROW0]) and not any(g[2 * (FROW0 + FROWS):]), ('글꼴 줄이 저장 범위 밖', i)
        rw = [struct.unpack_from('>H', g, 2 * r)[0] for r in range(FROW0, FROW0 + FROWS)]
        assert not any(w & 0x7F for w in rw), ('글꼴이 9열을 넘음', i)
        m9 = 0
        for k, w in enumerate(rw): m9 |= ((w >> 7) & 1) << (15 - k)
        fres[f(lay['FONT']) + FONT_B * i:f(lay['FONT']) + FONT_B * (i + 1)] = bytes(w >> 8 for w in rw) + struct.pack('>H', m9)
    for i, w in enumerate(advs): struct.pack_into('>H', fres, f(lay['ADV']) + 2 * i, w)
    sub = bytes(res) + bytes(fres); xtab = []
    for fid, body, _ in xa:
        assert len(body) <= VRB_MAX, ('XA 자막 쪽이 0x1000 을 넘음', fid, len(body))
        sz = (len(body) + 2047) & ~2047
        xtab.append((fid, len(sub) // 2048, sz)); sub += body + bytes(sz - len(body))
    blk = bytearray(lay['END'] - BLOCK)
    blk[0:4] = b'GTV2'
    struct.pack_into('>4I', blk, VAR - BLOCK, 0xFFFFFFFF, 0, 0, 0)
    blk[LOCC - BLOCK:LOCC - BLOCK + 32] = struct.pack('>16H', 0x000A, *[0] * 15)
    blk[SPR - BLOCK:SPR - BLOCK + 32] = struct.pack('>16H', 0x0000, 0, 0x0088, LUTO >> 3, TEXO >> 3, (W_ // 8) << 8 | H_, XA & 0xFFFF, YA & 0xFFFF, *[0] * 8)
    blk[ENDC - BLOCK:ENDC - BLOCK + 32] = struct.pack('>16H', 0x8000, *[0] * 15)
    blk[TPL - BLOCK:TPL - BLOCK + 32] = struct.pack('>16H', 0x8000, CMDV >> 3, *[0] * 14)
    blk[CODE - BLOCK:CODE - BLOCK + len(c)] = c
    for k, (fid, sec, sz) in enumerate(xtab): struct.pack_into('>HHII', blk, XTAB - BLOCK + 12 * k, fid, 0, sec, sz)
    for t, (sh, cn, dc) in enumerate(TYPES):
        blk[TSH - BLOCK + t] = sh; blk[TCN - BLOCK + t] = cn; struct.pack_into('>H', blk, TDC - BLOCK + 2 * t, dc)
    return bytes(blk), sub, a.lab, lay


def patch(z0, data=None):
    """/0(원본) → (훅 넣은 /0, 자막 자료 파일, 라벨, 배치)"""
    data = data or build_data()
    blk, sub, lab, lay = build_sub(data); lab = dict(lab, TPL=TPL | 0x80000000)
    s = bytearray(z0)
    assert len(s) == 595088, '/0 크기가 원본과 다름'
    for L, fn, nm in [(L, XA_FN, 'xwrap') for L in XA_LITS] + [(L, AIF_FN, 'awrap') for L in AIF_LITS] + [(VBO_LIT, VBO_ORIG, 'vbo'), (LOAD_LIT, GFS_LOAD, 'lwrap'), (END_LIT, END_ORIG, 'TPL'), (CDC_LIT, CDC_W, 'cwrap')]:
        assert struct.unpack_from('>I', s, L - BIN_BASE)[0] == fn, hex(L); struct.pack_into('>I', s, L - BIN_BASE, lab[nm])
    s += bytes(BLOCK - BIN_BASE - len(s)); s += blk
    return bytes(s), sub, lab, lay


# ───────── 자료 ─────────
def build_font(chars):
    """갈무리11 비트맵(한글 잉크 윗선 = 0행) — 없는 글자만 나눔고딕 1비트 (모노모노 그대로)"""
    import bdf
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    g = bdf.Font(GALMURI)
    ys = [y for c in '가각힣맑앙' for x, y in g.draw(c)[0]]
    top, bot = min(ys), max(ys); off = -top + max(0, (GROWS - (bot - top + 1)) // 2)
    order = sorted(chars); idx = {c: i for i, c in enumerate(order)}
    bits, advs, miss = [], [], []
    for c in order:
        rows = [0] * GROWS
        if ord(c) in g.g:
            pts, w = g.draw(c)
            for x, y in pts:
                yy = y + off
                if 0 <= yy < GROWS and 0 <= x < 16: rows[yy] |= 0x8000 >> x
            adv = 4 if c == ' ' else max(1, min(16, w))
        else:
            fb = ImageFont.truetype(NANUM, 56); im = Image.new('L', (64, 64), 0)
            ImageDraw.Draw(im).text((0, -fb.getbbox('가')[1]), c, font=fb, fill=255)
            cov = np.array(im.resize((16, 16), Image.BOX), float) / 255
            for y in range(GROWS):
                rows[y] = sum(0x8000 >> x for x in range(16) if cov[y, x] > 0.45)
            adv = max(1, min(16, int(round(ImageFont.truetype(NANUM, 14).getlength(c))))); miss.append(c)
        bits.append(b''.join(struct.pack('>H', r) for r in rows)); advs.append(adv)
    if miss: print('  갈무리11 에 없는 글자(나눔으로):', ''.join(miss))
    return idx, bits, advs


def wrap(t, W, maxw):
    out = []; cur = ''
    for w in t.split(' '):
        cand = (cur + ' ' + w) if cur else w
        if W(cand) <= maxw: cur = cand
        else:
            assert cur, ('낱말 하나가 폭 넘침', w); out.append(cur); cur = w
    if cur: out.append(cur)
    return out


def fid_table():
    t = {l.split('\t')[1].rstrip('\n'): int(l.split('\t')[0]) for l in open(os.path.join(ROOT, 'work', 'fid.tsv'), encoding='utf-8')}
    t['T04_LYRICS.AIF'] = LYR_FID
    return t


def rows():
    out = []
    for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'voice', SUB_TSV), encoding='utf-8'), delimiter='\t'):
        ko = r['한글'].strip()
        if not ko: continue
        ko = PUNCT_SP.sub(r'\1', ko)
        assert not re.search(r'[぀-ヿ一-鿿]', ko), ('가나·한자 남음', r['파일'], ko)
        out.append((r['파일'], float(r['시작']), float(r['끝']), ko))
    for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'voice', LYR_TSV), encoding='utf-8'), delimiter='\t'):  # 가사(맨 끝 = 상주 표 마지막)
        ko = r['한글'].strip()
        if ko: out.append(('T04_LYRICS.AIF', float(r['시작']), float(r['끝']), PUNCT_SP.sub(r'\1', ko)))
    return out


def build_data():
    """→ (글자 번호, 글꼴, 폭, AIF [(fid, 쪽 목록 바이트, 쪽들)], XA [(fid, 쪽 목록 바이트, 쪽들)])"""
    rs = rows(); FT = fid_table()
    chars = set(''.join(ko for *_, ko in rs)) | {' '}
    idx, bits, advs = build_font(chars)
    W = lambda s: sum(advs[idx[c]] for c in s)
    files = list(dict.fromkeys(f for f, *_ in rs)); aif, xa = [], []
    for f in files:
        segs = [(t0, t1, ko) for ff, t0, t1, ko in rs if ff == f]
        pages = []
        for j, (t0, t1, ko) in enumerate(segs):
            nxt = segs[j + 1][0] if j + 1 < len(segs) else t1 + 1.0
            end = min(nxt, t1 + 0.6)                                                       # 말 끝난 뒤 0.6초 더(다음 말 전까지)
            ls = wrap(ko, W, MAXW); grp = [ls[k:k + 2] for k in range(0, len(ls), 2)]
            tot = sum(len(''.join(g)) for g in grp); t = t0
            for k, g in enumerate(grp):
                b = end if k == len(grp) - 1 else t + (t1 - t0) * len(''.join(g)) / tot
                pages.append((int(t * FPS), max(int(b * FPS), int(t * FPS) + 1), g)); t = b
        body = struct.pack('>H', len(pages)); pp = []
        for f0, f1, g in pages:
            ys = LY if len(g) == 2 else LY[1:]
            lines = []
            for l, y in zip(g, ys):
                w = W(l); lines.append(((W_ - w) // 2, y, [idx[c] for c in l], w))
            x0 = min(l[0] for l in lines); x1 = max(l[0] + l[3] for l in lines)
            bx0 = max(0, x0 - 6) >> 1; bx1 = (min(W_, x1 + 6) + 1) >> 1
            by0 = ys[0] - 3; by1 = min(H_ - 1, ys[-1] + GROWS + 3)
            pb = struct.pack('>7H', f0, f1, len(lines), bx0, bx1, by0, by1)
            for x, y, gl, w in lines:
                pb += struct.pack('>3H', x, y, len(gl)) + b''.join(struct.pack('>H', k) for k in gl)
            pb = struct.pack('>H', 2 + len(pb)) + pb
            body += pb; pp.append((f0, f1, bx0, bx1, by0, by1, [(x, y, gl) for x, y, gl, w in lines]))
        (aif if f.endswith('.AIF') else xa).append((FT[f], body, pp))
    return idx, bits, advs, aif, xa


def ref_render(page, font_bits, advs):
    """render 와 같은 셈(검산용)"""
    f0, f1, bx0, bx1, by0, by1, lines = page
    px = [[0] * W_ for _ in range(H_)]
    for y in range(by0, by1):
        for b in range(bx0, bx1): px[y][2 * b] = px[y][2 * b + 1] = 1
    for x, ly, gl in lines:
        for g in gl:
            bits = font_bits[g]
            for r in range(GROWS):
                v = bits[2 * r] << 8 | bits[2 * r + 1]
                for c in range(16):
                    if v & (0x8000 >> c):
                        xx, yy = x + c, ly + r
                        if xx + 1 < W_ and yy + 1 < H_ and px[yy + 1][xx + 1] == 1: px[yy + 1][xx + 1] = 3
                        if xx < W_ and yy < H_: px[yy][xx] = 2
            x += advs[g]
    return bytes(px[y][x] << 4 | px[y][x + 1] for y in range(H_) for x in range(0, W_, 2))


def ref_pal(regs_copy, cram):
    """pal 과 같은 셈 — regs_copy: SGL VDP2 사본 바이트(0x120 이상), cram: CRAM 바이트 → 색 참조표 4 칸"""
    g = lambda o: struct.unpack_from('>H', regs_copy, o)[0]
    t = g(0xE0) & 7; sh, cn, dcm = TYPES[t]
    bp = min(3, cn - 1)                                                                   # 고정 레지스터(우선순위는 보일 때 7)
    pr = bp << sh
    ofs = ((g(0xE6) >> 4) & 7) << 8; nm = 1023 if ((g(0x0E) >> 12) & 3) == 0 else 2047
    mn, mi, mx, xi = 0x7FFF, 1, -1, 1
    for i in range(1, dcm + 1):
        c = struct.unpack_from('>H', cram, 2 * ((ofs + i) & nm))[0]
        b = (c & 31) + (c >> 5 & 31) + (c >> 10 & 31)
        if b < mn: mn, mi = b, i
        if b > mx: mx, xi = b, i
    return [0, pr | mi, pr | xi, pr | mi]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    d = build_data()
    z0 = open(os.path.join(ROOT, 'work', '0.bin'), 'rb').read()
    s, sub, lab, lay = patch(z0, d)
    print('글자', len(d[2]), 'AIF', len(d[3]), 'XA', len(d[4]), '/0', len(s), '섹터', (len(s) + 2047) // 2048, '자료 파일', len(sub), '섹터', len(sub) // 2048,
          '상주', hex(lay['RES_SIZE']), '블록 끝', hex(lay['END']))
