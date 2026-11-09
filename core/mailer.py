"""診断結果メールの組み立てと送信。Streamlit に依存しない。

接続情報は環境変数、または .streamlit/secrets.toml から読み込む（環境変数を優先）。
"""
from __future__ import annotations

import smtplib
import ssl
import os
import tomllib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from pathlib import Path
from typing import Any

# ===== [BLOCK: SETTINGS] START =====
SECRETS_PATH = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"
SENDER_NAME = "Harmonize 組織診断"
TIMEOUT_SECONDS = 15


class MailNotConfigured(RuntimeError):
    """SMTP の接続情報が設定されていない。"""


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    security: str  # starttls / ssl / none
    username: str
    password: str
    sender: str


def load_settings() -> SmtpSettings:
    values: dict[str, Any] = {}
    if SECRETS_PATH.exists():
        values.update(tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8")))
    values.update({key: value for key, value in os.environ.items() if key.startswith("SMTP_")})
    host = str(values.get("SMTP_HOST", "")).strip()
    sender = str(values.get("SMTP_FROM", "")).strip()
    if not host or not sender:
        raise MailNotConfigured("SMTP_HOST and SMTP_FROM are required")
    return SmtpSettings(
        host=host,
        port=int(values.get("SMTP_PORT", 587)),
        security=str(values.get("SMTP_SECURITY", "starttls")).lower(),
        username=str(values.get("SMTP_USERNAME", "")),
        password=str(values.get("SMTP_PASSWORD", "")),
        sender=sender,
    )
# ===== [BLOCK: SETTINGS] END =====


# ===== [BLOCK: MESSAGE_BODY] START =====
def _axis_line(axis: dict[str, Any]) -> str:
    chosen = axis[axis["side"]]
    return f"{axis['name']}：{axis['score']}点（{axis['min']}〜{axis['max']}点）　判定 {chosen['code']}（{chosen['full']}）"


def _plain_body(diagnosis: dict[str, Any], booking_url: str) -> str:
    item = diagnosis["type"]
    axes = "\n".join(_axis_line(axis) for axis in diagnosis["axes"])
    return (
        "Harmonize 組織診断の結果をお送りします。\n\n"
        f"{item['code']}型：{item['name']}\n{item['group']}\n\n"
        f"■ 組織傾向の特徴\n{item['feature']}\n\n"
        f"■ 4軸のスコア\n{axes}\n\n"
        f"■ 組織の強み\n{item['strength']}\n\n"
        f"■ 組織の弱み\n{item['weakness']}\n\n"
        f"■ 改善に向けたポイント\n{item['improvement']}\n\n"
        f"無料ご相談（60分）のお申し込みはこちら\n{booking_url}\n"
    )


def _html_body(diagnosis: dict[str, Any], booking_url: str) -> str:
    item = diagnosis["type"]
    heading = 'style="color:#173156;font-size:16px;margin:28px 0 8px"'
    paragraph = 'style="margin:0;line-height:1.8"'
    rows = "".join(
        f'<tr><td style="padding:6px 12px 6px 0">{escape(axis["name"])}</td>'
        f'<td style="padding:6px 12px 6px 0;white-space:nowrap"><b>{axis["score"]}点</b></td>'
        f'<td style="padding:6px 0">{axis["code"]}（{escape(axis[axis["side"]]["full"])}）</td></tr>'
        for axis in diagnosis["axes"]
    )
    return (
        '<div style="max-width:560px;margin:0 auto;padding:24px 16px;color:#1c2b3a;font-size:15px;'
        "font-family:'Hiragino Sans',Meiryo,sans-serif\">"
        '<p style="margin:0;color:#5a6b78">Harmonize 組織診断の結果をお送りします。</p>'
        f'<p style="margin:16px 0 0;color:#5a6b78">{escape(item["group"])}</p>'
        f'<h1 style="color:#173156;font-size:40px;line-height:1.2;margin:4px 0">{item["code"]}型</h1>'
        f'<p style="margin:0;color:#173156;font-size:22px;font-weight:bold">{escape(item["name"])}</p>'
        f"<h2 {heading}>組織傾向の特徴</h2><p {paragraph}>{escape(item['feature'])}</p>"
        f'<h2 {heading}>4軸のスコア</h2><table style="border-collapse:collapse">{rows}</table>'
        f"<h2 {heading}>組織の強み</h2><p {paragraph}>{escape(item['strength'])}</p>"
        f"<h2 {heading}>組織の弱み</h2><p {paragraph}>{escape(item['weakness'])}</p>"
        f"<h2 {heading}>改善に向けたポイント</h2><p {paragraph}>{escape(item['improvement'])}</p>"
        f'<p style="margin:32px 0 0;text-align:center"><a href="{escape(booking_url)}" '
        'style="display:inline-block;background:#173156;color:#fff;padding:14px 32px;border-radius:28px;'
        'font-weight:bold;text-decoration:none">無料ご相談（60分）に申し込む</a></p>'
        "</div>"
    )
# ===== [BLOCK: MESSAGE_BODY] END =====


# ===== [BLOCK: BUILD_MESSAGE] START =====
def build_result_message(
    diagnosis: dict[str, Any], recipient: str, booking_url: str, sender: str
) -> EmailMessage:
    item = diagnosis["type"]
    message = EmailMessage()
    message["Subject"] = f"【Harmonize 組織診断】診断結果：{item['code']}型 {item['name']}"
    message["From"] = formataddr((SENDER_NAME, sender))
    message["To"] = recipient
    message.set_content(_plain_body(diagnosis, booking_url))
    message.add_alternative(_html_body(diagnosis, booking_url), subtype="html")
    return message
# ===== [BLOCK: BUILD_MESSAGE] END =====


# ===== [BLOCK: SEND_MESSAGE] START =====
def send(message: EmailMessage, settings: SmtpSettings) -> None:
    context = ssl.create_default_context()
    if settings.security == "ssl":
        client: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.host, settings.port, timeout=TIMEOUT_SECONDS, context=context
        )
    else:
        client = smtplib.SMTP(settings.host, settings.port, timeout=TIMEOUT_SECONDS)
    with client:
        if settings.security == "starttls":
            client.starttls(context=context)
        if settings.username:
            client.login(settings.username, settings.password)
        client.send_message(message)
# ===== [BLOCK: SEND_MESSAGE] END =====
