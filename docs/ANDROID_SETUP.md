# Android 설치 및 운영 가이드

Android 공기계 한 대에서 Classroom TV Lite를 실행하고 교실 TV로 미러링하는 방법입니다.
처음 설치할 때만 터미널 명령을 입력하며, 이후에는 서버 실행과 브라우저 접속만 하면 됩니다.

## 1. 준비물

- Android 7 이상 스마트폰 또는 태블릿
- 안정적인 충전기와 Wi-Fi
- HDMI 입력 또는 무선 미러링을 지원하는 TV
- [F-Droid](https://f-droid.org/packages/com.termux/) 또는
  [공식 GitHub](https://github.com/termux/termux-app/releases)의 Termux
- 화면 켜짐 유지 명령을 사용할 경우 같은 출처의
  [Termux:API](https://f-droid.org/packages/com.termux.api/)

Google Play의 Termux는 공식 권장판보다 기능 차이와 제약이 있으므로 F-Droid판 또는
공식 GitHub판을 권장합니다. Termux와 Termux:API를 설치할 경우 두 앱을 반드시 같은
출처에서 받으세요.

## 2. Termux에 설치하기

Termux를 열고 아래 명령을 한 줄씩 실행합니다.

```bash
pkg update
pkg upgrade
pkg install git python termux-api
git clone https://github.com/SKR6582/Classroom_TV_Lite.git
cd Classroom_TV_Lite
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

중간에 계속 진행할지 묻는 화면이 나오면 `Y`를 입력합니다.

## 3. 서버 실행하기

다음 명령을 실행합니다.

```bash
cd ~/Classroom_TV_Lite
source .venv/bin/activate
termux-wake-lock
python app.py
```

`Classroom TV Lite: http://localhost:53111`이 보이면 정상입니다. Termux 화면을
종료하지 말고 홈 버튼으로 나간 뒤 Chrome 또는 삼성 인터넷에서
<http://localhost:53111>을 엽니다.

`termux-wake-lock`이 실패하더라도 대시보드는 실행됩니다. 장시간 운영하려면 같은
출처의 Termux:API 앱이 설치되어 있는지 확인하세요.

## 4. 처음 설정하기

처음 접속하면 설정 페이지가 열립니다. 화면 위에서부터 다음 순서로 입력합니다.

1. 학급 이름
2. NEIS API 키와 학교 정보
3. 학년·반과 교시 시간
4. 월요일부터 금요일 기본 시간표
5. 필요한 경우 날짜별 시간표 변경
6. 교실 공지와 기본 입력된
   [Notion 상세 가이드 주소](https://app.notion.com/p/Classroom-TV-Lite-3dd54b03965e8047b272df3015806757?source=copy_link)
7. TV 거리와 크기에 맞춘 카드별 글씨 크기

학교명 검색이 안 되면 교육청 코드와 표준학교코드를 직접 입력할 수 있습니다.
저장 후 대시보드로 이동하며, 설정은 `~/.classroom-tv-lite/`에 보관됩니다.
Notion 주소를 비우면 대시보드의 가이드 QR은 표시되지 않습니다.

## 5. TV에 연결하기

### 유선 HDMI

USB-C 영상 출력을 지원하는 기기는 USB-C-HDMI 어댑터로 연결할 수 있습니다.
모든 USB-C 기기가 영상 출력을 지원하는 것은 아니므로 기기 사양을 먼저 확인하세요.

1. 스마트폰과 TV를 HDMI 어댑터 및 케이블로 연결합니다.
2. TV 입력을 연결한 HDMI 번호로 바꿉니다.
3. 스마트폰을 가로 방향으로 돌립니다.
4. TV 화면 비율을 `16:9`, `원본`, `화면 맞춤` 중 잘리지 않는 항목으로 설정합니다.

### 무선 미러링

Smart View, 화면 공유, Cast 등 기기에서 제공하는 기능을 사용합니다. 스마트폰과 TV를
같은 Wi-Fi에 연결하고 빠른 설정창에서 미러링 대상을 선택하세요. 학교 Wi-Fi가 기기 간
통신을 차단하면 유선 HDMI가 더 안정적입니다.

## 6. 장시간 운영 설정

- Android 설정에서 Termux와 사용하는 브라우저를 배터리 최적화 대상에서 제외합니다.
- 화면 자동 회전을 켜고 기기를 가로 방향으로 고정합니다.
- 브라우저의 `홈 화면에 추가`를 사용하면 주소창 없이 열기 편합니다.
- 대시보드를 한 번 터치해 화면 켜짐 유지 권한을 다시 요청합니다.
- 저전력 모드를 끄고, 가능하면 배터리 보호 충전 한도를 사용합니다.
- 직사광선과 밀폐 공간을 피하고 기기 발열을 주기적으로 확인합니다.

브라우저에 `화면 켜짐 유지 중`이 표시되면 Wake Lock이 동작 중입니다. 표시가 해제된
경우 화면을 한 번 터치하세요.

## 7. 업데이트와 백업

업데이트 전 설정 화면의 `백업과 도움말`에서 설정 파일을 내보내는 것을 권장합니다.
서버를 `Ctrl+C`로 종료한 뒤 다음 명령을 실행합니다.

```bash
cd ~/Classroom_TV_Lite
git pull --ff-only
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

API 키를 포함한 백업 파일은 외부에 공유하지 마세요.

## 8. 문제 해결

- **페이지가 열리지 않음:** Termux에서 서버가 실행 중인지, 주소가
  `http://localhost:53111`인지 확인합니다.
- **`Address already in use`:** 이전 서버가 실행 중입니다. 기존 Termux 창으로 돌아가
  그 서버를 계속 사용하거나 `Ctrl+C`로 종료한 후 다시 실행합니다.
- **급식·시간표 오류:** 인터넷 연결, NEIS API 키, 교육청 코드와 학교 코드를 확인합니다.
  NEIS 장애 시 기본 시간표 또는 저장된 캐시가 표시될 수 있습니다.
- **화면이 꺼짐:** 배터리 최적화 제외, `termux-wake-lock`, 브라우저 화면 터치를 차례로
  확인합니다.
- **TV 화면이 잘림:** TV의 오버스캔을 끄거나 `화면 맞춤`을 선택합니다.

