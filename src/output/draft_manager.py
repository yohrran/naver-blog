import os

from src.config import DRAFTS_DIR


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
