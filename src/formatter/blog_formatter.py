from datetime import datetime, timedelta, timezone

from src.config import MAX_ARTICLES_PER_TOPIC, TOPIC_KEYWORDS

KST = timezone(timedelta(hours=9))


def format_draft(news_articles, youtube_videos):
    """수집된 데이터를 블로그 초안(마크다운 + HTML)으로 변환한다."""
    today = datetime.now(KST).strftime("%Y-%m-%d")
    grouped = _group_by_topic(news_articles)
    tags = _generate_tags(news_articles, youtube_videos)

    md = _build_markdown(today, grouped, youtube_videos, tags)
    html = _build_html(today, grouped, youtube_videos, tags)

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


def _generate_tags(articles, videos):
    """태그 추천 목록을 생성한다."""
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


def _build_markdown(date, grouped, videos, tags):
    """마크다운 형식 초안을 생성한다."""
    lines = [
        f"# [{date}] 오늘의 경제 뉴스 정리",
        "",
        "---",
        "",
    ]

    for topic, articles in grouped.items():
        lines.append(f"## {topic}")
        lines.append("")
        for article in articles:
            desc = article["description"][:80] + "..." if len(article["description"]) > 80 else article["description"]
            lines.append(f"- **[{article['title']}]({article['link']})** - {desc}")
        lines.append("")
        lines.append("---")
        lines.append("")

    if videos:
        lines.append("## 오늘의 경제 유튜브")
        lines.append("")
        for video in videos:
            lines.append(f"### {video['title']}")
            lines.append(f"채널: {video['channel_title']}")
            lines.append("")
            lines.append(f"[![영상 보기](https://img.youtube.com/vi/{video['video_id']}/mqdefault.jpg)](https://www.youtube.com/watch?v={video['video_id']})")
            lines.append("")
            if video["transcript"]:
                summary = video["transcript"][:300] + "..." if len(video["transcript"]) > 300 else video["transcript"]
                lines.append(f"> {summary}")
                lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(f"**태그**: {', '.join(tags)}")
    lines.append("")

    return "\n".join(lines)


def _build_html(date, grouped, videos, tags):
    """네이버 블로그 붙여넣기용 HTML 초안을 생성한다."""
    parts = [
        "<!DOCTYPE html>",
        '<html lang="ko">',
        "<head>",
        '<meta charset="UTF-8">',
        f"<title>[{date}] 오늘의 경제 뉴스 정리</title>",
        "<style>",
        "  body { font-family: 'Noto Sans KR', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; color: #333; }",
        "  h1 { color: #03c75a; border-bottom: 3px solid #03c75a; padding-bottom: 10px; }",
        "  h2 { color: #1a1a1a; margin-top: 30px; padding: 8px 12px; background: #f5f5f5; border-left: 4px solid #03c75a; }",
        "  h3 { color: #333; margin-top: 20px; }",
        "  blockquote { background: #fafafa; border-left: 3px solid #ddd; margin: 10px 0; padding: 10px 15px; color: #666; }",
        "  a { color: #03c75a; text-decoration: none; }",
        "  a:hover { text-decoration: underline; }",
        "  .video-card { border: 1px solid #eee; border-radius: 8px; padding: 15px; margin: 10px 0; }",
        "  .video-card img { width: 100%; max-width: 480px; border-radius: 4px; }",
        "  .tags { margin-top: 30px; padding: 10px; background: #f0f0f0; border-radius: 5px; }",
        "  .tag { display: inline-block; background: #03c75a; color: white; padding: 3px 10px; border-radius: 12px; margin: 3px; font-size: 13px; }",
        "  hr { border: none; border-top: 1px solid #eee; margin: 25px 0; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>[{date}] 오늘의 경제 뉴스 정리</h1>",
    ]

    for topic, articles in grouped.items():
        parts.append(f"<h2>{topic}</h2>")
        parts.append("<ul>")
        for article in articles:
            desc = article["description"][:80] + "..." if len(article["description"]) > 80 else article["description"]
            parts.append(f'<li><a href="{article["link"]}" target="_blank"><strong>{article["title"]}</strong></a> - {desc}</li>')
        parts.append("</ul>")
        parts.append("<hr>")

    if videos:
        parts.append("<h2>오늘의 경제 유튜브</h2>")
        for video in videos:
            url = f"https://www.youtube.com/watch?v={video['video_id']}"
            thumb = f"https://img.youtube.com/vi/{video['video_id']}/mqdefault.jpg"
            parts.append('<div class="video-card">')
            parts.append(f"<h3>{video['title']}</h3>")
            parts.append(f"<p>채널: {video['channel_title']}</p>")
            parts.append(f'<a href="{url}" target="_blank"><img src="{thumb}" alt="{video["title"]}"></a>')
            if video["transcript"]:
                summary = video["transcript"][:300] + "..." if len(video["transcript"]) > 300 else video["transcript"]
                parts.append(f"<blockquote>{summary}</blockquote>")
            parts.append("</div>")
        parts.append("<hr>")

    parts.append('<div class="tags">')
    parts.append("<strong>태그: </strong>")
    for tag in tags:
        parts.append(f'<span class="tag">{tag}</span>')
    parts.append("</div>")

    parts.append("</body>")
    parts.append("</html>")

    return "\n".join(parts)
