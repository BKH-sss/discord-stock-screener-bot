# ?? 미국 주식 3개년 성장성 & 재무 건전성 디스코드 봇

매일 아침 7시(KST)에 **부채비율 120% 이하**를 만족하는 종목 중 다음 3가지 항목의 **TOP 20**을 디스코드로 알림 전송합니다:
1. **최근 3년간 자산 증가율 TOP 20**
2. **최근 3년간 영업이익 증가율 TOP 20**
3. **최근 3년간 매출액 증가율 TOP 20**

---

## ??? 설정 및 사용법

### 1. 패키지 설치
\\\ash
pip install -r requirements.txt
\\\

### 2. 환경변수 설정 (\.env\)
디스코드 서버의 채널 설정 -> [연동] -> [웹후크]에서 웹후크 URL을 생성한 후, 프로젝트 루트에 \.env\ 파일을 생성하고 등록합니다:

\\\env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_id/your_webhook_token
\\\

### 3. 실행 방법

#### (방법 1) 즉시 1회 실행 / 테스트
\\\ash
python stock_bot.py
\\\

#### (방법 2) 로컬 / 개인 서버에서 상시 실행 (매일 아침 7시)
\\\ash
python scheduler.py
\\\

#### (방법 3) 무료 클라우드 자동 실행 (GitHub Actions 추천)
1. 본 프로젝트를 본인의 GitHub 저장소에 Push합니다.
2. GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions** 메뉴로 이동합니다.
3. **New repository secret**을 클릭하여 다음을 등록합니다:
   - Name: \DISCORD_WEBHOOK_URL\
   - Value: 디스코드 웹후크 URL 붙여넣기
4. \.github/workflows/daily_stock_report.yml\에 의해 **매일 아침 7시(KST / UTC 22:00)** 에 완전 무료로 자동 실행됩니다.
