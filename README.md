# ⚾ KBO 알림 봇

KBO 경기 일정과 선발 라인업을 텔레그램으로 알려주는 자동화 봇입니다.  
현재 **한화 이글스** 팬을 위해 운영 중이며, Python 스크립트와 Docker로 구동됩니다.

---

## 주요 기능

| 기능 | 시각 | 설명 |
|---|---|---|
| 경기 일정 알림 | 매일 오전 10시 | 오늘 한화 경기 여부, 상대팀, 선발투수, 오늘 KBO 전체 경기 요약 |
| 라인업 알림 | 경기 시작 3시간 전부터 5분 간격 폴링 | 네이버 뉴스에서 한화 선발 라인업 기사 감지 후 타순·선발투수 전송 |
| 경기 취소 감지 | 위 두 기능 공통 | 우천취소 등 경기 취소 시 별도 알림 전송 |

---

## 아키텍처

```
GitHub (main push)
    └─▶ GitHub Actions (SSH)
            └─▶ Oracle Cloud VM
                    └─▶ Docker (kbo-bot)
                            ├─▶ check_schedule   ─▶ Naver Sports API ─▶ Telegram
                            └─▶ lineup_polling   ─▶ Naver News API + GPT-4o-mini ─▶ Telegram
```

- **APScheduler**: 매일 10:00 경기 확인 / 5분 간격 라인업 폴링
- **GitHub Actions**: `main` 브랜치 푸시 시 SSH로 서버 자동 배포
- **Docker**: Python 컨테이너 기반 24/7 운영, 상태는 볼륨(`/data/state.json`)에 저장

---

## 디렉터리 구조

```
kbo-bot/
├── scripts/
│   ├── main.py              # APScheduler 진입점
│   ├── check_schedule.py    # 경기 일정 확인 및 알림
│   ├── lineup_polling.py    # 라인업 기사 탐색 및 알림
│   ├── kbo_api.py           # Naver Sports API 클라이언트
│   ├── naver_news.py        # 네이버 뉴스 검색 + HTML 파싱
│   ├── lineup_parser.py     # GPT-4o-mini 라인업 파싱
│   ├── telegram.py          # 텔레그램 발송
│   └── state.py             # 당일 상태 관리 (/data/state.json)
├── workflows/               # 구 n8n 워크플로우 (참고용)
├── .github/workflows/
│   └── deploy.yml           # GitHub Actions CI/CD
├── Dockerfile.kbot          # Python 컨테이너
├── requirements.txt
├── docker-compose.yml       # 로컬 개발용
├── docker-compose.prod.yml  # 프로덕션 배포용
└── .env.example             # 환경변수 샘플
```

---

## 시작하기

### 1. 사전 요구사항

- Docker, Docker Compose
- 텔레그램 봇 토큰 및 채팅방 ID
- [네이버 Open API](https://developers.naver.com) 애플리케이션 (뉴스 검색용)
- OpenAI API 키 (GPT-4o-mini, 라인업 파싱용)

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
GPT_API_KEY=              # OpenAI API 키
```

### 3. 로컬 실행

```bash
docker compose up -d --build kbo-bot
docker compose logs -f kbo-bot
```

### 4. 스크립트 단독 실행 (테스트)

```bash
pip install -r requirements.txt

cd scripts
python check_schedule.py   # 오늘 경기 확인 및 텔레그램 발송
```

---

## 배포 (CI/CD)

`main` 브랜치에 푸시하면 GitHub Actions가 SSH로 서버에 접속하여 kbo-bot 컨테이너를 재빌드·재시작합니다.

```
git push origin main
→ SSH 접속
→ git pull
→ docker compose up -d --build kbo-bot
```

GitHub 저장소 Secrets에 아래 값을 설정해야 합니다.

| Secret | 설명 |
|---|---|
| `SSH_HOST` | 서버 IP 또는 도메인 |
| `SSH_USER` | SSH 접속 사용자명 |
| `SSH_PRIVATE_KEY` | SSH 개인키 |

---

## 동작 흐름

```
[매일 10:00 KST]
check_schedule 실행
├── 한화 경기 없음 → 종료
├── 경기 취소 → 취소 알림 발송 → 종료
└── 경기 있음 → 일정 알림 발송 → state.json에 game_time 저장

[5분 간격]
lineup_polling 실행
├── 오늘 경기 없음 / 이미 발송 → 스킵
├── 경기 시작 3시간 전 이전 or 시작 1시간 후 이후 → 스킵
├── 네이버 뉴스에 라인업 기사 없음 → 스킵 (5분 후 재시도)
└── 기사 발견 → HTML 파싱 → GPT 라인업 추출
    ├── 라인업 정상 → 타순 알림 발송 → lineup_sent=true 저장
    └── 경기취소 감지 → 취소 알림 발송
```

---

## 사용 API

| API | 용도 | 인증 |
|---|---|---|
| Naver Sports API (`api-gw.sports.naver.com`) | KBO 경기 일정 및 상세 정보 | 불필요 (public) |
| Naver Open API (뉴스 검색) | 선발 라인업 기사 탐색 | 클라이언트 ID/시크릿 |
| OpenAI API (GPT-4o-mini) | 기사 본문에서 라인업 JSON 추출 | API 키 |
| Telegram Bot API | 메시지 전송 | 봇 토큰 |

---

## KBO 팀 코드

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
