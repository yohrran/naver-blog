"""완성글 작성 CLI.

    python -m src.compose                        # 오늘 수집 초안으로 글 쓰기
    python -m src.compose --date 2026-08-25      # 특정 날짜 초안으로
    python -m src.compose --topic "주제"          # 임의 주제로
    python -m src.compose --topic "주제" --notes "참고할 메모"
"""

import argparse
import sys

from src.generator.post_file import save_post
from src.generator.post_writer import PostWriteError, write_from_draft, write_from_topic
from src.output.draft_manager import load_draft_markdown


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="python -m src.compose",
        description="수집 초안이나 임의 주제로 블로그 완성글을 씁니다.",
    )
    parser.add_argument("--date", help="사용할 초안 날짜 (YYYY-MM-DD, 기본: 오늘)")
    parser.add_argument("--topic", help="임의 주제로 글쓰기 (초안 대신 사용)")
    parser.add_argument("--notes", default="", help="--topic과 함께 넘길 참고 메모")
    parser.add_argument("--instruction", default="", help="이번 글에만 적용할 추가 지시")
    parser.add_argument("--overwrite", action="store_true", help="같은 이름 파일 덮어쓰기")
    return parser.parse_args(argv)


def _write_post(args):
    """입력 갈래에 따라 글을 만든다."""
    if args.topic:
        print(f"=== 주제로 글쓰기: {args.topic} ===")
        return write_from_topic(args.topic, args.notes, args.instruction)

    date, markdown = load_draft_markdown(args.date)
    print(f"=== {date} 초안으로 글쓰기 ({len(markdown)}자) ===")
    return write_from_draft(markdown, date, args.instruction)


def main(argv=None):
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    try:
        post = _write_post(args)
        path = save_post(post, overwrite=args.overwrite)
    except (PostWriteError, FileNotFoundError, OSError) as e:
        print(f"[ERROR] {e}")
        return 1

    print()
    print(f"제목: {post['title']}")
    print(f"태그: {', '.join(post['tags'])}")
    print(f"길이: {len(post['body'])}자")
    print()
    print("확인 후 아래 명령으로 네이버 에디터에 채워 넣으세요:")
    print(f"  python -m src.publish {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
