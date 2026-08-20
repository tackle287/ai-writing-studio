"""文章の要約。"""

import streamlit as st

from core import ui
from core.prompt import data_block

FEATURE = "要約"

FORMATS = {
    "3行まとめ": "最も重要な点だけを3行にまとめる。1行は50文字以内。",
    "箇条書き": "階層のない箇条書きで、要点を5〜8個。各項目は1文。",
    "見出し付きサマリー": "内容の塊ごとに ## 見出しを立て、その下に2〜4行で要約する。",
    "議事録スタイル": "「決定事項」「議論の要点」「宿題・ToDo（担当と期限つき）」の3セクションに整理する。",
    "エグゼクティブサマリー": "結論を最初に述べ、根拠、数値、示唆、推奨アクションの順で構成する。",
    "1文で要約": "全体をたった1文（80文字以内）で言い切る。",
}


def _prompt(text: str, fmt: str, focus: str, keep_terms: bool, add_keywords: bool) -> str:
    extras = []
    if keep_terms:
        extras.append("- 原文の固有名詞・専門用語・数値は言い換えずそのまま残す。")
    if add_keywords:
        extras.append("- 要約の最後に「キーワード: 」として重要語を5個ほど並べる。")

    return f"""次の文章を要約してください。

# 要約の形式
{FORMATS[fmt]}

# 特に注目してほしい観点
{focus or '特になし（全体をバランスよく）'}

# ルール
- 原文にない情報を足さない。推測を事実のように書かない。
- 原文の主張と立場を変えない。
{chr(10).join(extras)}

# 原文
{data_block(text, "原文")}"""


def render() -> None:
    ui.page_header("📄", "文章要約", "長文・資料・議事録を、目的に合わせた形にまとめ直します。")

    text = ui.source_text_input(
        "要約したい文章 **必須**",
        key="sum_src",
        height=300,
        placeholder="記事、議事録、レポートなどを貼り付けてください。PDFの読み込みにも対応しています。",
    )

    col1, col2 = st.columns(2)
    fmt = col1.selectbox("要約の形式", list(FORMATS.keys()))
    focus = col2.text_input("注目する観点（任意）", placeholder="例）コストと納期に関する部分")

    col3, col4 = st.columns(2)
    keep_terms = col3.checkbox("専門用語・数値をそのまま残す", value=True)
    add_keywords = col4.checkbox("キーワードを抽出する", value=False)

    if st.button("要約する", type="primary", use_container_width=True):
        if ui.require_input(text, "要約したい文章を入力してください。"):
            ui.generate(
                "sum_result",
                feature=FEATURE,
                title=f"{fmt}：{text[:30]}…",
                prompt=_prompt(text, fmt, focus, keep_terms, add_keywords),
            )

    ui.show_result("sum_result", filename_stem="summary")
