import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD


def send_draft_email(draft):
    """블로그 초안을 Gmail로 발송한다."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[WARN] GMAIL_ADDRESS / GMAIL_APP_PASSWORD 미설정, 이메일 발송 건너뜀")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{draft['date']}] 오늘의 경제 뉴스 정리"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS

    msg.attach(MIMEText(draft["markdown"], "plain", "utf-8"))
    msg.attach(MIMEText(draft["html"], "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL] 발송 완료: {GMAIL_ADDRESS}")
        return True
    except Exception as e:
        print(f"[ERROR] 이메일 발송 실패: {e}")
        return False
