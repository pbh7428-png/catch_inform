"""Gmail SMTP로 HTML 메일을 보낸다. 앱 비밀번호는 `.env`에서만 읽고 출력하지 않는다."""

import smtplib
from email.message import EmailMessage
from pathlib import Path

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
REQUIRED_KEYS = ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD")


class MailError(Exception):
    """설정이 없거나 발송에 실패했을 때. 메시지에 비밀번호를 넣지 않는다."""


def load_env(path: Path) -> dict:
    """`KEY=값` 형식의 줄을 읽는다. 빈 줄과 #으로 시작하는 줄은 건너뛴다."""
    if not path.exists():
        raise MailError(f"{path.name} 파일이 없습니다. .env.example을 복사해 채워주세요.")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    missing = [key for key in REQUIRED_KEYS if not env.get(key)]
    if missing:
        raise MailError(f"{path.name}에 값이 없습니다: {', '.join(missing)}")
    return env


def build_message(env: dict, subject: str, html: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = env["GMAIL_ADDRESS"]
    message["To"] = env.get("MAIL_TO") or env["GMAIL_ADDRESS"]
    message.set_content("HTML을 표시할 수 있는 메일 앱에서 열어주세요.")
    message.add_alternative(html, subtype="html")
    return message


def send(env: dict, subject: str, html: str) -> str:
    """발송하고 받는 주소를 돌려준다."""
    message = build_message(env, subject, html)
    # 앱 비밀번호는 화면에 4자씩 띄어 보이므로 공백을 지운다.
    password = env["GMAIL_APP_PASSWORD"].replace(" ", "")
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.login(env["GMAIL_ADDRESS"], password)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as error:
        raise MailError("Gmail 로그인 실패: 주소와 앱 비밀번호를 확인해주세요.") from error
    except (smtplib.SMTPException, OSError) as error:
        raise MailError(f"발송 실패: {type(error).__name__}") from error
    return message["To"]
