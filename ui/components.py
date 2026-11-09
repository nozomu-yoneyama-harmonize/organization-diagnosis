"""画面パーツの HTML を組み立てる。ロジックは持たず、受け取った値を描くだけ。"""
from __future__ import annotations

import base64
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# ===== [BLOCK: ASSET_LOADERS] START =====
@lru_cache(maxsize=1)
def stylesheet() -> str:
    return "<style>" + (ASSETS / "styles.css").read_text(encoding="utf-8") + "</style>"


@lru_cache(maxsize=1)
def logo_src() -> str:
    encoded = base64.b64encode((ASSETS / "logo.png").read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def logo(css_class: str = "hz-logo") -> str:
    return f'<img class="{css_class}" src="{logo_src()}" alt="Harmonize">'
# ===== [BLOCK: ASSET_LOADERS] END =====


# ===== [BLOCK: SPINE_CHART] START =====
ROW_HEIGHT = 84
TRACK_CENTER = 66
LINE_COLOR = "#7bb2af"


def _spine_x(position: float) -> float:
    """両端の点が枠で切れないよう、0〜1 を 4〜96% に写す。"""
    return 4 + 92 * position


def spine(axes: list[dict[str, Any]]) -> str:
    """4軸を縦に並べ、各軸の位置を線でつないだ「組織の骨格図」。"""
    points = " ".join(
        f"{_spine_x(axis['position']):.2f},{index * ROW_HEIGHT + TRACK_CENTER}"
        for index, axis in enumerate(axes)
    )
    rows = []
    for axis in axes:
        side = axis.get("side", "")
        a_class = "is-on" if side == "a" else ""
        b_class = "is-on" if side == "b" else ""
        center = f'{escape(axis["name"])} <strong>{axis["score"]}点</strong>'
        tooltip = f'{escape(axis["name"])}：{axis["score"]}点（{axis["min"]}〜{axis["max"]}点、{axis["threshold"]}点以下は{escape(axis["a"]["short"])}側）'
        rows.append(
            f'<div class="hz-spine__row" title="{tooltip}">'
            f'<div class="hz-spine__labels">'
            f'<span class="{a_class}">{escape(axis["a"]["short"])}</span>'
            f'<span class="hz-spine__axis">{center}</span>'
            f'<span class="{b_class}">{escape(axis["b"]["short"])}</span>'
            f"</div>"
            f'<div class="hz-spine__track"><i></i>'
            f'<b class="hz-spine__dot side-{side}" style="left:{_spine_x(axis["position"]):.2f}%"></b>'
            f"</div></div>"
        )
    # st.html は <svg> を取り除くため、背景画像として線を描く
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 {len(axes) * ROW_HEIGHT}' preserveAspectRatio='none'>"
        f"<polyline points='{points}' fill='none' stroke='{LINE_COLOR}' stroke-width='2' vector-effect='non-scaling-stroke'/></svg>"
    )
    line = f'<div class="hz-spine__line" style="background-image:url(&quot;data:image/svg+xml,{quote(svg)}&quot;)"></div>'
    return f'<div class="hz-spine">{line}{"".join(rows)}</div>'
# ===== [BLOCK: SPINE_CHART] END =====


# ===== [BLOCK: QUIZ_PARTS] START =====
def progress_header(axes: list[dict[str, Any]], counts: list[int], current: int) -> str:
    total = sum(len(axis["question_ids"]) for axis in axes)
    answered = sum(counts)
    bars = "".join(
        f'<span class="{"is-current" if index == current else ""}">'
        f'<i style="width:{count / len(axis["question_ids"]) * 100:.0f}%"></i></span>'
        for index, (axis, count) in enumerate(zip(axes, counts))
    )
    return (
        f'<div class="hz-progress" role="progressbar" aria-valuemin="0" aria-valuemax="{total}" '
        f'aria-valuenow="{answered}" aria-label="回答の進み具合">'
        f'<div class="hz-progress__meta"><span>{escape(axes[current]["name"])}</span>'
        f"<strong>{answered} / {total}問</strong></div>"
        f'<div class="hz-progress__bars">{bars}</div></div>'
    )


