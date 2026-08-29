# 네이버 블로그 자동화

경제 뉴스를 매일 수집하고, Claude로 블로그 글을 쓰고, 네이버에 붙여넣기 좋게 넘겨주는 Python 도구입니다.

**발행 버튼은 사람이 누릅니다.** 자동 발행은 하지 않습니다 ([왜 그런지](#왜-자동-발행은-하지-않나요)).

## 동작 흐름

```
[1] 수집 (매일 09:00 KST, GitHub Actions 자동)
    네이버 뉴스 API + YouTube Data API
            ↓  주제별 분류 (주제당 3건)
    drafts/YYYY-MM-DD.md + .html  →  Gmail 발송

[2] 글쓰기 (python -m src.compose)
    수집 초안 또는 임의 주제
            ↓  Claude API (blog-post.md의 문체를 따라)
    posts/YYYY-MM-DD-제목.md

[3] 붙여넣기 (python -m src.handoff)
    제목·본문·태그 복사 버튼이 달린 페이지 한 장
            ↓  서식 유지한 채로 세 번 붙여넣기
    사람이 확인하고 [발행] 클릭
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
│   ├── output/
│   │   ├── draft_manager.py    # 초안 저장/읽기
│   │   └── email_sender.py     # Gmail 발송
│   ├── compose.py              # [글쓰기] CLI
│   ├── generator/
│   │   ├── style.py            # 문체 규칙 + 시스템 프롬프트
│   │   ├── post_writer.py      # Claude API 호출
│   │   └── post_file.py        # 완성글 파일 형식
│   ├── handoff.py              # [붙여넣기] CLI
│   └── publisher/
│       ├── handoff_page.py     # 복사 버튼 달린 페이지 생성
│       ├── markdown_html.py    # 마크다운 → 붙여넣기용 HTML (기본)
│       └── editor_text.py      # 마크다운 → 평문 ([평문으로] 대비책)
├── drafts/                     # 수집 초안 (날짜별, 자동 커밋)
├── posts/                      # 완성글 (gitignore됨)
├── blog-post.md                # 문체 학습용 예시 글
├── .github/workflows/
│   └── daily-blog.yml          # GitHub Actions 워크플로우
├── requirements.txt            # 수집용 (CI가 설치)
├── requirements-write.txt      # 글쓰기·발행용 (로컬)
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
| Claude API | [Anthropic Console](https://console.anthropic.com/) | 유료 (글 한 편 약 $0.05~0.15) |

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
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 3. 설치

```bash
pip3 install -r requirements-write.txt
```

`requirements.txt`는 수집만 돌리는 GitHub Actions용으로 가볍게 유지합니다.
로컬에서 글쓰기까지 쓰려면 위처럼 `requirements-write.txt`를 설치하세요.

[3] 붙여넣기 단계는 추가 설치가 필요 없습니다. 표준 라이브러리만 씁니다.

## 사용법

### [1] 뉴스 수집

```bash
python -m src.main              # 오늘 뉴스 수집 → drafts/
python -m src.main --overwrite  # 기존 파일 덮어쓰기
```

GitHub Actions가 매일 09:00 KST에 자동 실행하므로 보통 직접 칠 일은 없습니다.

### [2] 글쓰기

```bash
# 오늘 수집한 뉴스로 글 쓰기
python -m src.compose

# 특정 날짜 초안으로
python -m src.compose --date 2026-08-25

# 아무 주제나
python -m src.compose --topic "맥북에서 개발 환경 세팅한 이야기"

# 참고 메모를 같이 주면 그 내용을 재료로 씁니다
python -m src.compose --topic "재테크 앱 3개 써본 후기" --notes "토스는 UI가 좋고, 뱅크샐러드는 자산 연동이 빠르고..."

# 이번 글에만 적용할 지시
python -m src.compose --instruction "이번엔 반도체 이야기를 중심으로"
```

결과는 `posts/YYYY-MM-DD-제목.md`에 저장됩니다. 발행 전에 열어서 고치세요.

**메모 없이 개인 경험을 요구하면 글에 `[여기에 경험 추가]` 표시만 남습니다.** 없는 경험을
지어내지 않도록 일부러 막아둔 동작입니다.

### [3] 붙여넣기

```bash
python -m src.handoff                              # posts/의 최신 글
python -m src.handoff posts/2026-08-26-어쩌고.md    # 특정 글
python -m src.handoff --no-open                    # 파일만 만들고 안 엶
```

브라우저에 복사 버튼 세 개짜리 페이지가 열립니다. 네이버 글쓰기 창을 옆에 띄워두고
위에서부터 제목 → 본문 → 태그 순으로 붙여넣으면 됩니다.

본문은 **서식이 살아서** 들어갑니다. 소제목, 굵게, 링크, 목록이 그대로 붙습니다.
서식이 이상하게 들어가는 날엔 같은 자리의 [평문으로] 버튼을 쓰면 됩니다.

로그인도, 세션도, 브라우저 자동화도 필요 없습니다. 글 파일 하나만 읽습니다.
**발행 버튼은 직접 누르세요.** 사진은 에디터에서 넣는 게 빠릅니다.

## 왜 자동 발행은 하지 않나요

네이버 공식 글쓰기 API는 [2020년 5월에 종료](https://www.newspim.com/news/view/20200413000737)됐고
대체 API가 없습니다. 남은 방법은 브라우저 자동화뿐인데, 네이버는 "사람의 물리적인 작성 및 등록
범주"를 벗어난 접근을 차단 대상으로 보고 있습니다. 무인 자동 발행은 계정 제재 위험이 있습니다.

그래서 이 도구는 **클립보드까지만** 채웁니다. 마지막 클릭이 사람 몫으로 남으면 제재 위험이
낮아지고, 잘못 쓴 글이 그대로 올라가는 사고도 막힙니다.

덤으로, 붙여넣기는 타이핑보다 결과가 좋습니다. 스마트에디터는 마크다운을 해석하지 않아서
키보드로 치면 `##`와 `**`를 떼어낸 평문만 들어가지만, 클립보드는 HTML을 함께 실어 나릅니다.
소제목과 굵게를 에디터에서 다시 입힐 일이 없어집니다.

## 문체 바꾸기

글의 톤은 두 곳에서 결정됩니다.

1. `blog-post.md` — 예시 글. 이 글의 톤을 따라 씁니다. 다른 글로 바꾸면 톤이 바뀝니다.
2. `src/generator/style.py`의 `STYLE_RULES` — 명시적인 규칙 (존댓말, 문단 길이, 금지 표현 등)

예시 글을 바꾸는 쪽이 규칙을 고치는 것보다 효과가 큽니다.

## 붙여넣기가 이상할 때

**서식이 깨져서 붙는다면** 같은 자리의 [평문으로] 버튼을 쓰세요. 기호를 걷어낸 평문이
들어가고, 서식은 에디터에서 입히면 됩니다.

**글에 배경색이 따라 붙는다면** 복사 원본에 페이지 스타일이 샌 것입니다. 크롬은 선택 영역을
복사할 때 계산된 스타일을 인라인으로 박아 보냅니다. `handoff_page.py`의 CSS에서 리셋 범위가
`.wrap, .wrap *`인지 확인하세요. 전역 `*`로 되돌리면 이 증상이 재발합니다.

**태그가 한 덩어리로 들어간다면** 칩을 하나씩 눌러 개별 복사하면 됩니다.

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
