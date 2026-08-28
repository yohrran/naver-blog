"""네이버 로그인 세션 관리.

로그인은 **자동화하지 않는다.** 브라우저를 띄워주면 사람이 직접 로그인하고,
그때 만들어진 쿠키는 전용 프로파일에 남아 다음 실행에서 그대로 재사용된다.

이렇게 하는 이유:
- 아이디/비밀번호를 코드나 .env에 둘 필요가 없다
- 캡차·2단계 인증을 사람이 처리하므로 로그인 폼 변경에 안 깨진다
- 프로파일이 고정되어 매번 '새 기기'로 잡히지 않는다

세션 수명은 전적으로 '로그인 상태 유지'에 달려 있다. 체크하지 않으면
NID_AUT/NID_SES가 만료 없는 세션 쿠키로 발급되고, 세션 쿠키는 정의상
브라우저를 닫는 순간 프로파일에도 남지 않는다. 그래서 로그인 화면을 띄울 때
이 체크박스를 미리 켜준다. 프로파일과 체크박스는 한 쌍으로 동작한다.
"""

import os
import sys
import time

from playwright.sync_api import Error as PlaywrightError

from src.config import NAVER_PROFILE_DIR

LOGIN_URL = "https://nid.naver.com/nidlogin.login"

# 자동화 탐지를 조금이라도 줄이기 위한 실행 옵션
_LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]

# 로그인 성공 시 네이버가 심는 쿠키. 둘 다 있어야 로그인된 상태로 본다.
LOGIN_COOKIE_NAMES = ("NID_AUT", "NID_SES")

# '로그인 상태 유지' 체크박스. 네이버가 로그인 폼을 바꾸면 여기가 깨진다.
# input은 1px로 숨겨져 있고(스크린리더용), 감싸는 div가 tabindex=0이라
# 키보드로 조작할 수 있다.
LOGIN_STAY_CHECKBOX = "#loginStay"
LOGIN_STAY_LABEL = "label[for='loginStay']"
LOGIN_STAY_TOGGLE = ".option_item.stay"

# 터미널이 없을 때 로그인을 기다리는 한도
LOGIN_WAIT_TIMEOUT = 300
LOGIN_POLL_INTERVAL = 2

_RELOGIN_HINT = "`python -m src.publish --login`으로 다시 로그인해주세요."


def profile_exists():
    return os.path.isdir(NAVER_PROFILE_DIR)


def launch_profile_context(playwright, headless=False):
    """전용 프로파일로 브라우저를 띄운다. 실제 Chrome이 있으면 그걸 쓴다.

    persistent context는 브라우저와 컨텍스트가 한 몸이라 close()도 하나뿐이다.
    """
    options = {
        "user_data_dir": NAVER_PROFILE_DIR,
        "headless": headless,
        "args": _LAUNCH_ARGS,
    }

    try:
        return playwright.chromium.launch_persistent_context(channel="chrome", **options)
    except PlaywrightError:
        print("[WARN] 시스템 Chrome을 찾지 못해 번들 Chromium으로 실행합니다.")
        return playwright.chromium.launch_persistent_context(**options)


def has_login_cookies(context):
    """로그인 쿠키가 모두 있는지 본다."""
    try:
        names = {cookie["name"] for cookie in context.cookies()}
    except PlaywrightError as e:
        raise RuntimeError(f"브라우저가 닫혔습니다: {e}") from e

    return all(name in names for name in LOGIN_COOKIE_NAMES)


def new_logged_in_context(playwright, headless=False):
    """로그인된 브라우저 컨텍스트를 돌려준다. 아니면 그 자리에서 알려준다.

    페이지를 열어보고 리다이렉트를 관찰하는 대신 쿠키를 먼저 확인한다.
    만료됐을 때 엉뚱한 화면에서 선택자를 못 찾고 헤매는 일이 없어진다.
    """
    if not profile_exists():
        raise FileNotFoundError(f"네이버 로그인 세션이 없습니다.\n먼저 {_RELOGIN_HINT}")

    context = launch_profile_context(playwright, headless=headless)

    try:
        if not has_login_cookies(context):
            raise RuntimeError(f"로그인 세션이 만료되었습니다.\n{_RELOGIN_HINT}")
    except RuntimeError:
        context.close()
        raise

    return context


