"""완성글 파일의 형식(프런트매터 + 본문) 파싱과 저장.

파일 형식:

    ---
    제목: 어쩌고
    태그: 태그1, 태그2
    ---

    본문...

글 하나는 dict로 다룬다: {"title": str, "tags": [str], "body": str}
"""

import os
import re
from datetime import datetime, timedelta, timezone

from src.config import POSTS_DIR

KST = timezone(timedelta(hours=9))

_FRONTMATTER_RE = re.compile(
    r"\A\s*---\s*\n(?P<meta>.*?)\n\s*---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)

# 파일명에 쓸 수 없는 문자
_UNSAFE_FILENAME_RE = re.compile(r"[^0-9A-Za-z가-힣]+")


class PostFormatError(ValueError):
    """모델 응답이 약속한 형식을 벗어났을 때."""


def parse_post(text):
    """프런트매터가 붙은 글을 dict로 파싱한다."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise PostFormatError(
            "프런트매터(--- 제목/태그 ---)를 찾지 못했습니다. "
            f"응답 앞부분: {text[:200]!r}"
        )

    meta = {}
    for line in match.group("meta").splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()

    title = meta.get("제목", "").strip()
    if not title:
        raise PostFormatError("제목이 비어 있습니다.")

    tags = [t.strip().lstrip("#") for t in meta.get("태그", "").split(",")]
    tags = [t for t in tags if t]

    body = match.group("body").strip()
    if not body:
        raise PostFormatError("본문이 비어 있습니다.")

    return {"title": title, "tags": tags, "body": body}


def render_post(post):
    """dict를 프런트매터가 붙은 파일 내용으로 직렬화한다."""
    return (
        "---\n"
        f"제목: {post['title']}\n"
        f"태그: {', '.join(post['tags'])}\n"
        "---\n\n"
        f"{post['body']}\n"
    )


def _slugify(title, max_length=30):
    """제목을 파일명 조각으로 바꾼다."""
    slug = _UNSAFE_FILENAME_RE.sub("-", title).strip("-")
    return slug[:max_length] or "post"


def build_post_path(post, date=None):
    """저장 경로를 만든다: posts/YYYY-MM-DD-제목조각.md"""
    date = date or datetime.now(KST).strftime("%Y-%m-%d")
    return os.path.join(POSTS_DIR, f"{date}-{_slugify(post['title'])}.md")


def save_post(post, path=None, overwrite=False):
    """완성글을 파일로 저장하고 경로를 돌려준다."""
    path = path or build_post_path(post)

    if os.path.exists(path) and not overwrite:
        print(f"[SKIP] 이미 존재합니다: {path} (--overwrite로 덮어쓰기)")
        return path

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_post(post))
    except OSError as e:
        raise OSError(f"글 저장에 실패했습니다 ({path}): {e}") from e

    print(f"[SAVE] {path}")
    return path


def load_post(path):
    """저장된 완성글을 다시 dict로 읽는다."""
    try:
        with open(path, encoding="utf-8") as f:
            return parse_post(f.read())
    except OSError as e:
        raise OSError(f"글 파일을 읽지 못했습니다 ({path}): {e}") from e


def find_latest_post():
    """posts/에서 가장 최근 파일 경로를 찾는다. 없으면 None."""
    if not os.path.isdir(POSTS_DIR):
        return None

    files = sorted(f for f in os.listdir(POSTS_DIR) if f.endswith(".md"))
    return os.path.join(POSTS_DIR, files[-1]) if files else None
