"""마크다운 본문을 스마트에디터에 붙여넣을 HTML로 바꾼다.

`editor_text.py`와 짝이다. 그쪽은 키보드로 칠 평문을 만드느라 서식을 버리고,
이쪽은 클립보드에 실을 HTML을 만들며 서식을 지킨다.

스마트에디터는 마크다운을 해석하지 않지만 **붙여넣은 HTML은 해석한다.**
그래서 굵게·소제목·링크·목록을 살린 채로 넣을 수 있다.

라이브러리를 쓰지 않는 건 의도다. 우리 글이 실제로 쓰는 문법은
제목·구분선·목록·인용·코드블록·굵게·링크가 전부고,
1단계(`blog_formatter._build_html`)도 같은 방식으로 HTML을 만든다.
"""

import re
from html import escape

_HEADING_RE = re.compile(r"^(#{1,6})\s*(.+?)\s*#*$")
_HR_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_UL_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_OL_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_FENCE_RE = re.compile(r"^\s*```")

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")
_INLINE_CODE_RE = re.compile(r"`([^`]+?)`")

# 글 제목이 이미 h1이므로 본문 제목은 h2부터 시작한다.
# 붙여넣었을 때 본문 안에 h1이 또 나오면 문서 구조가 어그러진다.
_MIN_HEADING = 2
_MAX_HEADING = 4


def markdown_to_html(markdown):
    """마크다운 본문을 붙여넣기용 HTML 문자열로 변환한다."""
    lines = markdown.splitlines()
    blocks = []
    index = 0

    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue

        index, block = _take_block(lines, index)
        if block:
            blocks.append(block)

    return "\n".join(blocks)


def _take_block(lines, index):
    """현재 줄에서 시작하는 블록 하나를 잘라내 (다음 인덱스, HTML)을 돌려준다."""
    line = lines[index]

    if _FENCE_RE.match(line):
        return _take_code(lines, index)
    if _HR_RE.match(line):
        return index + 1, "<hr>"
    if _HEADING_RE.match(line):
        return index + 1, _render_heading(line)
    if _UL_RE.match(line):
        return _take_list(lines, index, _UL_RE, "ul")
    if _OL_RE.match(line):
        return _take_list(lines, index, _OL_RE, "ol")
    if _QUOTE_RE.match(line):
        return _take_quote(lines, index)

    return _take_paragraph(lines, index)


def _starts_new_block(line):
    """이 줄이 문단을 끊고 새 블록을 여는가."""
    if not line.strip():
        return True
    return any(
        pattern.match(line)
        for pattern in (_FENCE_RE, _HR_RE, _HEADING_RE, _UL_RE, _OL_RE, _QUOTE_RE)
    )


def _render_heading(line):
    hashes, text = _HEADING_RE.match(line).groups()
    level = min(max(len(hashes), _MIN_HEADING), _MAX_HEADING)
    return f"<h{level}>{_inline(text)}</h{level}>"


def _take_code(lines, index):
    """```로 열린 코드블록을 닫힘까지 삼킨다. 닫히지 않으면 끝까지."""
    body = []
    index += 1

    while index < len(lines) and not _FENCE_RE.match(lines[index]):
        body.append(lines[index])
        index += 1

    return index + 1, f"<pre><code>{escape(chr(10).join(body))}</code></pre>"


def _take_list(lines, index, pattern, tag):
    """같은 종류의 목록 줄이 이어지는 동안 묶는다. 중첩은 평평하게 편다."""
    items = []

    while index < len(lines):
        match = pattern.match(lines[index])
        if not match:
            break
        items.append(f"<li>{_inline(match.group(1))}</li>")
        index += 1

    return index, f"<{tag}>{''.join(items)}</{tag}>"


def _take_quote(lines, index):
    """연속된 인용 줄을 하나의 blockquote로 묶는다."""
    parts = []

    while index < len(lines):
        match = _QUOTE_RE.match(lines[index])
        if not match:
            break
        parts.append(_inline(match.group(1)))
        index += 1

    return index, f"<blockquote><p>{'<br>'.join(parts)}</p></blockquote>"


def _take_paragraph(lines, index):
    """문단 안의 줄바꿈을 <br>로 살린다.

    마크다운 규칙대로면 연속한 줄은 한 문단으로 합쳐지지만, 이 블로그의 글은
    한 문장을 한 줄로 끊는 리듬 자체가 문체다. 합쳐버리면 톤이 무너진다.
    """
    parts = []

    while index < len(lines) and not _starts_new_block(lines[index]):
        parts.append(_inline(lines[index].strip()))
        index += 1

    return index, f"<p>{'<br>'.join(parts)}</p>"


def _inline(text):
    """줄 안의 마크다운 기호를 HTML 태그로 바꾼다.

    이스케이프를 먼저 한다. `&`, `<`, `>`만 바뀌므로 마크다운 기호는
    그대로 남아 아래 정규식이 정상 동작한다.
    """
    text = escape(text)
    text = _IMAGE_RE.sub(r'<img src="\2" alt="\1">', text)
    text = _LINK_RE.sub(r'<a href="\2">\1</a>', text)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)
    text = _INLINE_CODE_RE.sub(r"<code>\1</code>", text)
    return text
