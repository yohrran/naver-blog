import re
from datetime import datetime, timedelta, timezone
from html import escape

from src.config import MAX_ARTICLES_PER_TOPIC, TOPIC_KEYWORDS

KST = timezone(timedelta(hours=9))

STOPWORDS = {
    "이", "가", "은", "는", "을", "를", "에", "의", "와", "과", "로", "으로",
    "도", "에서", "한", "하는", "하고", "및", "등", "더", "또", "그", "이번",
    "지난", "올해", "내년", "대한", "관련", "통해", "위해", "대해", "위", "대",
    "수", "것", "일", "말", "중", "후", "전", "통", "오늘", "내일", "어제",
    "최근", "현재", "향후", "올해도", "이후", "당일", "해당", "기자",
}

TOPIC_ICONS = {
    "증시": "📈",
    "환율": "💱",
    "금리": "🏦",
    "부동산": "🏠",
    "조선주": "🚢",
    "반도체": "💾",
    "재테크": "💰",
    "경제 일반": "📊",
    "기타": "📌",
}


def format_draft(news_articles, youtube_videos):
    """수집된 데이터를 블로그 초안(마크다운 + HTML)으로 변환한다."""
    today = datetime.now(KST).strftime("%Y-%m-%d")
    grouped = _group_by_topic(news_articles)
    keywords = _extract_keywords(news_articles, youtube_videos)
    tags = _generate_tags(news_articles, youtube_videos)

    md = _build_markdown(today, grouped, youtube_videos, keywords, tags)
    html = _build_html(today, grouped, youtube_videos, keywords, tags)

    return {"date": today, "markdown": md, "html": html}


def _group_by_topic(articles):
    """키워드 기반으로 기사를 주제별 그룹핑한다."""
    groups = {topic: [] for topic in TOPIC_KEYWORDS}
    groups["기타"] = []

    for article in articles:
        text = f"{article['title']} {article['description']}".lower()
        matched = False
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                groups[topic].append(article)
                matched = True
                break
        if not matched:
            groups["기타"].append(article)

    return {
        topic: items[:MAX_ARTICLES_PER_TOPIC]
        for topic, items in groups.items()
        if items
    }


def _extract_keywords(articles, videos, top_n=12):
    """기사 제목 빈도 기반으로 오늘의 핵심 키워드를 추출한다.

    - 제목 단어: 2배 가중치 (편집자가 의도적으로 선택한 핵심어)
    - 설명/영상 제목 단어: 1배 가중치
    - 2글자 이상 한글·대문자 영어·4글자 이상 영소문자만 추출
    """
    word_count = {}

    for article in articles:
        title_words = re.findall(r"[가-힣]{2,}|[A-Z]{2,}|[a-zA-Z]{4,}", article["title"])
        for w in title_words:
            if w not in STOPWORDS:
                word_count[w] = word_count.get(w, 0) + 2

        desc_words = re.findall(r"[가-힣]{2,}|[A-Z]{2,}", article["description"])
        for w in desc_words:
            if w not in STOPWORDS:
                word_count[w] = word_count.get(w, 0) + 1

    for video in videos:
        title_words = re.findall(r"[가-힣]{2,}|[A-Z]{2,}", video["title"])
        for w in title_words:
            if w not in STOPWORDS:
                word_count[w] = word_count.get(w, 0) + 1

    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]


def _generate_tags(articles, videos):
    """태그 목록을 생성한다."""
    base_tags = ["경제뉴스", "오늘의경제", "경제정리", "주식", "투자"]
    topic_tags = set()

    for article in articles:
        for topic, keywords in TOPIC_KEYWORDS.items():
            text = f"{article['title']} {article['description']}".lower()
            if any(kw in text for kw in keywords):
                topic_tags.add(topic)

    for video in videos:
        topic_tags.add(video["channel_title"])

    return base_tags + sorted(topic_tags)


def _build_markdown(date, grouped, videos, keywords, tags):
    """마크다운 형식 초안을 생성한다."""
    lines = [
        f"# [{date}] 오늘의 경제 뉴스",
        "",
        f"**오늘의 키워드**: {' '.join(f'`{k}`' for k in keywords)}",
        "",
        "---",
        "",
    ]

    for topic, articles in grouped.items():
        icon = TOPIC_ICONS.get(topic, "•")
        lines.append(f"## {icon} {topic} ({len(articles)}건)")
        lines.append("")
        for article in articles:
            lines.append(f"- [{article['title']}]({article['link']})")
        lines.append("")

    if videos:
        lines.append("## 🎬 오늘의 유튜브")
        lines.append("")
        for video in videos:
            url = f"https://www.youtube.com/watch?v={video['video_id']}"
            lines.append(f"- [{video['title']}]({url}) — {video['channel_title']}")
        lines.append("")

    lines.append(f"**태그**: {', '.join(tags)}")
    lines.append("")

    return "\n".join(lines)


