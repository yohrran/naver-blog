import re
from datetime import datetime, timedelta, timezone
from html import unescape

import requests

from src.config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NEWS_KEYWORDS

KST = timezone(timedelta(hours=9))


def collect_news():
    """네이버 뉴스 API로 경제 키워드별 뉴스를 수집한다."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[WARN] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 미설정, 뉴스 수집 건너뜀")
        return []

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }

    today = datetime.now(KST).date()
    all_articles = []
    seen_titles = set()

    for keyword in NEWS_KEYWORDS:
        params = {
            "query": keyword,
            "display": 20,
            "sort": "date",
        }

        try:
            resp = requests.get(
                "https://openapi.naver.com/v1/search/news.json",
                headers=headers,
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except requests.RequestException as e:
            print(f"[ERROR] 뉴스 수집 실패 (keyword={keyword}): {e}")
            continue

        for item in items:
            pub_date = _parse_pub_date(item.get("pubDate", ""))
            if pub_date and pub_date.date() != today:
                continue

            title = _strip_html(item.get("title", ""))
            if title in seen_titles:
                continue
            seen_titles.add(title)

            all_articles.append({
                "title": title,
                "description": _strip_html(item.get("description", "")),
                "link": item.get("originallink") or item.get("link", ""),
                "pub_date": pub_date.isoformat() if pub_date else "",
                "source": keyword,
            })

    print(f"[INFO] 네이버 뉴스 {len(all_articles)}건 수집 완료")
    return all_articles


def _parse_pub_date(date_str):
    """RFC 2822 형식 날짜를 파싱한다."""
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str).astimezone(KST)
    except Exception:
        return None


def _strip_html(text):
    """HTML 태그 제거 및 엔티티 디코딩."""
    text = unescape(text)
    return re.sub(r"<[^>]+>", "", text).strip()
