import os
from dotenv import load_dotenv

load_dotenv()

_ROOT = os.path.dirname(os.path.dirname(__file__))

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

NEWS_KEYWORDS = ["증시", "환율", "금리", "부동산", "코스피", "코스닥", "경제", "조선주", "반도체", "재테크"]

# 유튜브 채널 목록 (채널ID: 채널명)
# 채널 추가/삭제는 여기서 수정
YOUTUBE_CHANNEL_IDS = [
    "UCF8AeLlUbEpKju6v1H6p8Eg",
    "UCsJ6RuBiTVWRX156FVbeaGg",
    "UCJo6G1u0e_-wS-JQn3T-zEw",
    "UChlv4GSd7OQl3js-jkLOnFA",
    "UCntrdZrZwXiPxdObi5MHqBw",
]

MAX_ARTICLES_PER_TOPIC = 3

TOPIC_KEYWORDS = {
    "증시": ["증시", "코스피", "코스닥", "주식", "상장", "종목", "주가"],
    "환율": ["환율", "달러", "엔화", "위안", "원화"],
    "금리": ["금리", "기준금리", "한은", "한국은행", "통화정책"],
    "부동산": ["부동산", "아파트", "전세", "매매", "분양", "주택"],
    "조선주": ["조선주", "조선업", "조선소", "한화오션", "HD현대중공업", "삼성중공업", "수주"],
    "반도체": ["반도체", "삼성전자", "SK하이닉스", "HBM", "파운드리", "메모리", "AI칩"],
    "재테크": ["재테크", "저축", "적금", "ETF", "펀드", "절세", "연금"],
    "경제 일반": ["경제", "GDP", "물가", "인플레이션", "수출", "수입"],
}

DRAFTS_DIR = os.path.join(_ROOT, "drafts")

# --- 글 작성(generator) 설정 ---

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")

# 완성글이 저장되는 곳 (drafts/는 수집 초안, posts/는 발행용 완성글)
POSTS_DIR = os.path.join(_ROOT, "posts")

# 문체 학습용 예시 글. 이 파일의 톤을 따라 씁니다.
STYLE_SAMPLE_PATH = os.path.join(_ROOT, "blog-post.md")

# --- 발행(publisher) 설정 ---

# blog.naver.com/<여기> 에 해당하는 아이디
NAVER_BLOG_ID = os.getenv("NAVER_BLOG_ID", "")

# 수동 로그인 1회로 만들어지는 브라우저 세션 파일 (절대 커밋 금지)
NAVER_SESSION_PATH = os.path.join(_ROOT, ".naver_session.json")