def _build_html(date, grouped, videos, keywords, tags):
    """네이버 블로그용 대시보드형 HTML 초안을 생성한다."""
    total_articles = sum(len(v) for v in grouped.values())

    parts = [
        "<!DOCTYPE html>",
        '<html lang="ko">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"<title>[{date}] 오늘의 경제</title>",
        f"<style>{_css()}</style>",
        "</head>",
        "<body>",
        # 헤더
        '<header>',
        f'  <h1>📰 오늘의 경제 <span class="date">{date}</span></h1>',
        f'  <p class="meta">뉴스 {total_articles}건 · 영상 {len(videos)}개</p>',
        '</header>',
    ]

    # 오늘의 키워드
    if keywords:
        parts += [
            '<section class="keywords">',
            '  <h2>🔑 오늘의 키워드</h2>',
            '  <div class="kw-list">',
        ]
        for kw in keywords:
            parts.append(f'    <span class="kw">{kw}</span>')
        parts += ["  </div>", "</section>"]

    # 뉴스 토픽 카드
    parts.append('<section class="topics">')
    for topic, articles in grouped.items():
        icon = TOPIC_ICONS.get(topic, "•")
        parts += [
            '  <div class="topic-card">',
            f'    <h3>{icon} {topic} <span class="count">{len(articles)}</span></h3>',
            "    <ul>",
        ]
        for article in articles:
            parts.append(
                f'      <li><a href="{escape(article["link"])}" target="_blank">{escape(article["title"])}</a></li>'
            )
        parts += ["    </ul>", "  </div>"]
    parts.append("</section>")

    # 유튜브 그리드
    if videos:
        parts += [
            '<section class="videos">',
            '  <h2>🎬 오늘의 유튜브</h2>',
            '  <div class="video-grid">',
        ]
        for video in videos:
            url = f"https://www.youtube.com/watch?v={video['video_id']}"
            thumb = f"https://img.youtube.com/vi/{video['video_id']}/mqdefault.jpg"
            parts += [
                '    <div class="video-item">',
                f'      <a href="{url}" target="_blank"><img src="{thumb}" alt="{escape(video["title"])}"></a>',
                f'      <p class="v-title"><a href="{url}" target="_blank">{escape(video["title"])}</a></p>',
                f'      <p class="v-ch">{escape(video["channel_title"])}</p>',
                "    </div>",
            ]
        parts += ["  </div>", "</section>"]

    # 태그 푸터
    parts.append('<footer class="tags">')
    for tag in tags:
        parts.append(f'  <span class="tag">{tag}</span>')
    parts += ["</footer>", "</body>", "</html>"]

    return "\n".join(parts)


def _css():
    return """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Noto Sans KR', sans-serif; background: #f4f6f8; color: #222; padding: 16px; max-width: 960px; margin: 0 auto; }

header { background: #fff; border-radius: 10px; padding: 18px 20px; margin-bottom: 14px; border-left: 5px solid #03c75a; }
header h1 { font-size: 1.3rem; color: #111; }
.date { color: #03c75a; }
.meta { color: #999; font-size: 0.82rem; margin-top: 4px; }

.keywords { background: #fff; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px; }
.keywords h2 { font-size: 0.9rem; color: #666; margin-bottom: 10px; }
.kw-list { display: flex; flex-wrap: wrap; gap: 7px; }
.kw { background: #e6f7ee; color: #02a64f; font-weight: 700; padding: 4px 13px; border-radius: 20px; font-size: 0.88rem; border: 1px solid #b8e8cc; }

.topics { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-bottom: 14px; }
.topic-card { background: #fff; border-radius: 10px; padding: 14px 16px; }
.topic-card h3 { font-size: 0.9rem; color: #444; margin-bottom: 9px; display: flex; align-items: center; gap: 5px; }
.count { background: #03c75a; color: #fff; font-size: 0.72rem; padding: 1px 7px; border-radius: 10px; margin-left: auto; font-weight: 400; }
.topic-card ul { list-style: none; }
.topic-card li { padding: 4px 0; border-bottom: 1px solid #f2f2f2; font-size: 0.84rem; line-height: 1.45; }
.topic-card li:last-child { border-bottom: none; }
.topic-card a { color: #333; text-decoration: none; }
.topic-card a:hover { color: #03c75a; }

.videos { background: #fff; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px; }
.videos h2 { font-size: 0.9rem; color: #666; margin-bottom: 12px; }
.video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.video-item img { width: 100%; border-radius: 6px; display: block; }
.v-title { font-size: 0.8rem; margin-top: 5px; line-height: 1.35; }
.v-title a { color: #333; text-decoration: none; }
.v-title a:hover { color: #03c75a; }
.v-ch { font-size: 0.73rem; color: #aaa; margin-top: 2px; }

.tags { background: #fff; border-radius: 10px; padding: 12px 16px; display: flex; flex-wrap: wrap; gap: 6px; }
.tag { background: #03c75a; color: #fff; padding: 3px 10px; border-radius: 12px; font-size: 0.78rem; }
"""
