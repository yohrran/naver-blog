"""네이버 에디터 채우기 CLI. 발행 버튼은 사람이 누른다.

    python -m src.publish --login            # 최초 1회: 직접 로그인해 세션 저장
    python -m src.publish                    # posts/의 최신 글을 에디터에 채우기
    python -m src.publish posts/2026-08-26-어쩌고.md
    python -m src.publish --debug            # 선택자가 깨졌을 때 DOM 확인용
"""

import argparse
import sys

from playwright.sync_api import sync_playwright

from src.config import NAVER_BLOG_ID
from src.generator.post_file import find_latest_post, load_post
from src.publisher.naver_editor import open_and_fill
from src.publisher.naver_session import (
    launch_browser,
    new_logged_in_context,
    save_session,
    session_exists,
)


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="python -m src.publish",
        description="완성글을 네이버 글쓰기 에디터에 채웁니다. 발행은 직접 하세요.",
    )
    parser.add_argument("path", nargs="?", help="글 파일 경로 (기본: posts/의 최신 파일)")
    parser.add_argument("--login", action="store_true", help="네이버 로그인 세션 저장")
    parser.add_argument("--debug", action="store_true", help="입력 후 브라우저를 멈춰 DOM 확인")
    return parser.parse_args(argv)


def _resolve_post_path(path):
    """사용할 글 파일 경로를 정한다."""
    if path:
        return path

    latest = find_latest_post()
    if latest is None:
        raise FileNotFoundError(
            "posts/에 글이 없습니다. 먼저 `python -m src.compose`로 글을 쓰세요."
        )

    print(f"[INFO] 최신 글을 사용합니다: {latest}")
    return latest


def _require_session():
    """세션이 없으면 브라우저를 띄우기 전에 미리 알려준다."""
    if not session_exists():
        raise FileNotFoundError(
            "네이버 로그인 세션이 없습니다.\n"
            "먼저 `python -m src.publish --login`을 실행해 로그인해주세요."
        )


def main(argv=None):
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    try:
        # 브라우저를 띄우기 전에 파일부터 확인한다.
        # 순서가 반대면 실패했을 때 브라우저가 떴다 죽으며 지저분한 로그가 남는다.
        post = None
        if not args.login:
            _require_session()
            post = load_post(_resolve_post_path(args.path))

        with sync_playwright() as playwright:
            if args.login:
                save_session(playwright)
                return 0

            open_and_fill(
                playwright,
                post,
                NAVER_BLOG_ID,
                browser_factory=launch_browser,
                context_factory=new_logged_in_context,
                debug=args.debug,
            )
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as e:
        print(f"[ERROR] {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
