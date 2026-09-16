# iPhone·iPad 접속 및 TV 연결 가이드

iOS와 iPadOS에서는 Termux를 사용할 수 없고 일반 앱이 Flask 서버를 계속 실행하기도
어렵습니다. 따라서 iPhone 또는 iPad는 **화면 표시와 TV 미러링용**으로 사용하고,
Classroom TV Lite 서버는 Android, Mac, PC 또는 Raspberry Pi에서 실행해야 합니다.

## 1. 구성 확인

필요한 기기는 다음과 같습니다.

- Classroom TV Lite 서버를 실행할 Android, Mac, PC 또는 Raspberry Pi
- Safari를 사용할 iPhone 또는 iPad
- 두 기기가 함께 연결된 Wi-Fi
- AirPlay 지원 TV·Apple TV 또는 HDMI 어댑터

iPhone 한 대만으로 설치·서버 실행·미러링을 모두 처리하는 방식은 권장하지 않습니다.

## 2. 서버를 같은 Wi-Fi에 공개하기

서버 기기에서 저장소 폴더로 이동한 뒤 외부 접속을 허용하여 실행합니다.

```bash
source .venv/bin/activate
CLASSROOM_HOST=0.0.0.0 python app.py
```

Android Termux라면 먼저 다음과 같이 이동합니다.

```bash
cd ~/Classroom_TV_Lite
source .venv/bin/activate
CLASSROOM_HOST=0.0.0.0 python app.py
```

서버 기기의 Wi-Fi 상세 정보에서 IP 주소를 확인합니다. 예를 들어 IP 주소가
`192.168.0.25`라면 iPhone Safari에서 아래 주소를 엽니다.

```text
http://192.168.0.25:53111
```

`localhost`는 서버를 실행하는 기기 자신을 뜻합니다. iPhone에서
`http://localhost:53111`을 열면 다른 기기의 서버에 연결되지 않습니다.

## 3. 초기 설정하기

설정은 iPhone이 아니라 서버 기기에 저장됩니다. NEIS API 키가 Wi-Fi에서 평문 HTTP로
전송되지 않도록 **서버 기기의 브라우저에서 `http://localhost:53111`을 열어** 다음
항목을 먼저 설정하는 것을 권장합니다.

1. 학급 이름
2. NEIS API 키와 학교 정보
3. 학년·반과 교시 시간
4. 기본 시간표와 날짜별 변경
5. 교실 공지
6. TV 거리와 크기에 맞춘 카드별 글씨 크기

설정을 한 번 저장하면 iPhone에서는 서버의 IP 주소로 접속만 해도 동일한 대시보드가
보입니다.

## 4. 홈 화면에서 전체 화면으로 열기

1. Safari에서 대시보드 주소를 엽니다.
2. 공유 버튼을 누릅니다.
3. `홈 화면에 추가`를 선택합니다.
4. 추가된 Classroom TV 아이콘을 눌러 실행합니다.
5. 기기를 가로 방향으로 돌립니다.

가로 화면으로 전환되지 않으면 제어 센터에서 화면 방향 잠금을 끄세요.

## 5. 화면이 꺼지지 않게 설정하기

같은 Wi-Fi의 `http://192.168...` 주소는 HTTPS 보안 연결이 아니므로 iOS의 브라우저
Wake Lock이 동작하지 않을 수 있습니다. 안정적인 장시간 표시를 위해 아래 설정을
사용하세요.

1. `설정 → 디스플레이 및 밝기 → 자동 잠금 → 안 함`
2. 저전력 모드 끄기
3. 충전기에 연결
4. 필요하면 `설정 → 손쉬운 사용 → 사용법 유도`를 켜서 다른 앱으로 빠지는 것을 방지

조직에서 관리하는 기기는 `자동 잠금 → 안 함`을 선택할 수 없을 수 있습니다. 이 경우
기기 관리자 정책을 확인하거나 HTTPS 연결을 별도로 구성해야 합니다.

## 6. TV에 연결하기

### AirPlay

1. iPhone 또는 iPad와 TV를 같은 Wi-Fi에 연결합니다.
2. 제어 센터를 엽니다.
3. `화면 미러링`을 누릅니다.
4. Apple TV 또는 AirPlay 지원 TV를 선택합니다.
5. TV에 코드가 표시되면 iPhone에 입력합니다.

화면이 잘리면 TV의 화면 비율을 `16:9` 또는 `화면 맞춤`으로 설정합니다. Apple TV를
사용한다면 AirPlay 디스플레이 언더스캔 설정도 확인하세요.

### 유선 HDMI

- USB-C iPhone·iPad: USB-C-HDMI 어댑터
- Lightning iPhone·iPad: Lightning Digital AV 어댑터

어댑터와 HDMI 케이블을 연결하고 TV 입력을 해당 HDMI 번호로 변경합니다. 수업 중
지연과 무선 끊김을 줄이려면 유선 연결이 가장 안정적입니다.

## 7. 보안 주의사항

`CLASSROOM_HOST=0.0.0.0`으로 실행하면 같은 네트워크의 다른 기기도 서버에 접속할 수
있습니다.

- 신뢰할 수 있는 교실·개인 Wi-Fi에서만 사용합니다.
- 공유기에서 53111 포트 포워딩을 설정하지 않습니다.
- 공용 Wi-Fi에서는 NEIS API 키 설정 화면을 열지 않는 것을 권장합니다.
- 사용이 끝나면 서버 터미널에서 `Ctrl+C`를 눌러 종료합니다.

## 8. 문제 해결

- **Safari에서 연결할 수 없음:** 두 기기가 같은 Wi-Fi인지, 서버 명령에
  `CLASSROOM_HOST=0.0.0.0`이 포함됐는지, IP 주소가 바뀌지 않았는지 확인합니다.
- **학교 Wi-Fi에서만 실패:** 네트워크가 기기 간 통신을 차단할 수 있습니다. 개인
  핫스팟 또는 별도 공유기를 사용하거나 Android 기기에서 직접 실행하세요.
- **AirPlay 대상이 안 보임:** TV와 iPhone의 Wi-Fi, AirPlay 활성화 여부를 확인합니다.
- **화면이 꺼짐:** 자동 잠금을 `안 함`으로 바꾸고 저전력 모드를 끕니다.
- **주소창이 계속 보임:** Safari 공유 메뉴의 `홈 화면에 추가`로 실행합니다.
- **설정이 저장되지 않음:** 설정은 iPhone이 아닌 서버 기기의 저장 공간에 기록됩니다.

