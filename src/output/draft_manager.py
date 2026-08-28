import os
from datetime import datetime, timedelta, timezone

from src.config import DRAFTS_DIR

KST = timezone(timedelta(hours=9))


def load_draft_markdown(date=None):
    """저장된 수집 초안의 마크다운을 읽는다.

    date를 생략하면 오늘 날짜(KST)를 쓴다. 파일이 없으면 FileNotFoundError.
    """
    date = date or datetime.now(KST).strftime("%Y-%m-%d")
    path = os.path.join(DRAFTS_DIR, f"{date}.md")

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{date} 초안이 없습니다: {path}\n"
            "먼저 `python -m src.main`으로 뉴스를 수집하세요."
        )

    try:
        with open(path, encoding="utf-8") as f:
            return date, f.read()
    except OSError as e:
        raise OSError(f"초안을 읽지 못했습니다 ({path}): {e}") from e


def save_draft(draft, overwrite=False):
    """블로그 초안을 마크다운 + HTML 파일로 저장한다."""
    os.makedirs(DRAFTS_DIR, exist_ok=True)

    date = draft["date"]
    md_path = os.path.join(DRAFTS_DIR, f"{date}.md")
    html_path = os.path.join(DRAFTS_DIR, f"{date}.html")

    saved = []

    for path, content, label in [
        (md_path, draft["markdown"], "마크다운"),
        (html_path, draft["html"], "HTML"),
    ]:
        if os.path.exists(path) and not overwrite:
            print(f"[SKIP] {label} 파일이 이미 존재합니다: {path}")
            continue

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[SAVE] {label} 저장 완료: {path}")
        saved.append(path)

    return saved
