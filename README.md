# ⚾ KBO 알림 봇

KBO 경기 일정과 선발 라인업을 텔레그램으로 알려주는 자동화 봇입니다.  
현재 **한화 이글스** 팬을 위해 운영 중이며, n8n 워크플로우와 Python 스크립트로 구동됩니다.

---

## 주요 기능

| 기능 | 시각 | 설명 |
|---|---|---|
| 경기 일정 알림 | 매일 오전 10시 | 오늘 한화 경기 여부, 상대팀, 선발투수, 오늘 KBO 전체 경기 요약 |
| 라인업 알림 | 평일 15–18시 / 주말 11–14시 (5분 폴링) | 네이버 뉴스에서 한화 선발 라인업 파싱 후 타순 전송 |
| 경기 취소 감지 | 위 두 플로우 공통 | 우천취소 등 경기 취소 시 별도 알림 전송 |

---

## 아키텍처

```
GitHub (main push)
    └─▶ GitHub Actions (SSH)
            └─▶ Oracle Cloud VM
                    └─▶ Docker (n8n)
                            ├─▶ check_schedule 워크플로우  ─▶ Naver Sports API ─▶ Telegram
                            └─▶ lineup_polling 워크플로우  ─▶ Naver News API   ─▶ Telegram
```

- **n8n**: 스케줄 트리거 및 워크플로우 오케스트레이션
- **Python 스크립트**: 로컬 테스트 및 로직 검증용 독립 실행 파일
- **GitHub Actions**: `main` 브랜치 푸시 시 SSH로 서버에 자동 배포
- **Docker**: n8n 컨테이너 기반 운영

---

## 디렉터리 구조

```
kbo-bot/
├── workflows/
│   ├── check_schedule.json   # 경기 일정 확인 n8n 워크플로우
│   └── lineup_polling.json   # 라인업 폴링 n8n 워크플로우
├── scripts/
│   ├── check_schedule.py     # 경기 일정 확인 (로컬 테스트용)
│   └── lineup_polling.py     # 라인업 폴링 (로컬 테스트용)
├── .github/workflows/
│   └── deploy.yml            # GitHub Actions CI/CD
├── docker-compose.yml        # 로컬 개발용
├── docker-compose.prod.yml   # 프로덕션 배포용
├── deploy.sh                 # 서버 배포 스크립트
└── .env.example              # 환경변수 샘플
```

---

## 시작하기

### 1. 사전 요구사항

- Docker, Docker Compose
- 텔레그램 봇 토큰 및 채팅방 ID
- [네이버 Open API](https://developers.naver.com) 애플리케이션 (뉴스 검색용)

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열고 아래 값을 채워 넣습니다.

```env
TELEGRAM_BOT_TOKEN=       # BotFather에서 발급
TELEGRAM_BOT_CHAT_ID=     # 알림 받을 채팅방 ID
NAVER_CLIENT_ID=          # 네이버 API 클라이언트 ID
NAVER_CLIENT_SECRET=      # 네이버 API 클라이언트 시크릿
```

### 3. 로컬 실행

```bash
# n8n 컨테이너 시작
docker-compose up -d

# 브라우저에서 n8n 접속
open http://localhost:5678

# 워크플로우 임포트 (n8n UI에서 직접 임포트하거나 아래 명령 사용)
docker exec -i n8n n8n import:workflow --input=/dev/stdin < workflows/check_schedule.json
docker exec -i n8n n8n import:workflow --input=/dev/stdin < workflows/lineup_polling.json
```

### 4. Python 스크립트 단독 실행 (테스트)

```bash
pip install requests pytz

TELEGRAM_BOT_TOKEN=xxx NAVER_CLIENT_ID=xxx NAVER_CLIENT_SECRET=xxx \
    python scripts/check_schedule.py
```

---

## 배포 (CI/CD)

`main` 브랜치에 푸시하면 GitHub Actions가 SSH로 서버에 접속하여 `deploy.sh`를 실행합니다.

```bash
# deploy.sh 흐름
git pull
→ 워크플로우 n8n으로 임포트
→ 워크플로우 활성화
→ n8n 컨테이너 재시작
```

GitHub 저장소 Secrets에 아래 값을 설정해야 합니다.

| Secret | 설명 |
|---|---|
| `SSH_HOST` | 서버 IP 또는 도메인 |
| `SSH_USER` | SSH 접속 사용자명 |
| `SSH_PRIVATE_KEY` | SSH 개인키 |

---

## 사용 API

| API | 용도 | 인증 |
|---|---|---|
| Naver Sports API (`api-gw.sports.naver.com`) | KBO 경기 일정 및 상세 정보 | 불필요 (public) |
| Naver Open API (뉴스 검색) | 선발 라인업 기사 탐색 | 클라이언트 ID/시크릿 |
| Telegram Bot API | 메시지 전송 | 봇 토큰 |

---

## 추후 확장 방안

현재 봇은 한화 이글스 단일 팀을 대상으로 하드코딩되어 있습니다.  
이를 **멀티팀 지원 텔레그램 챗봇**으로 발전시키는 것을 목표로 합니다.

### 목표

> 사용자가 원하는 KBO 팀을 설정하면, 경기 알림부터 라인업 파싱 로직까지 모든 코드와 프롬프트가 해당 팀 기준으로 자동 반영되는 인터랙티브 텔레그램 챗봇

```
사용자: /setteam 두산
봇: ✅ 팀이 두산 베어스로 설정되었습니다!
    이제부터 두산 경기 일정과 라인업을 알려드릴게요 ⚾

사용자: /setteam KIA
봇: ✅ 팀이 KIA 타이거즈로 설정되었습니다!
```

### 구현 계획

- **팀 설정 명령어** (`/setteam <팀명>`): 사용자별 팀 코드와 팀명을 DB 또는 파일에 저장
- **동적 팀 코드 반영**: 현재 하드코딩된 팀 코드(`HH`)와 팀명(`한화`)을 설정값에서 읽어오도록 전면 변경
- **라인업 검색 쿼리 자동화**: `"한화 이글스 라인업"` 같은 검색어를 설정된 팀에 맞게 자동 생성
- **라인업 파싱 패턴 일반화**: 특정 팀명에 의존하는 정규식과 문자열 매칭을 팀 설정값 기반으로 범용 처리
- **알림 메시지 템플릿화**: 팀 이름·이모지·고유 응원 문구를 팀별로 설정 가능하도록 구성
- **다중 사용자 지원**: 각 사용자(chat_id)가 독립적으로 팀을 설정하고 알림을 수신

### KBO 팀 코드 목록

| 팀명 | 코드 | | 팀명 | 코드 |
|---|---|---|---|---|
| 한화 이글스 | `HH` | | KIA 타이거즈 | `HT` |
| 두산 베어스 | `OB` | | LG 트윈스 | `LG` |
| 삼성 라이온즈 | `SS` | | NC 다이노스 | `NC` |
| 롯데 자이언츠 | `LT` | | SSG 랜더스 | `SK` |
| KT 위즈 | `KT` | | 키움 히어로즈 | `WO` |

---

## 라이선스

MIT