def page_intro(axis: dict[str, Any], page_index: int, page_count: int) -> str:
    opening = (
        f'<div class="hz-opening">{logo("hz-logo hz-logo--small")}'
        "<h1>組織診断</h1>"
        "<p>数値管理、組織、業務フロー、会議の4軸から、自社の現状を16タイプに分類します。全40問、所要時間は約6分です。</p></div>"
        if page_index == 0
        else ""
    )
    return (
        f'{opening}<div class="hz-intro">'
        f'<p>{page_index + 1} / {page_count} ページ</p>'
        f'<h2>{escape(axis["a"]["short"])}か、{escape(axis["b"]["short"])}か</h2>'
        "<p>理想ではなく、いまの実態に近いほうを選んでください。円が大きいほど、その傾向が強いことを表します。</p>"
        "</div>"
    )


def question_head(question: dict[str, Any], is_missing: bool) -> str:
    missing = '<em class="hz-q__missing">未回答</em>' if is_missing else ""
    return (
        f'<div class="hz-q{" is-missing" if is_missing else ""}">'
        f'<div class="hz-q__head"><span>{question["id"]}</span>'
        f'<h3>{escape(question["theme"])}</h3>{missing}</div>'
        f'<div class="hz-q__poles"><p class="is-a">{escape(question["a"])}</p>'
        f'<p class="is-b">{escape(question["b"])}</p></div></div>'
    )


def validation_alert(missing_ids: list[str]) -> str:
    return (
        f'<div class="hz-alert" role="alert">未回答が{len(missing_ids)}問あります（{"、".join(missing_ids)}）。'
        "すべて回答すると次へ進めます。</div>"
    )


def scroll_script(selector: str, nonce: str) -> str:
    """Streamlit は再描画でスクロール位置を戻さないため、ページ切替時だけ移動する。"""
    return (
        "<script>(function(){"
        f"/* {nonce} */"
        f'var target=document.querySelector("{selector}");'
        'var main=document.querySelector(\'[data-testid="stMain"]\');'
        'var calm=matchMedia("(prefers-reduced-motion: reduce)").matches;'
        'if(target){target.scrollIntoView({block:"center",behavior:calm?"auto":"smooth"});}'
        "else if(main){main.scrollTo(0,0);}"
        "window.scrollTo(0,0);"
        "})();</script>"
    )
# ===== [BLOCK: QUIZ_PARTS] END =====


# ===== [BLOCK: RESULT_PARTS] START =====
def result_hero(diagnosis: dict[str, Any]) -> str:
    type_data = diagnosis["type"]
    cells = "".join(
        f'<div class="side-{axis["side"]}"><b>{axis["code"]}</b><span>{escape(axis[axis["side"]]["short"])}</span></div>'
        for axis in diagnosis["axes"]
    )
    return (
        f'<div class="hz-result">{logo("hz-logo hz-logo--small")}'
        f'<p class="hz-result__group">{escape(type_data["group"])}</p>'
        f'<div class="hz-code" aria-label="{type_data["code"]}型">{cells}<div class="hz-code__suffix"><b>型</b></div></div>'
        f'<h1>{escape(type_data["name"])}</h1>'
        f'<p class="hz-result__lede">{escape(type_data["feature"])}</p>'
        "</div>"
    )


def result_body(diagnosis: dict[str, Any]) -> str:
    type_data = diagnosis["type"]
    return (
        f'<section class="hz-block"><h2>組織の骨格図</h2>{spine(diagnosis["axes"])}'
        '<p class="hz-spine__note">中央の目盛りが判定の境目です。30点以下で左側、31点以上で右側のタイプになります。</p></section>'
        '<div class="hz-pair">'
        f'<section><h2>組織の強み</h2><p>{escape(type_data["strength"])}</p></section>'
        f'<section><h2>組織の弱み</h2><p>{escape(type_data["weakness"])}</p></section>'
        "</div>"
    )


def result_next(diagnosis: dict[str, Any]) -> str:
    return (
        "<h2>改善に向けたポイント</h2>"
        f'<p>{escape(diagnosis["type"]["improvement"])}</p>'
        '<p class="hz-next__note">60分の無料ご相談で、自社では何から着手するかを一緒に整理します。日程は予約ページからお選びいただけます。</p>'
    )


def email_sent(address: str) -> str:
    return f'<p class="hz-next__done" role="status">{escape(address)} に診断結果を送信しました。</p>'

# ===== [BLOCK: RESULT_PARTS] END =====
