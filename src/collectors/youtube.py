from datetime import datetime, timedelta, timezone

import requests
from youtube_transcript_api import YouTubeTranscriptApi

from src.config import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_IDS

KST = timezone(timedelta(hours=9))


def collect_youtube():
    """YouTube Data API로 경제 채널의 당일 영상을 수집한다."""
    if not YOUTUBE_API_KEY:
        print("[WARN] YOUTUBE_API_KEY 미설정, 유튜브 수집 건너뜀")
        return []

    today = datetime.now(KST).date()
    published_after = datetime(today.year, today.month, today.day, tzinfo=KST).astimezone(
        timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    all_videos = []

    for channel_id in YOUTUBE_CHANNEL_IDS:
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "publishedAfter": published_after,
            "maxResults": 5,
            "type": "video",
            "key": YOUTUBE_API_KEY,
        }

        try:
            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except requests.RequestException as e:
            print(f"[ERROR] 유튜브 수집 실패 (channel={channel_id}): {e}")
            continue

        for item in items:
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            if not video_id:
                continue

            transcript = _get_transcript(video_id)

            all_videos.append({
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "video_id": video_id,
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "transcript": transcript,
            })

    print(f"[INFO] 유튜브 영상 {len(all_videos)}건 수집 완료")
    return all_videos


def _get_transcript(video_id):
    """유튜브 영상의 한국어 자막을 추출한다. 실패 시 빈 문자열 반환."""
    try:
        ytt = YouTubeTranscriptApi()
        entries = ytt.fetch(video_id, languages=["ko"])
        return " ".join(entry.text for entry in entries)
    except Exception as e:
        print(f"[WARN] 자막 추출 실패 (video={video_id}): {e}")
        return ""
