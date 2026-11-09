"""診断の判定ロジック。

Streamlit にも DB にも依存しない純粋関数だけを置く。
JavaScript へ移植するときは、このファイルと data/scoring_vectors.json だけを見ればよい。
"""
from __future__ import annotations

from typing import Any, Mapping


# ===== [BLOCK: ERRORS] START =====
class AnswerValidationError(ValueError):
    """回答が不正なときの例外。missing=未回答、invalid=範囲外の設問ID。"""

    def __init__(self, missing: list[str], invalid: list[str]):
        self.missing = missing
        self.invalid = invalid
        super().__init__(f"missing={missing} invalid={invalid}")
# ===== [BLOCK: ERRORS] END =====


# ===== [BLOCK: VALIDATE_ANSWERS] START =====
def validate_answers(quiz: Mapping[str, Any], answers: Mapping[str, int]) -> None:
    low, high = quiz["scale"]["min"], quiz["scale"]["max"]
    missing: list[str] = []
    invalid: list[str] = []
    for question in quiz["questions"]:
        qid = question["id"]
        if qid not in answers or answers[qid] is None:
            missing.append(qid)
            continue
        value = answers[qid]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            invalid.append(qid)
    if missing or invalid:
        raise AnswerValidationError(missing, invalid)
# ===== [BLOCK: VALIDATE_ANSWERS] END =====


# ===== [BLOCK: SCORE_ANSWERS] START =====
def score_answers(quiz: Mapping[str, Any], answers: Mapping[str, int]) -> dict[str, Any]:
    """軸ごとに加算し、合計が threshold 以下なら A 側、超えたら B 側と判定する。"""
    validate_answers(quiz, answers)
    low, high = quiz["scale"]["min"], quiz["scale"]["max"]
    axes: list[dict[str, Any]] = []
    type_code = ""
    for axis in quiz["axes"]:
        count = len(axis["question_ids"])
        score = sum(answers[qid] for qid in axis["question_ids"])
        side = "a" if score <= axis["threshold"] else "b"
        min_score, max_score = count * low, count * high
        type_code += axis[side]["code"]
        axes.append(
            {
                "id": axis["id"],
                "name": axis["name"],
                "score": score,
                "min": min_score,
                "max": max_score,
                "threshold": axis["threshold"],
                "side": side,
                "code": axis[side]["code"],
                "position": (score - min_score) / (max_score - min_score),
                "a": axis["a"],
                "b": axis["b"],
            }
        )
    return {"type_code": type_code, "axes": axes}
# ===== [BLOCK: SCORE_ANSWERS] END =====
