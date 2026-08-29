"""완성글을 "복사해서 붙여넣기 좋은" 한 장짜리 HTML로 만든다.

3단계의 두 번째 방식이다. `naver_editor.py`가 브라우저를 몰아 타이핑한다면,
이쪽은 사람이 직접 붙여넣도록 클립보드만 채워준다. 네이버 DOM에 의존하지
않으므로 에디터가 바뀌어도 깨지지 않는다.

## 왜 터미널 출력이 아니라 HTML인가

클립보드에 **서식**을 실으려면 브라우저가 필요하다. `pbcopy`로는 평문만
나가고, 평문으로 넣으면 소제목·굵게·링크를 에디터에서 다시 손으로 입혀야
한다. 그게 지금 `editor_text.py`가 겪던 손실이다.

## 왜 execCommand인가 (deprecated인데도)

이 파일은 `file://`로 열린다. `navigator.clipboard` 객체는 거기서도 존재하지만
`write()`는 보안 컨텍스트를 요구하고, 무엇보다 **서식을 실으려면 `ClipboardItem`이
필요한데 그쪽이 더 까다롭다.** 사용자 클릭으로 시작된 `document.execCommand('copy')`는
`file://`에서 선택 영역을 그대로 복사하며, 브라우저가 `text/html`을 알아서 함께 실어준다.
그래서 서식·평문 양쪽 다 이 경로 하나로 통일했다. (2026-08-29 크롬에서 왕복 검증함)

## 미리보기와 복사본을 왜 따로 두는가

크롬은 선택 영역을 복사할 때 **계산된 스타일을 인라인으로 박아** 클립보드에
넣는다. 보기 좋으라고 미리보기에 준 글꼴·색이 그대로 네이버 본문에 따라
들어간다는 뜻이다. 그래서 화면에 보이는 `#preview`와, 실제로 복사되는
화면 밖 `#clip`을 분리했다. `#clip`에는 스타일을 주지 않는다.
"""

import os
from html import escape

from src.publisher.editor_text import markdown_to_editor_text
from src.publisher.markdown_html import markdown_to_html

_CSS = """
:root {
  --bg: #f6f7f9; --card: #fff; --line: #e3e6ea; --text: #1a1d21;
  --muted: #6b7280; --accent: #03c75a; --accent-ink: #0b5c30;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181c; --card: #1e2126; --line: #2e333a; --text: #e8eaed;
    --muted: #9aa1ab; --accent: #03c75a; --accent-ink: #7ee0a8;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 32px 20px 80px; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo",
               "Pretendard", "Malgun Gothic", sans-serif;
  line-height: 1.7; -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 760px; margin: 0 auto; }
header { margin-bottom: 28px; }
header h1 { font-size: 21px; margin: 0 0 6px; line-height: 1.45; }
header .meta { color: var(--muted); font-size: 13px; margin: 0; }
.step {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 18px 20px; margin-bottom: 16px;
}
.step.done { border-color: var(--accent); }
.head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.num {
  flex: none; width: 24px; height: 24px; border-radius: 50%;
  background: var(--line); color: var(--text);
  font-size: 13px; font-weight: 700; display: grid; place-items: center;
}
.step.done .num { background: var(--accent); color: #fff; }
.head h2 { font-size: 15px; margin: 0; flex: 1; }
.hint { color: var(--muted); font-size: 12.5px; margin: 8px 0 0; }
button {
  font: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
  border: 1px solid var(--line); background: transparent; color: var(--text);
  border-radius: 7px; padding: 6px 13px;
}
button:hover { border-color: var(--accent); color: var(--accent-ink); }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
button.primary:hover { color: #fff; opacity: .9; }
.value {
  margin-top: 12px; padding: 12px 14px; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line);
  font-size: 15px; font-weight: 600;
}
.chips { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 12px; }
.chip { border-radius: 999px; padding: 5px 12px; font-weight: 500; }
#preview {
  margin-top: 14px; padding: 16px 18px; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line);
  max-height: 420px; overflow-y: auto; font-size: 14.5px;
}
#preview h2, #preview h3, #preview h4 { font-size: 16px; margin: 22px 0 8px; }
#preview p { margin: 0 0 14px; }
#preview ul, #preview ol { margin: 0 0 14px; padding-left: 20px; }
#preview li { margin-bottom: 4px; }
#preview a { color: var(--accent-ink); }
#preview hr { border: 0; border-top: 1px solid var(--line); margin: 20px 0; }
#preview blockquote {
  margin: 0 0 14px; padding-left: 14px; border-left: 3px solid var(--line);
  color: var(--muted);
}
#preview pre {
  background: var(--card); padding: 12px; border-radius: 6px; overflow-x: auto;
  font-size: 13px;
}
#preview img { max-width: 100%; }
.warn {
  margin-top: 20px; padding: 14px 16px; border-radius: 10px;
  border: 1px solid var(--line); color: var(--muted); font-size: 13px;
}
.warn strong { color: var(--text); }
/* 화면 밖 복사 원본. display:none이면 선택이 안 되므로 밀어내기만 한다. */
.offscreen { position: fixed; top: 0; left: -100000px; width: 640px; }
#toast {
  position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%) translateY(20px);
  background: #1a1d21; color: #fff; padding: 11px 20px; border-radius: 999px;
  font-size: 13.5px; font-weight: 600; opacity: 0; pointer-events: none;
  transition: opacity .18s, transform .18s;
}
#toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
"""

