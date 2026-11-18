import json
from pathlib import Path

import pytest

from core import backend, mailer, scoring, storage

VECTORS = json.loads((Path(__file__).parent.parent / "data" / "scoring_vectors.json").read_text(encoding="utf-8"))


def to_answers(values):
    return {f"Q{i:02d}": value for i, value in enumerate(values, start=1)}


# ===== [BLOCK: DATA_INTEGRITY] START =====
def test_quiz_has_60_complete_questions():
    quiz = backend.get_quiz()
    assert [q["id"] for q in quiz["questions"]] == [f"Q{i:02d}" for i in range(1, 61)]
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
    response = backend.submit_diagnosis(to_answers([1] * 60))
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
    assert backend.submit_diagnosis(to_answers([5] * 60))["type"]["code"] == "IFPR"
# ===== [BLOCK: BACKEND_PERSISTENCE] END =====


# ===== [BLOCK: RESULT_EMAIL] START =====
BOOKING = "https://timerex.net/s/harmonize-inc/744bcdd8"
SETTINGS = mailer.SmtpSettings("smtp.test", 587, "none", "", "", "info@example.com")


def make_diagnosis(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    return backend.submit_diagnosis(to_answers([5] * 30 + [1] * 15 + [5] * 15))


def test_message_contains_result_and_booking_link(tmp_path, monkeypatch):
    diagnosis = make_diagnosis(tmp_path, monkeypatch)
    message = mailer.build_result_message(diagnosis, "a@example.com", BOOKING, SETTINGS.sender)
    plain = message.get_body(("plain",)).get_content()
    html_body = message.get_body(("html",)).get_content()
    assert "IFSR型" in message["Subject"]
    assert message["To"] == "a@example.com"
    for body in (plain, html_body):
        assert BOOKING in body and diagnosis["type"]["improvement"] in body and "75点" in body


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


# ===== [BLOCK: ROLE_LEADS] START =====
def with_lead(monkeypatch, code, segment, text):
    roles = json.loads(json.dumps(backend.get_roles()))
    roles["leads"][code][segment] = text
    monkeypatch.setattr(backend, "get_roles", lambda: roles)


def test_role_leads_cover_all_types_and_segments():
    roles = backend.get_roles()
    assert [r["id"] for r in roles["roles"]] == ["founder", "successor", "manager", "other"]
    assert set(roles["leads"]) == set(backend.get_types())
    segments = {r["segment"] for r in roles["roles"] if r["segment"]}
    assert segments == set(roles["segments"])
    assert all(set(item) == segments for item in roles["leads"].values())
    assert all(text for item in roles["leads"].values() for text in item.values())


def test_lead_switches_by_role_and_falls_back_to_feature(monkeypatch):
    leads = backend.get_roles()["leads"]["DHST"]
    assert leads["founder"] != leads["successor"] != leads["manager"]
    for segment in ("founder", "successor", "manager"):
        assert backend.resolve_lead("DHST", segment) == {"text": leads[segment], "segment": segment, "personalized": True}
    with_lead(monkeypatch, "DHST", "founder", "")
    feature = backend.get_types()["DHST"]["feature"]
    for role in ("founder", "other", None, "unknown"):  # 文言が空・その他・未選択は共通文
        assert backend.resolve_lead("DHST", role) == {"text": feature, "segment": None, "personalized": False}


def test_role_is_saved_and_unknown_role_is_dropped(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    backend.submit_diagnosis(to_answers([1] * 60), "founder")
    assert backend.submit_diagnosis(to_answers([1] * 60), "<script>")["role"] is None
    columns, rows = storage.fetch_table("diagnoses")
    assert [row[columns.index("respondent_role")] for row in rows] == ["founder", None]


def test_old_database_gets_role_column(tmp_path, monkeypatch):
    import sqlite3
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE diagnoses (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, quiz_version TEXT NOT NULL,"
            " type_code TEXT NOT NULL, axis_scores TEXT NOT NULL, answers TEXT NOT NULL)"
        )
    connection.close()
    monkeypatch.setattr(storage, "DB_PATH", path)
    backend.submit_diagnosis(to_answers([1] * 60), "manager")
    columns, rows = storage.fetch_table("diagnoses")
    assert rows[0][columns.index("respondent_role")] == "manager"


def test_mail_includes_personalized_lead(tmp_path, monkeypatch):
    with_lead(monkeypatch, "IFSR", "founder", "創業者向けの総評")
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    diagnosis = backend.submit_diagnosis(to_answers([5] * 30 + [1] * 15 + [5] * 15), "founder")
    message = mailer.build_result_message(diagnosis, "a@example.com", BOOKING, SETTINGS.sender)
    for body in (message.get_body(("plain",)).get_content(), message.get_body(("html",)).get_content()):
        assert "総評" in body and "創業者向けの総評" in body and diagnosis["type"]["feature"] in body
# ===== [BLOCK: ROLE_LEADS] END =====
