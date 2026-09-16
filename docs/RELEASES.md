# stable 브랜치 배포 가이드

Classroom TV Lite는 개발 코드와 사용자 기기에 배포되는 코드를 분리합니다.

- `main`: 개발과 검증에 사용하는 브랜치
- `stable`: 비개발자 사용자에게 배포하는 브랜치

설정 페이지의 업데이트 버튼은 `origin/stable`만 확인합니다. 사용자는 Git 명령을
입력하지 않고 검증된 버전만 받을 수 있습니다.

## 최초 stable 브랜치 만들기

모든 테스트를 통과한 `main`에서 한 번만 실행합니다.

```bash
git switch main
git branch stable
git push -u origin stable
```

## 새 버전 배포하기

1. `main`에서 기능 개발과 테스트를 완료합니다.
2. 작업 트리가 깨끗하고 원격 `main`과 동기화됐는지 확인합니다.
3. `stable`을 `main`까지 fast-forward 합니다.

```bash
git switch main
git pull --ff-only origin main
python -m unittest discover -s tests -v
node --test tests/test_time.mjs tests/test_display.mjs

git switch stable
git merge --ff-only main
git push origin stable
git switch main
```

`stable`에는 직접 기능 커밋을 만들지 않습니다. `--ff-only`가 실패하면 브랜치 이력이
갈라진 것이므로 강제 푸시하지 말고 원인을 먼저 확인합니다.

## 사용자 기기의 업데이트 동작

설정 페이지에서 업데이트를 실행하면 앱이 다음 순서로 처리합니다.

1. 작업 트리에 수정된 파일이 없는지 확인
2. `origin/stable` 최신 상태 조회
3. 로컬 코드가 stable까지 fast-forward 가능한지 확인
4. 코드 업데이트
5. `requirements.txt` 의존성 설치
6. 서버 자동 재시작

수정된 파일, 로컬 전용 커밋 또는 갈라진 이력이 발견되면 사용자 데이터를 보호하기
위해 업데이트를 중단합니다. 설정과 캐시는 저장소 밖의 `~/.classroom-tv-lite/`에
있으므로 정상 업데이트 중에는 삭제되지 않습니다.

## 문제 버전 대응

이미 배포한 `stable`을 강제로 과거 커밋으로 되돌리지 않습니다. `main`에서 수정
커밋을 만든 뒤 테스트하고 다시 `stable`로 fast-forward 하는 방식으로 대응합니다.

