import json
from pathlib import Path

import pytest

from core import backend, mailer, scoring, storage

VECTORS = json.loads((Path(__file__).parent.parent / "data" / "scoring_vectors.json").read_text(encoding="utf-8"))


def to_answers(values):
    return {f"Q{i:02d}": value for i, value in enumerate(values, start=1)}


# ===== [BLOCK: DATA_INTEGRITY] START =====
def test_quiz_has_40_complete_questions():
    quiz = backend.get_quiz()
    assert [q["id"] for q in quiz["questions"]] == [f"Q{i:02d}" for i in range(1, 41)]
    assert all(q["theme"] and q["a"] and q["b"] for q in quiz["questions"])


def test_all_16_type_codes_have_content():
    quiz = backend.get_quiz()
    types = backend._get_types()
    codes = {
        a + b + c + d
        for a in (quiz["axes"][0]["a"]["code"], quiz["axes"][0]["b"]["code"])
        for b in (quiz["axes"][1]["a"]["code"], quiz["axes"][1]["b"]["code"])
        for c in (quiz["axes"][2]["a"]["code"], quiz["axes"][2]["b"]["code"])
        for d in (quiz["axes"][3]["a"]["code"], quiz["axes"][3]["b"]["code"])
    }
    assert codes == set(types)
    for item in types.values():
        assert all(item[key] for key in ("name", "group", "feature", "strength", "weakness", "improvement"))
# ===== [BLOCK: DATA_INTEGRITY] END =====


# ===== [BLOCK: GOLDEN_VECTORS] START =====
@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: c["name"])
def test_golden_vectors(case):
    result = scoring.score_answers(backend.get_quiz(), to_answers(case["answers"]))
    assert result["type_code"] == case["expected"]["type_code"]
    assert [axis["score"] for axis in result["axes"]] == case["expected"]["scores"]


@pytest.mark.parametrize("case", VECTORS["errors"], ids=lambda c: c["name"])
def test_invalid_answers_are_rejected(case):
    with pytest.raises(scoring.AnswerValidationError) as error:
        scoring.score_answers(backend.get_quiz(), to_answers(case["answers"]))
    assert getattr(error.value, case["error"]) == case["ids"]
# ===== [BLOCK: GOLDEN_VECTORS] END =====


# ===== [BLOCK: BACKEND_PERSISTENCE] START =====
def test_submit_event_and_lead_are_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    response = backend.submit_diagnosis(to_answers([1] * 40))
    assert response["type"]["code"] == "DHST"
    json.dumps(response)  # API にそのまま載せられること

    backend.record_event(response["id"], "cta_click")
    assert backend.create_lead(response["id"], "株式会社A", "山田", "not-an-email")["ok"] is False
    assert backend.create_lead(response["id"], "株式会社A", "山田", "a@example.com")["ok"] is True

    assert len(storage.fetch_table("diagnoses")[1]) == 1
    assert len(storage.fetch_table("events")[1]) == 1
    assert len(storage.fetch_table("leads")[1]) == 1


def test_save_failure_still_returns_result(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(storage, "save_diagnosis", boom)
    assert backend.submit_diagnosis(to_answers([5] * 40))["type"]["code"] == "IFPR"
# ===== [BLOCK: BACKEND_PERSISTENCE] END =====


# ===== [BLOCK: RESULT_EMAIL] START =====
BOOKING = "https://timerex.net/s/harmonize-inc/744bcdd8"
SETTINGS = mailer.SmtpSettings("smtp.test", 587, "none", "", "", "info@example.com")


def make_diagnosis(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    return backend.submit_diagnosis(to_answers([5] * 20 + [1] * 10 + [5] * 10))


def test_message_contains_result_and_booking_link(tmp_path, monkeypatch):
    diagnosis = make_diagnosis(tmp_path, monkeypatch)
    message = mailer.build_result_message(diagnosis, "a@example.com", BOOKING, SETTINGS.sender)
    plain = message.get_body(("plain",)).get_content()
    html_body = message.get_body(("html",)).get_content()
    assert "IFSR型" in message["Subject"]
    assert message["To"] == "a@example.com"
    for body in (plain, html_body):
        assert BOOKING in body and diagnosis["type"]["improvement"] in body and "50点" in body


def test_send_email_records_event_without_storing_address(tmp_path, monkeypatch):
    diagnosis = make_diagnosis(tmp_path, monkeypatch)
    sent = []
    monkeypatch.setattr(mailer, "load_settings", lambda: SETTINGS)
    monkeypatch.setattr(mailer, "send", lambda message, settings: sent.append(message))
    assert backend.send_result_email(diagnosis, " a@example.com ", BOOKING) == {"ok": True}
    assert sent[0]["To"] == "a@example.com"
    columns, rows = storage.fetch_table("events")
    assert rows[0][columns.index("name")] == "result_email_sent"
    assert "a@example.com" not in str([storage.fetch_table(t)[1] for t in ("diagnoses", "events", "leads")])


@pytest.mark.parametrize("address", ["", "no-at-mark", "a b@example.com", "a@example.com\r\nBcc: x@example.com"])
def test_invalid_address_is_rejected_before_sending(tmp_path, monkeypatch, address):
    diagnosis = make_diagnosis(tmp_path, monkeypatch)
    monkeypatch.setattr(mailer, "send", lambda *args: pytest.fail("must not send"))
    assert backend.send_result_email(diagnosis, address, BOOKING)["error"] == "invalid_email"


def test_missing_settings_and_send_failure_are_reported(tmp_path, monkeypatch):
    diagnosis = make_diagnosis(tmp_path, monkeypatch)
    monkeypatch.setattr(mailer, "SECRETS_PATH", tmp_path / "none.toml")
    for key in ("SMTP_HOST", "SMTP_FROM"):
        monkeypatch.delenv(key, raising=False)
    assert backend.send_result_email(diagnosis, "a@example.com", BOOKING)["error"] == "not_configured"

    def refused(*args):
        raise ConnectionRefusedError

    monkeypatch.setattr(mailer, "load_settings", lambda: SETTINGS)
    monkeypatch.setattr(mailer, "send", refused)
    assert backend.send_result_email(diagnosis, "a@example.com", BOOKING)["error"] == "send_failed"
# ===== [BLOCK: RESULT_EMAIL] END =====
