"""완성글을 붙여넣기용 페이지로 뽑는 CLI. 브라우저로 열어 복사만 하면 된다.

    python -m src.handoff                          # posts/의 최신 글
    python -m src.handoff posts/2026-08-29-어쩌고.md
    python -m src.handoff --no-open                # 파일만 만들고 열지 않음

네이버 DOM도, 로그인 세션도, 브라우저 자동화도 필요 없다. 글 파일 하나만 읽는다.
"""

import argparse
import pathlib
import sys
import webbrowser

from src.generator.post_file import find_latest_post, load_post
from src.publisher.handoff_page import save_handoff


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="python -m src.handoff",
        description="완성글을 복사·붙여넣기용 HTML 한 장으로 만듭니다.",
    )
    parser.add_argument("path", nargs="?", help="글 파일 경로 (기본: posts/의 최신 파일)")
    parser.add_argument("-o", "--output", help="저장 경로 (기본: 글 파일 옆 .handoff.html)")
    parser.add_argument("--no-open", action="store_true", help="브라우저를 열지 않음")
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


def _open_in_browser(path):
    """기본 브라우저로 연다. 못 열어도 경로는 이미 찍혀 있으니 실패로 보지 않는다."""
    url = pathlib.Path(path).resolve().as_uri()

    if webbrowser.open(url):
        return

    print(f"[WARN] 브라우저를 열지 못했습니다. 직접 열어주세요: {url}")


def main(argv=None):
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    try:
        post_path = _resolve_post_path(args.path)
        post = load_post(post_path)
        path = save_handoff(post, post_path, args.output)
    except (FileNotFoundError, ValueError, OSError) as e:
        print(f"[ERROR] {e}")
        return 1

    print(f"[SAVE] {path}")

    if not args.no_open:
        _open_in_browser(path)

    print()
    print("=" * 60)
    print("  1. [제목 복사] → 네이버 제목란에 붙여넣기")
    print("  2. [서식 유지 복사] → 본문에 붙여넣기")
    print("  3. [태그 복사] → 발행 패널 태그란에 붙여넣기")
    print("  4. 확인하고 직접 [발행]")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
