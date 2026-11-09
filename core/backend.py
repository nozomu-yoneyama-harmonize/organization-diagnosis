"""画面から呼ぶ唯一の窓口。

app.py はこのモジュールの関数だけを使い、やり取りは JSON にできる dict のみとする。
JavaScript バックエンドへ移行するときは、各関数の中身を HTTP 呼び出しに差し替える。
対応する API は docs/migration-to-js.md を参照。
"""
from __future__ import annotations

import json
import logging
import re
import smtplib
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from core import mailer, scoring, storage

logger = logging.getLogger(__name__)

# ===== [BLOCK: DATA_LOADING] START =====
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def get_quiz() -> dict[str, Any]:
    """GET /api/v1/quiz 相当。"""
    return json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _get_types() -> dict[str, Any]:
    return json.loads((DATA_DIR / "types.json").read_text(encoding="utf-8"))["types"]
# ===== [BLOCK: DATA_LOADING] END =====


# ===== [BLOCK: SUBMIT_DIAGNOSIS] START =====
def submit_diagnosis(answers: dict[str, int]) -> dict[str, Any]:
    """POST /api/v1/diagnoses 相当。保存に失敗しても診断結果は返す。"""
    quiz = get_quiz()
    result = scoring.score_answers(quiz, answers)
    diagnosis_id = str(uuid.uuid4())
    try:
        storage.save_diagnosis(
            diagnosis_id,
            quiz["version"],
            result["type_code"],
            {axis["id"]: axis["score"] for axis in result["axes"]},
            answers,
        )
    except Exception:  # 保存失敗で利用者の結果表示を止めない
        logger.exception("failed to save diagnosis")
    return {
        "id": diagnosis_id,
        "type": _get_types()[result["type_code"]],
        "axes": result["axes"],
    }
# ===== [BLOCK: SUBMIT_DIAGNOSIS] END =====


# ===== [BLOCK: RECORD_EVENT] START =====
def record_event(diagnosis_id: str, name: str) -> None:
    """POST /api/v1/diagnoses/{id}/events 相当。計測の失敗は画面に影響させない。"""
    try:
        storage.save_event(diagnosis_id, name)
    except Exception:
        logger.exception("failed to save event")
# ===== [BLOCK: RECORD_EVENT] END =====


# ===== [BLOCK: CREATE_LEAD] START =====
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_lead(company: str, name: str, email: str) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not company.strip():
        errors["company"] = "会社名を入力してください"
    if not name.strip():
        errors["name"] = "お名前を入力してください"
    if not EMAIL_PATTERN.match(email.strip()):
        errors["email"] = "メールアドレスは name@example.com の形式で入力してください"
    return errors


def create_lead(diagnosis_id: str, company: str, name: str, email: str) -> dict[str, Any]:
    """POST /api/v1/leads 相当。"""
    errors = validate_lead(company, name, email)
    if errors:
        return {"ok": False, "errors": errors}
    lead_id = storage.save_lead(diagnosis_id, company.strip(), name.strip(), email.strip())
    return {"ok": True, "id": lead_id}
# ===== [BLOCK: CREATE_LEAD] END =====


# ===== [BLOCK: SEND_RESULT_EMAIL] START =====
def send_result_email(diagnosis: dict[str, Any], email: str, booking_url: str) -> dict[str, Any]:
    """POST /api/v1/diagnoses/{id}/email 相当。アドレスは保存しない。"""
    recipient = email.strip()
    if not EMAIL_PATTERN.match(recipient):
        return {"ok": False, "error": "invalid_email"}
    try:
        settings = mailer.load_settings()
        message = mailer.build_result_message(diagnosis, recipient, booking_url, settings.sender)
        mailer.send(message, settings)
    except mailer.MailNotConfigured:
        logger.warning("SMTP settings are missing")
        return {"ok": False, "error": "not_configured"}
    except (OSError, smtplib.SMTPException, ValueError):
        logger.exception("failed to send result email")
        return {"ok": False, "error": "send_failed"}
    record_event(diagnosis["id"], "result_email_sent")
    return {"ok": True}
# ===== [BLOCK: SEND_RESULT_EMAIL] END =====
