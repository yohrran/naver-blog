"""스마트에디터를 열고 제목·본문·태그를 채운다.

**발행 버튼은 절대 누르지 않는다.** 내용만 채우고 브라우저를 열어둔 채 멈춘다.
최종 확인과 발행은 사람이 한다.

주의: 아래 SELECTORS는 네이버가 에디터 DOM을 바꾸면 깨진다.
깨졌을 때는 `--debug`로 실행해 브라우저 개발자도구로 실제 선택자를 확인한 뒤
이 딕셔너리만 고치면 된다. 나머지 로직은 건드릴 필요가 없다.
"""

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.publisher.editor_text import markdown_to_editor_text

WRITE_URL = "https://blog.naver.com/{blog_id}?Redirect=Write"

# 에디터가 들어 있는 iframe
EDITOR_FRAME = "#mainFrame"

# 후보를 위에서부터 시도한다. 하나라도 걸리면 그걸 쓴다.
SELECTORS = {
    # 열자마자 뜨는 팝업들 (임시저장 복구 / 도움말)
    "dismiss": [
        ".se-popup-button-cancel",
        ".se-help-panel-close-button",
        "button.se-popup-close-button",
    ],
    "title": [
        ".se-section-documentTitle .se-text-paragraph",
        ".se-documentTitle .se-text-paragraph",
        "[contenteditable='true'][data-a11y-title='제목']",
    ],
    "body": [
        ".se-section-text .se-text-paragraph",
        ".se-component.se-text .se-text-paragraph",
    ],
}

DEFAULT_TIMEOUT_MS = 15000
TYPE_DELAY_MS = 8


def _first_visible(frame, candidates, timeout_ms=DEFAULT_TIMEOUT_MS):
    """후보 선택자 중 먼저 보이는 것을 돌려준다. 없으면 None."""
    per_candidate = max(timeout_ms // max(len(candidates), 1), 2000)

    for selector in candidates:
        locator = frame.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=per_candidate)
            return locator
        except PlaywrightTimeoutError:
            continue

    return None


def _dismiss_popups(frame):
    """임시저장 복구·도움말 팝업을 닫는다. 없으면 조용히 넘어간다."""
    for selector in SELECTORS["dismiss"]:
        locator = frame.locator(selector).first
        try:
            if locator.is_visible(timeout=2000):
                locator.click()
                print(f"[INFO] 팝업 닫음: {selector}")
        except PlaywrightError:
            continue


def _type_into(page, locator, text):
    """요소를 클릭해 포커스를 준 뒤 타이핑한다."""
    locator.click()
    page.keyboard.type(text, delay=TYPE_DELAY_MS)


def fill_editor(page, post, debug=False):
    """열려 있는 글쓰기 페이지에 제목과 본문을 채운다."""
    frame = page.frame_locator(EDITOR_FRAME)

    _dismiss_popups(frame)

    title_box = _first_visible(frame, SELECTORS["title"])
    if title_box is None:
        raise RuntimeError(
            "제목 입력란을 찾지 못했습니다. 네이버가 에디터 구조를 바꿨을 수 있습니다.\n"
            "`--debug`로 다시 실행해 실제 선택자를 확인한 뒤 "
            "src/publisher/naver_editor.py의 SELECTORS를 고쳐주세요."
        )

    _type_into(page, title_box, post["title"])
    print(f"[INFO] 제목 입력 완료: {post['title']}")

    body_box = _first_visible(frame, SELECTORS["body"])
    if body_box is None:
        raise RuntimeError(
            "본문 입력란을 찾지 못했습니다. 제목은 입력되었으니 본문만 직접 붙여넣어 주세요."
        )

    body_text = markdown_to_editor_text(post["body"])
    _type_into(page, body_box, body_text)
    print(f"[INFO] 본문 입력 완료 ({len(body_text)}자)")

    if debug:
        print("[DEBUG] page.pause() — Playwright Inspector에서 DOM을 확인하세요.")
        page.pause()


def open_and_fill(playwright, post, blog_id, browser_factory, context_factory, debug=False):
    """브라우저를 띄우고 글쓰기 화면에 내용을 채운 뒤, 사람이 발행하도록 기다린다."""
    if not blog_id:
        raise ValueError(
            "NAVER_BLOG_ID가 설정되지 않았습니다. "
            "blog.naver.com/<아이디>의 <아이디>를 .env에 넣어주세요."
        )

    browser = browser_factory(playwright, headless=False)
    context = context_factory(browser)
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT_MS)

    try:
        page.goto(WRITE_URL.format(blog_id=blog_id), wait_until="domcontentloaded")

        if "nidlogin" in page.url:
            raise RuntimeError(
                "로그인 세션이 만료되었습니다. "
                "`python -m src.publish --login`으로 다시 로그인해주세요."
            )

        fill_editor(page, post, debug=debug)

        print()
        print("=" * 60)
        print("  내용을 채웠습니다. 브라우저에서 확인하세요.")
        print("  서식을 다듬고, 사진을 넣고, 태그를 입력한 뒤")
        print("  직접 [발행] 버튼을 누르시면 됩니다.")
        print()
        print(f"  추천 태그: {', '.join(post['tags'])}")
        print("=" * 60)
        print()
        _wait_for_enter("브라우저를 닫으려면 Enter > ")
    except PlaywrightTimeoutError as e:
        # 브라우저를 열어둔 채 멈춘다. 바로 닫으면 무엇이 잘못됐는지 볼 수 없다.
        print(f"[ERROR] 페이지가 제때 뜨지 않았습니다: {e}")
        _wait_for_enter("브라우저를 열어뒀습니다. 확인 후 Enter > ")
        raise RuntimeError("에디터 입력에 실패했습니다.") from e
    except RuntimeError:
        print("[INFO] 브라우저를 열어뒀습니다. 남은 부분은 직접 채우셔도 됩니다.")
        _wait_for_enter("확인 후 Enter > ")
        raise
    finally:
        browser.close()


def _wait_for_enter(message):
    """사람이 브라우저를 다 쓸 때까지 기다린다."""
    try:
        input(message)
    except (EOFError, KeyboardInterrupt):
        print()
