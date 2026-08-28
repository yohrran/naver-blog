"""Claude API로 블로그 완성글을 쓴다.

두 갈래의 입력을 받는다.
- 수집 초안(drafts/YYYY-MM-DD.md) -> 오늘의 경제 뉴스 글
- 임의 주제 문자열 -> 아무 주제나

두 경우 모두 같은 시스템 프롬프트(문체)를 쓰기 때문에 프롬프트 캐시가 적중한다.
"""

import anthropic

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from src.generator.post_file import parse_post
from src.generator.style import build_system_prompt

# 블로그 글 한 편이면 충분한 길이. 스트리밍이라 타임아웃 걱정은 없다.
MAX_TOKENS = 16000


class PostWriteError(RuntimeError):
    """글 생성에 실패했을 때."""


def _build_client():
    if not ANTHROPIC_API_KEY:
        raise PostWriteError(
            "ANTHROPIC_API_KEY가 설정되지 않았습니다. .env에 추가해주세요."
        )
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _call_claude(user_message):
    """Claude를 호출하고 텍스트 응답을 돌려준다."""
    client = _build_client()

    try:
        with client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": build_system_prompt(),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            message = stream.get_final_message()
    except anthropic.AuthenticationError as e:
        raise PostWriteError(f"API 키가 유효하지 않습니다: {e}") from e
    except anthropic.RateLimitError as e:
        raise PostWriteError(f"요청이 너무 많습니다. 잠시 후 다시 시도하세요: {e}") from e
    except anthropic.APIStatusError as e:
        raise PostWriteError(f"API 오류 ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise PostWriteError(f"네트워크 오류로 Claude에 연결하지 못했습니다: {e}") from e

    if message.stop_reason == "refusal":
        raise PostWriteError("모델이 이 주제에 대한 작성을 거절했습니다.")

    text = "".join(b.text for b in message.content if b.type == "text").strip()
    if not text:
        raise PostWriteError("모델이 빈 응답을 돌려줬습니다.")

    usage = message.usage
    print(
        f"[INFO] 토큰: 입력 {usage.input_tokens} / 출력 {usage.output_tokens} / "
        f"캐시적중 {usage.cache_read_input_tokens}"
    )

    return text


def _to_post(text):
    """모델 응답을 글 dict로 바꾼다."""
    try:
        return parse_post(text)
    except ValueError as e:
        raise PostWriteError(f"모델 응답 형식이 올바르지 않습니다: {e}") from e


def write_from_draft(draft_markdown, date, extra_instruction=""):
    """수집 초안을 재료로 오늘의 경제 뉴스 글을 쓴다."""
    if not draft_markdown.strip():
        raise PostWriteError("초안이 비어 있습니다.")

    user_message = f"""아래는 {date}에 자동으로 수집한 경제 뉴스와 유튜브 영상 목록이다.
이걸 재료로 블로그 글 한 편을 써라.

지켜야 할 것:
- 기사 제목을 그냥 나열하지 마라. 오늘 시장에서 실제로 무슨 일이 있었는지 흐름으로 엮어라.
- 재료에 없는 사실, 수치, 인용을 만들어내지 마라. 확실하지 않으면 쓰지 마라.
- 매수·매도 추천을 하지 마라. 무슨 일이 있었는지만 전달한다.
- 주제 3~5개를 골라 다루고, 나머지는 버려라. 전부 다루려 하지 마라.
- 원문 링크는 각 주제 끝에 마크다운 링크로 붙여라.
{extra_instruction}

<수집자료>
{draft_markdown}
</수집자료>"""

    return _to_post(_call_claude(user_message))


def write_from_topic(topic, notes="", extra_instruction=""):
    """임의 주제로 글을 쓴다."""
    if not topic.strip():
        raise PostWriteError("주제가 비어 있습니다.")

    sections = [f"주제: {topic}"]
    if notes.strip():
        sections.append(f"\n참고할 메모:\n{notes.strip()}")

    sections.append(
        """
지켜야 할 것:
- 확인되지 않은 사실, 수치, 인용을 만들어내지 마라. 모르면 모른다고 쓰거나 빼라.
- 겪은 일처럼 쓰되, 실제로 있었던 일인 것처럼 구체적인 거짓 경험을 지어내지 마라.
  메모에 없는 개인적 일화가 필요하면 `[여기에 경험 추가]`라고 자리만 표시해라.
- 1500~2500자 사이로 써라."""
    )

    if extra_instruction:
        sections.append(extra_instruction)

    return _to_post(_call_claude("\n".join(sections)))
