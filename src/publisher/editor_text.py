"""마크다운을 스마트에디터에 타이핑할 평문으로 바꾼다.

스마트에디터는 마크다운 문법을 해석하지 않는다. `## 제목`을 그대로 치면
화면에도 `## 제목`이라고 남는다. 그래서 문법 기호를 걷어내고
사람이 읽을 수 있는 평문으로 만든 뒤, 서식은 에디터에서 직접 입힌다.
"""

import re

_HEADING_RE = re.compile(r"^(#{1,6})\s*(.+?)\s*#*$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")
_INLINE_CODE_RE = re.compile(r"`([^`]+?)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_HR_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?")
_LIST_RE = re.compile(r"^(\s*)[-*+]\s+")


def _clean_inline(text):
    """줄 안의 마크다운 기호를 걷어낸다."""
    text = _IMAGE_RE.sub(r"[사진: \1]", text)
    text = _LINK_RE.sub(r"\1 (\2)", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    return text


def markdown_to_editor_text(markdown):
    """마크다운 본문을 에디터에 칠 평문으로 변환한다.

    - 제목(#)은 기호만 떼고 한 줄로 남긴다
    - 구분선(---)은 빈 줄로 바꾼다
    - 코드블록(```)은 내용만 남긴다
    - 목록의 `-`는 가독성을 위해 유지한다
    """
    lines = []
    in_code_block = False

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            lines.append(line)
            continue

        if _HR_RE.match(line):
            lines.append("")
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            lines.append(_clean_inline(heading.group(2)))
            continue

        line = _BLOCKQUOTE_RE.sub("", line)
        line = _LIST_RE.sub(r"\1- ", line)
        lines.append(_clean_inline(line))

    return _collapse_blank_lines(lines)


def _collapse_blank_lines(lines):
    """빈 줄이 3개 이상 이어지면 하나로 줄인다."""
    result = []
    blank_run = 0

    for line in lines:
        if line.strip():
            blank_run = 0
            result.append(line)
            continue

        blank_run += 1
        if blank_run <= 1:
            result.append("")

    return "\n".join(result).strip()