def _login_stay_enabled(page):
    """'로그인 상태 유지'가 실제로 켜졌는지 본다.

    checked만 보면 부족하다. 네이버는 자체 핸들러에서 value를 off->on으로
    바꾸고 폼으로 전송되는 건 그 value다. 핸들러가 돌지 않았다면 화면상으로만
    켜지고 서버는 로그인을 유지하지 않는다. 그래서 둘 다 확인한다.
    """
    script = (
        "() => { const el = document.querySelector(%r);"
        " return el ? el.checked && el.value === 'on' : false; }" % LOGIN_STAY_CHECKBOX
    )

    try:
        return bool(page.evaluate(script))
    except PlaywrightError:
        return False


def _toggle_by_keyboard(page):
    """감싸는 div에 포커스를 주고 Space를 누른다. 가장 사람에 가까운 경로."""
    page.locator(LOGIN_STAY_TOGGLE).focus(timeout=5000)
    page.keyboard.press("Space")


def _toggle_by_label_click(page):
    """label을 JS로 클릭한다. Playwright 클릭이 막힐 때를 위한 폴백."""
    page.evaluate("() => document.querySelector(%r).click()" % LOGIN_STAY_LABEL)


def _enable_login_stay(page):
    """'로그인 상태 유지'를 미리 켜둔다.

    이게 꺼져 있으면 로그인 쿠키가 만료 없는 세션 쿠키로 발급되고, 세션 쿠키는
    브라우저를 닫는 순간 프로파일에도 남지 않는다. 실패해도 로그인 자체는
    되므로 막지 않고 경고만 남긴다.
    """
    if _login_stay_enabled(page):
        return True

    for toggle in (_toggle_by_keyboard, _toggle_by_label_click):
        try:
            toggle(page)
        except PlaywrightError as e:
            print(f"[WARN] '로그인 상태 유지' 조작 실패({toggle.__name__}): {e}")
            continue

        if _login_stay_enabled(page):
            print("[INFO] '로그인 상태 유지'를 켰습니다. 세션이 오래 유지됩니다.")
            return True

    print("[WARN] 로그인 화면에서 '로그인 상태 유지'를 직접 켜주세요.")
    print("[WARN] 켜지 않으면 브라우저를 닫는 순간 세션이 사라집니다.")
    return False


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
        if has_login_cookies(context):
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


def _report_session_lifetime(context):
    """로그인 쿠키가 얼마나 갈지 알려준다."""
    try:
        cookies = context.cookies()
    except PlaywrightError:
        return

    expiries = [
        c.get("expires", -1) for c in cookies if c["name"] in LOGIN_COOKIE_NAMES
    ]

    if not expiries or min(expiries) <= 0:
        print("[WARN] 로그인 쿠키에 만료가 없습니다(세션 쿠키).")
        print("[WARN] 브라우저를 닫으면 사라지므로 다음 실행에 다시 로그인해야 합니다.")
        return

    days = (min(expiries) - time.time()) / 86400
    print(f"[INFO] 로그인 세션이 약 {days:.0f}일간 유지됩니다.")


def run_login(playwright):
    """브라우저를 띄워 사람이 로그인하게 하고, 쿠키를 프로파일에 남긴다."""
    context = launch_profile_context(playwright, headless=False)
    page = context.pages[0] if context.pages else context.new_page()

    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
    except PlaywrightError as e:
        context.close()
        raise RuntimeError(f"로그인 페이지를 열지 못했습니다: {e}") from e

    _enable_login_stay(page)

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
        _report_session_lifetime(context)
    except RuntimeError:
        context.close()
        raise

    # 쿠키가 프로파일에 실제로 기록되도록 정상 종료시킨다
    context.close()

    # 프로파일에 로그인 쿠키가 들어 있으므로 소유자만 접근하게 막는다
    try:
        os.chmod(NAVER_PROFILE_DIR, 0o700)
    except OSError:
        pass

    print(f"[SAVE] 로그인 프로파일 저장 완료: {NAVER_PROFILE_DIR}")
    print("[INFO] 이 디렉터리는 로그인 쿠키를 담고 있습니다. 커밋하거나 공유하지 마세요.")