_JS = """
function flash(message) {
  var toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(function () {
    toast.classList.remove('show');
  }, 1600);
}

// 서식을 살린 복사. 선택 영역을 복사하면 브라우저가 text/html을 함께 실어준다.
function copyNode(node) {
  var selection = window.getSelection();
  var range = document.createRange();
  selection.removeAllRanges();
  range.selectNodeContents(node);
  selection.addRange(range);

  var ok = false;
  try { ok = document.execCommand('copy'); } catch (e) { ok = false; }

  selection.removeAllRanges();
  return ok;
}

// 평문 복사. file://에는 navigator.clipboard가 없어 textarea로 떨어진다.
function copyText(text) {
  var area = document.getElementById('clip-text');
  area.value = text;
  area.focus();
  area.setSelectionRange(0, text.length);

  var ok = false;
  try { ok = document.execCommand('copy'); } catch (e) { ok = false; }

  area.blur();
  return ok;
}

function markDone(button) {
  var step = button.closest('.step');
  if (step) { step.classList.add('done'); }
}

function handle(button) {
  var mode = button.dataset.copy;
  var ok;

  if (mode === 'rich') {
    ok = copyNode(document.getElementById('clip-body'));
  } else if (mode === 'plain') {
    ok = copyText(document.getElementById('clip-plain').value);
  } else {
    ok = copyText(document.getElementById(button.dataset.source).textContent);
  }

  if (ok) {
    markDone(button);
    flash(button.dataset.label + ' 복사됨 — 네이버에 붙여넣으세요');
  } else {
    flash('복사에 실패했습니다. 미리보기를 직접 드래그해 복사해주세요.');
  }
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-copy]').forEach(function (button) {
    button.addEventListener('click', function () { handle(button); });
  });
});
"""


def _tag_chips(tags):
    """태그 하나씩 눌러 복사할 수 있는 칩. 붙여넣기가 안 쪼개질 때를 위한 대비다."""
    return "".join(
        f'<button class="chip" data-copy="text" data-source="tag-{i}" '
        f'data-label="태그">{escape(tag)}'
        f'<span class="offscreen" id="tag-{i}">{escape(tag)}</span></button>'
        for i, tag in enumerate(tags)
    )


def _tag_section(tags):
    if not tags:
        return ""

    joined = ", ".join(tags)
    return f"""
<section class="step">
  <div class="head">
    <span class="num">3</span>
    <h2>태그 {len(tags)}개</h2>
    <button data-copy="text" data-source="src-tags" data-label="태그">전체 복사</button>
  </div>
  <p class="hint">발행 설정 패널의 태그 입력창에 넣습니다.
     한 번에 안 들어가면 아래 칩을 하나씩 눌러 복사하세요.</p>
  <div class="chips">{_tag_chips(tags)}</div>
  <span class="offscreen" id="src-tags">{escape(joined)}</span>
</section>"""


def build_handoff_html(post):
    """완성글 dict를 핸드오프 페이지 HTML 문자열로 만든다."""
    body_html = markdown_to_html(post["body"])
    body_plain = markdown_to_editor_text(post["body"])
    title = escape(post["title"])

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>붙여넣기 — {title}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>{title}</h1>
  <p class="meta">본문 {len(body_plain):,}자 · 태그 {len(post["tags"])}개 ·
     네이버 글쓰기 창을 옆에 띄우고 위에서부터 붙여넣으세요</p>
</header>

<section class="step">
  <div class="head">
    <span class="num">1</span>
    <h2>제목</h2>
    <button data-copy="text" data-source="src-title" data-label="제목">복사</button>
  </div>
  <div class="value">{title}</div>
  <span class="offscreen" id="src-title">{title}</span>
</section>

<section class="step">
  <div class="head">
    <span class="num">2</span>
    <h2>본문</h2>
    <button class="primary" data-copy="rich" data-label="본문">서식 유지 복사</button>
    <button data-copy="plain" data-label="본문(평문)">평문으로</button>
  </div>
  <p class="hint">소제목·굵게·링크·목록이 살아서 붙습니다.
     서식이 이상하게 들어가면 [평문으로]를 쓰세요.</p>
  <div id="preview">{body_html}</div>
</section>
{_tag_section(post["tags"])}

<div class="warn">
  <strong>발행 버튼은 직접 누르세요.</strong>
  네이버는 사람의 작성 범위를 벗어난 접근을 차단하며, 자동 발행은 계정 제재 위험이 있습니다.
  이 페이지는 클립보드만 채웁니다.
</div>

</div>

<div class="offscreen" id="clip-body">{body_html}</div>
<textarea class="offscreen" id="clip-plain" readonly>{escape(body_plain)}</textarea>
<textarea class="offscreen" id="clip-text"></textarea>
<div id="toast" role="status"></div>

<script>{_JS}</script>
</body>
</html>
"""


def build_handoff_path(post_path):
    """글 파일 경로 옆에 핸드오프 파일 경로를 만든다: xxx.md → xxx.handoff.html"""
    stem, _, _ = post_path.rpartition(".md")
    return f"{stem or post_path}.handoff.html"


def save_handoff(post, post_path, path=None):
    """핸드오프 페이지를 파일로 저장하고 경로를 돌려준다.

    글 파일 옆에 둔다. posts/는 gitignore 대상이라 이 파일도 함께 빠진다.
    """
    path = path or build_handoff_path(post_path)

    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_handoff_html(post))
    except OSError as e:
        raise OSError(f"핸드오프 페이지 저장에 실패했습니다 ({path}): {e}") from e

    return path
