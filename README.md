# @namja_sokmaeum 자동 업로드

매일 밤 9시(한국 시간)에 GitHub Actions가 `posts.json`에서 아직 안 올린 게시물 1개를 골라 인스타그램에 캐러셀로 올립니다.

```
make_cards.py      문구(posts.json) → 카드 이미지(out/*.jpg)
publish.mjs        out/ 이미지를 인스타그램 API로 업로드
published.json     이미 올린 게시물 기록 (자동 갱신)
.github/workflows/publish.yml   매일 실행 스케줄
```

## 1. 인스타 계정 준비
1. 프로필 사진에 `profile.jpg` 올리기
2. 설정 → 계정 유형 및 도구 → **프로페셔널 계정으로 전환 → 비즈니스**

## 2. Meta 개발자 앱 (완료)
- 통합 로그인 구성 + 시스템 사용자 토큰 (만료되지 않음, 갱신 불필요)
- 토큰은 채팅·코드에 붙여넣지 말고 GitHub Secrets에만 저장

## 3. GitHub 저장소 만들기
1. GitHub에서 **Public** 저장소 생성 (이미지를 인스타가 가져갈 수 있어야 해서 공개여야 함)
2. 이 폴더 전체를 `main` 브랜치에 push
3. 저장소 Settings → Secrets and variables → Actions → **New repository secret**
   - `IG_TOKEN` : 개발자 화면에서 받은 토큰 (필수)
   - `IG_USER_ID` : 개발자 화면에 Instagram 계정 ID가 보이면 넣기 (선택, 없으면 자동 확인)

## 4. 테스트
저장소 Actions 탭 → **인스타 자동 업로드 → Run workflow** 에서 mode 선택
1. `check` : 토큰과 계정 연결 확인 → 로그에 `@namja_sokmaeum`과 "게시 권한 OK"가 나오면 성공
2. `dry_run` : 다음에 올릴 게시물 이미지·캡션 확인
3. `publish` : 실제 업로드
이후에는 매일 밤 9시에 자동으로 1개씩 올라갑니다.

## 새 게시물 추가
1. `posts.json`에 게시물 추가
2. `python3 make_cards.py posts.json out` 으로 이미지 생성
3. `out/`, `posts.json` 커밋 & push → 순서대로 자동 업로드
