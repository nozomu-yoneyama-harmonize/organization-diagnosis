"""Harmonize 16タイプ組織診断 プロトタイプ。 起動: streamlit run app.py"""
from __future__ import annotations

from typing import Any

import streamlit as st

from core import backend
from core.scoring import AnswerValidationError
from ui import components as ui

# ===== [BLOCK: PAGE_CONFIG] START =====
st.set_page_config(page_title="Harmonize 組織診断", page_icon="assets/logo.png", layout="centered")
st.html(ui.stylesheet())

MAX_EMAILS_PER_SESSION = 3
BOOKING_URL = "https://timerex.net/s/harmonize-inc/744bcdd8"
# ===== [BLOCK: PAGE_CONFIG] END =====


# ===== [BLOCK: SESSION_STATE] START =====
def init_state() -> None:
    defaults: dict[str, Any] = {
        "phase": "quiz",
        "page": 0,
        "answers": {},
        "missing": [],
        "attempt": 0,
        "diagnosis": None,
        "email_sent_to": None,
        "email_count": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go(phase: str, page: int = 0) -> None:
    st.session_state.phase = phase
    st.session_state.page = page
    st.session_state.missing = []
    st.rerun()


def restart() -> None:
    st.session_state.answers = {}
    st.session_state.diagnosis = None
    st.session_state.email_sent_to = None
    go("quiz")


def store_answer(question_id: str) -> None:
    st.session_state.answers[question_id] = st.session_state[f"ans_{question_id}"]
    if question_id in st.session_state.missing:
        st.session_state.missing.remove(question_id)
# ===== [BLOCK: SESSION_STATE] END =====


# ===== [BLOCK: SCREEN_QUIZ] START =====
def render_quiz(quiz: dict[str, Any]) -> None:
    axes = quiz["axes"]
    page = st.session_state.page
    axis = axes[page]
    answers = st.session_state.answers
    questions = [q for q in quiz["questions"] if q["axis"] == axis["id"]]
    option_labels = {int(value): label for value, label in quiz["scale"]["labels"].items()}
    options = list(option_labels)

    counts = [sum(qid in answers for qid in item["question_ids"]) for item in axes]
    st.html(ui.progress_header(axes, counts, page))
    st.html(ui.page_intro(axis, page, len(axes)))

    for question in questions:
        question_id = question["id"]
        with st.container(key=f"card_{question_id}"):
            st.html(ui.question_head(question, question_id in st.session_state.missing))
            saved = answers.get(question_id)
            st.radio(
                f"{question_id} {question['theme']}",
                options,
                index=None if saved is None else options.index(saved),
                format_func=option_labels.get,
                horizontal=True,
                label_visibility="collapsed",
                key=f"ans_{question_id}",
                on_change=store_answer,
                args=(question_id,),
            )

    if st.session_state.missing:
        st.html(ui.validation_alert(st.session_state.missing))

    is_last = page == len(axes) - 1
    with st.container(horizontal=True, key="nav"):
        if page > 0 and st.button("前へ戻る", key="back", width="stretch"):
            go("quiz", page - 1)
        if st.button("結果を見る" if is_last else "次へ進む", type="primary", key="next", width="stretch"):
            missing = [q["id"] for q in questions if q["id"] not in answers]
            if missing:
                st.session_state.missing = missing
                st.session_state.attempt += 1
                st.rerun()
            if is_last:
                finish_quiz(quiz)
            go("quiz", page + 1)

    if st.session_state.missing:
        selector = f".st-key-card_{st.session_state.missing[0]}"
        nonce = f"missing-{st.session_state.attempt}"
    else:
        selector, nonce = "#hz-none", f"page-{page}"
    st.html(ui.scroll_script(selector, nonce), unsafe_allow_javascript=True)
# ===== [BLOCK: SCREEN_QUIZ] END =====


# ===== [BLOCK: FINISH_QUIZ] START =====
def finish_quiz(quiz: dict[str, Any]) -> None:
    """全問そろっていれば判定して結果へ。漏れがあればそのページへ戻す。"""
    try:
        st.session_state.diagnosis = backend.submit_diagnosis(st.session_state.answers)
    except AnswerValidationError as error:
        problem_ids = error.missing + error.invalid
        first = next(q for q in quiz["questions"] if q["id"] in problem_ids)
        page = next(i for i, axis in enumerate(quiz["axes"]) if axis["id"] == first["axis"])
        st.session_state.phase, st.session_state.page = "quiz", page
        st.session_state.missing = [i for i in problem_ids if i in quiz["axes"][page]["question_ids"]]
        st.session_state.attempt += 1
        st.rerun()
    go("result")
# ===== [BLOCK: FINISH_QUIZ] END =====


# ===== [BLOCK: EMAIL_DIALOG] START =====
EMAIL_ERROR_MESSAGES = {
    "invalid_email": "メールアドレスは name@example.com の形式で入力してください",
    "not_configured": "メール送信の設定が完了していないため送信できません",
    "send_failed": "送信できませんでした。アドレスを確認して、もう一度お試しください",
}


@st.dialog("結果をメールに送る")
def email_dialog(diagnosis: dict[str, Any]) -> None:
    with st.form("email_form", border=False):
        email = st.text_input("メールアドレス", autocomplete="email")
        st.caption("入力したアドレスは、この診断結果の送信にのみ使用し、保存しません。")
        submitted = st.form_submit_button("送信する", type="primary", width="stretch")
    if not submitted:
        return
    if st.session_state.email_count >= MAX_EMAILS_PER_SESSION:
        st.error(f"送信できるのは1回の診断につき{MAX_EMAILS_PER_SESSION}通までです")
        return
    with st.spinner("送信しています"):
        response = backend.send_result_email(diagnosis, email, BOOKING_URL)
    if response["ok"]:
        st.session_state.email_count += 1
        st.session_state.email_sent_to = email.strip()
        st.rerun()
    st.error(EMAIL_ERROR_MESSAGES[response["error"]])
# ===== [BLOCK: EMAIL_DIALOG] END =====


# ===== [BLOCK: SCREEN_RESULT] START =====
def render_result() -> None:
    diagnosis = st.session_state.diagnosis
    if diagnosis is None:
        go("quiz")
    st.html(ui.result_hero(diagnosis))
    st.html(ui.result_body(diagnosis))
    with st.container(key="next_band"):
        st.html(ui.result_next(diagnosis))
        st.link_button(
            "無料ご相談（60分）に申し込む",
            BOOKING_URL,
            key="cta",
            type="primary",
            width="stretch",
            on_click=backend.record_event,
            args=(diagnosis["id"], "cta_click"),
        )
        if st.button("結果をメールに送る", key="email_result", width="stretch"):
            email_dialog(diagnosis)
        if st.session_state.email_sent_to:
            st.html(ui.email_sent(st.session_state.email_sent_to))
    if st.button("もう一度診断する", key="retry", type="tertiary", width="stretch"):
        restart()
    st.html(ui.scroll_script("#hz-none", f"result-{diagnosis['id']}"), unsafe_allow_javascript=True)
# ===== [BLOCK: SCREEN_RESULT] END =====


# ===== [BLOCK: ROUTER] START =====
def main() -> None:
    init_state()
    quiz = backend.get_quiz()
    phase = st.session_state.phase
    if phase == "result":
        render_result()
    else:
        render_quiz(quiz)


main()
# ===== [BLOCK: ROUTER] END =====
