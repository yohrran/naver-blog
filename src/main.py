"""네이버 블로그 경제 기사 자동 수집 파이프라인."""

import sys

from src.collectors.naver_news import collect_news
from src.collectors.youtube import collect_youtube
from src.formatter.blog_formatter import format_draft
from src.output.draft_manager import save_draft
from src.output.email_sender import send_draft_email


def main():
    overwrite = "--overwrite" in sys.argv

    print("=== 1. 뉴스 수집 ===")
    news = collect_news()
    videos = collect_youtube()

    if not news and not videos:
        print("[WARN] 수집된 데이터가 없습니다. 종료합니다.")
        return

    print(f"\n=== 2. 포맷팅 (뉴스 {len(news)}건, 영상 {len(videos)}건) ===")
    draft = format_draft(news, videos)

    print("\n=== 3. 저장 ===")
    saved = save_draft(draft, overwrite=overwrite)

    print("\n=== 4. 이메일 발송 ===")
    send_draft_email(draft)

    if saved:
        print(f"\n완료! {len(saved)}개 파일 저장됨.")
    else:
        print("\n저장된 파일 없음 (이미 존재하는 파일은 --overwrite 옵션으로 덮어쓰기).")


if __name__ == "__main__":
    main()
