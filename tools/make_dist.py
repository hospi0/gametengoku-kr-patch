# -*- coding: utf-8 -*-
r"""게임 천국 배포 묶음 — dist/GameTengoku_KR_<VER>/ : 트랙 01 xdelta + xdelta.exe + readme.txt(CP949) + 한글패치_적용.bat(CP949)
  (모노모노 tools/make_dist.py 를 옮김, 2026-11-09) 바뀌는 트랙: 트랙 01 만(크기 같음, cue 그대로)
  검증: 원본 트랙 01 → xdelta 적용 → md5 = 빌드 트랙 01 md5
  python tools/make_dist.py   (먼저 python tools/discbuild.py --write)"""
import hashlib, os, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

VER = 'v0.9'
XDELTA = r'C:\claude\utils\xdelta.exe'
ROM = 'Game Tengoku - The Game Paradise! (Japan)'
SRC = r'C:\claude\roms\ss\Game Tengoku - The Game Paradise (Japan)'
OUT = os.path.join(ROOT, 'work', 'disc')
NAME = 'GameTengoku_KR_' + VER
TITLE = '게임 천국 (Game Tengoku - The Game Paradise!, 세가 새턴 일본판) 한글 패치 ' + VER


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


README = """{title}
{line}

12개의 트랙으로 이루어진 {rom} 의
트랙 01번에 패치하시면 됩니다.

원본md5 : {o}
패치md5 : {d}

입니다.


[ 적용 방법 ]

  1) 원본 트랙 01 파일을 이 폴더에 복사
       "{bin}"
  2) 한글패치_적용.bat 실행 → 이름 끝에 [KR] 이 붙은 파일이 만들어집니다
  3) 만든 파일 이름을 원본 트랙 01 이름으로 바꿔 넣고, 트랙 02~12 와 cue 는 원본 그대로 쓰세요

  직접 적용:
    xdelta.exe -d -s "원본 트랙 01" "{patch}" "결과 파일"
  (Delta Patcher 같은 xdelta3 GUI 도구로 적용해도 됩니다. 원본이 다르면 xdelta 가 적용을 거부합니다.)


[ 바뀌는 것 ]

  - 음성 자막(새로 추가): 메뉴 점원·나레이션, 캐릭터 대사, 게임 해설·회화 데모 음성극,
    오프닝 노래 가사, 가로·세로(타테) 화면 모두
  - 메뉴 그림 글자: 메인 메뉴·옵션·키 설정·사운드 테스트·데이터 모드·회상 모드
  - 아케이드·어레인지 모드 선택 화면, 게임 중 표시(이름 띠·하이스코어·포즈·스테이지 판·컨티뉴)
  - 스테이지 클리어·보너스, 로딩 화면, 엔딩 문구, 오프닝 크레딧·성우 이름
  - 노래방 월드 가사 글자, 가정용 월드 RPG 전투 창, 랭킹 화면 제목·순위


[ 알려진 점 ]

  - 타이틀 로고, 영어 글자, 포스터 같은 자료 그림은 원본 그대로입니다.
  - 이름 입력판과 랭킹의 이름(기본 이름 포함)은 아직 일본어입니다.
  - 음성 자막은 음성을 받아쓰기한 뒤 번역했습니다. 일부는 원문과 다를 수 있습니다.
  - 음성은 원본 일본어 그대로입니다.
  - 패치 전 세이브스테이트로는 실행하지 마세요. 처음부터 부팅해 주세요.
"""

BAT = r"""@echo off
chcp 949 >nul
set "XD=%~dp0xdelta.exe"
if not exist "%~dp0{bin}" (
  echo   [오류] 원본 트랙 01 파일을 이 폴더에 넣어 주세요 - readme 참고.
  pause & exit /b 1
)
"%XD%" -d -f -s "%~dp0{bin}" "%~dp0{patch}" "%~dp0{kbin}"
if errorlevel 1 (
  echo   [오류] 패치 실패 - 원본이 다를 수 있습니다 - readme 의 원본md5 확인.
  pause & exit /b 1
)
echo   완료: "{kbin}"
pause
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = os.path.join(ROOT, 'dist', NAME)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    b = '%s (Track 01).bin' % ROM
    src, out = os.path.join(SRC, b), os.path.join(OUT, 'Track01.bin')
    patch = NAME + '_Track01.xdelta'; pp = os.path.join(d, patch)
    subprocess.run([XDELTA, '-e', '-9', '-B', '536870912', '-f', '-s', src, out, pp], check=True)
    chk = os.path.join(d, '_check.bin')
    subprocess.run([XDELTA, '-d', '-f', '-s', src, pp, chk], check=True)
    o, want, got = md5(src), md5(out), md5(chk)
    os.remove(chk)
    assert got == want, ('패치 적용 결과가 빌드와 다름', got, want)
    print('트랙 01 원본md5 %s → 패치md5 %s · %s %d B' % (o, want, patch, os.path.getsize(pp)))
    shutil.copy2(XDELTA, os.path.join(d, 'xdelta.exe'))
    kbin = '%s (Track 01) [KR].bin' % ROM
    readme = README.format(title=TITLE, line='=' * 60, rom=ROM, o=o, d=want, bin=b, patch=patch)
    open(os.path.join(d, 'readme.txt'), 'wb').write(readme.replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(d, '한글패치_적용.bat'), 'wb').write(BAT.format(bin=b, patch=patch, kbin=kbin).replace('\n', '\r\n').encode('cp949'))
    z = os.path.join(ROOT, 'dist', NAME + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(d)):
            zf.write(os.path.join(d, f), NAME + '/' + f)
    print('✅', d)
    for f in sorted(os.listdir(d)):
        print('  %-56s %12d' % (f, os.path.getsize(os.path.join(d, f))))
    print('  zip %s %d B · md5 %s' % (os.path.basename(z), os.path.getsize(z), md5(z)))


if __name__ == '__main__':
    main()
