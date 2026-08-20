"""リライト：同じ内容を別の文体・長さ・読者向けに書き換える。"""

import streamlit as st

import config
from core import ui
from core.prompt import data_block

FEATURE = "リライト"

GOALS = {
    "もっと丁寧に": "より丁寧で礼儀正しい表現にする。相手への配慮を加える。",
    "もっとカジュアルに": "肩の力を抜いた、話しかけるような文章にする。",
    "もっと簡潔に": "意味を保ったまま、無駄を削ってできるだけ短くする。",
    "もっと詳しく": "説明や具体例を補い、内容を厚くする。",
    "専門的・硬い文章に": "専門用語を適切に使い、論理的で格式のある文章にする。",
    "やさしく噛み砕く": "専門用語を避け、中学生でも分かる言葉で説明し直す。",
    "説得力を上げる": "主張→根拠→具体例→結論の流れを整え、読み手を動かす文章にする。",
    "感情を込める": "書き手の思いが伝わる、熱のある文章にする。",
    "箇条書きに整理する": "内容を構造化し、見出しと箇条書きで一目で分かる形にする。",
    "文章化する": "箇条書きやメモを、つながりのある文章に組み立てる。",
}


def _prompt(text: str, goal: str, tone: str, audience: str, length: str, notes: str, variants: int) -> str:
    variant_rule = (
        f"方向性の異なる案を{variants}つ出し、それぞれ「### 案1」のような見出しを付け、"
        "見出しの直後に一行でその案の狙いを書く。"
        if variants > 1
        else "案は1つだけ出す。前置きや解説は書かない。"
    )
    return f"""次の文章をリライトしてください。

# リライトの目的
{GOALS[goal]}

# 条件
- トーン: {tone}
- 想定読者: {audience}
- 長さ: {length}
- その他の要望: {notes or '特になし'}

# 出力ルール
- {variant_rule}
- 元の文章の意味・事実を変えない。情報を勝手に足さない。

# 元の文章
{data_block(text, "元の文章")}"""


def render() -> None:
    ui.page_header("🔄", "リライト・文体変換", "同じ内容を、別の言い方・長さ・読者向けに書き換えます。")

    text = ui.source_text_input(
        "書き換えたい文章 **必須**",
        key="rw_src",
        height=260,
        placeholder="ここに元の文章を貼り付けてください。",
    )

    col1, col2 = st.columns(2)
    goal = col1.selectbox("リライトの目的", list(GOALS.keys()))
    audience = col2.selectbox("想定読者", config.AUDIENCES)

    col3, col4, col5 = st.columns(3)
    tone = col3.selectbox("トーン", config.TONES)
    length = col4.selectbox(
        "長さ", ["元の文章と同じくらい", "半分程度に短く", "1.5〜2倍に長く", "指定なし"]
    )
    variants = col5.number_input("出す案の数", min_value=1, max_value=5, value=1)

    notes = st.text_input("追加の要望（任意）", placeholder="例）語尾を統一して / 数字は残して")

    if st.button("リライトする", type="primary", use_container_width=True):
        if ui.require_input(text, "書き換えたい文章を入力してください。"):
            ui.generate(
                "rw_result",
                feature=FEATURE,
                title=f"{goal}：{text[:30]}…",
                prompt=_prompt(text, goal, tone, audience, length, notes, int(variants)),
            )

    ui.show_result("rw_result", filename_stem="rewrite")
