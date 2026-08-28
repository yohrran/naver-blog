"""네이버 로그인 세션 관리.

로그인은 **자동화하지 않는다.** 브라우저를 띄워주면 사람이 직접 로그인하고,
그때 만들어진 쿠키만 파일로 저장해 다음부터 재사용한다.

이렇게 하는 이유:
- 아이디/비밀번호를 코드나 .env에 둘 필요가 없다
- 캡차·2단계 인증을 사람이 처리하므로 로그인 폼 변경에 안 깨진다
"""

import os
import sys
import time

from playwright.sync_api import Error as PlaywrightError

from src.config import NAVER_SESSION_PATH

LOGIN_URL = "https://nid.naver.com/nidlogin.login"

# 자동화 탐지를 조금이라도 줄이기 위한 실행 옵션
_LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]

# 로그인 성공 시 네이버가 심는 쿠키. 둘 다 있어야 로그인된 상태로 본다.
LOGIN_COOKIE_NAMES = ("NID_AUT", "NID_SES")

# 터미널이 없을 때 로그인을 기다리는 한도
LOGIN_WAIT_TIMEOUT = 300
LOGIN_POLL_INTERVAL = 2


def launch_browser(playwright, headless=False):
    """브라우저를 띄운다. 실제 Chrome이 있으면 그걸 쓴다."""
    try:
        return playwright.chromium.launch(
            headless=headless, channel="chrome", args=_LAUNCH_ARGS
        )
    except PlaywrightError:
        print("[WARN] 시스템 Chrome을 찾지 못해 번들 Chromium으로 실행합니다.")
        return playwright.chromium.launch(headless=headless, args=_LAUNCH_ARGS)


def session_exists():
    return os.path.exists(NAVER_SESSION_PATH)


def new_logged_in_context(browser):
    """저장된 세션으로 브라우저 컨텍스트를 만든다."""
    if not session_exists():
        raise FileNotFoundError(
            f"로그인 세션이 없습니다: {NAVER_SESSION_PATH}\n"
            "먼저 `python -m src.publish --login`을 실행해 로그인해주세요."
        )

    return browser.new_context(storage_state=NAVER_SESSION_PATH)


def _has_login_cookies(context):
    """로그인 쿠키가 모두 생겼는지 본다."""
    try:
        names = {cookie["name"] for cookie in context.cookies()}
    except PlaywrightError as e:
        raise RuntimeError(f"브라우저가 닫혔습니다: {e}") from e

    return all(name in names for name in LOGIN_COOKIE_NAMES)


def _wait_for_enter():
    """터미널이 붙어 있을 때: 사람이 Enter를 누를 때까지 기다린다."""
    try:
        input("로그인 완료 후 Enter > ")
    except (EOFError, KeyboardInterrupt):
        raise RuntimeError("로그인이 취소되었습니다.")


def _wait_for_login_cookies(context):
    """터미널이 없을 때: 로그인 쿠키가 생길 때까지 브라우저를 지켜본다.

    stdin이 없는 환경(백그라운드 실행, 에이전트 세션)에서는 input()이 바로
    EOF를 던진다. 사람이 해야 할 일은 브라우저에서 로그인하는 것이지 Enter를
    누르는 게 아니므로, 완료 신호를 브라우저 쪽에서 직접 읽는다.
    """
    deadline = time.monotonic() + LOGIN_WAIT_TIMEOUT

    while time.monotonic() < deadline:
        if _has_login_cookies(context):
            # 로그인 직후 리다이렉트가 끝나도록 잠깐 둔다
            time.sleep(LOGIN_POLL_INTERVAL)
            print("[INFO] 로그인을 감지했습니다.")
            return
        time.sleep(LOGIN_POLL_INTERVAL)

    raise RuntimeError(
        f"{LOGIN_WAIT_TIMEOUT}초 안에 로그인이 확인되지 않았습니다. 다시 실행해주세요."
    )


def _wait_for_login(context):
    """사람이 로그인을 끝낼 때까지 기다린다."""
    if sys.stdin.isatty():
        _wait_for_enter()
    else:
        _wait_for_login_cookies(context)


def save_session(playwright):
    """브라우저를 띄워 사람이 로그인하게 하고, 끝나면 세션을 저장한다."""
    browser = launch_browser(playwright, headless=False)
    context = browser.new_context()
    page = context.new_page()

    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
    except PlaywrightError as e:
        browser.close()
        raise RuntimeError(f"로그인 페이지를 열지 못했습니다: {e}") from e

    print()
    print("=" * 60)
    print("  브라우저에서 네이버에 직접 로그인해주세요.")
    if sys.stdin.isatty():
        print("  로그인이 끝나면 이 터미널로 돌아와 Enter를 누르세요.")
    else:
        print(f"  로그인이 끝나면 자동으로 감지합니다. (최대 {LOGIN_WAIT_TIMEOUT}초)")
    print("=" * 60)
    print()

    try:
        _wait_for_login(context)
    except RuntimeError:
        browser.close()
        raise

    try:
        context.storage_state(path=NAVER_SESSION_PATH)
    except PlaywrightError as e:
        browser.close()
        raise RuntimeError(f"세션 저장에 실패했습니다: {e}") from e

    browser.close()

    # 쿠키 파일이므로 소유자만 읽게 제한한다
    try:
        os.chmod(NAVER_SESSION_PATH, 0o600)
    except OSError:
        pass

    print(f"[SAVE] 세션 저장 완료: {NAVER_SESSION_PATH}")
    print("[INFO] 이 파일은 로그인 쿠키입니다. 절대 커밋하거나 공유하지 마세요.")
