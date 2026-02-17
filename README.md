# 네이버 블로그 경제 기사 자동 수집 시스템

매일 경제 뉴스(네이버 뉴스)와 유튜브 경제 채널 영상을 자동 수집하고, 블로그에 올릴 수 있는 초안을 생성하는 Python 스크립트입니다.

GitHub Actions로 매일 오전 9시(KST)에 자동 실행되며, 결과를 Gmail로 발송합니다.

## 동작 흐름

```
네이버 뉴스 API → 키워드별 당일 기사 수집
YouTube Data API → 지정 채널 당일 영상 + 자막 수집
        ↓
주제별 분류 (주제당 3건) + 블로그 포맷 변환
        ↓
마크다운(.md) + HTML(.html) 파일 저장
        ↓
Gmail 자동 발송
```

## 프로젝트 구조

```
naver-blog/
├── src/
│   ├── main.py                 # 메인 파이프라인
│   ├── config.py               # 설정값 (키워드, 채널, 주제 등)
│   ├── collectors/
│   │   ├── naver_news.py       # 네이버 뉴스 수집기
│   │   └── youtube.py          # 유튜브 영상 수집기
│   ├── formatter/
│   │   └── blog_formatter.py   # 블로그 초안 포맷터
│   └── output/
│       ├── draft_manager.py    # 파일 저장
│       └── email_sender.py     # Gmail 발송
├── drafts/                     # 생성된 블로그 초안 (날짜별)
├── .github/workflows/
│   └── daily-blog.yml          # GitHub Actions 워크플로우
├── requirements.txt
├── .env.example
└── .gitignore
```

## 설정 방법

### 1. API 키 발급

| API | 발급처 | 비용 |
|-----|--------|------|
| 네이버 검색 API | [Naver Developers](https://developers.naver.com/) | 무료 (일 25,000건) |
| YouTube Data API v3 | [Google Cloud Console](https://console.cloud.google.com/) | 무료 (일 10,000 유닛) |
| Gmail 앱 비밀번호 | [Google 앱 비밀번호](https://myaccount.google.com/apppasswords) | 무료 (2단계 인증 필요) |

### 2. 환경변수 설정

`.env.example`을 `.env`로 복사 후 값을 입력합니다:

```bash
cp .env.example .env
```

```env
NAVER_CLIENT_ID=네이버_Client_ID
NAVER_CLIENT_SECRET=네이버_Client_Secret
YOUTUBE_API_KEY=유튜브_API_키
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=16자리_앱_비밀번호
```

### 3. 실행

```bash
pip install -r requirements.txt
python -m src.main              # 실행
python -m src.main --overwrite  # 기존 파일 덮어쓰기
```

## 커스터마이징

모든 수집 설정은 `src/config.py` 한 파일에서 관리합니다.

### 뉴스 검색 키워드 변경

`NEWS_KEYWORDS` 리스트를 수정하면 네이버 뉴스 검색어가 바뀝니다:

```python
# src/config.py
NEWS_KEYWORDS = ["증시", "환율", "금리", "부동산", "코스피", "코스닥", "경제", "조선주", "반도체", "재테크"]
```

예시) IT 뉴스를 추가하고 싶다면:
```python
NEWS_KEYWORDS = ["증시", "환율", "금리", "부동산", "코스피", "코스닥", "경제", "조선주", "반도체", "재테크", "AI", "스타트업"]
```

### 뉴스 주제 분류 변경

`TOPIC_KEYWORDS`를 수정하면 기사가 어떤 주제로 분류되는지 바뀝니다:

```python
# src/config.py
TOPIC_KEYWORDS = {
    "증시": ["증시", "코스피", "코스닥", "주식", "상장", "종목", "주가"],
    "환율": ["환율", "달러", "엔화", "위안", "원화"],
    # ... 기존 주제들 ...

    # 새 주제 추가 예시
    "AI": ["AI", "인공지능", "ChatGPT", "딥러닝", "LLM"],
}
```

기사 제목/설명에 해당 키워드가 포함되면 그 주제로 분류됩니다.

### 주제별 기사 수 변경

```python
# src/config.py
MAX_ARTICLES_PER_TOPIC = 3  # 주제당 최대 기사 수 (기본: 3)
```

### 유튜브 채널 변경

`YOUTUBE_CHANNEL_IDS` 리스트에서 채널을 추가/삭제합니다:

```python
# src/config.py
YOUTUBE_CHANNEL_IDS = [
    "UCF8AeLlUbEpKju6v1H6p8Eg",   # 한국경제TV
    "UCsJ6RuBiTVWRX156FVbeaGg",   # 슈카월드
    "UCJo6G1u0e_-wS-JQn3T-zEw",   # 머니코믹스
    "UChlv4GSd7OQl3js-jkLOnFA",   # 삼프로TV
    "UCntrdZrZwXiPxdObi5MHqBw",   # 채널 5
]
```

채널 ID 찾는 법:
1. 유튜브에서 해당 채널 페이지 이동
2. 주소창의 `youtube.com/channel/` 뒤에 오는 문자열이 채널 ID
3. `@채널명` 형태의 URL인 경우: 채널 페이지 → 우클릭 → 페이지 소스 보기 → `channel_id` 검색

### 실행 시간 변경

`.github/workflows/daily-blog.yml`에서 cron 스케줄을 수정합니다:

```yaml
schedule:
  - cron: "0 0 * * *"   # UTC 00:00 = KST 09:00
```

| 원하는 시간(KST) | cron 설정 (UTC) |
|---|---|
| 오전 6시 | `0 21 * * *` (전날) |
| 오전 7시 | `0 22 * * *` (전날) |
| 오전 9시 | `0 0 * * *` |
| 오후 12시 | `0 3 * * *` |

## GitHub Actions 자동화

Repository Settings → Secrets and variables → Actions에 아래 5개 Secret을 추가하면 자동화가 동작합니다:

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `YOUTUBE_API_KEY`
- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`
